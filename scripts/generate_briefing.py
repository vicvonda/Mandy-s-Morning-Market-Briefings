#!/usr/bin/env python3
"""Generate Mandy's Morning Market Briefing using Claude with web search."""

import anthropic
import os
from datetime import datetime

def generate_briefing():
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    today = datetime.now().strftime("%A, %B %-d, %Y")

    prompt = f"""Today is {today}. Generate Mandy's Morning Market Briefing.

RULES:
- Output ONLY the briefing. No preamble, no "I'll search for...", no meta-commentary. Start directly with the first section header.
- Be ruthlessly concise. Max 4 bullets per subsection. Only include what's genuinely striking or actionable.
- Skip any subsection where there's nothing material to report.
- Add timestamps wherever possible (e.g. [June 2, premarket], [May 15, CNBC]).

Search for: index levels + moves, top stock movers, premarket action, key economic events this week, earnings this week, Trump/family Truth Social posts + stock trades + business deals + DJT stock price.

Output using EXACTLY this format — no extra headers, no markdown bold on subsection labels:

## SECTION 1 — MARKET SNAPSHOT

[Previous close → Today] One-line index summary: S&P 500, Nasdaq, Dow, Russell 2000 % moves and the single biggest driver.

[Today, open] Top movers at open — ticker +/-% and one-line reason. Max 4.

[Today, premarket] Notable premarket movers with context. Max 3.

[Week ahead — macro] Key dates only: jobs report, CPI, Fed, major earnings. Max 4 bullets.

[Earnings season] Standout beats/misses this week only. Max 3 bullets.

---

## SECTION 2 — TRUMP & FAMILY ACTIVITY

[Date, source] Trump stock trades or OGE disclosures — what he bought/sold and when.

[Date, source] Trump Truth Social or public statements naming companies/sectors — exact quote if possible, market reaction.

[Ongoing] Trump sons (Eric, Don Jr.) deals, investments, crypto activity this week.

[Today] DJT price, % move, any news.

---

## SECTION 3 — OVERLAP: Market Movers + Trump Exposure

| Ticker / Sector | Market Signal | Trump/Family Angle |
|---|---|---|
| Only rows that appear in BOTH sections above | | |

---

KEY RISKS
- Risk 1 (most urgent)
- Risk 2
- Risk 3

Sources: List every source you actually used as markdown links. Use the real article URL where possible, not just the homepage. Format: [Publication Name](https://full-url.com/article) · [Publication Name](https://...) — include as many as you referenced, minimum 5.
"""

    response = client.messages.create(
        model="claude-opus-4-8",
        max_tokens=4096,
        tools=[{
            "type": "web_search_20250305",
            "name": "web_search",
            "max_uses": 15
        }],
        messages=[{"role": "user", "content": prompt}]
    )

    briefing = ""
    for block in response.content:
        if hasattr(block, "text"):
            briefing += block.text

    # Strip any preamble before the first section header
    import re
    match = re.search(r'(##\s*SECTION|SECTION\s+1)', briefing)
    if match:
        briefing = briefing[match.start():]

    output_path = "/tmp/claude_briefing.md"
    with open(output_path, "w") as f:
        f.write(briefing)

    print(f"Briefing written to {output_path}")
    print(briefing[:500])

if __name__ == "__main__":
    generate_briefing()
