import asyncio
import os
import logging
import http.client
import sys
import threading
import time
import requests
from datetime import datetime
from dotenv import load_dotenv

from aiogram import Bot, Dispatcher, F
from aiogram.enums import ParseMode
from aiogram.filters import Command, CommandStart
from aiogram.types import Message

load_dotenv()
ACCESS_ID = int(os.getenv("TELEGRAM_CHAT_ID"))
BOT_TOKEN = os.getenv("TELEGRAM_TOKEN")
UPDATE_TIME = int(os.getenv("UPDATE_TIME"))

dp = Dispatcher()


@dp.message(F.from_user.id == ACCESS_ID, CommandStart())
async def start(message: Message) -> None:
    logging.info(f'start {message.chat.id}')
    await message.answer(f'/get_ip - get ip')


@dp.message(F.from_user.id == ACCESS_ID, Command('get_ip'))
async def get_ip_command(message: Message) -> None:
    logging.info(f'get ip {message.chat.id}')
    ip = get_ip()
    msg = f'{ip}\n{datetime.now()}'
    logging.info(msg)
    await message.answer(msg)


async def main() -> None:
    bot = Bot(token=BOT_TOKEN, parse_mode=ParseMode.HTML)
    await dp.start_polling(bot)


def send_message(token, chat_id, text) -> dict:
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    data = {"chat_id": chat_id, "text": text}
    response = requests.post(url, data=data)
    return response.json()


def get_ip() -> str:
    conn = http.client.HTTPConnection("ifconfig.me")
    conn.request("GET", "/ip")
    ip = conn.getresponse().read().decode()
    conn.close()
    return ip


def run_tg() -> None:
    asyncio.run(main())


def autoupdate(curr_ip: str) -> None:
    while True:
        last_ip = curr_ip
        curr_ip = get_ip()
        if last_ip != curr_ip:
            msg = f'{last_ip} --> {curr_ip}\n{datetime.now()}'
            r = send_message(BOT_TOKEN, ACCESS_ID, msg)
            logging.debug(r)
        time.sleep(UPDATE_TIME)


if __name__ == '__main__':
    logging.basicConfig(level=os.getenv('LOGGING_LEVEL'), stream=sys.stdout)
    th1 = threading.Thread(target=run_tg)
    th2 = threading.Thread(target=autoupdate, args=(get_ip(),))
    th1.start()
    th2.start()
    th1.join()
    th2.join()
