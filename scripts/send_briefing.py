#!/usr/bin/env python3
"""
Mandy's Morning Market Briefing — send_briefing.py
Usage:  echo "briefing text" | python3 send_briefing.py
Auth:   python3 send_briefing.py --auth   (one-time OAuth setup)
"""

import os, sys, re, base64, argparse, smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import date

SCOPES      = ["https://www.googleapis.com/auth/gmail.send"]
TOKEN_PATH  = os.path.expanduser("~/.gmail_token.json")
CREDS_PATH  = os.path.expanduser("~/.gmail_credentials.json")
TO_EMAIL    = "twanbeauty@gmail.com"
SMS_EMAIL   = "18622521290@tmomail.net"
PHOTO_URL   = "https://drive.google.com/uc?export=view&id=1Db8RkN1QMo5TIeo9hm2tRlknaZ_17sst"


def get_credentials():
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials

    # Headless / GitHub Actions: build creds directly from env vars
    client_id     = os.environ.get("GMAIL_CLIENT_ID")
    client_secret = os.environ.get("GMAIL_CLIENT_SECRET")
    refresh_token = os.environ.get("GMAIL_REFRESH_TOKEN")

    if client_id and client_secret and refresh_token:
        creds = Credentials(
            token=None,
            refresh_token=refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=client_id,
            client_secret=client_secret,
            scopes=SCOPES,
        )
        creds.refresh(Request())
        return creds

    # Local dev fallback: file-based token
    from google_auth_oauthlib.flow import InstalledAppFlow
    creds = None
    if os.path.exists(TOKEN_PATH):
        creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(CREDS_PATH):
                print(f"ERROR: credentials not found at {CREDS_PATH}", file=sys.stderr)
                sys.exit(1)
            flow = InstalledAppFlow.from_client_secrets_file(CREDS_PATH, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(TOKEN_PATH, "w") as f:
            f.write(creds.to_json())
    return creds


TICKER_EMOJIS = {
    "NVDA": "🤖", "AAPL": "🍎", "MSFT": "🪟", "AMZN": "📦", "GOOGL": "🔍",
    "GOOG": "🔍", "META": "👁️", "TSLA": "⚡", "PLTR": "🛡️", "AVGO": "💻",
    "CRWD": "🔐", "HPE": "🖥️", "MRVL": "💎", "AMD": "🔴", "INTC": "🔵",
    "DJT": "🏛️", "INTU": "📉", "SPY": "📊", "QQQ": "💹", "ORCL": "🔶",
    "CRM": "☁️", "NFLX": "🎬", "DIS": "🏰", "JPM": "🏦", "GS": "🏦",
    "XOM": "🛢️", "CVX": "🛢️", "FIVE": "🛒", "ABVX": "🧬", "SBFM": "📣",
    "NU": "💳", "COIN": "🪙", "MSTR": "₿", "DELL": "💾", "TXN": "🔬",
    "NOW": "☁️", "DXST": "📋", "JZ": "🤝", "NU": "💳",
}

BOLD_PATTERNS = [
    r'\$[\d,.]+(?:\s*(?:billion|million|trillion|[BMT])\b)?',
    r'\b(?:record high|all-time high|new high|historic high)\b',
    r'\b(?:surged?|plunged?|soared?|crashed?|spiked?|tanked?|halted?|rallied?)\b',
    r'\b(?:beat|beats|miss|misses|blowout|blockbuster)\b',
    r'\b(?:downgraded?|upgraded?)\b',
    r'\b(?:Iran|Hormuz|Fed|FOMC|CPI|PPI|GDP|Truth Social)\b',
    r'\b(?:tariff|tariffs|sanction[s]?)\b',
]

def bold_important(text):
    """Wrap skimmable terms in bold."""
    for pattern in BOLD_PATTERNS:
        text = re.sub(pattern, lambda m: f"<b>{m.group(0)}</b>", text, flags=re.I)
    return text

def enrich_text(text):
    """Bold and add emoji to known ticker symbols."""
    for ticker, emoji in TICKER_EMOJIS.items():
        text = re.sub(rf'\b{re.escape(ticker)}\b(?!\s[^\s]{{1,2}}\s)', f'<b>{ticker}</b> {emoji}', text)
    return text


def add_arrows(text):
    """Convert +3.5% → ↑+3.5% in green, -2.1% → ↓-2.1% in red."""
    def replace(m):
        s = m.group(0)
        if s.startswith("+"):
            return f"<span style='color:#3a9e6a;font-weight:700'>↑{s}</span>"
        else:
            return f"<span style='color:#c04060;font-weight:700'>↓{s}</span>"
    return re.sub(r'[+\-]\d+\.?\d*%', replace, text)


def section_icon(title):
    t = title.upper()
    if "MARKET" in t or "SNAPSHOT" in t: return "📈"
    if "TRUMP" in t or "FAMILY" in t:    return "🏛️"
    if "OVERLAP" in t or "EXPOSURE" in t: return "🔗"
    if "RISK" in t:                       return "⚠️"
    return "◆"


def render_table(rows):
    """Render tab- or pipe-separated rows as a styled HTML table."""
    html = "<table style='width:100%;border-collapse:collapse;font-size:13px;margin:10px 0'>"
    for i, row in enumerate(rows):
        cells = [c.strip() for c in re.split(r'\t|\|', row) if c.strip()]
        if not cells:
            continue
        bg = "#fdf6f0" if i == 0 else ("#fff" if i % 2 else "#fdf9f7")
        fw = "700" if i == 0 else "400"
        html += f"<tr style='background:{bg}'>"
        for cell in cells:
            html += f"<td style='padding:8px 10px;border-bottom:1px solid #f0e8e0;font-weight:{fw};color:#333'>{add_arrows(cell)}</td>"
        html += "</tr>"
    html += "</table>"
    return html


def markdown_to_html(text):
    today = date.today().strftime("%A, %B %d, %Y").upper()

    sections_html = ""
    current_section_title = ""
    current_section_icon  = ""
    current_items         = []
    in_table              = False
    table_rows            = []
    key_risks             = []
    sources_line          = ""
    in_risks              = False

    def flush_section():
        nonlocal current_items, in_table, table_rows
        if not current_section_title and not current_items:
            return ""
        out = ""
        if current_section_title:
            out += f"""
            <div style='margin:28px 0 14px'>
              <div style='display:flex;align-items:center;gap:8px;margin-bottom:12px'>
                <span style='font-size:18px'>{current_section_icon}</span>
                <span style='font-family:Georgia,serif;font-size:11px;font-weight:700;
                  letter-spacing:0.16em;text-transform:uppercase;color:#8a6a5a'>
                  {current_section_title}
                </span>
                <span style='color:#a8d5a2;font-size:13px'>◇</span>
              </div>
            </div>"""
        if in_table and table_rows:
            out += render_table(table_rows)
            table_rows.clear()
            in_table = False
        for ts, content in current_items:
            enriched = add_arrows(enrich_text(bold_important(content)))
            if ts:
                # Timestamped item — card with colored left border
                pill = f"<span style='display:inline-block;background:linear-gradient(135deg,#f5c5b5,#e8a090);color:#fff;font-size:9.5px;font-weight:700;letter-spacing:0.08em;padding:3px 9px;border-radius:20px;margin-right:9px;white-space:nowrap;text-transform:uppercase'>{ts}</span>"
                out += f"<div style='margin:6px 0;padding:12px 14px;background:#fffaf8;border-left:3px solid #f0a898;border-radius:0 8px 8px 0;font-size:13.5px;line-height:1.7;color:#3a2e2e'>{pill}{enriched}</div>"
            else:
                # Plain bullet — diamond marker
                dot = "<span style='color:#e8b4a0;font-size:8px;vertical-align:middle;margin-right:10px;line-height:1'>◆</span>"
                out += f"<div style='padding:10px 0;border-bottom:1px solid #f5eeea;font-size:13.5px;line-height:1.7;color:#3a2e2e'>{dot}{enriched}</div>"
        current_items.clear()
        return out

    lines = text.split("\n")
    i = 0
    while i < len(lines):
        line = lines[i]

        # Sources line
        if line.strip().startswith("Sources:"):
            sources_line = line.strip()
            i += 1
            continue

        # KEY RISKS block
        if re.match(r'^KEY RISKS', line.strip(), re.I):
            in_risks = True
            i += 1
            continue
        if in_risks:
            if line.strip().startswith("-"):
                key_risks.append(line.strip()[1:].strip())
                i += 1
                continue
            elif line.strip() == "":
                i += 1
                continue
            else:
                in_risks = False

        # Section header: "SECTION 1 — MARKET SNAPSHOT" or "## MARKET SNAPSHOT"
        sec_match = re.match(r'^(?:SECTION\s+\d+\s*[—–-]+\s*|##\s*)(.+)', line.strip())
        if sec_match:
            sections_html += flush_section()
            current_section_title = sec_match.group(1).strip()
            current_section_icon  = section_icon(current_section_title)
            in_table = False
            i += 1
            continue

        # Table row (contains tab or pipe)
        if "\t" in line or ("|" in line and line.count("|") >= 2):
            in_table = True
            table_rows.append(line)
            i += 1
            continue
        elif in_table and table_rows:
            current_items.append(("", render_table(table_rows)))
            table_rows = []
            in_table = False

        # Timestamped bullet: [Jun 1, open] text...
        ts_match = re.match(r'^\[([^\]]+)\]\s*(.*)', line.strip())
        if ts_match:
            current_items.append((ts_match.group(1), ts_match.group(2)))
            i += 1
            continue

        # Plain bullet
        if line.strip().startswith("- "):
            current_items.append(("", line.strip()[2:]))
            i += 1
            continue

        # Non-empty plain paragraph — skip horizontal rules and markdown artifacts
        if line.strip() and not re.match(r'^[-*_]{2,}$', line.strip()) and not re.match(r'^\*{1,2}[^*]+\*{1,2}$', line.strip()):
            current_items.append(("", line.strip()))
        i += 1

    sections_html += flush_section()

    # KEY RISKS block
    risks_html = ""
    if key_risks:
        items = "".join(f"<li style='padding:6px 0;font-size:13.5px;color:#6b4c2a;line-height:1.5'>⚠️ {r}</li>" for r in key_risks)
        risks_html = f"""
        <div style='background:#fff8f0;border:1px solid #f0d8c0;border-radius:10px;padding:16px 20px;margin:22px 0'>
          <div style='font-size:11px;font-weight:700;letter-spacing:0.12em;color:#b87040;text-transform:uppercase;margin-bottom:10px'>Key Risks</div>
          <ul style='margin:0;padding:0;list-style:none'>{items}</ul>
        </div>"""

    # Sources — rendered as styled chips
    sources_html = ""
    if sources_line:
        raw = sources_line.replace("Sources:", "").strip()
        chips = ""
        for m in re.finditer(r'\[([^\]]+)\]\(([^)]+)\)', raw):
            label, url = m.group(1), m.group(2)
            chips += f"<a href='{url}' style='display:inline-block;padding:5px 12px;margin:3px 4px 3px 0;background:#f5eeea;border-radius:20px;font-size:11px;font-weight:600;color:#8a6a5a;text-decoration:none;letter-spacing:0.03em'>{label}</a>"
        if chips:
            sources_html = f"""
            <div style='margin-top:24px;padding-top:18px;border-top:1px solid #f0e8e0'>
              <div style='font-size:9.5px;font-weight:700;letter-spacing:0.18em;color:#c4a898;text-transform:uppercase;margin-bottom:10px'>Sources</div>
              <div>{chips}</div>
            </div>"""

    return f"""<!DOCTYPE html>
<html>
<body style="margin:0;padding:0;background:#fdf6f0;font-family:'Helvetica Neue',Arial,sans-serif">
<div style="max-width:640px;margin:28px auto;background:#fff;border-radius:16px;overflow:hidden;box-shadow:0 4px 32px rgba(0,0,0,0.09)">

  <!-- Header -->
  <div style="background:linear-gradient(135deg,#fce8e8 0%,#fdf0e8 40%,#e8f5ee 100%);padding:40px 44px 32px;text-align:center;position:relative">
    <div style="font-size:16px;letter-spacing:0.2em;color:#e8a0b8;margin-bottom:12px">&#x25C6; &nbsp; &#x25C6; &nbsp; &#x25C6;</div>
    <p style="margin:0 0 8px;font-size:11px;letter-spacing:0.2em;color:#b09090;font-weight:600;text-transform:uppercase">{today}</p>
    <h1 style="margin:0 0 8px;font-family:Georgia,serif;font-size:28px;font-weight:400;color:#2c1f1f;letter-spacing:-0.01em">Mandy's Morning Market Briefing</h1>
    <p style="margin:0 0 20px;font-size:11px;letter-spacing:0.18em;color:#b09090;text-transform:uppercase">Your Daily Financial Intelligence</p>
    <div style="display:flex;align-items:center;justify-content:center;gap:8px;margin-bottom:20px">
      <div style="height:1px;width:60px;background:linear-gradient(90deg,transparent,#a8d5a2)"></div>
      <span style="color:#a8d5a2;font-size:14px">◆</span>
      <div style="height:1px;width:60px;background:linear-gradient(90deg,#a8d5a2,transparent)"></div>
    </div>
    <img src="{PHOTO_URL}" alt="Mandy" style="width:200px;height:200px;object-fit:cover;object-position:top;border-radius:50%;border:4px solid rgba(255,255,255,0.8);box-shadow:0 4px 20px rgba(0,0,0,0.12)" />
  </div>

  <!-- Accent bar -->
  <div style="height:3px;background:linear-gradient(90deg,#f0a0a0,#a8d5a2)"></div>

  <!-- Body -->
  <div style="padding:30px 44px 36px">
    {sections_html}
    {risks_html}
    {sources_html}
  </div>

  <!-- Footer -->
  <div style="background:#fdf6f0;border-top:1px solid #f0e8e0;padding:16px 44px;display:flex;align-items:center;justify-content:space-between">
    <p style="margin:0;font-size:10px;color:#c4a898;letter-spacing:0.1em;text-transform:uppercase">Curated by Claude · Mandy's Finance</p>
    <p style="margin:0;font-size:10px;color:#c4a898">{date.today().year}</p>
  </div>

</div>
</body>
</html>"""


def send_email(subject, body_text):
    from googleapiclient.discovery import build
    creds = get_credentials()
    service = build("gmail", "v1", credentials=creds)

    msg = MIMEMultipart("alternative")
    msg["to"]      = TO_EMAIL
    msg["from"]    = "me"
    msg["subject"] = subject
    msg.attach(MIMEText(body_text, "plain"))
    msg.attach(MIMEText(markdown_to_html(body_text), "html"))

    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    result = service.users().messages().send(userId="me", body={"raw": raw}).execute()
    print(f"✓ Email sent · ID {result['id']}")


def send_sms(body_text):
    """Send short preview via T-Mobile email-to-SMS gateway."""
    try:
        creds = get_credentials()
        from googleapiclient.discovery import build
        service = build("gmail", "v1", credentials=creds)

        # Strip markdown, keep first ~300 chars
        preview = re.sub(r'\*\*|##|__|\[.*?\]\(.*?\)', '', body_text)
        preview = re.sub(r'\n{2,}', '\n', preview).strip()[:300]

        msg = MIMEText(preview, "plain")
        msg["to"]      = SMS_EMAIL
        msg["from"]    = "me"
        msg["subject"] = ""
        raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
        service.users().messages().send(userId="me", body={"raw": raw}).execute()
        print(f"✓ SMS sent to {SMS_EMAIL}")
    except Exception as e:
        print(f"⚠ SMS failed: {e}", file=sys.stderr)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--auth",    action="store_true", help="One-time OAuth setup")
    parser.add_argument("--no-sms",  action="store_true", help="Skip SMS")
    parser.add_argument("--subject", default=f"Mandy's Morning Market Briefing — {date.today().strftime('%b %d, %Y')}")
    args = parser.parse_args()

    if args.auth:
        get_credentials()
        print("✓ Auth complete. Token saved.")
        sys.exit(0)

    body = sys.stdin.read().strip()
    if not body:
        print("ERROR: no briefing content on stdin", file=sys.stderr)
        sys.exit(1)

    send_email(args.subject, body)
    if not args.no_sms:
        send_sms(body)
