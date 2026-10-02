import os
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import Application, CommandHandler, ContextTypes

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")

WEB_APP_URL = "https://areltrg01.github.io/rasmm/"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [
            InlineKeyboardButton(
                "🚀 RA SMM'yi Aç",
                web_app=WebAppInfo(url=WEB_APP_URL)
            )
        ]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "🔥 RA SMM\n\n"
        "Sosyal medya hizmetlerine ulaşmak için aşağıdaki butona tıklayın.",
        reply_markup=reply_markup
    )

def main():
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN bulunamadı.")

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))

    print("RA SMM Bot çalışıyor...")
    app.run_polling()

if __name__ == "__main__":
    main()
