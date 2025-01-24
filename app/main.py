import asyncio
import os
import logging
import http.client
import sys
from datetime import datetime
import requests
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher
from aiogram.filters import Command, CommandStart
from aiogram.types import Message

USER_FILE = "data/users.txt"

load_dotenv()
BOT_TOKEN = os.getenv("TELEGRAM_TOKEN")
UPDATE_TIME = int(os.getenv("UPDATE_TIME", 60))

logging.basicConfig(
    level=os.getenv('LOGGING_LEVEL', 'INFO').upper(),
    format='%(asctime)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)


def load_users() -> set:
    os.makedirs(os.path.dirname(USER_FILE), exist_ok=True)
    if os.path.exists(USER_FILE):
        with open(USER_FILE, "r") as file:
            return set(int(line.strip()) for line in file if line.strip().isdigit())
    return set()


def save_users(users: set) -> None:
    os.makedirs(os.path.dirname(USER_FILE), exist_ok=True)
    with open(USER_FILE, "w") as file:
        file.writelines(f"{user}\n" for user in users)


users = load_users()


async def start(message: Message) -> None:
    if message.chat.id not in users:
        users.add(message.chat.id)
        save_users(users)
        logging.info(f"New user added: {message.chat.id}")
    await send_message( message.chat.id, f"Current IP: {await get_ip()}"
                                                   "\n/get_ip - get current IP address")


async def get_ip_command(message: Message) -> None:
    logging.debug(f"Get IP command received from {message.chat.id}")
    ip = await get_ip()
    await send_message(message.chat.id, f"Current IP: {ip}")


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
        for user_id in users:
            await send_message(user_id, f"Server started.\nCurrent IP: {current_ip}")
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
                    logging.info(f"Connection restored: {datetime.now()}")
                    for user_id in users:
                        await send_message(user_id, f"Connection restored.\nCurrent IP: {current_ip}")

                if current_ip != old_ip:  # IP changed
                    msg = f"\n{old_ip} –> {current_ip}"
                    logging.info(f"IP changed: {msg}")
                    for user_id in users:
                        await send_message(user_id, msg)

            except Exception as e:
                logging.error(f"Error in autoupdate loop: {e}")
            await asyncio.sleep(UPDATE_TIME)
    except Exception as e:
        logging.error(f"Critical error in autoupdate: {e}")


def create_bot_and_dispatcher() -> tuple[Bot, Dispatcher]:
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()
    dp.message.register(start, CommandStart())
    dp.message.register(get_ip_command, Command("get_ip"))
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


async def send_message(chat_id: int, text: str) -> None:
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        data = {"chat_id": chat_id, "text": text}
        response = requests.post(url, data=data, timeout=10)
        response.raise_for_status()
        logging.debug(f"Message sent successfully to {chat_id}: {response.json()}")
    except requests.RequestException as e:
        logging.error(f"Error sending message to {chat_id}: {e}")


if __name__ == '__main__':
    try:
        asyncio.run(main_bot())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Bot stopped.")
