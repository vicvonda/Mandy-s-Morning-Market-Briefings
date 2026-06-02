#!/bin/bash
DEFAULT_SUBJECT="Mandy's Morning Market Briefing"
SUBJECT="${1:-$DEFAULT_SUBJECT}"
BODY_FILE="${2:-/tmp/claude_briefing.md}"
RECIPIENT="${GMAIL_USER}"

ACCESS_TOKEN=$(curl -s -X POST https://oauth2.googleapis.com/token \
  -d "client_id=${GMAIL_CLIENT_ID}" \
  -d "client_secret=${GMAIL_CLIENT_SECRET}" \
  -d "refresh_token=${GMAIL_REFRESH_TOKEN}" \
  -d "grant_type=refresh_token" | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

if [[ -z "$ACCESS_TOKEN" || "$ACCESS_TOKEN" == "None" ]]; then
  echo "ERROR: Could not get Gmail access token" >&2; exit 1
fi

RAW=$(python3 scripts/encode_email.py "$GMAIL_USER" "$RECIPIENT" "$SUBJECT" "$BODY_FILE")

RESULT=$(curl -s -X POST \
  "https://gmail.googleapis.com/gmail/v1/users/me/messages/send" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" \
  -H "Content-Type: application/json" \
  -d "{\"raw\": \"${RAW}\"}")

if echo "$RESULT" | python3 -c "import sys,json; d=json.load(sys.stdin); exit(0 if 'id' in d else 1)" 2>/dev/null; then
  echo "Email sent to ${RECIPIENT}"
else
  echo "Send failed: $RESULT" >&2; exit 1
fi
