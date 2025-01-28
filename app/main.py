import asyncio
import os
import logging
import http.client
import sys
import requests
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
    await send_message(message.chat.id, f"Current IP: {await get_ip()}"
                                        "\n/get_ip - get current IP address")


async def get_ip_command(message: Message) -> None:
    try:
        logging.debug(f"Get IP command received from {message.chat.id}")
        ip = await get_ip()
        await send_message(message.chat.id, f"Current IP: {ip}")
    except Exception as e:
        logging.error(f"Error in get_ip_command: {e}")
        await send_message(message.chat.id, "Error retrieving IP. Please try again later.")


async def get_ip() -> str:
    try:
        conn = http.client.HTTPConnection("ifconfig.me", timeout=5)
        conn.request("GET", "/ip")
        response = conn.getresponse()
        if response.status == 200:
            ip = response.read().decode().strip()
            return ip
        else:
            logging.error(f"Failed to get IP. HTTP status: {response.status}")
            return "Unknown IP"
    except Exception as e:
        logging.error(f"Error fetching IP: {e}")
        return "Error fetching IP"


async def autoupdate(bot: Bot, dp: Dispatcher) -> None:
    try:
        current_ip = await get_ip()
        connection_ok = current_ip not in ["Error fetching IP", "Unknown IP"]
        for user_id in users:
            await send_message(user_id, f"Server started.\nCurrent IP: {current_ip}")

        while True:
            try:
                old_ip = current_ip
                current_ip = await get_ip()
                new_connection_ok = current_ip not in ["Error fetching IP", "Unknown IP"]

                if not connection_ok and new_connection_ok:
                    logging.info("Connection restored.")
                    for user_id in users:
                        await send_message(user_id, f"Connection restored.\nCurrent IP: {current_ip}")

                if new_connection_ok and current_ip != old_ip:
                    msg = f"IP changed: {old_ip} -> {current_ip}"
                    logging.info(msg)
                    for user_id in users:
                        await send_message(user_id, msg)
                    bot, dp = await restart_polling(bot, dp)

                connection_ok = new_connection_ok
            except Exception as e:
                logging.error(f"Error in autoupdate loop: {e}")

            await asyncio.sleep(UPDATE_TIME)
    except Exception as e:
        logging.critical(f"Critical error in autoupdate: {e}")


async def restart_polling(bot: Bot, dp: Dispatcher) -> tuple[Bot, Dispatcher]:
    logging.info("Restarting bot due to IP change...")
    try:
        dp.shutdown()
        await bot.session.close()
        logging.info("Polling stopped successfully.")
        await asyncio.sleep(5)
        logging.info("Starting new polling...")
        new_bot, new_dp = create_bot_and_dispatcher()
        await asyncio.create_task(new_dp.start_polling(new_bot))
        logging.info("Polling restarted successfully.")
        return new_bot, new_dp
    except Exception as e:
        logging.error(f"Error during polling restart: {e}")
        return bot, dp


def create_bot_and_dispatcher() -> tuple[Bot, Dispatcher]:
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()
    dp.message.register(start, CommandStart())
    dp.message.register(get_ip_command, Command("get_ip"))
    return bot, dp


async def main_bot() -> None:
    bot, dp = create_bot_and_dispatcher()
    autoupdate_task = asyncio.create_task(autoupdate(bot, dp))
    try:
        await dp.start_polling(bot)
    except Exception as e:
        logging.error(f"Critical error in polling: {e}")
    finally:
        autoupdate_task.cancel()
        await autoupdate_task
        await bot.session.close()


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
