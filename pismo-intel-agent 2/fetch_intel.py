"""
fetch_intel.py — Pismo Brewing Alcohol Consumption Trend Digest

Fetches recent news via Google News RSS, asks Claude to identify the top 5
alcohol consumption trends relevant to a California craft brewery, and emails
a formatted digest.

Usage:
    python fetch_intel.py                  # regular weekly run
    python fetch_intel.py --dry-run        # fetch feeds only, skip Claude + email
    python fetch_intel.py --hours 168      # lookback window (default 7 days)
"""

import argparse
import json
import os
import smtplib
import time
from datetime import datetime, timedelta, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from urllib.parse import quote_plus

import anthropic
import feedparser
from dotenv import load_dotenv

from config import FEED_USER_AGENT, TOPICS, TREND_SYSTEM

load_dotenv()

FEED_FILE = "trend_digest.json"
LOOKBACK_HOURS = 168  # 7 days

CATEGORY_COLORS = {
    "Consumption Trends": "#2563eb",
    "Craft Beer Industry": "#d97706",
    "Consumer Behavior": "#16a34a",
    "Regulatory/Economic": "#dc2626",
    "Local Market": "#7c3aed",
}


# ── RSS FETCHING ──────────────────────────────────────────────────────────────

def google_news_url(query: str) -> str:
    return (
        "https://news.google.com/rss/search"
        f"?q={quote_plus(query)}&hl=en-US&gl=US&ceid=US:en"
    )


def fetch_feed(url: str, cutoff: datetime, source_label: str = "") -> list[dict]:
    items = []
    try:
        feed = feedparser.parse(url, agent=FEED_USER_AGENT)
        status = getattr(feed, "status", 0)
        if status in (403, 404, 410):
            print(f"      ↳ HTTP {status}: {url[:65]}")
            return []
        for entry in feed.entries[:8]:
            pub = entry.get("published_parsed") or entry.get("updated_parsed")
            if pub:
                pub_dt = datetime(*pub[:6], tzinfo=timezone.utc)
                if pub_dt < cutoff:
                    continue
            title = (entry.get("title") or "").strip()
            if not title:
                continue
            entry_source = entry.get("source", {}).get("title", "") if hasattr(entry, "get") else ""
            items.append({
                "title": title,
                "summary": (entry.get("summary") or "")[:400].strip(),
                "published": entry.get("published", "unknown date"),
                "source": source_label or entry_source,
            })
    except Exception as e:
        print(f"      ↳ Feed error: {e}")
    return items


def fetch_topic_items(topic: dict, hours: int) -> list[dict]:
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    all_items = []

    # Direct RSS feeds (industry / local press) — highest signal
    for feed_cfg in topic.get("feeds", []):
        label = feed_cfg.get("label", "")
        items = fetch_feed(feed_cfg["url"], cutoff, source_label=label)
        if items:
            print(f"      ✓ {len(items)} via feed: {label}")
        all_items.extend(items)
        time.sleep(0.3)

    # Broader Google News RSS queries
    for query in topic.get("google_news_queries", []):
        items = fetch_feed(google_news_url(query), cutoff)
        if items:
            print(f"      ✓ {len(items)} via: '{query}'")
        all_items.extend(items)
        time.sleep(0.3)

    seen, deduped = set(), []
    for item in all_items:
        key = item["title"].lower()[:80]
        if key and key not in seen:
            seen.add(key)
            deduped.append(item)

    return deduped[:20]


# ── CLAUDE HELPERS ────────────────────────────────────────────────────────────

def parse_json(raw: str) -> dict:
    raw = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        start, end = raw.find("{"), raw.rfind("}")
        if start != -1 and end != -1:
            return json.loads(raw[start:end + 1])
        raise ValueError(f"Could not parse JSON:\n{raw[:400]}")


def call_claude(prompt: str, system: str) -> dict:
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=4096,
        system=system,
        messages=[{"role": "user", "content": prompt}],
    )
    if response.stop_reason == "max_tokens":
        print("  ⚠ Truncated — retrying in concise mode...")
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=4096,
            system=system,
            messages=[{"role": "user", "content": prompt + (
                "\n\nCRITICAL: Response was truncated. Be extremely concise. "
                "Return only valid JSON. Stop after closing brace."
            )}],
        )
    return parse_json(response.content[0].text)


# ── TREND ANALYSIS ───────────────────────────────────────────────────────────

def run_trend_analysis(all_items: dict) -> dict:
    lines = [
        "Here are recent news articles gathered this week, grouped by topic area.",
        "Identify the TOP 5 alcohol consumption trends most relevant to Pismo",
        "Brewing, a craft brewery in Pismo Beach, California.\n",
    ]

    for topic_name, items in all_items.items():
        lines.append(f"## {topic_name}")
        if not items:
            lines.append("No new articles this week.\n")
            continue
        for item in items:
            src = f" [{item['source']}]" if item.get("source") else ""
            lines.append(f"- {item['title']}{src} ({item['published']})")
            if item["summary"]:
                lines.append(f"  {item['summary'][:250]}")
        lines.append("")

    lines.append("\nReturn only the JSON with the top 5 trends, ranked most to least important.")
    prompt = "\n".join(lines)

    result = call_claude(prompt, TREND_SYSTEM)
    trends = result.get("trends", [])
    print(f"  ✓ {len(trends)} trends identified")
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "trends": trends,
    }


# ── JSON SAVE ─────────────────────────────────────────────────────────────────

def save_json(data: dict, path: str) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"✓ Saved → {path}")


# ── EMAIL BUILDER ─────────────────────────────────────────────────────────────

def _ul(items: list) -> str:
    if not items:
        return "<span style='color:#94a3b8;font-size:12px'>None noted</span>"
    lis = "".join(f"<li style='margin-bottom:3px'>{i}</li>" for i in items if i)
    return f"<ul style='margin:4px 0;padding-left:16px;font-size:12px'>{lis}</ul>"


def build_digest_email(data: dict) -> str:
    trends = sorted(data.get("trends", []), key=lambda t: t.get("rank", 99))
    generated = data.get("generated_at", "")

    cards = ""
    for t in trends:
        category = t.get("category", "")
        color = CATEGORY_COLORS.get(category, "#64748b")
        cards += (
            f"<div style='margin-bottom:20px;border:1px solid #e2e8f0;border-left:4px solid {color};"
            f"padding:14px 18px;border-radius:4px'>"
            f"<div style='font-size:11px;color:{color};font-weight:bold;text-transform:uppercase;margin-bottom:4px'>"
            f"#{t.get('rank','')} &nbsp;·&nbsp; {category}</div>"
            f"<h3 style='margin:0 0 8px 0;color:#1e293b;font-size:16px'>{t.get('headline','')}</h3>"
            f"<p style='margin:0 0 10px 0;font-size:13px;color:#374151;line-height:1.5'>{t.get('summary','')}</p>"
            f"<div style='background:#f0fdf4;border:1px solid #bbf7d0;padding:8px 12px;border-radius:4px;font-size:12px;color:#166534'>"
            f"<strong>🍺 Why it matters for Pismo Brewing:</strong> {t.get('why_it_matters_to_pismo_brewing','')}"
            f"</div>"
            + (f"<div style='margin-top:8px;font-size:11px;color:#94a3b8'>Sources: {', '.join(t.get('sources', []))}</div>"
               if t.get('sources') else "")
            + "</div>"
        )

    if not trends:
        cards = "<p style='color:#64748b;font-size:13px'>No significant trends identified this week.</p>"

    return (
        "<!DOCTYPE html><html><body style='font-family:Arial,sans-serif;max-width:720px;margin:0 auto;padding:28px;color:#1e293b'>"
        "<h1 style='color:#92400e;margin-bottom:2px'>🍺 Pismo Brewing</h1>"
        "<h2 style='font-weight:normal;color:#64748b;margin-top:0;font-size:15px'>Weekly Alcohol Consumption Trend Digest</h2>"
        f"<p style='color:#94a3b8;font-size:11px;border-bottom:1px solid #e2e8f0;padding-bottom:14px'>Generated: {generated}</p>"
        f"<p style='font-size:13px;color:#374151'>Top 5 trends in California &amp; U.S. alcohol consumption this week:</p>"
        + cards
        + "<hr style='border:none;border-top:1px solid #e2e8f0;margin:28px 0'>"
        "<p style='font-size:11px;color:#94a3b8'>Pismo Brewing Trend Digest · Every Monday · Powered by Claude</p>"
        "</body></html>"
    )


# ── EMAIL SEND (Gmail SMTP) ───────────────────────────────────────────────────

def send_email(subject: str, html: str) -> None:
    from_addr = os.getenv("EMAIL_FROM")
    to_addr = os.getenv("EMAIL_TO")
    app_password = os.getenv("EMAIL_PASSWORD")
    smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))

    if not all([from_addr, to_addr, app_password]):
        print("⚠  EMAIL_FROM / EMAIL_TO / EMAIL_PASSWORD not set. Skipping email.")
        return

    recipients = [a.strip() for a in to_addr.split(",")]

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = from_addr
    msg["To"] = ", ".join(recipients)
    msg.attach(MIMEText(html, "html"))

    try:
        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.starttls()
            server.login(from_addr, app_password)
            server.sendmail(from_addr, recipients, msg.as_string())
        print(f"✓ Email sent → {', '.join(recipients)}")
    except Exception as e:
        print(f"✗ Email failed: {e}")


# ── MAIN ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Pismo Brewing Trend Digest")
    parser.add_argument("--dry-run", action="store_true", help="Fetch feeds only, skip Claude + email")
    parser.add_argument("--hours", type=int, default=LOOKBACK_HOURS, help="Lookback window in hours")
    args = parser.parse_args()

    print(f"\nPismo Brewing Trend Digest — {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    date_str = datetime.now().strftime("%b %d, %Y")

    print(f"Lookback: {args.hours}h  |  Topics: {len(TOPICS)}\n")

    all_items: dict[str, list] = {}
    for topic in TOPICS:
        print(f"  {topic['name']}")
        items = fetch_topic_items(topic, hours=args.hours)
        all_items[topic["name"]] = items
        print(f"    → {len(items)} items\n")

    total = sum(len(v) for v in all_items.values())
    print(f"Total items: {total}")

    if args.dry_run:
        print("\n[dry-run] Skipping Claude + email.")
        return

    print("\nRunning Claude analysis...")
    result = run_trend_analysis(all_items)

    save_json(result, FEED_FILE)
    send_email(
        subject=f"Pismo Brewing — Weekly Alcohol Trend Digest — {date_str}",
        html=build_digest_email(result),
    )
    print("\nDone.\n")


if __name__ == "__main__":
    main()
