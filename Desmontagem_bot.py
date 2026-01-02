import requests
import time
from datetime import datetime, timezone

# =========================
# CONFIGURAÇÕES
# =========================
PUT_VENDIDA = "BTC-30JAN26-82000-P"
PUT_COMPRADA = "BTC-30JAN26-75000-P"

PREMIO_RECEBIDO = 0.013 #em BTC
TARGET_SPREAD = 0.5  #vender quando a desmontagem chegar a 50% do premio recebido
INTERVALO = 60  # segundos entre leituras

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

def run():
    # =========================
    # LOOP PRINCIPAL
    # =========================
    print("🔄 Robô iniciado. Monitorando spread para DESMONTAGEM de BULL PUT SPREAD...\n")
    print(f"\033[34mCOMPRAR: {PUT_VENDIDA}\033[0m e \033[31mVENDER: {PUT_COMPRADA}\033[0m\n")

    #while True:
    #    try:
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
            print(f"Preco BTC: {last_priceBTC}")
            print(f"Risco Total: {spreadOpcoes}")
    #            print(f"Spread Montagem Atual: {spreadMontagem:.5f} BTC")
    #            print(f"{PUT_VENDIDA} {putvendida_bid:.5f} x {putvendida_ask:.5f} BTC")
            print(f"Spread Desmontagem Atual: {spreadDesmontagem:.5f} BTC")
    #            print(f"{PUT_COMPRADA} {putcomprada_bid:.5f} x {putcomprada_ask:.5f} BTC")  
            
            print(f"Premio Recebido: {PREMIO_RECEBIDO}")
            
            limiteDesmontagem = PREMIO_RECEBIDO * TARGET_SPREAD

            if spreadDesmontagem <= limiteDesmontagem:
                print("\033[33mSPREAD ALVO ATINGIDO PARA DESMONTAGEM!\033[0m")
                print("👉 Aqui entraria a lógica de trade para desmontar")
                
                return f"COMPRAR: {PUT_VENDIDA}\nVENDER: {PUT_COMPRADA}\n\nPreco BTC: {last_priceBTC}\nSpread de Desmontagem ATUAL: {spreadDesmontagem:.4f}\nLimite Minimo Definido: {limiteDesmontagem:.4f}\n\n<b>RESULTADO: Desmontar Estrutura</b>"
            else:
                print(f"\033[33mSpread de Desmontagem SUPERIOR ao Limite Minimo Definido: {limiteDesmontagem:.4f} BTC\033[0m")
                return f"COMPRAR: {PUT_VENDIDA}\nVENDER: {PUT_COMPRADA}\n\nPreco BTC: {last_priceBTC}\nSpread de Desmontagem ATUAL: {spreadDesmontagem:.4f}\nLimite Minimo Definido: {limiteDesmontagem:.4f}\n\n<b>RESULTADO: Spread de Desmontagem SUPERIOR ao Limite Minimo Definido</b>"

        else:
            print("⚠️ Sem liquidez suficiente/n")
            return "Sem liquidez suficiente"
