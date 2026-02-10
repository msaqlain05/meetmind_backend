# MeetMind Deployment Guide

## Table of Contents
- [Development Setup](#development-setup)
- [Production Deployment](#production-deployment)
- [Docker Deployment](#docker-deployment)
- [Environment Configuration](#environment-configuration)
- [Database Setup](#database-setup)
- [Monitoring & Logging](#monitoring--logging)
- [Troubleshooting](#troubleshooting)

---

## Development Setup

### Prerequisites

- **Python 3.9+** (Python 3.13 recommended)
- **FFmpeg** (for audio processing)
- **OpenAI API Key** (for Whisper and GPT)
- **Git** (for version control)

### Step 1: Install System Dependencies

#### Ubuntu/Debian
```bash
sudo apt update
sudo apt install -y python3 python3-pip python3-venv ffmpeg
```

#### macOS
```bash
brew install python@3.9 ffmpeg
```

#### Windows
1. Install Python from [python.org](https://python.org)
2. Install FFmpeg from [ffmpeg.org](https://ffmpeg.org/download.html)
3. Add FFmpeg to PATH

### Step 2: Clone Repository

```bash
cd /path/to/your/projects
git clone <repository-url>
cd MeetMind
```

### Step 3: Create Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### Step 4: Install Dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### Step 5: Configure Environment

Create `.env` file:

```bash
cp .env.example .env
```

Edit `.env` and add your OpenAI API key:

```env
# Database Configuration
DATABASE_URL=sqlite:///./data/meetmind.db

# Upload Configuration
UPLOAD_DIR=./uploads
MAX_UPLOAD_SIZE_MB=100

# OpenAI Configuration (Required)
OPENAI_API_KEY=sk-your-actual-api-key-here

# Application Configuration
APP_NAME=MeetMind
DEBUG=True
```

### Step 6: Verify FFmpeg Installation

```bash
ffmpeg -version
ffprobe -version
```

Both commands should return version information.

### Step 7: Run the Server

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Server will be available at:
- API: `http://localhost:8000`
- Docs: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

### Step 8: Test the API

```bash
# Health check
curl http://localhost:8000/health

# Upload test (replace with actual audio file)
curl -X POST "http://localhost:8000/meetings/upload" \
  -F "user_id=test-user" \
  -F "audio_file=@test-audio.mp3"
```

---

## Production Deployment

### Architecture Overview

```
Internet
    ↓
[Load Balancer / Reverse Proxy (nginx)]
    ↓
[Uvicorn Workers (Gunicorn)]
    ↓
[FastAPI Application]
    ↓
[PostgreSQL Database]
```

### Prerequisites

- **Linux Server** (Ubuntu 20.04+ recommended)
- **PostgreSQL 12+**
- **Nginx**
- **Supervisor** or **systemd** (for process management)
- **SSL Certificate** (Let's Encrypt recommended)

### Step 1: Server Setup

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install dependencies
sudo apt install -y python3.9 python3.9-venv python3-pip \
  postgresql postgresql-contrib nginx supervisor ffmpeg git
```

### Step 2: Create Application User

```bash
sudo useradd -m -s /bin/bash meetmind
sudo su - meetmind
```

### Step 3: Deploy Application

```bash
# Clone repository
git clone <repository-url> /home/meetmind/app
cd /home/meetmind/app

# Create virtual environment
python3.9 -m venv venv
source venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt
pip install gunicorn
```

### Step 4: Configure PostgreSQL

```bash
# Switch to postgres user
sudo su - postgres

# Create database and user
psql
```

```sql
CREATE DATABASE meetmind;
CREATE USER meetmind_user WITH PASSWORD 'secure_password_here';
GRANT ALL PRIVILEGES ON DATABASE meetmind TO meetmind_user;
\q
```

### Step 5: Production Environment Configuration

Create `/home/meetmind/app/.env`:

```env
# Database Configuration
DATABASE_URL=postgresql://meetmind_user:secure_password_here@localhost/meetmind

# Upload Configuration
UPLOAD_DIR=/home/meetmind/uploads
MAX_UPLOAD_SIZE_MB=100

# OpenAI Configuration
OPENAI_API_KEY=sk-your-production-api-key

# Application Configuration
APP_NAME=MeetMind
DEBUG=False
```

Create upload directory:

```bash
mkdir -p /home/meetmind/uploads
chmod 755 /home/meetmind/uploads
```

### Step 6: Database Migration

Update `app/models/meeting.py` for PostgreSQL:

```python
# Change UUID import
from sqlalchemy.dialects.postgresql import UUID
import uuid

# Update User model
class User(Base):
    __tablename__ = "users"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    # ... rest of model

# Update Meeting model
class Meeting(Base):
    __tablename__ = "meetings"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    # ... rest of model
```

Initialize database:

```bash
source venv/bin/activate
python -c "from app.database import init_db; init_db()"
```

### Step 7: Configure Gunicorn

Create `/home/meetmind/app/gunicorn_config.py`:

```python
import multiprocessing

# Server socket
bind = "127.0.0.1:8000"
backlog = 2048

# Worker processes
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "uvicorn.workers.UvicornWorker"
worker_connections = 1000
timeout = 300  # 5 minutes for large file uploads
keepalive = 2

# Logging
accesslog = "/home/meetmind/logs/access.log"
errorlog = "/home/meetmind/logs/error.log"
loglevel = "info"

# Process naming
proc_name = "meetmind"

# Server mechanics
daemon = False
pidfile = "/home/meetmind/app/gunicorn.pid"
user = "meetmind"
group = "meetmind"
```

Create log directory:

```bash
mkdir -p /home/meetmind/logs
```

### Step 8: Configure Supervisor

Create `/etc/supervisor/conf.d/meetmind.conf`:

```ini
[program:meetmind]
command=/home/meetmind/app/venv/bin/gunicorn -c /home/meetmind/app/gunicorn_config.py app.main:app
directory=/home/meetmind/app
user=meetmind
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=/home/meetmind/logs/supervisor.log
environment=PATH="/home/meetmind/app/venv/bin"
```

Start the service:

```bash
sudo supervisorctl reread
sudo supervisorctl update
sudo supervisorctl start meetmind
sudo supervisorctl status meetmind
```

### Step 9: Configure Nginx

Create `/etc/nginx/sites-available/meetmind`:

```nginx
upstream meetmind {
    server 127.0.0.1:8000;
}

server {
    listen 80;
    server_name your-domain.com;
    
    # Redirect HTTP to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name your-domain.com;
    
    # SSL Configuration
    ssl_certificate /etc/letsencrypt/live/your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    
    # Upload size limit
    client_max_body_size 100M;
    
    # Timeouts for large uploads
    proxy_connect_timeout 300s;
    proxy_send_timeout 300s;
    proxy_read_timeout 300s;
    
    location / {
        proxy_pass http://meetmind;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    
    # Security headers
    add_header X-Content-Type-Options nosniff;
    add_header X-Frame-Options DENY;
    add_header X-XSS-Protection "1; mode=block";
}
```

Enable site and restart Nginx:

```bash
sudo ln -s /etc/nginx/sites-available/meetmind /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

### Step 10: SSL Certificate (Let's Encrypt)

```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com
```

### Step 11: Firewall Configuration

```bash
sudo ufw allow 22/tcp   # SSH
sudo ufw allow 80/tcp   # HTTP
sudo ufw allow 443/tcp  # HTTPS
sudo ufw enable
```

---

## Docker Deployment

### Dockerfile

Create `Dockerfile`:

```dockerfile
FROM python:3.9-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt \
    && pip install gunicorn

# Copy application
COPY . .

# Create necessary directories
RUN mkdir -p /app/data /app/uploads

# Expose port
EXPOSE 8000

# Run application
CMD ["gunicorn", "-w", "4", "-k", "uvicorn.workers.UvicornWorker", \
     "--bind", "0.0.0.0:8000", "--timeout", "300", "app.main:app"]
```

### Docker Compose

Create `docker-compose.yml`:

```yaml
version: '3.8'

services:
  app:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://meetmind:password@db:5432/meetmind
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - UPLOAD_DIR=/app/uploads
      - MAX_UPLOAD_SIZE_MB=100
      - APP_NAME=MeetMind
      - DEBUG=False
    volumes:
      - ./uploads:/app/uploads
      - ./data:/app/data
    depends_on:
      - db
    restart: unless-stopped

  db:
    image: postgres:14
    environment:
      - POSTGRES_DB=meetmind
      - POSTGRES_USER=meetmind
      - POSTGRES_PASSWORD=password
    volumes:
      - postgres_data:/var/lib/postgresql/data
    restart: unless-stopped

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - ./ssl:/etc/nginx/ssl
    depends_on:
      - app
    restart: unless-stopped

volumes:
  postgres_data:
```

### Build and Run

```bash
# Build image
docker-compose build

# Start services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

---

## Environment Configuration

### Environment Variables Reference

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DATABASE_URL` | No | `sqlite:///./data/meetmind.db` | Database connection string |
| `UPLOAD_DIR` | No | `./uploads` | Temporary audio file storage |
| `MAX_UPLOAD_SIZE_MB` | No | `100` | Maximum upload size in MB |
| `OPENAI_API_KEY` | **Yes** | None | OpenAI API key |
| `APP_NAME` | No | `MeetMind` | Application name |
| `DEBUG` | No | `True` | Debug mode (set to `False` in production) |

### Production Best Practices

1. **Never commit `.env` files** to version control
2. **Use environment-specific configs** (dev, staging, prod)
3. **Store secrets in secure vaults** (AWS Secrets Manager, HashiCorp Vault)
4. **Rotate API keys regularly**
5. **Use strong database passwords**
6. **Enable SSL/TLS** for all connections

---

## Database Setup

### SQLite (Development)

Automatically created on first run. No additional setup needed.

**Location:** `./data/meetmind.db`

### PostgreSQL (Production)

#### Installation

```bash
sudo apt install postgresql postgresql-contrib
```

#### Create Database

```bash
sudo -u postgres psql
```

```sql
CREATE DATABASE meetmind;
CREATE USER meetmind_user WITH PASSWORD 'your_secure_password';
GRANT ALL PRIVILEGES ON DATABASE meetmind TO meetmind_user;
\q
```

#### Connection String

```env
DATABASE_URL=postgresql://meetmind_user:your_secure_password@localhost/meetmind
```

#### Backup

```bash
# Backup
pg_dump -U meetmind_user meetmind > backup.sql

# Restore
psql -U meetmind_user meetmind < backup.sql
```

---

## Monitoring & Logging

### Application Logs

Logs are written to:
- **Gunicorn Access**: `/home/meetmind/logs/access.log`
- **Gunicorn Error**: `/home/meetmind/logs/error.log`
- **Supervisor**: `/home/meetmind/logs/supervisor.log`

### Log Rotation

Create `/etc/logrotate.d/meetmind`:

```
/home/meetmind/logs/*.log {
    daily
    rotate 14
    compress
    delaycompress
    notifempty
    missingok
    create 0640 meetmind meetmind
}
```

### Health Monitoring

Use the `/health` endpoint for monitoring:

```bash
curl https://your-domain.com/health
```

### Prometheus Metrics (Optional)

Install `prometheus-fastapi-instrumentator`:

```bash
pip install prometheus-fastapi-instrumentator
```

Update `app/main.py`:

```python
from prometheus_fastapi_instrumentator import Instrumentator

app = FastAPI(...)

Instrumentator().instrument(app).expose(app)
```

Metrics available at `/metrics`.

---

## Troubleshooting

### Common Issues

#### 1. FFmpeg Not Found

**Error:** `FFmpeg is not installed or not in PATH`

**Solution:**
```bash
# Ubuntu/Debian
sudo apt install ffmpeg

# macOS
brew install ffmpeg

# Verify
ffmpeg -version
```

#### 2. OpenAI API Key Error

**Error:** `OpenAI API key not configured`

**Solution:**
- Check `.env` file has `OPENAI_API_KEY=sk-...`
- Verify key is valid at [platform.openai.com](https://platform.openai.com)
- Ensure `.env` is in the same directory as `app/`

#### 3. Database Connection Error

**Error:** `Could not connect to database`

**Solution:**
```bash
# Check PostgreSQL is running
sudo systemctl status postgresql

# Verify connection string
psql -U meetmind_user -d meetmind -h localhost
```

#### 4. File Upload Fails

**Error:** `File too large` or `Invalid file type`

**Solution:**
- Check `MAX_UPLOAD_SIZE_MB` in `.env`
- Verify file format is supported (wav, mp3, webm, m4a, ogg)
- Check nginx `client_max_body_size` matches upload limit

#### 5. Slow Transcription

**Issue:** Large files take too long

**Solution:**
- Chunking is automatic for files >25MB
- Parallel processing is enabled by default
- Check OpenAI API rate limits
- Consider upgrading OpenAI account tier

#### 6. Permission Denied

**Error:** `Permission denied` when saving files

**Solution:**
```bash
# Fix upload directory permissions
sudo chown -R meetmind:meetmind /home/meetmind/uploads
sudo chmod 755 /home/meetmind/uploads
```

### Debug Mode

Enable debug logging:

```env
DEBUG=True
```

This will:
- Show SQL queries
- Provide detailed error messages
- Enable auto-reload on code changes

> [!CAUTION]
> Never enable `DEBUG=True` in production!

### Performance Tuning

#### Gunicorn Workers

```python
# Recommended: (2 x CPU cores) + 1
workers = multiprocessing.cpu_count() * 2 + 1
```

#### Database Connection Pool

```python
# For PostgreSQL
engine = create_engine(
    settings.database_url,
    pool_size=20,
    max_overflow=0
)
```

#### Upload Timeout

Increase for large files:

```python
# gunicorn_config.py
timeout = 600  # 10 minutes
```

```nginx
# nginx.conf
proxy_read_timeout 600s;
```

---

## Maintenance

### Regular Tasks

#### Daily
- Monitor logs for errors
- Check disk space (`df -h`)
- Verify API health endpoint

#### Weekly
- Review OpenAI API usage
- Check database size
- Clean old upload files (if any remain)

#### Monthly
- Update dependencies (`pip install --upgrade -r requirements.txt`)
- Rotate API keys
- Review security logs
- Backup database

### Updates

```bash
# Pull latest code
cd /home/meetmind/app
git pull

# Activate virtual environment
source venv/bin/activate

# Update dependencies
pip install -r requirements.txt

# Restart application
sudo supervisorctl restart meetmind
```

---

## Security Checklist

- [ ] HTTPS enabled with valid SSL certificate
- [ ] Firewall configured (only ports 22, 80, 443 open)
- [ ] Debug mode disabled in production
- [ ] Strong database passwords
- [ ] API keys stored securely (not in code)
- [ ] CORS configured for specific origins
- [ ] Regular security updates applied
- [ ] Logs monitored for suspicious activity
- [ ] Backups automated and tested
- [ ] Authentication implemented (if required)

---

## Support

For issues or questions:
1. Check the [Troubleshooting](#troubleshooting) section
2. Review logs in `/home/meetmind/logs/`
3. Check API documentation at `/docs`
4. Verify OpenAI API status
5. Review GitHub issues (if applicable)
