"""
Daily Tech News Agent
----------------------
Fetches recent tech news from feeds around the world, asks Claude to pick
the 5 most important stories and translate/summarize them in English,
then emails the result.

Required environment variables (set these as GitHub Actions "secrets"):
  ANTHROPIC_API_KEY   - your Claude API key
  GMAIL_ADDRESS       - the Gmail account that will SEND the email
  GMAIL_APP_PASSWORD  - an "app password" generated for that Gmail account
  TO_EMAIL            - your father's email address (where the digest goes)
"""

import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

import feedparser
import anthropic

# A mix of tech news sources from different countries/languages.
# Feel free to add/remove feeds.
RSS_FEEDS = [
    "https://techcrunch.com/feed/",            # USA
    "https://www.theverge.com/rss/index.xml",  # USA
    "https://arstechnica.com/feed/",           # USA
    "http://feeds.bbci.co.uk/news/technology/rss.xml",  # UK
    "https://www.heise.de/rss/heise-atom.xml", # Germany (German)
    "https://www.lemonde.fr/pixels/rss_full.xml",       # France (French)
    "https://japan.cnet.com/rss/index.rdf",    # Japan (Japanese)
    "https://www.itmedia.co.jp/news/rss/2.0/itmedia_all.xml", # Japan (Japanese)
]

MAX_ARTICLES_PER_FEED = 8


def fetch_articles():
    """Pull recent articles from all feeds."""
    articles = []
    for url in RSS_FEEDS:
        try:
            feed = feedparser.parse(url)
            source_name = feed.feed.get("title", url)
            for entry in feed.entries[:MAX_ARTICLES_PER_FEED]:
                articles.append({
                    "title": entry.get("title", ""),
                    "summary": entry.get("summary", "")[:500],
                    "link": entry.get("link", ""),
                    "source": source_name,
                })
        except Exception as e:
            print(f"Could not read feed {url}: {e}")
    return articles


def build_prompt(articles):
    listing = "\n\n".join(
        f"[{i}] Source: {a['source']}\nTitle: {a['title']}\nSummary: {a['summary']}\nLink: {a['link']}"
        for i, a in enumerate(articles)
    )

    return f"""You are a tech news curator preparing a short daily digest for someone
who reads only English.

Below is a list of recent tech news items from sources around the world.
Some are in languages other than English.

Your job:
1. Choose the 5 most important / interesting tech news stories overall
   (prioritize variety of topics and global relevance, not just one source).
2. For each chosen story, write in ENGLISH:
   - A short translated/clear title
   - A 2-3 sentence summary in English (translate if the original wasn't English)
   - The original source name
   - The link
3. Write a short, warm one-line intro at the top (addressed to "Dad").

Format the whole thing as plain text suitable for an email body. Number the
stories 1-5. Do not include any preamble, explanation, or notes outside the
email content itself.

Articles:

{listing}
"""


def get_digest(articles, api_key):
    client = anthropic.Anthropic(api_key=api_key)
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2000,
        messages=[{"role": "user", "content": build_prompt(articles)}],
    )
    return response.content[0].text


def send_email(body, from_addr, app_password, to_addr):
    msg = MIMEMultipart()
    msg["From"] = from_addr
    msg["To"] = to_addr
    msg["Subject"] = "Your Daily Tech News Digest"
    msg.attach(MIMEText(body, "plain"))

    with smtplib.SMTP("smtp.gmail.com", 587) as server:
        server.starttls()
        server.login(from_addr, app_password)
        server.sendmail(from_addr, to_addr, msg.as_string())


def main():
    api_key = os.environ["ANTHROPIC_API_KEY"]
    from_addr = os.environ["GMAIL_ADDRESS"]
    app_password = os.environ["GMAIL_APP_PASSWORD"]
    to_addr = os.environ["TO_EMAIL"]

    print("Fetching articles...")
    articles = fetch_articles()
    print(f"Fetched {len(articles)} articles total.")

    print("Asking Claude to pick and translate top 5...")
    digest = get_digest(articles, api_key)

    print("Sending email...")
    send_email(digest, from_addr, app_password, to_addr)
    print("Done!")


if __name__ == "__main__":
    main()
