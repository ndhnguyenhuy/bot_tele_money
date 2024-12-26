from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
import os
import json

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Xin chào! Tôi là bot của bạn.")

def create_app():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    return app

async def handler(request):
    if request.method == "POST":
        update = Update.de_json(await request.json(), create_app().bot)
        await create_app().process_update(update)
        return "OK"
    else:
        return "Hello, this is your Telegram bot."

if __name__ == "__main__":
    app = create_app()
    app.run_polling()

