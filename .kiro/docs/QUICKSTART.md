# Quick Start Guide

## Prerequisites Checklist

Before starting, ensure you have:

- [ ] Docker and Docker Compose installed
- [ ] wewe-rss service running (`docker ps | grep wewe-rss`)
- [ ] wewe-rss manually configured (logged in, subscribed to official accounts)
- [ ] MySQL accessible (port 3308 for dev, or via Docker network for pre)
- [ ] Ollama LLM service running (e.g., at 192.168.10.43:11434)
- [ ] WeCom webhook URL obtained

## Development Environment (5 minutes)

### Option 1: Run Locally (Recommended)

```bash
# 1. Navigate to project directory
cd analysis-ollama

# 2. Copy and configure environment file
cp .env.dev.example .env.dev
# Edit .env.dev with your actual values

# 3. Create virtual environment
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# 4. Install dependencies
pip install -r requirements.txt

# 5. Run the application
python main.py
```

### Option 2: Run in Docker

```bash
# 1. Navigate to project directory
cd analysis-ollama

# 2. Copy and configure environment file
cp .env.dev.example .env.dev
# Edit .env.dev with your actual values

# 3. Start container
docker-compose -f docker-compose.dev.yml up -d

# 4. View logs
docker-compose -f docker-compose.dev.yml logs -f
```

### Using Startup Script (Linux/Mac)

```bash
cd analysis-ollama
./scripts/start-dev.sh
```

## Pre-production Environment (10 minutes)

```bash
# 1. Navigate to project directory
cd analysis-ollama

# 2. Copy and configure environment file
cp .env.pre.example .env.pre
# Edit .env.pre with your actual values

# 3. Build Docker image
docker build -t analysis-ollama:latest .

# 4. Start container
docker-compose up -d

# 5. View logs
docker-compose logs -f
```

### Using Startup Script (Linux/Mac)

```bash
cd analysis-ollama
./scripts/start-pre.sh
```

## Configuration Quick Reference

### Development (.env.dev)

```bash
ENV=dev
WEWE_RSS_URL=http://localhost:4000
DB_HOST=127.0.0.1
DB_PORT=3308
```

### Pre-production (.env.pre)

```bash
ENV=pre
WEWE_RSS_URL=http://app:4000
DB_HOST=db
DB_PORT=3306
```

### Common Settings (Both Environments)

```bash
# Database
DB_USER=root
DB_PASSWORD=your_password
DB_NAME=analysis_ollama

# Ollama
OLLAMA_BASE_URL=http://192.168.10.43:11434
MODEL_NAME=deepseek-r1:32b

# WeCom
WECOM_WEBHOOK_URL=https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=YOUR_KEY

# Optional
POLL_INTERVAL_MINUTES=60
LOG_LEVEL=INFO
```

## Verification Steps

### 1. Check Health Checks

On startup, you should see:

```
================================================================================
Running startup health checks
================================================================================
✓ Configuration check passed
✓ Database check passed
✓ WeWe-RSS check passed
================================================================================
All health checks passed
================================================================================
```

### 2. Check Article Processing

Look for logs like:

```json
{
  "timestamp": "2024-01-15T10:30:45.123Z",
  "level": "INFO",
  "module": "core.rss_collector",
  "message": "Successfully fetched 5 articles from RSS feed"
}
```

### 3. Check Database

```bash
docker exec -it wewe-rss-db-1 mysql -u root -p
USE analysis_ollama;
SELECT COUNT(*) FROM articles;
SELECT COUNT(*) FROM extracted_projects;
```

### 4. Check WeCom Notifications

- Open your WeCom group
- Verify messages are being received
- Check message format and content

## Troubleshooting

### "Failed to connect to database"

```bash
# Check MySQL is running
docker ps | grep mysql

# Check port mapping (dev)
docker port wewe-rss-db-1

# Check network (pre)
docker network ls | grep wewe-rss
```

### "WeWe-RSS connectivity check failed"

```bash
# Check wewe-rss is running
docker ps | grep wewe-rss

# Test API (dev)
curl http://localhost:4000/feeds/all.atom

# Test API (pre, from container)
docker exec -it analysis-ollama-pre curl http://app:4000/feeds/all.atom
```

### "No articles fetched"

1. Verify wewe-rss has articles:
   ```bash
   curl http://localhost:4000/feeds/all.atom
   ```

2. Check if you completed manual login and subscription

3. Wait a few minutes for wewe-rss to scrape articles

### "LLM analysis timeout"

```bash
# Test Ollama connectivity
curl http://192.168.10.43:11434/api/tags

# Check Ollama logs
# (depends on your Ollama setup)
```

## Next Steps

- Read [Architecture Documentation](docs/ARCHITECTURE.md) for system design
- Read [Deployment Guide](docs/DEPLOYMENT.md) for detailed instructions
- Check logs regularly for errors
- Monitor database growth
- Set up log aggregation for production

## Common Commands

### View Logs

```bash
# Local
# Logs appear in terminal

# Docker (dev)
docker-compose -f docker-compose.dev.yml logs -f

# Docker (pre)
docker-compose logs -f
```

### Stop Service

```bash
# Local
Ctrl+C

# Docker (dev)
docker-compose -f docker-compose.dev.yml down

# Docker (pre)
docker-compose down
```

### Restart Service

```bash
# Local
python main.py

# Docker (dev)
docker-compose -f docker-compose.dev.yml restart

# Docker (pre)
docker-compose restart
```

### Update Code

```bash
# Local
git pull
pip install -r requirements.txt
python main.py

# Docker (dev)
git pull
docker-compose -f docker-compose.dev.yml restart

# Docker (pre)
git pull
docker build -t analysis-ollama:latest .
docker-compose down
docker-compose up -d
```

## Support

For detailed documentation:
- [README.md](README.md) - Project overview
- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) - System architecture
- [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) - Deployment guide

For issues:
- Check logs for error messages
- Review troubleshooting section
- Open a GitHub issue
