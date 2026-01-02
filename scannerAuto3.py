import requests
import pandas as pd
import time
from datetime import datetime, timezone

BASE_URL = "https://www.deribit.com/api/v2"
TELEGRAM_TOKEN = "8166949900:AAGOd_JdUaxvsyBmhBgtNkgnQJrmmsQSztM"  # Substitua pelo seu token do Bot
TELEGRAM_CHAT_ID = "742019027"  # Substitua pelo seu ID de chat

# Função para enviar alerta via Telegram
def send_telegram_alert(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    }
    print(f"Enviando mensagem para Telegram: {message}")  # Adicionando log de envio
    response = requests.post(url, data=payload)
    
    if response.status_code != 200:
        print(f"Erro ao enviar mensagem para o Telegram: {response.text}")
    else:
        print("Mensagem enviada com sucesso!")


# Função para pegar todas as opções ativas
def get_options(currency="BTC", kind="option"):
    r = requests.get(f"{BASE_URL}/public/get_instruments",
                     params={"currency": currency, "kind": kind})
    data = r.json()
    
    if "result" not in data:
        print("Erro na API:", data)
        return pd.DataFrame()
    
    return pd.DataFrame(data["result"])

# Função para pegar o ticker de uma opção específica
def get_ticker(instrument):
    r = requests.get(f"{BASE_URL}/public/ticker",
                     params={"instrument_name": instrument})
    return r.json().get("result", {})

# Pegar a cotação atual do BTC
def get_btc_price():
    r = requests.get(f"{BASE_URL}/public/get_index_price", params={"index_name": "btc_usd"})
    data = r.json()
    return data["result"]["index_price"]

# Função para calcular o DTE (dias até o vencimento)
def calculate_dte(expiration_timestamp):
    current_time = int(datetime.now(timezone.utc).timestamp())  # Timestamp atual
    dte = (expiration_timestamp / 1000) - current_time  # DTE em segundos
    dte_days = dte / (60 * 60 * 24)  # Converte para dias
    return int(dte_days)  # Retorna como inteiro (número de dias)

# Função para filtrar opções pelo prazo de vencimento (DTE) entre min_dte e max_dte
def get_options_by_dte(min_dte=20, max_dte=45, option_type="put"):
    options = get_options()  # Pega todas as opções disponíveis
    options_filtered = []
    
    for _, opt in options.iterrows():
        dte = calculate_dte(opt["expiration_timestamp"])
        if min_dte <= dte <= max_dte and opt["option_type"] == option_type:
            opt["dte"] = dte  # Adiciona a coluna de DTE (dias até o vencimento)
            options_filtered.append(opt)
    
    return pd.DataFrame(options_filtered)

# Função principal do scanner de spreads
def scanner_spreads(delta_sell, option_type="put", min_dte=20, max_dte=45, ratio_threshold=0.3):
    # Pega a cotação do BTC
    btc_price = get_btc_price()
    
    # Pega as opções dentro do intervalo de DTE entre min_dte e max_dte
    options = get_options_by_dte(min_dte=min_dte, max_dte=max_dte, option_type=option_type)
    
    print(f"Total de opções encontradas: {len(options)}")  # Verifique quantas opções foram encontradas

    # Dicionário para armazenar os spreads por vencimento
    all_spreads = {}

    # Para cada vencimento, crie uma tabela de spreads
    vencimentos = options["expiration_timestamp"].unique()
    print(f"Vencimentos encontrados: {vencimentos}")  # Verifique os vencimentos encontrados
    for vencimento in vencimentos:
        vencientoEmDTE = calculate_dte(vencimento)
        print(f"Buscando spreads para o vencimento em {vencientoEmDTE} dias...")

        # Filtra as opções para esse vencimento específico
        vencimento_options = options[options["expiration_timestamp"] == vencimento]
        
        # Selecionar opções de venda (vendendo uma opção com delta aproximado de delta_sell)
        sell_options = []
        for _, opt in vencimento_options.iterrows():
            ticker = get_ticker(opt["instrument_name"])
            delta = abs(ticker.get("greeks", {}).get("delta", 0))  # Proteção contra erro de falta de dados
            if delta >= delta_sell - 0.02 and delta <= delta_sell + 0.02:  # Faixa de delta +/- 0.02
                sell_options.append({
                    "instrument": opt["instrument_name"],
                    "strike": opt["strike"],
                    "delta": delta,
                    "price": ticker["best_bid_price"],
                    "expiration_timestamp": opt["expiration_timestamp"],
                    "dte": opt["dte"]  # Inclui o DTE para exibição
                })
        
        print(f"Opções de venda encontradas para o vencimento em {vencientoEmDTE} dias: {len(sell_options)}")  # Verifique as vendas encontradas

        # Selecionar opções de compra (com delta inferior ao da opção de venda)
        buy_options = []
        for _, opt in vencimento_options.iterrows():
            ticker = get_ticker(opt["instrument_name"])
            delta = abs(ticker.get("greeks", {}).get("delta", 0))
            if delta < delta_sell:  # Só compra com delta menor que o vendido
                buy_options.append({
                    "instrument": opt["instrument_name"],
                    "strike": opt["strike"],
                    "delta": delta,
                    "price": ticker["best_ask_price"],
                    "expiration_timestamp": opt["expiration_timestamp"],
                    "dte": opt["dte"]  # Inclui o DTE para exibição
                })
        
        print(f"Opções de compra encontradas para o vencimento em {vencientoEmDTE} dias: {len(buy_options)}")  # Verifique as compras encontradas

        # Gerar spreads e calcular o risco/premio
        spreads = []
        for s in sell_options:
            for b in buy_options:
                if b["strike"] < s["strike"]:  # Condição de um spread de put típico
                    credito_btc = s["price"] - b["price"]  # Crédito em BTC
                    risco_max = s["strike"] - b["strike"]  # Risco máximo em BTC
                    if risco_max > 0:
                        # Transformar o crédito em USD
                        credito_usd = credito_btc * btc_price
                        # Calcular a relação risco/premio
                        ratio = credito_usd / risco_max
                        #print(f"Calculando ratio para o spread {s['instrument']} / {b['instrument']}: {ratio}")  # Verifique o ratio calculado
                        spreads.append({
                            "sell": s["instrument"],
                            "buy": b["instrument"],
                            "credito_btc": credito_btc,
                            "credito_usd": credito_usd,
                            "risco_max": risco_max,
                            "ratio": ratio,
                            "sell_expiration": s["expiration_timestamp"],
                            "buy_expiration": b["expiration_timestamp"],
                            "sell_dte": s["dte"],  # Exibe o DTE da opção de venda
                            "buy_dte": b["dte"]  # Exibe o DTE da opção de compra
                        })

        
        print(f"Total de spreads encontrados para o vencimento em {vencientoEmDTE} dias: {len(spreads)}")  # Verifique o total de spreads encontrados

        # Adiciona a tabela de spreads para esse vencimento
        df_spreads = pd.DataFrame(spreads)
        if not df_spreads.empty:
            all_spreads[vencimento] = df_spreads.sort_values("ratio", ascending=False)

        # Verificando o alerta para ratio
        for index, row in df_spreads.iterrows():
            #print(f"Verificando ratio: {row['ratio']}")  # Adiciona um print para ver o ratio
            if row["ratio"] >= ratio_threshold:
                alert_message = f"ALERTA: Spread encontrado com ratio de {row['ratio']:.2f}! VENDER: {row['sell']} COMPRAR: {row['buy']}"
                #print(f"Alerta disparado: {alert_message}")  # Confirma se o alerta foi disparado
                send_telegram_alert(alert_message)

    return all_spreads


# Função para rodar o scanner a cada 5 minutos
def run_scanner(min_dte, max_dte, ratio_threshold):
    delta_sell = 0.25  # Delta da opção vendida
    
    while True:
        print(f"Rodando scanner para delta de venda {delta_sell}, vencimentos entre {min_dte} e {max_dte} dias...")
        
        all_spreads = scanner_spreads(delta_sell, option_type="put", min_dte=min_dte, max_dte=max_dte, ratio_threshold=ratio_threshold)
        
        if not all_spreads:
            print("Nenhum spread encontrado")
        else:
            for vencimento, df_spreads in all_spreads.items():
                print(f"Top spreads para o vencimento (DTE {df_spreads['sell_dte'].iloc[0]}):")
                print(df_spreads[["sell", "buy", "credito_usd", "risco_max", "ratio", "sell_dte", "buy_dte"]].head(10))

        # Aguardar 15 minutos antes de rodar novamente
        time.sleep(900)  # 300 segundos = 5 minutos

# Inicia o scanner
if __name__ == "__main__":
    run_scanner(min_dte=20, max_dte=45, ratio_threshold=0.33)
