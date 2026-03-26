# Use Python 3.10 official image with fixed version tag
FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Set timezone to Asia/Shanghai
ENV TZ=Asia/Shanghai
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Set Python to run in unbuffered mode (for real-time logs)
ENV PYTHONUNBUFFERED=1

# Health check - verify the app can import and settings are valid
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
  CMD python -c "from app.config.settings import settings; print('ok')" || exit 1

# Start command
CMD ["python", "-m", "app.main"]
