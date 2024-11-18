import logging
from datetime import time as dt_time
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
from bot_func.start import start
from bot_func.get_info_in_yfinanse import start_info_command, start_info
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from bot_func.info import bot_info
from bot_func.get_info_in_yfinanse import ask_time_range, send_excel_file, daily_task


TOKEN = '7826848821:AAH0cGGoGmrkC43OyP5kfZcKJeDZUq5RfBk'



def main() -> None:
    application = Application.builder().token(TOKEN).post_init(bot_info).build()
    scheduler = AsyncIOScheduler(timezone="Asia/Tashkent")
    
    # Har kuni 7:00 da ishga tushiriladigan vazifa
    job_queue = application.job_queue
    job_queue.run_daily(daily_task, time=dt_time(hour=6, minute=0))

    scheduler.start()

    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('start_info', start_info_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, ask_time_range))
    application.add_handler(CallbackQueryHandler(send_excel_file))
    application.run_polling()

if __name__ == "__main__":
    main()
