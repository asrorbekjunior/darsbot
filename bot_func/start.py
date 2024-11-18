from telegram import Update
from telegram.ext import ContextTypes


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        f"Salom {update.message.from_user.first_name}!",
        parse_mode='HTML'
    )
