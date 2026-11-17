#!/usr/bin/env bash
# Send one Telegram message to the repo owner: scripts/notify/telegram.sh "text"
#
# Needs TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID in the environment (repo secrets).
# Never fails the calling job: a missing secret or a Telegram outage only prints a
# warning, because the notification must not turn a green run red.
set -uo pipefail

TEXT="${1:-}"
if [ -z "${TELEGRAM_BOT_TOKEN:-}" ] || [ -z "${TELEGRAM_CHAT_ID:-}" ]; then
  echo "::warning::TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID not set; notification skipped."
  exit 0
fi

code=$(curl -s -o /tmp/telegram-response.json -w '%{http_code}' \
  "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
  --data-urlencode "chat_id=${TELEGRAM_CHAT_ID}" \
  --data-urlencode "text=${TEXT}" \
  --data-urlencode "disable_web_page_preview=true")
if [ "$code" != "200" ]; then
  echo "::warning::Telegram notification failed (HTTP $code): $(cat /tmp/telegram-response.json 2>/dev/null)"
fi
exit 0
