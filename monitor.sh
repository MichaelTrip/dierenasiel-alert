#!/bin/bash
# Simple monitoring script for dierenasiel-alert
# Usage: ./monitor.sh [interval_seconds]

INTERVAL=${1:-300}  # Default: check every 5 minutes (300 seconds)

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Run the monitor command with polling
dierenasiel-alert monitor --interval "$INTERVAL" --telegram

# Alternative: run once (for use with cron)
# dierenasiel-alert monitor --telegram
