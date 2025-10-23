# Monitoring Setup Guide

This guide explains how to set up continuous monitoring for new cats at the shelter.

## Option 1: Built-in Polling Mode (Simplest)

Run the application with the `--interval` flag to check periodically:

```bash
# Check every 5 minutes (300 seconds)
dierenasiel-alert monitor --interval 300 --telegram

# Check every 30 minutes
dierenasiel-alert monitor --interval 1800 --telegram
```

**Pros**: Simple, no additional setup needed
**Cons**: Needs to keep terminal open, or run in background manually

### Running in Background

```bash
# Using nohup
nohup dierenasiel-alert monitor --interval 300 --telegram > /tmp/dierenasiel.log 2>&1 &

# Or use screen/tmux
screen -S cat-monitor
dierenasiel-alert monitor --interval 300 --telegram
# Press Ctrl+A then D to detach
```

## Option 2: Systemd Service (Recommended for Linux)

Set up a systemd service to run continuously and restart automatically.

### Setup Steps:

1. **Set your Telegram credentials**:
   
   Edit `dierenasiel-alert.service` and replace:
   - `your_bot_token_here` with your actual Telegram bot token
   - `your_chat_id_here` with your actual chat ID

2. **Copy the service file**:
   
   ```bash
   sudo cp dierenasiel-alert.service /etc/systemd/system/
   ```

3. **Update the paths in the service file** (if needed):
   
   ```bash
   sudo nano /etc/systemd/system/dierenasiel-alert.service
   ```
   
   Update `WorkingDirectory` and `ExecStart` paths to match your installation.

4. **Enable and start the service**:
   
   ```bash
   # Reload systemd
   sudo systemctl daemon-reload
   
   # Enable service to start on boot
   sudo systemctl enable dierenasiel-alert
   
   # Start the service now
   sudo systemctl start dierenasiel-alert
   ```

### Managing the Service:

```bash
# Check status
sudo systemctl status dierenasiel-alert

# View logs
sudo journalctl -u dierenasiel-alert -f

# Stop the service
sudo systemctl stop dierenasiel-alert

# Restart the service
sudo systemctl restart dierenasiel-alert

# Disable service
sudo systemctl disable dierenasiel-alert
```

**Pros**: Automatic restart, runs on boot, proper logging
**Cons**: Requires root/sudo access

## Option 3: Cron Job (Scheduled Checks)

Run the monitor at specific times using cron.

### Setup Steps:

1. **Make the monitoring script executable**:
   
   ```bash
   chmod +x monitor.sh
   ```

2. **Edit your crontab**:
   
   ```bash
   crontab -e
   ```

3. **Add a cron entry**:
   
   ```bash
   # Check every 5 minutes
   */5 * * * * cd /home/michael/dev/dierenasiel-alert && ./monitor.sh 0
   
   # Check every hour at minute 0
   0 * * * * cd /home/michael/dev/dierenasiel-alert && ./monitor.sh 0
   
   # Check every day at 9 AM
   0 9 * * * cd /home/michael/dev/dierenasiel-alert && ./monitor.sh 0
   ```

4. **Set up environment variables** (create `.env` file):
   
   ```bash
   echo "TELEGRAM_BOT_TOKEN=your_token_here" >> .env
   echo "TELEGRAM_CHAT_ID=your_chat_id_here" >> .env
   ```
   
   Then update `monitor.sh` to source the `.env` file.

**Pros**: Simple, well-understood, works on all Unix systems
**Cons**: No automatic restart if fails, gaps between checks

## Option 4: Docker Container (Advanced)

For containerized deployment, create a Dockerfile:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
RUN pip install -e .

ENV TELEGRAM_BOT_TOKEN=""
ENV TELEGRAM_CHAT_ID=""

CMD ["dierenasiel-alert", "monitor", "--interval", "300", "--telegram"]
```

Then run:

```bash
docker build -t dierenasiel-alert .
docker run -d --name cat-monitor \
  -e TELEGRAM_BOT_TOKEN="your_token" \
  -e TELEGRAM_CHAT_ID="your_chat_id" \
  -v $(pwd)/data:/app/data \
  --restart unless-stopped \
  dierenasiel-alert
```

## Telegram Setup

Before monitoring with Telegram notifications:

1. **Create a Telegram bot**:
   - Message [@BotFather](https://t.me/BotFather) on Telegram
   - Send `/newbot` and follow the instructions
   - Save the bot token

2. **Get your chat ID**:
   - Message [@userinfobot](https://t.me/userinfobot) on Telegram
   - It will reply with your chat ID
   - Or start a chat with your bot and visit: `https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates`

3. **Set environment variables**:
   
   ```bash
   export TELEGRAM_BOT_TOKEN="your_bot_token_here"
   export TELEGRAM_CHAT_ID="your_chat_id_here"
   ```
   
   Or add to your `~/.bashrc` or `~/.zshrc`:
   
   ```bash
   echo 'export TELEGRAM_BOT_TOKEN="your_token"' >> ~/.zshrc
   echo 'export TELEGRAM_CHAT_ID="your_chat_id"' >> ~/.zshrc
   source ~/.zshrc
   ```

## Testing Your Setup

Before setting up continuous monitoring, test that everything works:

```bash
# List current cats
dierenasiel-alert list

# Run monitor once (to populate the seen database)
dierenasiel-alert monitor

# Test with Telegram (if configured)
dierenasiel-alert monitor --telegram
```

## Monitoring Multiple Shelters

To monitor multiple shelters, you can:

1. **Run multiple instances** with different store files:
   
   ```bash
   dierenasiel-alert monitor --site deKuipershoek --store data/kuipershoek.json --interval 300 &
   dierenasiel-alert monitor --site anotherShelter --store data/another.json --interval 300 &
   ```

2. **Create multiple systemd services**:
   
   Copy and modify the service file for each shelter.

## Troubleshooting

- **Check logs**: Look at systemd journal or redirect output to a log file
- **Verify credentials**: Ensure Telegram token and chat ID are correct
- **Test connectivity**: Make sure you can reach ikzoekbaas.nl
- **Check permissions**: Ensure the data directory is writable
- **Validate store file**: Look at `data/seen.json` to see tracked cats

## Recommended Setup

For most users, I recommend **Option 2 (Systemd service)**:
- Runs continuously in the background
- Automatic restart on failure
- Starts on system boot
- Easy to manage and monitor
- Proper logging

Start with a 5-minute interval (`--interval 300`) and adjust based on your needs.
