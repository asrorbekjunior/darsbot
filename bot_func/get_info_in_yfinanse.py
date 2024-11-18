import asyncio
import time
import pandas as pd
import os
from datetime import time as dt_time
from telegram.ext import ContextTypes
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.error import TelegramError
import yfinance as yf

# Fayl konfiguratsiyasi
ADMIN_ID = 6214462946
SRC_FOLDER = "src"
EXCEL_FILES = [
    "Aksiyalar-symboli1.xlsx", "Aksiyalar-symboli2.xlsx",
    "Aksiyalar-symboli3.xlsx", "Aksiyalar-symboli4.xlsx",
    "Aksiyalar-symboli5.xlsx", "Aksiyalar-symboli6.xlsx",
    "Aksiyalar-symboli7.xlsx", "Aksiyalar-symboli8.xlsx"
]

OUTPUT_FILE = "stack_info.xlsx"

# ATR14 hisoblash funksiyasi
def atr(ticker):
    data = yf.download(ticker, period="3mo", interval="1d")
    if data.empty:
        return None
    data['H-L'] = data['High'] - data['Low']
    data['H-PC'] = abs(data['High'] - data['Close'].shift(1))
    data['L-PC'] = abs(data['Low'] - data['Close'].shift(1))
    data['TR'] = data[['H-L', 'H-PC', 'L-PC']].max(axis=1)
    data['ATR14'] = data['TR'].rolling(window=14, min_periods=1).mean()
    latest_atr14 = data['ATR14'].iloc[-1] if not data['ATR14'].isna().all() else None
    return latest_atr14

# Ma'lumotlarni yuklash funksiyasi
async def fetch_stock_data(ticker_symbol):
    try:
        stock = yf.Ticker(ticker_symbol)
        options = stock.options
        total_call_volume = 0
        total_put_volume = 0

        for option_date in options:
            option_chain = stock.option_chain(option_date)
            calls = option_chain.calls
            puts = option_chain.puts
            total_call_volume += calls['volume'].sum()
            total_put_volume += puts['volume'].sum()

        data = stock.history(period="1d")
        time.sleep(2)
        row = {
            "Aksiya": ticker_symbol,
            "Current Price": data["Close"].iloc[0] if not data["Close"].isna().iloc[0] else 0,
            "Volume": data["Volume"].iloc[0] if not data["Volume"].isna().iloc[0] else 0,
            "ATR14": atr(ticker_symbol) or 0,
            "Short Float %": (stock.info.get("shortPercentOfFloat") or 0) * 100,
            "Institutional Ownership %": (stock.info.get("heldPercentInstitutions") or 0) * 100,
            "Income (M)": stock.info.get("netIncomeToCommon", 0) / 1e6,
            "Market Cap (M)": (stock.info.get("marketCap") or 0) / 1_000_000,
            "Options PUT volume": total_put_volume,
            "Options CALL volume": total_call_volume,
            "1 yil o‘zgarish %": (stock.info.get("52WeekChange") or 0) * 100,
            "Full time employees": stock.info.get("fullTimeEmployees") or "Noma'lum",
            "Sector": stock.info.get("sector") or "Noma'lum",
            "Industry": stock.info.get("industry") or "Noma'lum",
        }
    except Exception as e:
        row = {key: "Noma'lum" for key in ["Aksiya", "Current Price", "Volume", "ATR14", 
                                           "Short Float %", "Institutional Ownership %", 
                                           "Income (M)", "Market Cap (M)", 
                                           "Options PUT volume", "Options CALL volume", 
                                           "1 yil o‘zgarish %", "Full time employees", 
                                           "Sector", "Industry"]}
        print(f"{ticker_symbol} uchun ma'lumot olishda xatolik: {e}")
    return row

# Faylni tekshirish va yangilash
async def process_excel_file(file_name, user_id, context: ContextTypes.DEFAULT_TYPE):
    file_path = os.path.join(SRC_FOLDER, file_name)
    aksiyalar = pd.read_excel(file_path)['Symbol'].tolist()
    malumotlar = []

    for ticker_symbol in aksiyalar:
        row = await fetch_stock_data(ticker_symbol)
        malumotlar.append(row)

    # Ma'lumotlarni saqlash
    df = pd.DataFrame(malumotlar)
    if os.path.exists(OUTPUT_FILE):
        existing_df = pd.read_excel(OUTPUT_FILE)
        df = pd.concat([existing_df, df], ignore_index=True).drop_duplicates(subset="Aksiya")
    df.to_excel(OUTPUT_FILE, index=False)

    # Faylni yuborish
    bot = context.bot
    try:
        await bot.send_document(chat_id=user_id, document=open(OUTPUT_FILE, 'rb'))
        await bot.send_message(chat_id=user_id, text=f"{file_name} faylidan ma'lumotlar yuborildi.")
    except TelegramError as e:
        print(f"Faylni yuborishda xatolik: {e}")
    os.remove(OUTPUT_FILE)

# Har kuni soat 7:00 da ma'lumotlarni adminga yuborish
async def daily_task(context: ContextTypes.DEFAULT_TYPE):
    for file_name in EXCEL_FILES:
        await process_excel_file(file_name, ADMIN_ID, context)

# /start_info komandasi
async def start_info_command(update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_chat.id
    await update.message.reply_text("Ma'lumotlarni yig'ish boshlandi! Har 30 daqiqa oraliqda ma'lumotlar tayyorlanadi.")
    for file_name in EXCEL_FILES:
        await process_excel_file(file_name, user_id, context)
        await asyncio.sleep(1800)  # 30 daqiqa kutish


async def ask_time_range(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    context.user_data['ticker'] = update.message.text.upper()
    keyboard = [
        [InlineKeyboardButton("1m", callback_data="1mo"), InlineKeyboardButton("3m", callback_data="3mo"),
         InlineKeyboardButton("6m", callback_data="6mo")],
        [InlineKeyboardButton("1y", callback_data="1y"), InlineKeyboardButton("2y", callback_data="2y"),
         InlineKeyboardButton("5y", callback_data="5y"), InlineKeyboardButton("10y", callback_data="10y")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Vaqtni oralig'ini tanlang:", reply_markup=reply_markup)



# Excel faylni yaratish va yuborish funksiyasi
async def send_excel_file(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    period = query.data
    ticker = context.user_data['ticker']
    stock = yf.Ticker(ticker)
    info = stock.info
    opsions = stock.options

    total_call_volume = 0
    total_put_volume = 0

    for date in opsions:
        option_chain = stock.option_chain(date)
        calls = option_chain.calls
        puts = option_chain.puts
        
        # Shu sana uchun umumiy volumelarni jamlash
        total_call_volume += calls['volume'].sum()
        total_put_volume += puts['volume'].sum()

    if info:
        try:
            current_price = stock.history(period="1d")["Close"].iloc[-1]
            volume = stock.history(period="1d")["Volume"].iloc[-1]

            atr14 = atr(ticker)
            short_float = info.get("shortPercentOfFloat", "Topilmadi")
            inst_own = info.get("heldPercentInstitutions", "Topilmadi") * 100
            income = info.get("netIncomeToCommon", "Topilmadi") / 1e6
            market_cap = info.get("marketCap", "Topilmadi") / 1e6
            one_year_change = info.get("52WeekChange", "Topilmadi") * 100

            # Kerakli ma'lumotlarni olish
            company_description = info.get("longBusinessSummary", "No information")
            full_time_employees = info.get("fullTimeEmployees", "No information")
            fiscal_year_end = info.get("fiscalYearEnd", "No information")
            sector = info.get("sector", "No information")
            industry = info.get("industry", "No information")
            exchange = info.get("exchange", "No information")
            if exchange == "NMS":
                exchange = "Nasdaq"

            response = (
                f"<b>📊 {ticker} Aksiya Ma'lumotlari:</b>\n\n"
                f"<b>Exchange:</b> {exchange}\n"
                f"<b>Current Price:</b> {current_price}$\n"
                f"<b>Volume:</b> {volume}\n"
                f"<b>ATR14:</b> {atr14}\n"
                f"<b>Short Float %:</b> {short_float}\n"
                f"<b>Institutional Ownership %:</b> {inst_own:.2f}%\n"
                f"<b>Income (M):</b> {income:.2f}\n"
                f"<b>Market Cap (M):</b> {market_cap:.2f}\n"
                f"<b>Options PUT volume:</b> {total_put_volume}\n"
                f"<b>Option CALL volume:</b> {total_call_volume}\n"
                f"<b>1 yildagi change %:</b> {one_year_change:.2f}%\n"
                f"<b>Full time employees:</b> {full_time_employees}\n"
                f"<b>Fiscal year end:</b> {fiscal_year_end}\n"
                f"<b>Sector:</b> {sector}\n"
                f"<b>Industry:</b> {industry}\n\n"
                
            )

        except Exception as e:
            response = "Ma'lumotlarni olishda xatolik yuz berdi."
    else:
        response = "Kechirasiz, ushbu aksiya kodi bo'yicha ma'lumot topilmadi."

    
    # Aksiya ma'lumotlarini olish va Excelga yozish
    stock_data = yf.download(ticker, period=period)
    stock_data.index = stock_data.index.tz_localize(None)


    filename = f"{ticker}_{period}_data.xlsx"
    with pd.ExcelWriter(filename) as writer:
        stock_data.to_excel(writer, sheet_name=ticker)
        # ATR14 qiymatini fayl tavsifiga kiritamiz
        writer.book.properties.title = "Admin contact: https://t.me/Asrorbek_10_02"

    # Faylni foydalanuvchiga yuborish
    await query.message.reply_document(document=open(filename, 'rb'), filename=filename, caption=response, parse_mode='HTML')
    await query.message.reply_text(f"<b>Company Description:\n</b> <blockquote expandable>{company_description}</blockquote>\n", parse_mode="HTML")
    os.remove(filename)
