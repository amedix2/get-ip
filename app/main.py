import asyncio
import os
import logging
import http.client
import sys
from datetime import datetime
import requests
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command, CommandStart
from aiogram.types import Message

load_dotenv()
ACCESS_ID = int(os.getenv("TELEGRAM_CHAT_ID"))
BOT_TOKEN = os.getenv("TELEGRAM_TOKEN")
UPDATE_TIME = int(os.getenv("UPDATE_TIME", 60))

logging.basicConfig(
    level=os.getenv('LOGGING_LEVEL', 'INFO').upper(),
    format='%(asctime)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)


async def start(message: Message) -> None:
    logging.debug(f'Start command received from {message.chat.id}')
    await send_message(BOT_TOKEN, message.chat.id, f'Current IP: {await get_ip()}'
                                                   '\n/get_ip - get current IP address')


async def get_ip_command(message: Message) -> None:
    logging.debug(f'Get IP command received from {message.chat.id}')
    ip = await get_ip()
    msg = f'{ip}'
    logging.debug(f'Sending IP to user: {msg}')
    await send_message(BOT_TOKEN, message.chat.id, msg)


async def get_ip() -> str:
    try:
        conn = http.client.HTTPConnection("ifconfig.me", timeout=5)
        conn.request("GET", "/ip")
        response = conn.getresponse()
        if response.status == 200:
            ip = response.read().decode()
        else:
            logging.error(f"Failed to get IP. Status: {response.status}")
            ip = "Unknown IP"
        conn.close()
        return ip
    except Exception as e:
        logging.error(f"Error fetching IP: {e}")
        return "Error fetching IP"


async def autoupdate() -> None:
    try:
        new_conn = True
        current_ip = await get_ip()
        await send_message(BOT_TOKEN, ACCESS_ID, f'Server started.\nCurrent IP: {current_ip}')
        while True:
            try:
                old_conn = new_conn
                old_ip = current_ip
                current_ip = await get_ip()
                if current_ip in ["Error fetching IP", "Unknown IP"]:
                    current_ip = old_ip
                    new_conn = False
                else:
                    new_conn = True

                if not old_conn and new_conn:  # Connection restored
                    restored_message = (
                        f'Connection restored.\nCurrent IP: {current_ip}'
                    )
                    logging.info(f'Connection restored: {datetime.now()}')
                    for attempt in range(3):
                        try:
                            await send_message(BOT_TOKEN, ACCESS_ID, restored_message)
                            logging.debug("Restoration message sent successfully")
                            break
                        except Exception as e:
                            logging.error(f"Failed to send restoration message, attempt {attempt + 1}: {e}")
                            await asyncio.sleep(5)

                if current_ip != old_ip:  # IP changed
                    msg = f'\n{old_ip} –> {current_ip}'
                    logging.info(f'IP changed: {msg}')
                    await send_message(BOT_TOKEN, ACCESS_ID, msg)

            except Exception as e:
                logging.error(f"Error in autoupdate loop: {e}")
            await asyncio.sleep(UPDATE_TIME)
    except Exception as e:
        logging.error(f"Critical error in autoupdate: {e}")


def create_bot_and_dispatcher() -> tuple[Bot, Dispatcher]:
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()
    dp.message.register(start, CommandStart(), F.from_user.id == ACCESS_ID)
    dp.message.register(get_ip_command, Command('get_ip'), F.from_user.id == ACCESS_ID)
    return bot, dp


async def main_bot() -> None:
    bot, dp = create_bot_and_dispatcher()
    autoupdate_task = asyncio.create_task(autoupdate())
    try:
        await dp.start_polling(bot)
    except Exception as e:
        logging.error(f"Critical error in polling: {e}")
    finally:
        autoupdate_task.cancel()


async def send_message(token: str, chat_id: int, text: str) -> None:
    try:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        data = {"chat_id": chat_id, "text": text}
        response = requests.post(url, data=data, timeout=10)
        response.raise_for_status()
        logging.debug(f'Message sent successfully: {response.json()}')
    except requests.RequestException as e:
        logging.error(f"Error sending message: {e}")


if __name__ == '__main__':
    try:
        asyncio.run(main_bot())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Bot stopped.")
