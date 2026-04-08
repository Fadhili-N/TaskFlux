
"""
TaskFlux Telegram Monitor
Runs 24/7 on Railway and alerts Telegram when new tasks appear
"""

import time
import json
import os
import requests
import threading
from datetime import datetime
from flask import Flask

ACCESS_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyIjp7Il9pZCI6IjY5ODU5NDU3M2Q1MGM1ZmJkMmQ5NzUwNCIsImVtYWlsIjoibmFyb3Rzb2x1bXVtYmFAZ21haWwuY29tIiwiZmlyc3ROYW1lIjoiRmFkaGlsaSIsImxhc3ROYW1lIjoiQmVyYWNhaCIsImxvZ2luUHJvdmlkZXIiOiJsb2NhbCIsImlwQWRkcmVzcyI6IjJjMGY6ZWI2ODo2MzI6MTUwMDpmY2ViOmI1MzM6MzY2ODo3NTE5IiwicmVnaW9uRGV0YWlsIjp7ImNvdW50cnkiOiJSd2FuZGEiLCJjb3VudHJ5Q29kZSI6IlJXIn0sImVtYWlsVmVyaWZpZWQiOmZhbHNlLCJvbmJvYXJkaW5nQ29tcGxldGVkIjpmYWxzZSwicm9sZSI6Im1pY3JvLXdvcmtlciIsImRpc2NvcmRVc2VybmFtZSI6InRoZWVmbGV4XzE2NDEyIiwicmVkZGl0VXNlckxpbmsiOiJodHRwczovL3d3dy5yZWRkaXQuY29tL3VzZXIvQXBwcm9wcmlhdGUtQW50LTkwMzYvP3V0bV9zb3VyY2U9c2hhcmUmdXRtX21lZGl1bT13ZWIzeCZ1dG1fbmFtZT13ZWIzeGNzcyZ1dG1fdGVybT0xJnV0bV9jb250ZW50PXNoYXJlX2J1dHRvbiIsIndoYXRzYXBwTnVtYmVyIjoiKzI1NDc1OTA3NTgxMyIsImFjdGl2ZSI6dHJ1ZSwiY3JlYXRlZEF0IjoiMjAyNi0wMi0wNlQwNzoxMjoyMy44OTBaIiwidXBkYXRlZEF0IjoiMjAyNi0wNC0wOFQxMTozMjoxMi40NTFaIiwiX192IjowLCJyZWZlcnJhbENvZGUiOiI4OUI3RjQwMSIsIndpc2UiOnsicmVjaXBpZW50SWQiOiIxMzUxNTE1ODA3IiwiYWNjb3VudEhvbGRlck5hbWUiOiJGYWRoaWxpIEJlcmFjYWggIiwiY3VycmVuY3kiOiJLRVMiLCJ3aXRoZHJhd2FsQWNjb3VudFR5cGUiOiJNLVBFU0EifSwiZGlzY29yZCI6eyJpZCI6IjE0MDE5OTE1NzY2MzI0MjY1ODYiLCJ1c2VybmFtZSI6InRoZWVmbGV4XzE2NDEyIiwiY29ubmVjdGVkIjp0cnVlLCJzZXJ2ZXJNZW1iZXIiOnRydWV9LCJtaWNyb3dvcmtlck9uYm9hcmRpbmdDb21wbGV0ZWQiOnRydWUsInRlbXBFbWFpbCI6ImEwMDRhMDA3YWJlbEBnbWFpbC5jb20ifSwiaWF0IjoxNzc1NjQ4MzY4LCJleHAiOjE3NzYyNTMxNjh9.Yvm-H2bYQFkuCRS0zwkLhaIqd0qLdHsdsZWlJn_nj3k"

TELEGRAM_BOT_TOKEN = "8655127571:AAE23YOWRX6r7nLbcMV-K-x1Hw51q668ALg"
TELEGRAM_CHAT_ID = "7608400190"

DASHBOARD_URL = "https://taskflux.net/dashboard"

POLL_INTERVAL_SECONDS = 20
API_URL = "https://taskflux.net/api/tasks/task-pool"
STATE_FILE = "taskflux_seen_tasks.json"

app = Flask(__name__)

@app.route("/")
def home():
    return "TaskFlux Monitor Running"

def run_web():
    app.run(host="0.0.0.0", port=8080)

def load_seen():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE) as f:
            return set(json.load(f))
    return set()

def save_seen(seen):
    with open(STATE_FILE, "w") as f:
        json.dump(list(seen), f)

def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "HTML"
    }

    try:
        r = requests.post(url, json=payload, timeout=10)
        print(r.text)
    except Exception as e:
        print(e)

def fetch_task_pool():
    try:
        resp = requests.get(
            API_URL,
            cookies={"accessToken": ACCESS_TOKEN},
            timeout=15,
        )

        if resp.status_code == 200:
            return resp.json()

        elif resp.status_code in (401, 403):
            send_telegram("Token expired")
            return None

        else:
            return None

    except Exception:
        return None

def alert(count, tasks):

    lines = []

    for t in tasks[:3]:
        title = t.get("title") or "Task"
        reward = t.get("reward") or ""
        reward_str = f" — ${reward}" if reward else ""
        lines.append(f"• {title}{reward_str}")

    preview = "\n".join(lines)

    message = (
        f"🚨 {count} New TaskFlux Tasks\n\n"
        f"{preview}\n\n"
        f"👉 {DASHBOARD_URL}"
    )

    send_telegram(message)

def get_id(task):
    return str(
        task.get("_id")
        or json.dumps(task, sort_keys=True)
    )

def main():

    send_telegram("TaskFlux Monitor Started")

    seen = load_seen()

    while True:

        tasks = fetch_task_pool()

        if tasks:

            new = [t for t in tasks if get_id(t) not in seen]

            if new:
                alert(len(new), new)
                seen.update(get_id(t) for t in new)
                save_seen(seen)

        time.sleep(POLL_INTERVAL_SECONDS)

if __name__ == "__main__":
    threading.Thread(target=run_web).start()
    main()
