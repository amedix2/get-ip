import os
import http.client
import requests
import time
from datetime import datetime
from dotenv import load_dotenv


def send_message(token, chat_id, text):
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    data = {"chat_id": chat_id, "text": text}
    response = requests.post(url, data=data)
    return response.json()


if __name__ == '__main__':
    load_dotenv()
    TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
    TELEGRAM_CHAT_ID = int(os.getenv('TELEGRAM_CHAT_ID'))
    DELAY = int(os.getenv('DELAY'))

    conn = http.client.HTTPConnection("ifconfig.me")
    while True:
        conn.request("GET", "/ip")
        r = conn.getresponse().read().decode()
        msg = f'{r}\n{datetime.now()}'
        send_message(token=TELEGRAM_TOKEN, chat_id=TELEGRAM_CHAT_ID, text=msg)
        print(msg)
        time.sleep(DELAY)
