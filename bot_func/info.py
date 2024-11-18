from art import text2art
from colorama import Fore, init
from telegram.ext import Application


# Rangli matnlarni to'g'ri ko'rsatish uchun colorama-ni ishga tushiramiz
init(autoreset=True)

# Bot haqida malumotlarni chiqaruvchi funksiya
async def bot_info(app: Application):
    # Bot ma'lumotlarini olish
    bot = app.bot
    bot_details = await bot.get_me()

    # Bot nomini ASCII san'ati bilan chiqarish
    bot_name_art = text2art(bot_details.first_name, font="small")
    print(bot_name_art)

    # Username'ni qizil rangda chiqarish
    print(Fore.RED + f"Username: @{bot_details.username}")

    # Qo'shimcha ma'lumotlar
    print("Bot ID:", bot_details.id)
    print("Ismi:", bot_details.first_name)
    print("To'liq username:", bot_details.username)
    print("Botmi?:", bot_details.is_bot)