import requests
import json

# Endereço da carteira Hyperliquid
wallet_address = "0x08183aa09eF03Cf8475D909F507606F5044cBdAB"

def get_full_account_state(wallet):
    url = "https://api.hyperliquid.xyz/info"
    payload = {
        "type": "clearinghouseState",
        "user": wallet
    }

    response = requests.post(url, json=payload)
    if response.status_code == 200:
        data = response.json()
        print(json.dumps(data, indent=4))  # Exibe todos os dados formatados
    else:
        print(f"Erro ao buscar dados da conta: {response.status_code}")
        print(response.text)

# Executa a função
get_full_account_state(wallet_address)
