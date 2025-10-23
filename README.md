# Dierenasiel Alert

**Proudly vibecoded** 🎵✨

A small Python app that monitors the Dierenbescherming "Ik Zoek Baas" site and alerts you when new animals become available at a specific shelter or location.

## Why I Built This

Every time I wanted to visit the website to look at animals in the shelter, there were already new ones and cats already gone. I wanted to be alerted when a new cat was added to the site so I could look and decide if I wanted to make an appointment or not. Instead of constantly refreshing the website and potentially missing out on meeting a new furry friend, this tool does the monitoring for me!

## Features

- 🐾 **Multiple animal types**: cats (katten), dogs (honden), birds (vogels), rabbits and rodents (konijnen-en-knagers)
- 📍 **Location-based search**: Search by postal code with distance filter (10km, 25km, 50km)
- 🏠 **Shelter-based search**: Filter by specific shelter sites
- 📄 **PDF Reports**: Generate beautiful PDF reports with animal photos and details
- 🔔 **Multiple notification methods**: Console, desktop notifications (`notify-send`), and Telegram
- 📊 **List animals**: View all currently available animals with details
- 💾 **Smart tracking**: Persists seen IDs to avoid duplicate alerts
- 🔄 **Automatic pagination**: Scrapes all pages to find every available animal
- ⚙️ **Flexible options**: Animal type, location/site, availability, order, and polling interval

## Install

Create a virtual environment (recommended) and install dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Or install in development mode:

```bash
pip install -e .
```

This will install the `dierenasiel-alert` command globally in your environment.

## Run

### List available animals

List all currently available animals at a shelter or location:

**By shelter site:**
```bash
# List cats at a specific shelter (default)
dierenasiel-alert list --site deKuipershoek --availability available

# List dogs at a shelter
dierenasiel-alert list --animal-type honden --site deKuipershoek

# List birds at a shelter
dierenasiel-alert list --animal-type vogels --site deKuipershoek

# List rabbits and rodents
dierenasiel-alert list --animal-type konijnen-en-knagers --site deKuipershoek
```

**By location (postal code):**
```bash
# List cats within 50km of postal code 7323PM
dierenasiel-alert list --location 7323PM --distance 50km

# List dogs within 25km
dierenasiel-alert list --animal-type honden --location 7323PM --distance 25km

# List all cats in the area (no distance limit)
dierenasiel-alert list --location 7323PM
```

### Monitor for new animals

**Run once and exit:**
```bash
# Monitor cats at a shelter (default)
dierenasiel-alert monitor --site deKuipershoek

# Monitor dogs by location
dierenasiel-alert monitor --animal-type honden --location 7323PM --distance 50km

# Monitor birds
dierenasiel-alert monitor --animal-type vogels --site deKuipershoek
```

**Monitor continuously (every 5 minutes):**
```bash
# With shelter site
dierenasiel-alert monitor --interval 300 --site deKuipershoek

# With location
dierenasiel-alert monitor --interval 300 --location 7323PM --distance 50km
```

### Generate PDF reports

Create a PDF report with animal photos and details:

```bash
# Generate report for cats at a location
dierenasiel-alert report --location 7323PM --distance 50km --output cats_report.pdf

# Generate report for dogs at a shelter
dierenasiel-alert report --animal-type honden --site deKuipershoek --output dogs.pdf

# Custom title
dierenasiel-alert report --location 7323PM --distance 25km --output nearby_cats.pdf --title "Cats Near Me"
```

The PDF will include:
- 📸 High-quality photos of each animal
- 📝 Complete details (ID, name, type, location, availability)
- 🔗 Direct links to animal profiles

### Telegram Notifications

To enable Telegram notifications, you need to:

1. Create a Telegram bot via [@BotFather](https://t.me/botfather)
2. Get your chat ID (you can use [@userinfobot](https://t.me/userinfobot))
3. Set environment variables or pass them as arguments:

**Using environment variables:**
```bash
export TELEGRAM_BOT_TOKEN="your-bot-token"
export TELEGRAM_CHAT_ID="your-chat-id"
dierenasiel-alert monitor --telegram --interval 300
```

**Using command line arguments:**
```bash
dierenasiel-alert monitor --telegram --telegram-token "your-bot-token" --telegram-chat-id "your-chat-id" --interval 300
```

**With location-based search:**
```bash
dierenasiel-alert monitor --telegram --location 7323PM --distance 50km --interval 300
```

## Commands

### `list`

List all currently available animals at a shelter or location.

**Options:**
- `--animal-type` - one of `katten` (cats), `honden` (dogs), `vogels` (birds), `konijnen-en-knagers` (rabbits/rodents), default: `katten`
- `--site` - shelter site code (e.g., `deKuipershoek`) - mutually exclusive with `--location`
- `--location` - postal code for location-based search - mutually exclusive with `--site`
- `--distance` - distance filter: `10km`, `25km`, `50km`, or omit for all (only used with `--location`)
- `--availability` - filter by availability: `available`, `reserved`, `unavailable`, default: `available`
- `--order` - sort order: `aflopend` (descending) or `oplopend` (ascending), default: `aflopend`

### `monitor`

Monitor for new animals and send alerts when they become available.

**Options:**
- `--animal-type` - one of `katten` (cats), `honden` (dogs), `vogels` (birds), `konijnen-en-knagers` (rabbits/rodents), default: `katten`
- `--site` - shelter site code (e.g., `deKuipershoek`) - mutually exclusive with `--location`
- `--location` - postal code for location-based search - mutually exclusive with `--site`
- `--distance` - distance filter: `10km`, `25km`, `50km`, or omit for all (only used with `--location`)
- `--availability` - filter by availability: `available`, `reserved`, `unavailable`, default: `available`
- `--order` - sort order: `aflopend` (descending) or `oplopend` (ascending), default: `aflopend`
- `--interval` - polling interval in seconds; `0` runs once and exits, default: `0`
- `--store` - path to persistence JSON file, default: `~/.local/share/dierenasiel-alert/seen.json`
- `--telegram` - enable Telegram notifications
- `--telegram-token` - Telegram bot token (or set `TELEGRAM_BOT_TOKEN` env var)
- `--telegram-chat-id` - Telegram chat ID (or set `TELEGRAM_CHAT_ID` env var)

### `report`

Generate a PDF report with animal photos and details.

**Options:**
- `--animal-type` - one of `katten` (cats), `honden` (dogs), `vogels` (birds), `konijnen-en-knagers` (rabbits/rodents), default: `katten`
- `--site` - shelter site code (e.g., `deKuipershoek`) - mutually exclusive with `--location`
- `--location` - postal code for location-based search - mutually exclusive with `--site`
- `--distance` - distance filter: `10km`, `25km`, `50km`, or omit for all (only used with `--location`)
- `--availability` - filter by availability: `available`, `reserved`, `unavailable`, default: `available`
- `--order` - sort order: `aflopend` (descending) or `oplopend` (ascending), default: `aflopend`
- `--output` - output PDF file path, default: `animals_report.pdf`
- `--title` - custom title for the PDF report

## How it works

The scraper searches the Dierenbescherming "Ik Zoek Baas" website and extracts animal information from article cards with the `data-v-2f76df55` attribute. It:

1. **Searches by location or shelter site** - You can search by postal code with distance filters or by specific shelter sites
2. **Scrapes all pages automatically** - Uses pagination to find every available animal (with a polite 1-second delay between pages)
3. **Extracts complete information** - Gets animal ID, name, location, site, availability, photo URLs
4. **Tracks seen animals** - Stores animal IDs to avoid duplicate alerts
5. **Notifies you** - Sends alerts via console, desktop notifications, and/or Telegram

The numeric animal ID from URLs like `/asieldier/<animal-type>/<id>-<name>` is used as the stable unique identifier.

**Supported animal types:**
- `katten` - cats 🐱
- `honden` - dogs 🐶
- `vogels` - birds 🐦
- `konijnen-en-knagers` - rabbits and rodents 🐰

## Notification Methods

1. **Console**: Always prints new animals to standard output
2. **Desktop**: If `notify-send` is available (most Linux desktops), desktop notifications will be shown with appropriate emojis (🐱 for cats, 🐶 for dogs, 🐦 for birds, 🐰 for rabbits/rodents)
3. **Telegram**: If enabled with `--telegram` flag and proper credentials, sends rich notifications via Telegram bot

## Automation Examples

### Cron Jobs

**Monitor cats every 10 minutes with Telegram notifications:**
```cron
*/10 * * * * cd /path/to/dierenasiel-alert && . .venv/bin/activate && dierenasiel-alert monitor --telegram --location 7323PM --distance 50km >> monitor.log 2>&1
```

**Monitor dogs at a shelter every 15 minutes:**
```cron
*/15 * * * * cd /path/to/dierenasiel-alert && . .venv/bin/activate && dierenasiel-alert monitor --animal-type honden --site deKuipershoek >> monitor-dogs.log 2>&1
```

### Systemd Service

You can also set up a systemd service for continuous monitoring. See `dierenasiel-alert.service` and `MONITORING.md` for details.

### Shell Script

Use the included `monitor.sh` script:
```bash
./monitor.sh 300  # Check every 5 minutes (300 seconds)
```

## Technical Details

### Dependencies

- `requests` - HTTP requests for fetching web pages
- `beautifulsoup4` - HTML parsing and scraping
- `reportlab` - PDF generation with images

### Storage

By default, seen animal IDs are stored in `~/.local/share/dierenasiel-alert/seen.json`. This ensures:
- The tool works from any directory
- Data persists across sessions
- Multiple animal types can be tracked separately

### Rate Limiting

The scraper includes a 1-second delay between page requests to be respectful to the website. Please:
- Avoid very short polling intervals (< 5 minutes)
- Don't run multiple instances simultaneously
- Use reasonable distance filters to limit the number of results

## Notes

- This project performs simple HTML scraping with polite headers and reasonable rate limiting
- If the website structure changes, you may need to update the parsing logic in `scraper.py`
- The tool respects the website by adding delays between requests and using proper User-Agent headers

## Contributing

This project was **proudly vibecoded** 🎵✨ - built with creative flow and practical purpose. Feel free to fork, improve, or adapt it for your needs!

## License

MIT License - see [LICENSE](LICENSE) file for details.

Use this however you like! Just be kind to the animals and the websites. 🐾

Copyright (c) 2025 Michael Trip
