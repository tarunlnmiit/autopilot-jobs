#!/bin/bash
# Scripted demo session for asciinema recording.
# Record: asciinema rec demo/demo.cast --command "bash demo/run_demo.sh"
# Convert: agg demo/demo.cast demo/demo.gif

DEMO_PYTHON="${DEMO_PYTHON:-python3}"
DEMO_SCRIPT="$(cd "$(dirname "$0")" && pwd)/demo_run.py"

echo ""
echo "$ autopilot scan"
sleep 1
$DEMO_PYTHON "$DEMO_SCRIPT" scan

sleep 2

echo ""
echo "$ autopilot draft 1"
sleep 1
$DEMO_PYTHON "$DEMO_SCRIPT" draft

sleep 2

echo ""
echo "$ autopilot export --min 70"
sleep 1
$DEMO_PYTHON "$DEMO_SCRIPT" export

sleep 1
echo ""
echo "Done. Star the repo → github.com/tarunlnmiit/autopilot-jobhunt"
sleep 2
