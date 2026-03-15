# VoiceTV Service - Setup Guide

## Prerequisites

- Orange Pi (or any Linux system with Python 3.9+)
- Python 3.9 or later
- pip and virtualenv
- Network access to streaming services and smart devices
- For TV control: Samsung SmartThings setup OR Fire TV ADB access
- For voice: Google Cloud Speech-to-Text API key OR OpenAI Whisper API key

## Installation

### 1. Clone or Download Repository

```bash
cd /home/orangepi/Apps
git clone https://github.com/yourusername/VoiceTVService.git
cd VoiceTVService
```

### 2. Create Python Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Python Dependencies

```bash
cd backend
pip install -r requirements.txt
```

**Key dependencies:**
- Flask (API server)
- Flask-CORS (Cross-origin requests)
- Flask-Limiter (Rate limiting)
- SQLAlchemy (Database ORM)
- Requests (HTTP client)
- Google Cloud libraries (optional)

### 4. Environment Configuration

Create a `.env` file in the backend directory:

```bash
cp .env.example .env
```

Edit `.env` with your settings:

```bash
# Flask Configuration
FLASK_ENV=production
FLASK_DEBUG=False

# API Authentication (comma-separated list)
VOICETV_API_KEYS=dev-key-12345,your-production-key-here

# Logging
LOG_LEVEL=INFO

# Samsung SmartThings (if using Samsung TV)
SMARTTHINGS_TOKEN=your_smartthings_api_token

# Fire TV Device IPs (if using Fire TVs)
FIRETV_UPPER_LEFT_IP=192.168.1.101
FIRETV_UPPER_RIGHT_IP=192.168.1.102
FIRETV_LOWER_LEFT_IP=192.168.1.103
FIRETV_LOWER_RIGHT_IP=192.168.1.104

# Speech-to-Text Service
# Choose one: google (recommended) or openai
SPEECH_SERVICE=google
GOOGLE_CLOUD_API_KEY=your_google_cloud_key
OPENAI_API_KEY=your_openai_key

# Sonos Speaker Configuration
SONOS_SPEAKER_IP=192.168.1.50

# Streaming Service API Keys (optional, for future live integration)
YOUTUBE_TV_API_KEY=your_key
PEACOCK_API_KEY=your_key
PEACOCK_API_SECRET=your_secret
ESPN_PLUS_API_KEY=your_key
AMAZON_PRIME_API_KEY=your_key
HBO_MAX_API_KEY=your_key
```

## Configuration Details

### Samsung SmartThings Setup

1. Install SmartThings app on your phone
2. Register your Samsung TV in SmartThings
3. Get SmartThings API token:
   - Visit https://developer.smartthings.com/
   - Create account and app
   - Generate API token with device control permissions
   - Add token to SMARTTHINGS_TOKEN in .env

### Fire TV Setup

1. Enable ADB (Android Debug Bridge) on Fire TV:
   - Settings → About → Build Version (tap 7 times)
   - Settings → Device → Developer Options → Debugging → Enable
2. Note the IP address shown in Network settings
3. Connect from Orange Pi:
   ```bash
   adb connect FIRETV_IP_ADDRESS
   ```
4. Add IP addresses to .env

### Google Cloud Speech-to-Text Setup

1. Create Google Cloud project: https://console.cloud.google.com/
2. Enable Speech-to-Text API
3. Create service account with Speech-to-Text permission
4. Generate JSON key file
5. Set environment variable:
   ```bash
   export GOOGLE_APPLICATION_CREDENTIALS=/path/to/key.json
   ```

### Sonos Speaker Setup

1. Note the IP address of your Sonos speaker
2. Add to .env as SONOS_SPEAKER_IP
3. Optionally test connectivity:
   ```bash
   curl http://SONOS_IP:1400/status
   ```

## Running the Service

### Development Mode

```bash
cd backend
source ../venv/bin/activate
python app.py
```

Server will start on `http://localhost:5002`

### Production with Systemd

Create systemd service file:

```bash
sudo nano /etc/systemd/system/voicetv.service
```

Add:

```ini
[Unit]
Description=VoiceTV Service - Basement TV Control System
After=network.target

[Service]
Type=simple
User=orangepi
WorkingDirectory=/home/orangepi/Apps/VoiceTVService/backend
Environment="PATH=/home/orangepi/Apps/VoiceTVService/venv/bin"
EnvironmentFile=/home/orangepi/Apps/VoiceTVService/.env
ExecStart=/home/orangepi/Apps/VoiceTVService/venv/bin/python app.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl daemon-reload
sudo systemctl enable voicetv
sudo systemctl start voicetv
```

View logs:

```bash
sudo journalctl -u voicetv -f
```

## Testing

### Health Check

```bash
curl http://localhost:5002/health
```

Expected response:
```json
{
  "status": "healthy",
  "service": "VoiceTV Service",
  "version": "0.2.0"
}
```

### Search Test

```bash
curl "http://localhost:5002/api/search/all?query=breaking+bad" \
  -H "X-API-Key: dev-key-12345"
```

### TV Control Test

```bash
curl -X POST http://localhost:5002/api/tv/power \
  -H "Content-Type: application/json" \
  -H "X-API-Key: dev-key-12345" \
  -d '{"tv_id": "big_screen", "action": "on"}'
```

### Voice Command Test

```bash
curl -X POST http://localhost:5002/api/voice/command \
  -H "Content-Type: application/json" \
  -H "X-API-Key: dev-key-12345" \
  -d '{"transcript": "Put Breaking Bad on the big screen"}'
```

## Troubleshooting

### Port Already in Use

If port 5002 is already in use:

```bash
# Find process using port 5002
lsof -i :5002

# Kill process
kill -9 <PID>

# Or change port in app.py
```

### Permission Denied

If running with systemd:

```bash
# Make sure user has permissions
sudo chown -R orangepi:orangepi /home/orangepi/Apps/VoiceTVService

# Check log directory permissions
sudo chown -R orangepi:orangepi /home/orangepi/Apps/VoiceTVService/logs
```

### API Key Not Working

1. Verify API key in .env: `echo $VOICETV_API_KEYS`
2. Make sure .env is sourced: `source .env`
3. Check for typos in request headers
4. Restart service if changed

### Speech-to-Text Not Working

1. Verify GOOGLE_APPLICATION_CREDENTIALS is set:
   ```bash
   echo $GOOGLE_APPLICATION_CREDENTIALS
   ```
2. Test credentials file:
   ```bash
   curl https://oauth2.googleapis.com/tokeninfo -d access_token=$(cat /path/to/key.json | jq -r '.access_token')
   ```
3. Check logs for detailed error:
   ```bash
   tail -50 /home/orangepi/Apps/VoiceTVService/logs/voicetv.log
   ```

### TV Control Not Working

1. Verify device IP addresses are correct
2. Test connectivity:
   ```bash
   # For Samsung
   curl https://api.smartthings.com/v1/devices \
     -H "Authorization: Bearer $SMARTTHINGS_TOKEN"

   # For Fire TV
   adb connect FIRETV_IP
   ```
3. Check device is on same network
4. Verify credentials in .env

### Sonos Not Speaking

1. Verify Sonos IP in .env
2. Test Sonos connectivity:
   ```bash
   curl http://SONOS_IP:1400/status
   ```
3. Check speaker is on and connected
4. Verify speaker name matches in database

## Performance Tuning

### Increase Cache Size

In `backend/app.py`, adjust cache initialization:
```python
aggregator = SearchAggregator(cache_size=5000, cache_ttl=600)
```

### Rate Limiting Adjustment

Edit `backend/rate_limiter.py` to adjust limits:
```python
RATE_LIMITS = {
    'search_all': '50 per minute, 500 per hour',  # Increased
    ...
}
```

### Database Optimization

Add indexes for frequently queried fields:
```bash
cd backend
python -c "from database.db_init import init_db; init_db()"
```

## Security Hardening

### Change Default API Key

```bash
# Generate new secure key
python -c "import secrets; print(secrets.token_urlsafe(32))"

# Update .env
VOICETV_API_KEYS=your_new_secure_key
```

### Enable HTTPS

Use reverse proxy (nginx/Apache) in front of Flask:

```nginx
server {
    listen 443 ssl;
    server_name voicetv.local;

    ssl_certificate /etc/ssl/certs/cert.pem;
    ssl_certificate_key /etc/ssl/private/key.pem;

    location / {
        proxy_pass http://localhost:5002;
        proxy_set_header Host $host;
    }
}
```

### Firewall Configuration

Allow only necessary ports:

```bash
# Allow API access only from local network
sudo ufw allow from 192.168.1.0/24 to any port 5002

# Or specific IPs
sudo ufw allow from 192.168.1.100 to any port 5002
```

## Monitoring

### Check Service Status

```bash
sudo systemctl status voicetv
```

### View Real-time Logs

```bash
# Console output
sudo journalctl -u voicetv -f

# File logs
tail -f /home/orangepi/Apps/VoiceTVService/logs/voicetv.log

# Errors only
tail -f /home/orangepi/Apps/VoiceTVService/logs/voicetv_errors.log
```

### Monitor Performance

Check API response times in logs:
```bash
grep "search_time_ms" /home/orangepi/Apps/VoiceTVService/logs/voicetv.log
```

### Check Disk Usage

```bash
du -sh /home/orangepi/Apps/VoiceTVService/logs/
```

Log files are automatically rotated at 500MB.

## Updating

### Update Code

```bash
cd /home/orangepi/Apps/VoiceTVService
git pull origin main
```

### Update Dependencies

```bash
source venv/bin/activate
cd backend
pip install --upgrade -r requirements.txt
```

### Restart Service

```bash
sudo systemctl restart voicetv
```

## Uninstallation

### Remove Systemd Service

```bash
sudo systemctl stop voicetv
sudo systemctl disable voicetv
sudo rm /etc/systemd/system/voicetv.service
sudo systemctl daemon-reload
```

### Remove Application

```bash
rm -rf /home/orangepi/Apps/VoiceTVService
```

## Support

- **Logs**: `/home/orangepi/Apps/VoiceTVService/logs/`
- **API Docs**: See `docs/API.md`
- **Architecture**: See `docs/ARCHITECTURE.md`
