import asyncio
import os
import logging
import http.client
import sys
from datetime import datetime
from dotenv import load_dotenv

from aiogram import Bot, Dispatcher, F
from aiogram.enums import ParseMode
from aiogram.filters import Command, CommandStart
from aiogram.types import Message

load_dotenv()
ACCESS_ID = int(os.getenv("TELEGRAM_CHAT_ID"))
BOT_TOKEN = os.getenv("TELEGRAM_TOKEN")

dp = Dispatcher()


@dp.message(F.from_user.id == ACCESS_ID, CommandStart())
async def start(message: Message) -> None:
    logging.info(f'start {message.chat.id}')
    await message.answer(f'/get_ip - get ip')


@dp.message(F.from_user.id == ACCESS_ID, Command('get_ip'))
async def get_ip(message: Message) -> None:
    logging.info(f'get ip {message.chat.id}')
    conn = http.client.HTTPConnection("ifconfig.me")
    conn.request("GET", "/ip")
    ip = conn.getresponse().read().decode()
    conn.close()
    msg = f'{ip}\n{datetime.now()}'
    logging.info(msg)
    await message.answer(msg)


async def main() -> None:
    bot = Bot(token=BOT_TOKEN, parse_mode=ParseMode.HTML)
    await dp.start_polling(bot)


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(main())
