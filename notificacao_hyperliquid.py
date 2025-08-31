import requests
import json
import os
import time
from datetime import datetime
from tempfile import NamedTemporaryFile

print("✅ Imports concluídos", flush=True)

# Config (use variáveis de ambiente no Render)
DISCORD_WEBHOOK = os.getenv("DISCORD_WEBHOOK", "https://discord.com/api/webhooks/1411808916316098571/m_qTenLaTMvyf2e1xNklxFP2PVIvrVD328TFyofY1ciCUlFdWetiC-y4OIGLV23sW9vM")
WALLET_ADDRESS = os.getenv("WALLET_ADDRESS", "0x08183aa09eF03Cf8475D909F507606F5044cBdAB")
LAST_TRADE_FILE = os.getenv("LAST_TRADE_FILE", "/tmp/last_trade.json")

# HTTP session com retry e timeout
SESSION = requests.Session()
ADAPTER = requests.adapters.HTTPAdapter(max_retries=3)
SESSION.mount("https://", ADAPTER)
SESSION.mount("http://", ADAPTER)

HTTP_TIMEOUT = 10  # segundos

BASE_URL = "https://api.hyperliquid.xyz/info"

def http_post_json(url, payload, timeout=HTTP_TIMEOUT):
    try:
        resp = SESSION.post(url, json=payload, timeout=timeout)
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.RequestException as e:
        print(f"❌ HTTP error: {e}", flush=True)
        return None
    except json.JSONDecodeError as e:
        print(f"❌ JSON decode error: {e}", flush=True)
        return None

def get_latest_user_trade(wallet):
    print("🔍 Buscando último trade...", flush=True)
    data = http_post_json(BASE_URL, {"type": "userFills", "user": wallet})
    if data is None:
        return None
    if isinstance(data, list) and data:
        print("✅ Último trade encontrado", flush=True)
        return data[0]
    print("📭 Nenhuma movimentação encontrada.", flush=True)
    return None

def get_account_value(wallet):
    print("💰 Buscando valor da conta...", flush=True)
    data = http_post_json(BASE_URL, {"type": "clearinghouseState", "user": wallet})
    if not data:
        print("⚠️ Resposta vazia em clearinghouseState.", flush=True)
        return 0.0
    try:
        return float(data["marginSummary"]["accountValue"])
    except (KeyError, ValueError, TypeError):
        print("⚠️ Campo accountValue não encontrado ou inválido.", flush=True)
        return 0.0

def notify_discord(message):
    print("📤 Enviando notificação para o Discord...", flush=True)
    if not DISCORD_WEBHOOK or "discord.com/api/webhooks" not in DISCORD_WEBHOOK:
        print("❌ Webhook do Discord não configurado corretamente.", flush=True)
        return
    try:
        resp = SESSION.post(DISCORD_WEBHOOK, json={"content": message}, timeout=HTTP_TIMEOUT)
        if resp.status_code in (200, 204):
            print("✅ Notificação enviada com sucesso!", flush=True)
        else:
            print(f"❌ Erro ao enviar notificação: {resp.status_code} - {resp.text}", flush=True)
    except requests.exceptions.RequestException as e:
        print(f"❌ Erro ao enviar ao Discord: {e}", flush=True)

def load_last_trade():
    """Lê o JSON de forma resiliente (ignora JSON corrompido)."""
    try:
        if os.path.exists(LAST_TRADE_FILE):
            with open(LAST_TRADE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
    except json.JSONDecodeError:
        print("⚠️ last_trade.json corrompido. Ignorando e seguindo em frente.", flush=True)
    except Exception as e:
        print(f"⚠️ Erro ao ler {LAST_TRADE_FILE}: {e}", flush=True)
    return {}

def save_last_trade(trade):
    """Gravação atômica para evitar arquivos corrompidos."""
    os.makedirs(os.path.dirname(LAST_TRADE_FILE), exist_ok=True)
    try:
        with NamedTemporaryFile("w", delete=False, dir=os.path.dirname(LAST_TRADE_FILE), encoding="utf-8") as tf:
            json.dump(trade, tf)
            temp_name = tf.name
        os.replace(temp_name, LAST_TRADE_FILE)
        print(f"💾 Estado salvo em {LAST_TRADE_FILE}", flush=True)
    except Exception as e:
        print(f"❌ Erro ao salvar {LAST_TRADE_FILE}: {e}", flush=True)
        # Tenta remover o tmp se sobrou
        try:
            if 'temp_name' in locals() and os.path.exists(temp_name):
                os.remove(temp_name)
        except Exception:
            pass

def verificar_novos_trades():
    latest_fill = get_latest_user_trade(WALLET_ADDRESS)

    if latest_fill:
        operacao = latest_fill.get("dir", "Desconhecido")
        ativo = latest_fill.get("coin", "N/A")
        quantidade = latest_fill.get("sz", 0)
        preco = latest_fill.get("px", 0)

        pnl_raw = latest_fill.get("closedPnl", "0.0")
        try:
            pnl = float(pnl_raw)
        except (ValueError, TypeError):
            pnl = 0.0

        timestamp = latest_fill.get("time", 0)
        data_hora = datetime.fromtimestamp((timestamp or 0) / 1000).strftime("%d/%m/%Y %H:%M:%S")

        current_trade_summary = {
            "coin": ativo,
            "dir": operacao,
            "sz": quantidade,
            "px": preco,
            "closedPnl": pnl,
            "time": timestamp
        }

        last_trade_summary = load_last_trade()

        if current_trade_summary != last_trade_summary:
            account_value = get_account_value(WALLET_ADDRESS)
            msg = (
                "-----------------------------------------------\n"
                "📢 **Nova Operação:**\n"
                f"📊 Tipo: {operacao}\n"
                f"📈 PnL: {pnl:.2f} USDC\n"
                f"💼 Valor da Conta: {account_value:.2f} USDC\n"
                f"💵 Preço: {preco}\n"
                f"💰 Quantidade: {quantidade}\n"
                f"🦉 Ativo: {ativo}\n"
                f"📆 Data/Hora: {data_hora}\n"
                "-----------------------------------------------"
            )
            notify_discord(msg)
            save_last_trade(current_trade_summary)
        else:
            print("📭 Nenhuma nova movimentação detectada.", flush=True)
    else:
        print("🔁 Nenhum dado de trade retornado.", flush=True)

if __name__ == "__main__":
    print("🚀 Script iniciado com sucesso!", flush=True)
    print(f"🗂️ Usando LAST_TRADE_FILE = {LAST_TRADE_FILE}", flush=True)
    while True:
        try:
            verificar_novos_trades()
        except Exception as e:
            print(f"❌ Erro inesperado: {e}", flush=True)
        time.sleep(60)
