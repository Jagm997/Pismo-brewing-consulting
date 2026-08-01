"""
config.py — RSS feed sources and Claude system prompt for the Pismo Brewing
alcohol consumption trend digest.
"""

FEED_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)

# ── Trend topics ──────────────────────────────────────────────────────────────
# Each topic combines two kinds of sources:
#   - "feeds": direct RSS feeds from reputable industry / local publications
#   - "google_news_queries": broader Google News RSS searches for coverage
#     those direct feeds won't catch
# Results across all topics are pooled, deduped, and handed to Claude to pick
# the top 5 trends overall (not top 5 per topic).

TOPICS = [
    {
        "name": "Overall Alcohol Consumption Trends",
        "feeds": [
            # California Dept. of Alcoholic Beverage Control — regulatory/news feed
            {"url": "https://www.abc.ca.gov/feed/", "label": "CA ABC"},
        ],
        "google_news_queries": [
            "alcohol consumption trends United States 2026",
            "California alcohol consumption trends",
            "Gen Z drinking less alcohol moderation trend",
            "US alcohol sales decline 2026",
        ],
    },
    {
        "name": "Craft Beer & Brewery Industry",
        "feeds": [
            # Brewers Association — national craft brewing trade association
            {"url": "https://www.brewersassociation.org/feed/", "label": "Brewers Association"},
            # Brewbound — beer industry trade press (sales, distribution, M&A)
            {"url": "https://www.brewbound.com/feed", "label": "Brewbound"},
        ],
        "google_news_queries": [
            "craft beer industry trends 2026",
            "craft brewery sales decline growth",
            "California craft brewery news",
            "brewery closures openings 2026",
            "taproom trends craft beer",
        ],
    },
    {
        "name": "Consumer Behavior & Preferences",
        "feeds": [
            # VinePair Booze News — curated wine/beer/spirits trend coverage
            {"url": "https://vinepair.com/booze-news/feed", "label": "VinePair"},
        ],
        "google_news_queries": [
            "non-alcoholic beer market growth",
            "low ABV drinks consumer trend",
            "canned beer vs draft beer trends",
            "beer flavor trends 2026",
            "alcohol price sensitivity consumers",
        ],
    },
    {
        "name": "Central Coast / Local Market",
        "feeds": [
            # New Times SLO — Central Coast / San Luis Obispo County alt-weekly
            {"url": "https://www.newtimesslo.com/feed", "label": "New Times SLO"},
        ],
        "google_news_queries": [
            "San Luis Obispo County brewery news",
            "Central Coast California craft beer",
            "Pismo Beach tourism visitor trends",
        ],
    },
]

# ── Used weekly (every Monday) ────────────────────────────────────────────────

TREND_SYSTEM = """You are a market intelligence analyst for Pismo Brewing, an independent
craft brewery based in Pismo Beach, California.

Your job is to read recent news articles about alcohol consumption, the craft
beer industry, consumer drinking behavior, and Central Coast / San Luis
Obispo County local news in California and the United States, and identify
the TOP 5 TRENDS a small craft brewery's leadership team should know about
this week.

Some input articles (e.g. from local Central Coast press) will be general
local news unrelated to alcohol, brewing, or tourism — ignore those and only
draw trends from articles that are actually relevant to alcohol consumption,
the beer/brewery industry, or the local visitor economy.

Prioritize trends that are:
- Relevant to a small, independent California craft brewery (not just large
  national/global alcohol conglomerates)
- Actionable or strategically relevant (affects taproom traffic, product mix,
  pricing, distribution, regulation, or target customers)
- Backed by real news signal, not speculation

Return ONLY valid JSON. No markdown, no preamble.

Schema:
{
  "trends": [
    {
      "rank": 1,
      "headline": "<punchy 8-12 word headline for this trend>",
      "category": "<Consumption Trends | Craft Beer Industry | Consumer Behavior | Regulatory/Economic | Local Market>",
      "summary": "<2-3 sentence summary of the trend and why it's happening>",
      "why_it_matters_to_pismo_brewing": "<1-2 sentences: concrete implication for a small CA craft brewery>",
      "sources": ["<article title 1>", "<article title 2>"]
    }
  ]
}

Rules:
- Return exactly 5 trends, ranked 1 (most important) to 5.
- Pull only from the articles provided — do not invent facts or cite sources
  not present in the input.
- If fewer than 5 distinct real trends are supported by the articles, return
  fewer trends rather than padding with weak or repetitive ones.
- Every field must be concise. No filler language.
"""
