import os
import asyncio
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command

# Load your configuration from environment variables or paste tokens directly
API_TOKEN = os.getenv(8823867620:AAGrY3ytRsrl2NmZeUVci19zOVXAmFvUUY0)
GROUP_ID = int(os.getenv(4329733155)

logging.basicConfig(level=logging.INFO)

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer("Hello! Your verification bot is up and running.")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
