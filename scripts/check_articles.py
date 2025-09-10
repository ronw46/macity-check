import requests
from bs4 import BeautifulSoup
import sqlite3
import os
import time
import random

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
AUTHOR_URL_BASE = "https://www.macitynet.it/author/yuri"

DB_PATH = "scripts/db.sqlite"

def send_telegram_message(message: str):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "HTML",
        "disable_web_page_preview": True
    }
    try:
        response = requests.post(url, data=payload)
        response.raise_for_status()
    except Exception as e:
        print(f"[Telegram] Errore invio messaggio: {e}")

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS articles (
            url TEXT PRIMARY KEY,
            title TEXT,
            timestamp INTEGER
        )
    ''')
    conn.commit()
    conn.close()

def fetch_current_articles():
    articles = []
    page = 1
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)"
    }

    while True:
        url = f"{AUTHOR_URL_BASE}/page/{page}/"
        print(f"[Fetch] Scaricamento pagina {page}...")
        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            print(f"[Errore] Pagina {page} ha restituito {response.status_code}")
            break

        soup = BeautifulSoup(response.text, "html.parser")
        page_articles = []

        for a in soup.select("h2.entry-title a"):
            title = a.text.strip()
            link = a['href']
            page_articles.append((link, title))

        if not page_articles:
            print("[Fetch] Nessun articolo trovato, fine delle pagine.")
            break

        articles.extend(page_articles)
        page += 1

        # Attesa random per non farsi bloccare
        delay = random.uniform(1, 3)
        print(f"[Delay] Attendo {delay:.2f} secondi...")
        time.sleep(delay)

    print(f"[Fetch] Trovati {len(articles)} articoli totali.")
    return articles

def load_old_articles():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT url, title FROM articles")
    old_articles = c.fetchall()
    conn.close()
    return {url: title for url, title in old_articles}

def save_articles(articles):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    for url, title in articles:
        c.execute("INSERT OR IGNORE INTO articles (url, title, timestamp) VALUES (?, ?, ?)", (url, title, int(time.time())))
    conn.commit()
    conn.close()

def check_for_disappeared_articles(old_articles, current_articles):
    current_urls = {url for url, _ in current_articles}
    disappeared = []

    for url, title in old_articles.items():
        if url not in current_urls:
            disappeared.append((url, title))

    return disappeared

def main():
    init_db()

    current_articles = fetch_current_articles()
    old_articles = load_old_articles()

    if not old_articles:
        print("[Init] Primo run: salvataggio articoli iniziali.")
        save_articles(current_articles)
        return

    disappeared = check_for_disappeared_articles(old_articles, current_articles)

    if disappeared:
        message = "<b>⚠️ Articoli scomparsi da macitynet.it/author/yuri/</b>\n"
        for url, title in disappeared:
            message += f"• <a href=\"{url}\">{title}</a>\n"
        send_telegram_message(message)
    else:
        print("[Check] Nessun articolo scomparso.")

    save_articles(current_articles)

if __name__ == "__main__":
    main()
