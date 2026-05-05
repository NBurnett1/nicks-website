#!/usr/bin/env python3
"""
fetch_top_stories.py — Daily financial news aggregator.

Fetches top stories from Google News RSS feeds, extracts summaries,
and saves to public/data/top_stories.json for instant frontend loading.

Runs daily via GitHub Actions. Frontend reads the pre-cached file first,
then supplements with live client-side feeds.
"""

import json
import os
import re
import sys
from datetime import datetime, timezone
from html import unescape
from pathlib import Path

try:
    import feedparser
except ImportError:
    print("Installing feedparser...")
    os.system(f"{sys.executable} -m pip install feedparser")
    import feedparser

# ── Configuration ──────────────────────────────────────────────
DATA_DIR = Path(__file__).parent.parent / "public" / "data"
OUTPUT_FILE = DATA_DIR / "top_stories.json"

# RSS Feeds — Google News searches for financial topics
FEEDS = [
    {
        "url": "https://news.google.com/rss/search?q=global+financial+markets+economy+stocks&hl=en-AU&gl=AU&ceid=AU:en",
        "category": "Markets",
        "icon": "🌐",
    },
    {
        "url": "https://news.google.com/rss/search?q=ASX+Australian+stock+market+economy&hl=en-AU&gl=AU&ceid=AU:en",
        "category": "ASX",
        "icon": "🇦🇺",
    },
    {
        "url": "https://news.google.com/rss/search?q=interest+rates+central+bank+inflation+GDP&hl=en-AU&gl=AU&ceid=AU:en",
        "category": "Economy",
        "icon": "🏛️",
    },
    {
        "url": "https://news.google.com/rss/search?q=stock+market+earnings+investing&hl=en-US&gl=US&ceid=US:en",
        "category": "Investing",
        "icon": "📈",
    },
]

MAX_TOP_STORIES = 5
MAX_FEED_ARTICLES = 20


def clean_html(text: str) -> str:
    """Strip HTML tags and decode entities."""
    if not text:
        return ""
    text = re.sub(r"<[^>]*>", "", text)
    text = unescape(text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def clean_title(title: str) -> str:
    """Remove source suffix from Google News titles (e.g., 'Headline - Source')."""
    return re.sub(r"\s*[-–—]\s*[^-–—]+$", "", title).strip()


def extract_source(entry) -> str:
    """Extract source name from RSS entry."""
    source = getattr(entry, "source", None)
    if source and hasattr(source, "title"):
        return source.title
    # Google News often puts source in the title suffix
    match = re.search(r"[-–—]\s*(.+)$", entry.get("title", ""))
    if match:
        return match.group(1).strip()
    return "News"


def truncate_summary(text: str, max_len: int = 300) -> str:
    """Truncate text at a sentence boundary."""
    if len(text) <= max_len:
        return text
    truncated = text[:max_len]
    last_period = truncated.rfind(".")
    if last_period > 100:
        return truncated[: last_period + 1]
    return truncated + "…"


def get_source_icon(source: str) -> str:
    """Map known sources to emoji icons."""
    source_lower = source.lower()
    icon_map = {
        "reuters": "🌐",
        "cnbc": "📺",
        "bloomberg": "💹",
        "afr": "🇦🇺",
        "australian financial review": "🇦🇺",
        "marketwatch": "📊",
        "financial times": "📰",
        "ft": "📰",
        "yahoo": "📈",
        "livewire": "⚡",
        "abc": "🇦🇺",
        "nine": "🇦🇺",
        "the guardian": "📰",
        "wall street journal": "📰",
        "wsj": "📰",
    }
    for key, icon in icon_map.items():
        if key in source_lower:
            return icon
    return "🌐"


def fetch_all_articles() -> list:
    """Fetch articles from all configured RSS feeds."""
    all_articles = []

    for feed_config in FEEDS:
        try:
            print(f"  Fetching {feed_config['category']}...")
            feed = feedparser.parse(feed_config["url"])

            if not feed.entries:
                print(f"    ⚠ No entries from {feed_config['category']}")
                continue

            for entry in feed.entries[:MAX_FEED_ARTICLES]:
                title_raw = entry.get("title", "")
                source = extract_source(entry)
                title = clean_title(title_raw)

                if not title or len(title) < 10:
                    continue

                # Extract summary from description or content
                summary_raw = entry.get("summary", "") or entry.get("description", "")
                summary = clean_html(summary_raw)
                summary = truncate_summary(summary)

                # Parse publication date
                pub_date = entry.get("published", entry.get("updated", ""))

                article = {
                    "title": title,
                    "url": entry.get("link", ""),
                    "source": source,
                    "sourceIcon": get_source_icon(source),
                    "category": feed_config["category"],
                    "summary": summary if len(summary) > 20 else f"Latest {feed_config['category'].lower()} news and analysis from {source}.",
                    "pubDate": pub_date,
                    "fetchedAt": datetime.now(timezone.utc).isoformat(),
                }
                all_articles.append(article)

            print(f"    ✓ Got {min(len(feed.entries), MAX_FEED_ARTICLES)} articles")

        except Exception as e:
            print(f"    ✗ Error fetching {feed_config['category']}: {e}")

    return all_articles


def deduplicate_and_rank(articles: list) -> list:
    """Deduplicate by title similarity and rank by recency."""
    seen_titles = set()
    unique = []

    # Sort by date (most recent first)
    articles.sort(key=lambda a: a.get("pubDate", ""), reverse=True)

    for article in articles:
        # Normalize title for dedup
        key = re.sub(r"[^a-z0-9]", "", article["title"].lower())[:50]
        if key in seen_titles:
            continue
        seen_titles.add(key)
        unique.append(article)

    return unique


def main():
    print("═" * 50)
    print("📰 Fetching daily top stories...")
    print("═" * 50)

    articles = fetch_all_articles()
    print(f"\n  Total raw articles: {len(articles)}")

    ranked = deduplicate_and_rank(articles)
    print(f"  After dedup: {len(ranked)}")

    # Split into top stories and feed articles
    top_stories = ranked[:MAX_TOP_STORIES]
    feed_articles = ranked[MAX_TOP_STORIES:MAX_TOP_STORIES + 15]

    output = {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "topStories": top_stories,
        "feedArticles": feed_articles,
        "totalFetched": len(articles),
    }

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.write_text(json.dumps(output, indent=2, ensure_ascii=False))

    print(f"\n  ✓ Saved {len(top_stories)} top stories + {len(feed_articles)} feed articles")
    print(f"  → {OUTPUT_FILE}")

    # Print top stories
    print("\n  📌 Today's Top Stories:")
    for i, story in enumerate(top_stories, 1):
        print(f"     {i}. [{story['source']}] {story['title']}")
        if story.get("summary"):
            print(f"        → {story['summary'][:100]}...")

    print("\n" + "═" * 50)


if __name__ == "__main__":
    main()
