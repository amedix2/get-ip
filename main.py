import os
import logging
import http.client
from datetime import datetime
from dotenv import load_dotenv

from aiogram import Bot, Dispatcher, F, types
from aiogram.enums import ParseMode
from aiogram.filters import Command, CommandStart
from aiogram.types import Message
from aiogram.utils.markdown import hbold


def get_ip() -> str:
    conn = http.client.HTTPConnection("ifconfig.me")
    conn.request("GET", "/ip")
    r = conn.getresponse().read().decode()
    conn.close()
    return r


if __name__ == '__main__':
    load_dotenv()
    TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
    TELEGRAM_CHAT_ID = int(os.getenv('TELEGRAM_CHAT_ID'))
    DELAY = int(os.getenv('DELAY'))

    while True:
        ip = get_ip()
        msg = f'{ip}\n{datetime.now()}'
