import requests
from bs4 import BeautifulSoup
import json
import time

AUTHOR_URL = "https://www.macitynet.it/author/yuri/"
EXPECTED_AUTHOR = "Yuri Di Prodo"
MAX_ARTICLES = 1000
HEADERS = {"User-Agent": "Mozilla/5.0"}

def get_article_links():
    links = []
    page = 1
    while len(links) < MAX_ARTICLES:
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
            if len(links) >= MAX_ARTICLES:
                break
        page += 1
        time.sleep(1)
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

def main():
    print("🔍 Scanning latest articles...")
    current_articles = get_article_links()
    previous_articles = load_previous()
    current_urls = {a["url"]: a["title"] for a in current_articles}
    previous_urls = set(previous_articles.keys())

    removed = previous_urls - set(current_urls.keys())
    added = set(current_urls.keys()) - previous_urls

    if removed:
        print(f"⚠️ {len(removed)} articles missing from current list:")
        for url in removed:
            print(f" - {previous_articles[url]} ({url})")

    for article in current_articles:
        status = check_author(article)
        if status == "AUTHOR_CHANGED":
            print(f"❗ Author changed: {article['title']} ({article['url']})")
        elif status == "NOT_FOUND":
            print(f"❌ Article not reachable: {article['title']} ({article['url']})")
        time.sleep(1)

    save_current({a["url"]: a["title"] for a in current_articles})
    print("✅ Done.")

if __name__ == "__main__":
    main()
