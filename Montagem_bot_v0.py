import requests
import time
from datetime import datetime, timezone

# =========================
# CONFIGURAÇÕES
# =========================
PUT_VENDIDA = "BTC-30JAN26-84000-P"
PUT_COMPRADA = "BTC-30JAN26-80000-P"

TARGET_SPREAD = 0.25  # % DO SPREAD
INTERVALO = 60  # segundos entre leituras

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



# =========================
# FUNÇÃO PARA LER ORDER BOOK
# =========================
def get_best_prices(instrument):
    url = "https://www.deribit.com/api/v2/public/get_order_book"
    params = {
        "instrument_name": instrument,
        "depth": 1
    }
    response = requests.get(url, params=params).json()
    bids = response["result"]["bids"]
    asks = response["result"]["asks"]

    best_bid = bids[0][0] if bids else None
    best_ask = asks[0][0] if asks else None

    return best_bid, best_ask

# =========================
# LOOP PRINCIPAL
# =========================
print("🔄 Robô iniciado. Monitorando spread para Montagem de BULL PUT SPREAD...\n")

while True:
    try:
        putvendida_bid, putvendida_ask = get_best_prices(PUT_VENDIDA)
        putcomprada_bid, putcomprada_ask = get_best_prices(PUT_COMPRADA)

        #Buscar o strike das opcoes
        partsVendida = PUT_VENDIDA.split("-")
        strikeVendida = float(partsVendida[2])
        partsComprada = PUT_COMPRADA.split("-")
        strikeComprada = float(partsComprada[2])

        #calculo do Spread dos Strikes
        spreadOpcoes = strikeVendida - strikeComprada

        # Requisição para pegar o ticker do BTC-PERPETUAL e preco do BTC
        response = requests.get("https://www.deribit.com/api/v2/public/ticker?instrument_name=BTC-PERPETUAL")
        dadosBTC = response.json()

        if 'result' in dadosBTC:
            last_priceBTC = dadosBTC['result']['last_price']

        # CALCULO DO PRECO EM BTC DO SPREAD A SER VENDIDO NA BULL PUT SPREAD
        valorPremio = spreadOpcoes * TARGET_SPREAD
        valorPremio = valorPremio / last_priceBTC


        if putvendida_bid and putvendida_ask and putcomprada_bid and putcomprada_ask:
            spreadMontagem = putvendida_bid - putcomprada_ask
            spreadDesmontagem = putvendida_ask - putcomprada_bid
            
            current_time = datetime.fromtimestamp((datetime.now(timezone.utc).timestamp()))  # Timestamp atual
            print(f"========================================================= {current_time}")
            print(f"\033[31mVENDER: {PUT_VENDIDA}\033[0m e \033[34mCOMPRAR: {PUT_COMPRADA}\033[0m")
            print(f"Preco BTC: {last_priceBTC}")
            print(f"Risco Total: {spreadOpcoes}")
            print(f"Spread Montagem Atual: {spreadMontagem:.5f} BTC")
#            print(f"{PUT_VENDIDA} {putvendida_bid:.5f} x {putvendida_ask:.5f} BTC")
#            print(f"Spread Desmontagem Atual: {spreadDesmontagem:.5f} BTC")
#            print(f"{PUT_COMPRADA} {putcomprada_bid:.5f} x {putcomprada_ask:.5f} BTC")  

            if spreadMontagem >= valorPremio:
                print("\033[33mSPREAD ALVO ATINGIDO PARA MONTAGEM!\033[0m")
                print("👉 Aqui entraria a lógica de trade")
                
                send_telegram_alert(f"VENDER: {PUT_VENDIDA}\nCOMPRAR: {PUT_COMPRADA}\n\nPreco BTC: {last_priceBTC}\nSpread de Desmontagem ATUAL: {spreadDesmontagem:.4f}\nLimite Minimo Definido: {valorPremio:.4f}\n\nRESULTADO: Spread de MONTAGEM atingiu o spread de montagem minimo")
                break
            else:
                print(f"\033[33mSpread de Montagem inferior ao limite definido: {valorPremio:.3f} BTC\033[0m")
                #print("\033[31mTexto vermelho\033[0m")
                #print("\033[32mTexto verde\033[0m")
                #print("\033[33mTexto amarelo\033[0m")
                #print("\033[34mTexto azul\033[0m")

        else:
            print("⚠️ Sem liquidez suficiente/n")

        time.sleep(INTERVALO)

    except Exception as e:
        print("Erro:", e)
        time.sleep(INTERVALO)
