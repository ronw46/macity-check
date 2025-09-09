import requests
from bs4 import BeautifulSoup
import json
import os
import time
import random

# URL della tua pagina autore
AUTHOR_URL = "https://macitynet.it/author/yuri/"

# Header realistico per non sembrare un bot
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/117.0.0.0 Safari/537.36"
}

# Token e chat ID da GitHub Secrets (via env)
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def load_articles_history():
    if os.path.exists("articles.json"):
        with open("articles.json", "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_articles_history(data):
    with open("articles.json", "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def send_telegram_message(message):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("⚠️ Token Telegram o chat ID mancanti. Messaggio non inviato.")
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown",
        "disable_web_page_preview": True
    }
    try:
        res = requests.post(url, data=payload)
        if res.status_code != 200:
            print(f"❌ Errore invio Telegram: {res.text}")
    except Exception as e:
        print(f"❌ Eccezione invio Telegram: {e}")

def get_article_links():
    links = []
    page = 1
    while True:
        url = f"{AUTHOR_URL}page/{page}/"
        res = requests.get(url, headers=HEADERS)
        if res.status_code != 200:
            break
        soup = BeautifulSoup(res.text, "html.parser")
        articles = soup.select("h2.entry-title > a")
        if not articles:
            break
        for a in articles:
            links.append({"title": a.text.strip(), "url": a["href"]})
        page += 1
        time.sleep(random.uniform(1, 2))
    return links

def get_author_from_article(url):
    try:
        res = requests.get(url, headers=HEADERS, timeout=10)
        if res.status_code != 200:
            return None
        soup = BeautifulSoup(res.text, "html.parser")
        author_tag = soup.select_one("span.author.vcard")
        if not author_tag:
            return None
        return author_tag.text.strip()
    except Exception as e:
        print(f"Errore leggendo {url}: {e}")
        return None

def main():
    old_data = load_articles_history()
    new_data = {}

    articles = get_article_links()
    for article in articles:
        author = get_author_from_article(article["url"])
        new_data[article["url"]] = {
            "title": article["title"],
            "author": author
        }
        time.sleep(random.uniform(1, 2))

    changes = []
    for url, info in new_data.items():
        if url not in old_data:
            changes.append(f"🆕 *Nuovo articolo:* [{info['title']}]({url})")
        elif old_data[url]["author"] != info["author"]:
            changes.append(
                f"✏️ *Autore cambiato* per [{info['title']}]({url}):\n"
                f"da _{old_data[url]['author']}_ a _{info['author']}_"
            )

    for url in old_data:
        if url not in new_data:
            changes.append(f"🗑️ *Articolo rimosso:* [{old_data[url]['title']}]({url})")

    if changes:
        message = "🚨 *Modifiche rilevate negli articoli:*\n\n" + "\n\n".join(changes)
        print(message)
        send_telegram_message(message)
        save_articles_history(new_data)
    else:
        print("✅ Nessuna modifica rilevata.")

if __name__ == "__main__":
    main()
