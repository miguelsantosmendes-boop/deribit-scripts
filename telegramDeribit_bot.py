from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, CommandHandler, filters

import Desmontagem_bot
import Montagem_bot

TOKEN = "8166949900:AAGOd_JdUaxvsyBmhBgtNkgnQJrmmsQSztM"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Comandos disponíveis:\n"
        "/desmontagem_bot\n"
    )

async def desmontagem_bot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    #await update.message.reply_text("Rodando o script Desmontagem Bot")
    
    resultado = Desmontagem_bot.run()
    await update.message.reply_text(resultado, parse_mode="HTML")
    
async def montagem_bot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    #await update.message.reply_text("Rodando o script Desmontagem Bot")
    
    resultado = Montagem_bot.run()
    await update.message.reply_text(resultado, parse_mode="HTML")

def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("desmontagem_bot", desmontagem_bot))
    app.add_handler(CommandHandler("montagem_bot", montagem_bot))

    app.run_polling()

if __name__ == "__main__":
    main()

