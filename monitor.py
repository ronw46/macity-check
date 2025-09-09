import requests
from bs4 import BeautifulSoup
import json
import time
import os

AUTHOR_URL = "https://www.macitynet.it/author/yuri/"
EXPECTED_AUTHOR = "Yuri Di Prodo"
HEADERS = {"User-Agent": "Mozilla/5.0"}

def get_article_links():
    links = []
    page = 1
    print("🔍 Raccolta articoli da pagina autore...")
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
            href = a["href"]
            title = a.text.strip()
            links.append({"title": title, "url": href})
        page += 1
        time.sleep(0.5)
    print(f"✅ Trovati {len(links)} articoli.")
    return links

def check_author(article):
    res = requests.get(article["url"], headers=HEADERS)
    if res.status_code != 200:
        return "NOT_FOUND"
    soup = BeautifulSoup(res.text, "html.parser")
    text = soup.get_text()
    if EXPECTED_AUTHOR not in text:
        return "AUTHOR_CHANGED"
    return "OK"

def load_previous():
    try:
        with open("articles.json", "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_current(articles):
    with open("articles.json", "w") as f:
        json.dump(articles, f, indent=2)

def send_telegram(message):
    token = os.getenv("TELEGRAM_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message[:4000],  # Telegram message limit
        "parse_mode": "HTML"
    }
    try:
        r = requests.post(url, data=payload)
        if not r.ok:
            print(f"❌ Errore Telegram: {r.status_code} {r.text}")
    except Exception as e:
        print(f"❌ Errore Telegram: {e}")

def main():
    current_articles = get_article_links()
    previous_articles = load_previous()
    current_urls = {a["url"]: a["title"] for a in current_articles}
    previous_urls = set(previous_articles.keys())

    removed = previous_urls - set(current_urls.keys())
    changes = []

    # Controlla autore per ogni articolo
    for article in current_articles:
        status = check_author(article)
        if status == "AUTHOR_CHANGED":
            changes.append(f"❗ Autore cambiato:\n{article['title']}\n{article['url']}")
        elif status == "NOT_FOUND":
            changes.append(f"❌ Articolo non raggiungibile:\n{article['title']}\n{article['url']}")
        time.sleep(0.5)

    save_current({a["url"]: a["title"] for a in current_articles})

    if removed or changes:
        message = "<b>📡 Monitor WordPress - Cambiamenti rilevati</b>\n\n"
        if removed:
            message += f"⚠️ Articoli rimossi ({len(removed)}):\n"
            for url in removed:
                message += f"- {previous_articles[url]}\n"
        if changes:
            message += "\n" + "\n\n".join(changes)
        send_telegram(message)
    else:
        print("✅ Nessun cambiamento rilevato.")

if __name__ == "__main__":
    main()
