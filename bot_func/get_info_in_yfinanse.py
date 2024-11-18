import time
from telegram.ext import ContextTypes
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
import yfinance as yf
from telegram.error import TelegramError
import pandas as pd
import os

ADMIN_ID = 6214462946
EXCEL_INPUT = 'Aksiyalar-symboli.xlsx'
EXCEL_OUTPUT = 'stack_info.xlsx'


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
        time.sleep(1)
        row = {
            "Aksiya": ticker_symbol,
            "Current Price": data["Close"].iloc[0] if not data["Close"].isna().iloc[0] else 0,
            "Volume": data["Volume"].iloc[0] if not data["Volume"].isna().iloc[0] else 0,
            "ATR14": atr(ticker_symbol) or 0,
            "Short Float %": stock.info.get("shortPercentOfFloat") or 0,
            "Institutional Ownership %": (stock.info.get("heldPercentInstitutions") or 0) * 100,
            "Income (M)": stock.info.get("netIncomeToCommon", 0) / 1e6,
            "Market Cap (M)": (stock.info.get("marketCap") or 0) / 1_000_000,
            "Options PUT volume": total_put_volume,
            "Options CALL volume": total_call_volume,
            "1 yil o‘zgarish %": (stock.info.get("52WeekChange") or 0) * 100,
            "Full time employees": stock.info.get("fullTimeEmployees") or "Noma'lum",
            "Fiscal year end": stock.info.get("nextFiscalYearEnd") or "Noma'lum",
            "Sector": stock.info.get("sector") or "Noma'lum",
            "Industry": stock.info.get("industry") or "Noma'lum",
        }
    except Exception as e:
        print(data)
        row = {
            "Aksiya": ticker_symbol,
            "Current Price": 0,
            "Volume": 0,
            "ATR14": 0,
            "Short Float %": 0,
            "Institutional Ownership %": 0,
            "Income (M)": 0,
            "Market Cap (M)": 0,
            "Options PUT volume": 0,
            "Options CALL volume": 0,
            "1 yil o‘zgarish %": 0,
            "Full time employees": "Noma'lum",
            "Fiscal year end": "Noma'lum",
            "Sector": "Noma'lum",
            "Industry": "Noma'lum",
        }
        print(f"{ticker_symbol} uchun ma'lumot olishda xatolik: {e}")
    return row

async def start_info(context: ContextTypes.DEFAULT_TYPE) -> None:
    aksiyalar = pd.read_excel(EXCEL_INPUT)['Symbol'].tolist()
    malumotlar = []

    for ticker_symbol in aksiyalar:
        row = await fetch_stock_data(ticker_symbol)
        time.sleep(2)
        malumotlar.append(row)
        
        # Har bir aksiyadan keyin yozish
        df = pd.DataFrame(malumotlar)
        if os.path.exists(EXCEL_OUTPUT):
            existing_df = pd.read_excel(EXCEL_OUTPUT)
            df = pd.concat([existing_df, df], ignore_index=True).drop_duplicates(subset="Aksiya")
        df.to_excel(EXCEL_OUTPUT, index=False)

    # Faylni admin foydalanuvchiga yuborish
    bot = context.bot
    try:
        await bot.send_document(chat_id=ADMIN_ID, document=open(EXCEL_OUTPUT, 'rb'))
        await bot.send_message(chat_id=ADMIN_ID, text="Barcha ma'lumotlar yuklandi va saqlandi.")
    except TelegramError as r:
        print(r)
    os.remove(EXCEL_OUTPUT)

async def start_info_command(update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.message.from_user.id
    await update.message.reply_text(text="Ma'lumotlarni yuklayabman bir oz kuting...")
    aksiyalar = pd.read_excel(EXCEL_INPUT)['Symbol'].tolist()
    malumotlar = []

    for ticker_symbol in aksiyalar:
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
            row = {
                "Aksiya": ticker_symbol,
                "Current Price": data["Close"].iloc[0] if not data["Close"].isna().iloc[0] else 0,
                "Open": data["Open"].iloc[0],
                "High": data["High"].iloc[0],
                "Low": data["Low"].iloc[0],
                "Volume": data["Volume"].iloc[0] if not data["Volume"].isna().iloc[0] else 0,
                "ATR14": atr(ticker_symbol) or 0,
                "Short Float %": (stock.info.get("shortPercentOfFloat") or 0) * 100,
                "Institutional Ownership %": (stock.info.get("heldPercentInstitutions") or 0) * 100,
                "Income (M)": stock.info.get("netIncomeToCommon", 0) / 1e6,
                "Market Cap (M)": (stock.info.get("marketCap") or 0) / 1_000_000,
                "Options PUT volume": total_put_volume,
                "Options CALL volume": total_call_volume,
                "1 yil o‘zgarish %": (stock.info.get("52WeekChange") or 0) * 100,
                "Sector": stock.info.get("sector") or "Noma'lum",
                "Industry": stock.info.get("industry") or "Noma'lum",
            }
            malumotlar.append(row)
            time.sleep(2)
        except Exception as e:
            print(data)
            row = {
                "Aksiya": ticker_symbol,
                "Current Price": 0,
                "Open": 0,
                "High": 0,
                "Low": 0,
                "Volume": 0,
                "ATR14": 0,
                "Short Float %": 0,
                "Institutional Ownership %": 0,
                "Income (M)": 0,
                "Market Cap (M)": 0,
                "Options PUT volume": 0,
                "Options CALL volume": 0,
                "1 yil o‘zgarish %": 0,
                "Sector": "Noma'lum",
                "Industry": "Noma'lum",
            }
            malumotlar.append(row)
            print(f"{ticker_symbol} uchun ma'lumot olishda xatolik: {e}")

    df = pd.DataFrame(malumotlar)
    if os.path.exists(EXCEL_OUTPUT):
        existing_df = pd.read_excel(EXCEL_OUTPUT)
        df = pd.concat([existing_df, df], ignore_index=True).drop_duplicates(subset="Aksiya")
    df.to_excel(EXCEL_OUTPUT, index=False)

    # Faylni admin foydalanuvchiga yuborish
    bot = context.bot
    try:
        await bot.send_document(chat_id=user_id, document=open(EXCEL_OUTPUT, 'rb'))
        await bot.send_document(chat_id=ADMIN_ID, document=open(EXCEL_OUTPUT, 'rb'))
        await bot.send_message(chat_id=user_id, text="Barcha ma'lumotlar yuklandi va saqlandi.")
    except TelegramError as e:
        print(e)
    os.remove(EXCEL_OUTPUT)


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
