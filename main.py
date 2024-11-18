import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
from bot_func.start import start
from bot_func.get_info_in_yfinanse import start_info_command, start_info
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from bot_func.info import bot_info
from bot_func.get_info_in_yfinanse import ask_time_range, send_excel_file


TOKEN = '7826848821:AAH0cGGoGmrkC43OyP5kfZcKJeDZUq5RfBk'



def main() -> None:
    application = Application.builder().token(TOKEN).post_init(bot_info).build()
    scheduler = AsyncIOScheduler(timezone="Asia/Tashkent")
    
    # Schedule the start_info function to run at 19:00 daily
    scheduler.add_job(start_info, 'cron', hour=7, args=[application])  # Pass context

    scheduler.start()

    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('start_info', start_info_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, ask_time_range))
    application.add_handler(CallbackQueryHandler(send_excel_file))
    application.run_polling()

if __name__ == "__main__":
    main()
