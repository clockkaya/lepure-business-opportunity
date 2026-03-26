# Deployment Guide

## Overview

This guide provides step-by-step instructions for deploying the analysis-ollama service in both development and pre-production environments.

## Prerequisites

- Docker and Docker Compose installed
- wewe-rss service already running
- MySQL database accessible
- Ollama LLM service running (e.g., at 192.168.10.43:11434)
- WeCom webhook URL configured

## Environment Setup

### Development Environment

Development environment runs analysis-ollama locally (not in Docker) or in a Docker container with code mounted for hot reload.

#### Option 1: Run Locally (Recommended for Development)

1. **Create Python virtual environment**:
   ```bash
   cd analysis-ollama
   python3 -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment variables**:
   ```bash
   cp .env.dev.example .env.dev
   # Edit .env.dev with your actual values
   ```

4. **Run the application**:
   ```bash
   python main.py
   ```

#### Option 2: Run in Docker Container (with code mount)

1. **Configure environment variables**:
   ```bash
   cp .env.dev.example .env.dev
   # Edit .env.dev with your actual values
   ```

2. **Start the container**:
   ```bash
   docker-compose -f docker-compose.dev.yml up -d
   ```

3. **View logs**:
   ```bash
   docker-compose -f docker-compose.dev.yml logs -f
   ```

### Pre-production Environment

Pre-production environment runs analysis-ollama in a Docker container using a built image (no code mount).

1. **Configure environment variables**:
   ```bash
   cp .env.pre.example .env.pre
   # Edit .env.pre with your actual values
   ```

2. **Build Docker image**:
   ```bash
   docker build -t analysis-ollama:latest .
   ```

3. **Start the container**:
   ```bash
   docker-compose up -d
   ```

4. **View logs**:
   ```bash
   docker-compose logs -f
   ```

## Complete Startup Flow

**IMPORTANT**: The following steps must be executed in order. Do NOT start analysis-ollama before completing steps 1-3.

### Step 1: Start wewe-rss

```bash
cd wewe-rss
docker-compose up -d
```

Wait for containers to be healthy:
```bash
docker-compose ps
```

### Step 2: Manual Configuration (CRITICAL)

**This step MUST be completed by a human and cannot be automated.**

1. **Access wewe-rss Web UI**:
   ```
   http://localhost:4000
   ```

2. **Login to WeRead account**:
   - Click login button
   - Scan QR code with WeChat
   - Complete authentication

3. **Subscribe to target official accounts**:
   - Navigate to subscription management
   - Add official accounts you want to monitor
   - Save configuration

4. **Wait for initial article scraping**:
   - wewe-rss will start scraping articles
   - This may take a few minutes
   - Check the feed list to confirm articles are being collected

### Step 3: Verify wewe-rss is Working

Before starting analysis-ollama, verify that wewe-rss is functioning correctly:

1. **Check RSS feed**:
   ```bash
   curl "http://localhost:4000/feeds/all.atom?mode=fulltext&update=true"
   ```
   
   You should see XML output with article entries.

2. **Check database**:
   ```bash
   docker exec -it wewe-rss-db-1 mysql -u root -p
   # Enter password
   USE wewe-rss;
   SELECT COUNT(*) FROM FeedItem;
   ```
   
   You should see articles in the database.

### Step 4: Start analysis-ollama

**Only after steps 1-3 are complete**, start analysis-ollama:

**Development**:
```bash
cd analysis-ollama
python main.py
# OR
docker-compose -f docker-compose.dev.yml up -d
```

**Pre-production**:
```bash
cd analysis-ollama
docker-compose up -d
```

### Step 5: Verify analysis-ollama is Working

1. **Check logs**:
   ```bash
   # If running locally
   # Logs will appear in terminal
   
   # If running in Docker
   docker logs -f analysis-ollama-dev  # or analysis-ollama-pre
   ```

2. **Check database**:
   ```bash
   docker exec -it wewe-rss-db-1 mysql -u root -p
   # Enter password
   USE analysis_ollama;
   SELECT COUNT(*) FROM articles;
   SELECT COUNT(*) FROM extracted_projects;
   ```

3. **Check WeCom notifications**:
   - Verify messages are being sent to your WeCom group
   - Check message format and content

## Configuration Reference

### Environment Variables

#### Required Variables

| Variable | Description | Example (Dev) | Example (Pre) |
|----------|-------------|---------------|---------------|
| `ENV` | Environment identifier | `dev` | `pre` |
| `WEWE_RSS_URL` | WeWe-RSS API URL | `http://localhost:4000` | `http://app:4000` |
| `AUTH_CODE` | WeWe-RSS auth code | `123567` | `123567` |
| `DB_HOST` | MySQL host | `127.0.0.1` | `db` |
| `DB_PORT` | MySQL port | `3308` | `3306` |
| `DB_USER` | MySQL username | `root` | `root` |
| `DB_PASSWORD` | MySQL password | `your_password` | `your_password` |
| `DB_NAME` | Database name | `analysis_ollama` | `analysis_ollama` |
| `OLLAMA_BASE_URL` | Ollama API URL | `http://192.168.10.43:11434` | `http://192.168.10.43:11434` |
| `MODEL_NAME` | LLM model name | `deepseek-r1:32b` | `deepseek-r1:32b` |
| `WECOM_WEBHOOK_URL` | WeCom webhook URL | `https://qyapi.weixin.qq.com/...` | `https://qyapi.weixin.qq.com/...` |

#### Optional Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `POLL_INTERVAL_MINUTES` | Polling interval in minutes | `60` |
| `LOG_LEVEL` | Log level (DEBUG, INFO, WARNING, ERROR) | `INFO` |

### Configuration Files

- `.env.dev.example`: Development environment template
- `.env.pre.example`: Pre-production environment template
- `.env.example`: Generic template

**IMPORTANT**: Never commit actual `.env` files to git. They contain sensitive information.

## Docker Network Configuration

### Understanding Docker Networks

wewe-rss creates a Docker network when started:

```bash
# List Docker networks
docker network ls

# You should see something like:
# wewe-rss_default
```

### Connecting analysis-ollama to wewe-rss Network

The `docker-compose.yml` and `docker-compose.dev.yml` files are already configured to use the external network:

```yaml
networks:
  wewe-rss_default:
    external: true
```

### Troubleshooting Network Issues

If you see an error like "network wewe-rss_default not found":

1. **Check if wewe-rss is running**:
   ```bash
   docker-compose -f ../wewe-rss/docker-compose.yml ps
   ```

2. **Check network name**:
   ```bash
   docker network ls | grep wewe
   ```

3. **If network name is different**, update `docker-compose.yml`:
   ```yaml
   networks:
     wewe-rss_wewe-rss:  # Use actual network name
       external: true
   ```

## Validation

### Health Check Validation

When analysis-ollama starts, it runs health checks:

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

If any check fails, the application will exit with an error message.

### Functional Validation

1. **RSS Collection**:
   - Check logs for "Successfully fetched X articles from RSS feed"
   - Verify articles are inserted into `articles` table

2. **HTML Parsing**:
   - Check logs for "Cleaned HTML content: X chars -> Y chars"

3. **LLM Analysis**:
   - Check logs for "Successfully analyzed article: [title]"
   - Verify extracted data in `extracted_projects` table

4. **WeCom Notification**:
   - Check logs for "Successfully sent WeCom notification for project: [name]"
   - Verify messages appear in WeCom group

## Troubleshooting

### Common Issues

#### 1. "Failed to connect to database"

**Symptoms**:
```
ERROR: Failed to connect to database (attempt 1/3): Can't connect to MySQL server
```

**Solutions**:
- Verify MySQL is running: `docker ps | grep mysql`
- Check DB_HOST and DB_PORT in `.env` file
- For dev environment, ensure port 3308 is mapped: `docker port wewe-rss-db-1`
- For pre environment, ensure analysis-ollama is in wewe-rss network

#### 2. "WeWe-RSS connectivity check failed"

**Symptoms**:
```
WARNING: WeWe-RSS connectivity check failed: Connection refused
```

**Solutions**:
- Verify wewe-rss is running: `docker-compose -f ../wewe-rss/docker-compose.yml ps`
- Check WEWE_RSS_URL in `.env` file
- For dev environment, use `http://localhost:4000`
- For pre environment, use `http://app:4000`
- Ensure you completed manual login and subscription (Step 2)

#### 3. "network wewe-rss_default not found"

**Symptoms**:
```
ERROR: Network wewe-rss_default declared as external, but could not be found
```

**Solutions**:
- Start wewe-rss first: `cd ../wewe-rss && docker-compose up -d`
- Check actual network name: `docker network ls | grep wewe`
- Update `docker-compose.yml` if network name is different

#### 4. "LLM analysis timeout"

**Symptoms**:
```
ERROR: LLM analysis timeout (120 seconds) for article: [title]
```

**Solutions**:
- Verify Ollama service is running: `curl http://192.168.10.43:11434/api/tags`
- Check OLLAMA_BASE_URL in `.env` file
- Ensure network connectivity to Ollama host
- Consider using a smaller model if timeouts persist

#### 5. "No articles fetched from RSS feed"

**Symptoms**:
```
INFO: No articles fetched from RSS feed
```

**Solutions**:
- Verify wewe-rss has articles: `curl http://localhost:4000/feeds/all.atom`
- Check if you completed manual login and subscription (Step 2)
- Wait a few minutes for wewe-rss to scrape articles
- Check wewe-rss logs: `docker-compose -f ../wewe-rss/docker-compose.yml logs -f`

#### 6. "Configuration Error: Missing required environment variables"

**Symptoms**:
```
Configuration Error: Missing or invalid required environment variables
❌ WEWE_RSS_URL: Field required
```

**Solutions**:
- Ensure `.env.dev` or `.env.pre` file exists
- Copy from example: `cp .env.dev.example .env.dev`
- Fill in all required variables
- Check for typos in variable names

### Debugging Tips

1. **Enable DEBUG logging**:
   ```bash
   # In .env file
   LOG_LEVEL=DEBUG
   ```

2. **Check Docker container status**:
   ```bash
   docker ps -a
   docker logs [container_name]
   ```

3. **Check Docker network connectivity**:
   ```bash
   # From analysis-ollama container
   docker exec -it analysis-ollama-dev ping app
   docker exec -it analysis-ollama-dev ping db
   ```

4. **Check database connectivity**:
   ```bash
   docker exec -it wewe-rss-db-1 mysql -u root -p -e "SHOW DATABASES;"
   ```

5. **Test Ollama connectivity**:
   ```bash
   curl http://192.168.10.43:11434/api/tags
   ```

## Maintenance

### Updating the Application

**Development**:
```bash
# If running locally
git pull
pip install -r requirements.txt
python main.py

# If running in Docker
git pull
docker-compose -f docker-compose.dev.yml restart
```

**Pre-production**:
```bash
git pull
docker build -t analysis-ollama:latest .
docker-compose down
docker-compose up -d
```

### Viewing Logs

**Local**:
```bash
# Logs appear in terminal
```

**Docker**:
```bash
# Follow logs
docker logs -f analysis-ollama-dev  # or analysis-ollama-pre

# View last 100 lines
docker logs --tail 100 analysis-ollama-dev

# View logs since 1 hour ago
docker logs --since 1h analysis-ollama-dev
```

### Database Backup

```bash
# Backup analysis_ollama database
docker exec wewe-rss-db-1 mysqldump -u root -p analysis_ollama > backup_$(date +%Y%m%d).sql

# Restore from backup
docker exec -i wewe-rss-db-1 mysql -u root -p analysis_ollama < backup_20240115.sql
```

### Stopping Services

**Development**:
```bash
# If running locally
Ctrl+C

# If running in Docker
docker-compose -f docker-compose.dev.yml down
```

**Pre-production**:
```bash
docker-compose down
```

## Performance Tuning

### Database Connection Pool

Adjust in `core/db_repo.py`:
```python
engine = create_engine(
    settings.database_url,
    pool_size=5,        # Increase for more concurrent connections
    max_overflow=10,    # Increase for burst traffic
    pool_recycle=3600,  # Recycle connections every hour
    pool_pre_ping=True  # Verify connections before use
)
```

### Polling Interval

Adjust in `.env` file:
```bash
# Poll every 30 minutes instead of 60
POLL_INTERVAL_MINUTES=30
```

### LLM Timeout

Adjust in `core/llm_analyzer.py`:
```python
response = requests.post(
    f"{settings.OLLAMA_BASE_URL}/api/chat",
    json=payload,
    timeout=180  # Increase to 180 seconds
)
```

## Security Best Practices

1. **Never commit `.env` files**: Ensure `.gitignore` includes `.env*`
2. **Use strong database passwords**: Generate random passwords
3. **Restrict network access**: Use firewall rules to limit access
4. **Keep dependencies updated**: Regularly run `pip install --upgrade -r requirements.txt`
5. **Monitor logs**: Set up log aggregation and alerting
6. **Rotate credentials**: Periodically change database passwords and webhook URLs

## Monitoring

### Key Metrics to Monitor

1. **Application Health**:
   - Container status: `docker ps`
   - Health check status: `docker inspect analysis-ollama-pre | grep Health`

2. **Processing Metrics**:
   - Articles processed per hour
   - LLM analysis success rate
   - WeCom notification delivery rate

3. **Resource Usage**:
   - CPU usage: `docker stats analysis-ollama-pre`
   - Memory usage: `docker stats analysis-ollama-pre`
   - Disk usage: `df -h`

4. **Database Metrics**:
   - Connection pool usage
   - Query performance
   - Table sizes

### Log Monitoring

Set up log aggregation with tools like:
- ELK Stack (Elasticsearch, Logstash, Kibana)
- Grafana Loki
- Splunk

Example log query:
```
level:ERROR module:core.llm_analyzer
```

## Scaling Considerations

### Horizontal Scaling

To run multiple instances:

1. **Use different container names**:
   ```yaml
   services:
     analysis-ollama-1:
       container_name: analysis-ollama-pre-1
     analysis-ollama-2:
       container_name: analysis-ollama-pre-2
   ```

2. **Coordinate polling**: Use distributed locks or message queues to avoid duplicate processing

### Vertical Scaling

Increase container resources:
```yaml
services:
  analysis-ollama:
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 4G
        reservations:
          cpus: '1'
          memory: 2G
```

## Support

For issues and questions:
1. Check this documentation
2. Review logs for error messages
3. Check GitHub issues
4. Contact the development team
