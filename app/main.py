import asyncio
import os
import logging
import http.client
import sys
import threading
import requests
from time import sleep
from datetime import datetime
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher
from aiogram.filters import Command, CommandStart
from aiogram.types import Message

APP_DIR = os.path.dirname(os.path.abspath(__file__))
USER_FILE = os.path.join(APP_DIR, "users.txt")

load_dotenv()
BOT_TOKEN = os.getenv("TELEGRAM_TOKEN")
UPDATE_TIME = int(os.getenv("UPDATE_TIME", 60))

logging.basicConfig(
    level=os.getenv('LOGGING_LEVEL', 'INFO').upper(),
    format='%(asctime)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)


def load_users() -> set:
    if os.path.exists(USER_FILE):
        with open(USER_FILE, "r") as file:
            return set(int(line.strip()) for line in file if line.strip().isdigit())
    return set()


def save_users(users: set) -> None:
    with open(USER_FILE, "w") as file:
        file.writelines(f"{user}\n" for user in users)


users = load_users()


async def start(message: Message) -> None:
    if message.chat.id not in users:
        users.add(message.chat.id)
        save_users(users)
        logging.info(f"New user added: {message.chat.id} {message.from_user.username}")
    send_message(message.chat.id, f"Current IP: {get_ip()}"
                                  "\n/get_ip - get current IP address")


async def get_ip_command(message: Message) -> None:
    logging.debug(f"Get IP command received from {message.chat.id}")
    ip = get_ip()
    send_message(message.chat.id, f"Current IP: {ip}")


def get_ip() -> str:
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


def autoupdate() -> None:
    try:
        new_conn = True
        current_ip = get_ip()
        for user_id in users:
            send_message(user_id, f"Server started.\nCurrent IP: {current_ip}")
        while True:
            try:
                old_conn = new_conn
                old_ip = current_ip
                current_ip = get_ip()
                if current_ip in ["Error fetching IP", "Unknown IP"]:
                    current_ip = old_ip
                    new_conn = False
                else:
                    new_conn = True

                if not old_conn and new_conn:  # Connection restored
                    logging.info(f"Connection restored: {datetime.now()}")
                    for user_id in users:
                        send_message(user_id, f"Connection restored.\nCurrent IP: {current_ip}")

                if current_ip != old_ip:  # IP changed
                    msg = f"\n{old_ip} –> {current_ip}"
                    logging.info(f"IP changed: {msg}")
                    for user_id in users:
                        send_message(user_id, msg)

            except Exception as e:
                logging.error(f"Error in autoupdate loop: {e}")
            sleep(UPDATE_TIME)
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
    try:
        await dp.start_polling(bot)
    except Exception as e:
        logging.error(f"Critical error in polling: {e}")


def run_bot():
    asyncio.run(main_bot())


def send_message(chat_id: int, text: str) -> None:
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
        current_ip = get_ip()
        update_thread = threading.Thread(target=autoupdate, args=(current_ip,))
        update_thread.start()
        while True:
            bot_thread = threading.Thread(target=run_bot, daemon=True)
            bot_thread.start()
            bot_thread.join()
            logging.info("Restarting bot thread after completion.")

    except (KeyboardInterrupt, SystemExit):
        logging.info("Bot stopped.")
