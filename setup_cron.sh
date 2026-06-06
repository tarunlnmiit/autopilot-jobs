#!/bin/bash
# Sets up a daily cron job to run the job scan automatically.
# Usage: bash setup_cron.sh
#
# Customize these variables before running:
PYTHON="${AUTOPILOT_PYTHON:-$(which python3)}"
CRON_TIME="${AUTOPILOT_CRON:-30 2 * * *}"  # Default: 2:30 AM local time

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
LOG="$PROJECT_DIR/scan.log"

if [ ! -f "$PYTHON" ] && ! command -v "$PYTHON" &>/dev/null; then
    echo "Error: Python not found at '$PYTHON'"
    echo "Set AUTOPILOT_PYTHON=/path/to/python and re-run."
    exit 1
fi

CRON_LINE="$CRON_TIME cd \"$PROJECT_DIR\" && \"$PYTHON\" -m job_hunt.main scan >> \"$LOG\" 2>&1"

(crontab -l 2>/dev/null | grep -qF "job_hunt.main scan") && {
    echo "Cron job already set up."
    exit 0
}

(crontab -l 2>/dev/null; echo "$CRON_LINE") | crontab -
echo "Cron job added: $CRON_TIME"
echo "Python: $PYTHON"
echo "Logs: $LOG"
echo ""
echo "To verify: crontab -l"
echo "To remove: crontab -e  (delete the line)"
echo ""
echo "To set a different time, use:"
echo "  AUTOPILOT_CRON='0 9 * * *' bash setup_cron.sh  # 9:00 AM daily"
