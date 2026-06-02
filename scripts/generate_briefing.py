#!/usr/bin/env python3
"""Generate Mandy's Morning Market Briefing using Claude with web search."""

import anthropic
import os
from datetime import datetime

def generate_briefing():
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    today = datetime.now().strftime("%A, %B %-d, %Y")

    prompt = f"""Today is {today}. You are generating Mandy's Morning Market Briefing.

Search for the latest:
- S&P 500, Nasdaq, Dow, Russell 2000 levels and moves (previous close and today's open/premarket)
- Top individual stock movers today (% changes and reasons)
- Notable premarket movers with context
- Key economic data releases and Fed activity this week
- Major earnings reports this week and any recent beats/misses
- Any Trump or Trump family (Eric, Don Jr., Ivanka, Jared) public statements, Truth Social posts, or news mentioning specific companies, sectors, or markets
- Trump personal stock trades or financial disclosures (recent)
- Trump family business activity: investments, deals, crypto, company stakes
- DJT (Trump Media) stock price and any notable moves
- Add timestamps wherever possible

Generate the briefing using EXACTLY this format:

# MANDY'S MORNING MARKET BRIEFING
**{today} | Generated ~10:00 AM ET**

---

## SECTION 1 — MARKET SNAPSHOT

**[Previous close → Today] Indexes**
- [bullets: S&P 500, Nasdaq, Dow, Russell 2000 with % moves and key drivers]

**[Today, open] Top Individual Movers**
- [bullets: ticker, %, reason]

**[Today, premarket] Notable Movers**
- [bullets: ticker, %, context]

**[Week ahead — macro]**
- [bullets: dates and events]

**[Earnings season]**
- [bullets: key reports this week and themes]

---

## SECTION 2 — TRUMP & FAMILY ACTIVITY

**[Date, source] Trump Stock Trades / Financial Activity**
- [bullets]

**[Date, source] Trump Public Statements**
- [what he said, market reaction]

**[Ongoing] Trump Family Business Activity**
- [Eric, Don Jr. deals, investments, crypto]

**[Today] DJT Stock**
- [price, move, context]

---

## SECTION 3 — OVERLAP: Market Movers + Trump Exposure

| Ticker / Sector | Market Signal | Trump/Family Angle |
|---|---|---|
| [only include if in BOTH sections above] | | |

---

## KEY RISKS
- Risk 1
- Risk 2
- Risk 3
- Risk 4

---

*Sources: [TheStreet](https://thestreet.com) · [Yahoo Finance](https://finance.yahoo.com) · [CNBC](https://cnbc.com) · [Bloomberg](https://bloomberg.com)*
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

    output_path = "/tmp/claude_briefing.md"
    with open(output_path, "w") as f:
        f.write(briefing)

    print(f"Briefing written to {output_path}")
    print(briefing[:500])

if __name__ == "__main__":
    generate_briefing()
