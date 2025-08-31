
import requests
import json
import os
import time
from datetime import datetime


# Webhook do Discord
DISCORD_WEBHOOK = "https://discord.com/api/webhooks/1411808916316098571/m_qTenLaTMvyf2e1xNklxFP2PVIvrVD328TFyofY1ciCUlFdWetiC-y4OIGLV23sW9vM"

# Endereço da carteira Hyperliquid
wallet_address = "0x08183aa09eF03Cf8475D909F507606F5044cBdAB"

# Arquivo para armazenar o último trade
last_trade_file = "last_trade.json"

def get_latest_user_trade(wallet):
    url = "https://api.hyperliquid.xyz/info"
    payload = {
        "type": "userFills",
        "user": wallet
    }
    response = requests.post(url, json=payload)
    if response.status_code == 200:
        data = response.json()
        if data:
            return data[26]
        else:
            print("Nenhuma movimentação encontrada.")
            return None
    else:
        print(f"Erro: {response.status_code}")
        print(response.text)
        return None

def get_account_value(wallet):
    url = "https://api.hyperliquid.xyz/info"
    payload = {
        "type": "clearinghouseState",
        "user": wallet
    }
    response = requests.post(url, json=payload)
    if response.status_code == 200:
        data = response.json()
        try:
            return float(data["marginSummary"]["accountValue"])
        except (KeyError, ValueError):
            print("⚠️ Campo accountValue não encontrado ou inválido.")
            return 0.0
    else:
        print(f"Erro ao buscar valor da conta: {response.status_code}")
        print(response.text)
        return 0.0

def notify_discord(message):
    if not DISCORD_WEBHOOK:
        print("❌ Webhook do Discord não configurado.")
        return
    data = {"content": message}
    response = requests.post(DISCORD_WEBHOOK, json=data)
    if response.status_code == 204:
        print("✅ Notificação enviada com sucesso!")
    else:
        print(f"❌ Erro ao enviar notificação: {response.status_code}")
        print(response.text)

def load_last_trade():
    if os.path.exists(last_trade_file):
        with open(last_trade_file, "r") as f:
            return json.load(f)
    return {}

def save_last_trade(trade):
    with open(last_trade_file, "w") as f:
        json.dump(trade, f)

def verificar_novos_trades():
    latest_fill = get_latest_user_trade(wallet_address)

    if latest_fill:
        operacao = latest_fill.get("dir", "Desconhecido")
        ativo = latest_fill.get("coin", "N/A")
        quantidade = latest_fill.get("sz", 0)
        preco = latest_fill.get("px", 0)

        pnl_raw = latest_fill.get("closedPnl", "0.0")
        try:
            pnl = float(pnl_raw)
        except ValueError:
            pnl = 0.0

        timestamp = latest_fill.get("time", 0)
        data_hora = datetime.fromtimestamp(timestamp / 1000).strftime("%d/%m/%Y %H:%M:%S")

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
            account_value = get_account_value(wallet_address)
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
            print("📭 Nenhuma nova movimentação detectada.")
    else:
        print("🔁 Nenhum dado de trade retornado.")

# Loop contínuo para manter o script ativo
if __name__ == "__main__":
    while True:
        try:
            verificar_novos_trades()
        except Exception as e:
            print(f"❌ Erro inesperado: {e}")
        time.sleep(60)  # Espera 60 segundos antes de verificar novamente
