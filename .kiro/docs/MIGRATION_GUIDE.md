# Migration Guide

## Overview

This guide helps you migrate from the old "Docker + local hybrid" setup to the new environment-separated architecture.

## What Changed?

### Architecture Changes

**Before**:
- wewe-rss in Docker
- analysis-ollama running locally
- Mixed configuration
- No environment separation
- Basic error handling
- Print-based logging

**After**:
- wewe-rss in Docker (unchanged)
- analysis-ollama supports both local and Docker deployment
- Clear dev/pre environment separation
- Comprehensive error handling
- Structured JSON logging
- Health checks on startup
- Connection retry mechanisms
- Complete documentation

### File Structure Changes

**New Files**:
```
analysis-ollama/
├── core/
│   ├── logger.py              # NEW: Structured logging
│   └── health_check.py        # NEW: Startup health checks
├── docs/
│   ├── ARCHITECTURE.md        # NEW: Architecture documentation
│   └── DEPLOYMENT.md          # NEW: Deployment guide
├── scripts/
│   ├── start-dev.sh           # NEW: Dev startup script
│   └── start-pre.sh           # NEW: Pre startup script
├── Dockerfile                 # NEW: Container image
├── docker-compose.yml         # NEW: Pre environment
├── docker-compose.dev.yml     # NEW: Dev environment
├── .dockerignore              # NEW: Docker optimization
├── QUICKSTART.md              # NEW: Quick start guide
├── IMPLEMENTATION_SUMMARY.md  # NEW: Implementation summary
├── VALIDATION_CHECKLIST.md    # NEW: Validation checklist
└── MIGRATION_GUIDE.md         # NEW: This file
```

**Updated Files**:
```
analysis-ollama/
├── core/
│   ├── db_repo.py             # UPDATED: Retry, health check, connection pool
│   ├── rss_collector.py       # UPDATED: Logging, error handling
│   ├── html_parser.py         # UPDATED: Logging, error handling
│   ├── llm_analyzer.py        # UPDATED: Logging, error handling
│   └── notification.py        # UPDATED: Logging, error handling
├── config/
│   └── settings.py            # UPDATED: Validation, LOG_LEVEL
├── main.py                    # UPDATED: Logging, health checks
├── requirements.txt           # UPDATED: Fixed versions, new deps
└── README.md                  # UPDATED: Complete rewrite
```

## Migration Steps

### Step 1: Backup Current Setup

```bash
# Backup your current .env file
cp analysis-ollama/.env analysis-ollama/.env.backup

# Backup database (optional but recommended)
docker exec wewe-rss-db-1 mysqldump -u root -p analysis_ollama > backup_$(date +%Y%m%d).sql
```

### Step 2: Pull Latest Code

```bash
cd lepure-business-opportunity
git pull origin main
```

### Step 3: Update Dependencies

```bash
cd analysis-ollama
pip install -r requirements.txt
```

### Step 4: Migrate Configuration

#### For Development Environment

```bash
# Copy your old .env to .env.dev
cp .env.backup .env.dev

# Add new required variables to .env.dev
echo "LOG_LEVEL=INFO" >> .env.dev

# Verify DB_NAME is set
grep DB_NAME .env.dev || echo "DB_NAME=analysis_ollama" >> .env.dev
```

#### For Pre-production Environment

```bash
# Create .env.pre from example
cp .env.pre.example .env.pre

# Copy values from .env.backup and adjust for Docker network
# Edit .env.pre manually:
# - Change DB_HOST from 127.0.0.1 to db
# - Change DB_PORT from 3308 to 3306
# - Change WEWE_RSS_URL from http://localhost:4000 to http://app:4000
```

### Step 5: Update Database (if needed)

The database schema hasn't changed, but if you want to add the `feed_id` column for future extensibility:

```sql
-- Connect to database
docker exec -it wewe-rss-db-1 mysql -u root -p

USE analysis_ollama;

-- Add feed_id column if not exists
ALTER TABLE articles 
ADD COLUMN feed_id VARCHAR(100) NULL COMMENT '来源 feed ID，用于多公众号扩展'
AFTER guid;

-- Add index
CREATE INDEX idx_feed_id ON articles(feed_id);
```

### Step 6: Test Development Environment

```bash
cd analysis-ollama

# Option 1: Run locally
python main.py

# Option 2: Run in Docker
docker-compose -f docker-compose.dev.yml up -d
docker-compose -f docker-compose.dev.yml logs -f
```

**Expected Output**:
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

### Step 7: Verify Functionality

1. **Check logs are in JSON format**:
   ```json
   {
     "timestamp": "2024-01-15T10:30:45.123Z",
     "level": "INFO",
     "module": "core.rss_collector",
     "message": "Successfully fetched 5 articles from RSS feed"
   }
   ```

2. **Check database**:
   ```bash
   docker exec -it wewe-rss-db-1 mysql -u root -p
   USE analysis_ollama;
   SELECT COUNT(*) FROM articles;
   SELECT COUNT(*) FROM extracted_projects;
   ```

3. **Check WeCom notifications**:
   - Verify messages are still being sent
   - Check message format is correct

### Step 8: Deploy to Pre-production (Optional)

```bash
cd analysis-ollama

# Build image
docker build -t analysis-ollama:latest .

# Start container
docker-compose up -d

# Check logs
docker-compose logs -f
```

## Configuration Migration

### Old .env Format

```bash
# Old format (still works in dev)
WEWE_RSS_URL=http://localhost:4000
DB_HOST=127.0.0.1
DB_PORT=3308
```

### New .env.dev Format

```bash
# New dev format (same as old)
ENV=dev
WEWE_RSS_URL=http://localhost:4000
DB_HOST=127.0.0.1
DB_PORT=3308
DB_NAME=analysis_ollama
LOG_LEVEL=INFO
```

### New .env.pre Format

```bash
# New pre format (for Docker)
ENV=pre
WEWE_RSS_URL=http://app:4000
DB_HOST=db
DB_PORT=3306
DB_NAME=analysis_ollama
LOG_LEVEL=INFO
```

## Breaking Changes

### 1. Logging Output Format

**Before**: Plain text logs
```
Fetching RSS feed from: http://localhost:4000/feeds/all.atom
Successfully fetched 5 articles from RSS feed.
```

**After**: JSON logs
```json
{
  "timestamp": "2024-01-15T10:30:45.123Z",
  "level": "INFO",
  "module": "core.rss_collector",
  "message": "Fetching RSS feed from: http://localhost:4000/feeds/all.atom"
}
```

**Impact**: If you have log parsing scripts, update them to parse JSON.

### 2. Database Connection

**Before**: Simple connection, no retry
```python
engine = create_engine(settings.database_url, pool_recycle=3600)
```

**After**: Connection with retry and health check
```python
# Retries 3 times with 5 second intervals
# Includes health check function
```

**Impact**: Application may take longer to start if database is slow, but will be more reliable.

### 3. Error Handling

**Before**: Errors could crash the application
```python
articles = fetch_feed_articles()  # Could raise exception
```

**After**: Errors are handled gracefully
```python
articles = fetch_feed_articles()  # Returns empty list on error
```

**Impact**: Application is more stable but you need to monitor logs for errors.

### 4. Health Checks

**Before**: No health checks, application starts immediately

**After**: Health checks run on startup
```
✓ Configuration check passed
✓ Database check passed
✓ WeWe-RSS check passed
```

**Impact**: Application may fail to start if dependencies are not ready. This is intentional and helps catch configuration issues early.

## Rollback Procedure

If you need to rollback to the old version:

1. **Stop the new version**:
   ```bash
   # If running locally
   Ctrl+C
   
   # If running in Docker
   docker-compose down
   ```

2. **Restore old code**:
   ```bash
   git checkout <previous-commit-hash>
   ```

3. **Restore old configuration**:
   ```bash
   cp .env.backup .env
   ```

4. **Restore old dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

5. **Start old version**:
   ```bash
   python main.py
   ```

## Troubleshooting Migration Issues

### Issue 1: "Module 'pythonjsonlogger' not found"

**Solution**:
```bash
pip install python-json-logger
# or
pip install -r requirements.txt
```

### Issue 2: "Health checks failed"

**Solution**:
- Check that wewe-rss is running
- Check that MySQL is accessible
- Verify all environment variables are set
- Check logs for specific error

### Issue 3: "Logs are not in JSON format"

**Solution**:
- Ensure `core/logger.py` exists
- Ensure `main.py` calls `setup_logging()`
- Check that `python-json-logger` is installed

### Issue 4: "Database connection failed"

**Solution**:
- Check DB_HOST and DB_PORT in .env file
- For dev: ensure MySQL port 3308 is mapped
- For pre: ensure container is in wewe-rss network
- Check MySQL is running: `docker ps | grep mysql`

### Issue 5: "Docker network not found"

**Solution**:
```bash
# Check network exists
docker network ls | grep wewe-rss

# If not, start wewe-rss first
cd ../wewe-rss
docker-compose up -d
```

## Post-Migration Validation

After migration, verify:

- [ ] Application starts without errors
- [ ] Health checks pass
- [ ] Articles are fetched from RSS
- [ ] LLM analysis works
- [ ] Data is saved to database
- [ ] WeCom notifications are sent
- [ ] Logs are in JSON format
- [ ] No errors in logs
- [ ] Performance is acceptable

## Getting Help

If you encounter issues during migration:

1. Check the [Troubleshooting section](docs/DEPLOYMENT.md#troubleshooting) in DEPLOYMENT.md
2. Review logs for error messages
3. Check [VALIDATION_CHECKLIST.md](VALIDATION_CHECKLIST.md)
4. Open a GitHub issue with:
   - Error message
   - Log output
   - Configuration (sanitized)
   - Steps to reproduce

## Benefits of New Architecture

After migration, you'll have:

✅ **Better Reliability**:
- Connection retry mechanisms
- Comprehensive error handling
- Health checks on startup

✅ **Better Observability**:
- Structured JSON logging
- Detailed error messages
- Easy log parsing and monitoring

✅ **Better Deployment**:
- Docker containerization
- Environment separation (dev/pre)
- Easy scaling and distribution

✅ **Better Documentation**:
- Architecture documentation
- Deployment guide
- Quick start guide
- Troubleshooting guide

✅ **Better Extensibility**:
- Multi-feed support framework
- Dynamic webhook routing
- Clear extension points

## Timeline

Recommended migration timeline:

- **Week 1**: Test in development environment
- **Week 2**: Deploy to pre-production
- **Week 3**: Monitor and fix issues
- **Week 4**: Deploy to production

## Support

For migration support:
- Read [DEPLOYMENT.md](docs/DEPLOYMENT.md)
- Read [QUICKSTART.md](QUICKSTART.md)
- Check [VALIDATION_CHECKLIST.md](VALIDATION_CHECKLIST.md)
- Open a GitHub issue
