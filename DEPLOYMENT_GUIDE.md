# SiteLLM Vertebro - Deployment Guide

**Version**: 1.0  
**Date**: 2025-11-16  
**Status**: Production Ready

---

## 📋 Table of Contents

1. [Prerequisites](#prerequisites)
2. [Environment Variables](#environment-variables)
3. [Dependencies](#dependencies)
4. [Installation](#installation)
5. [Configuration](#configuration)
6. [Security Setup](#security-setup)
7. [Database Setup](#database-setup)
8. [Deployment](#deployment)
9. [Monitoring](#monitoring)
10. [Troubleshooting](#troubleshooting)

---

## Prerequisites

### Required Services
- **MongoDB** (4.x or later)
- **Redis** (6.x or later)
- **Qdrant** (for vector search)
- **Ollama** (for LLM inference)

### System Requirements
- Python 3.10-3.12
- 8GB+ RAM (16GB+ recommended)
- 50GB+ disk space
- Network access to MongoDB, Redis, Qdrant, and Ollama

---

## Environment Variables

### Core Configuration

```bash
# Application
APP_HOST=0.0.0.0
APP_PORT=8000
APP_DEBUG=false
APP_SSL_CERT=/path/to/cert.pem
APP_SSL_KEY=/path/to/key.pem

# CORS
CORS_ORIGINS=http://localhost:3000,https://yourdomain.com
ALLOW_ALL_ORIGINS=false
```

### MongoDB Configuration

```bash
# MongoDB Connection
MONGO_HOST=localhost
MONGO_PORT=27017
MONGO_USERNAME=your_username
MONGO_PASSWORD=your_password
MONGO_DATABASE=sitellm
MONGO_AUTH_DATABASE=admin

# Connection Pooling
MONGO_MIN_POOL_SIZE=10
MONGO_MAX_POOL_SIZE=100
MONGO_MAX_IDLE_TIME_MS=30000

# Collections
MONGO_CONTEXTS_COLLECTION=contexts
MONGO_PRESETS_COLLECTION=presets
MONGO_DOCUMENTS_COLLECTION=documents
MONGO_QA_COLLECTION=qa_pairs
MONGO_READING_COLLECTION=reading_pages
MONGO_VOICE_SAMPLES_COLLECTION=voice_samples
MONGO_VOICE_JOBS_COLLECTION=voice_jobs
```

### Redis Configuration

```bash
# Redis Connection
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=your_redis_password
REDIS_DB=0

# Cache TTLs
CACHE_TTL_LLM_RESULTS=3600
CACHE_TTL_EMBEDDINGS=86400
CACHE_TTL_SEARCH=900
```

### Qdrant Configuration

```bash
QDRANT_URL=http://localhost:6333
QDRANT_COLLECTION=documents
```

### Ollama Configuration

```bash
OLLAMA_BASE_URL=http://localhost:11434
```

### Security Configuration

```bash
# Rate Limiting
RATE_LIMIT_READ_PER_MIN=100
RATE_LIMIT_WRITE_PER_MIN=10
RATE_LIMIT_PER_HOUR=1000
RATE_LIMITING_ENABLED=true

# CSRF
CSRF_SECRET_KEY=your-secret-csrf-key-change-me

# Security Headers
CSP_ENABLED=true
GZIP_ENABLED=true

# Basic Auth (for admin panel)
ADMIN_USERNAME=admin
ADMIN_PASSWORD=your-secure-password
```

### Voice Assistant Configuration

```bash
# Voice STT Provider (simple, whisper, vosk)
VOICE_STT_PROVIDER=simple

# Voice TTS Provider (demo, elevenlabs, azure)
VOICE_TTS_PROVIDER=demo

# Voice Session
VOICE_SESSION_TIMEOUT=3600
VOICE_MAX_CONCURRENT_SESSIONS=100
WS_MAX_CONNECTIONS=1000
WS_PING_INTERVAL=30

# ElevenLabs (optional)
ELEVENLABS_API_KEY=your-elevenlabs-api-key

# Azure Speech (optional)
AZURE_SPEECH_KEY=your-azure-speech-key
AZURE_SPEECH_REGION=eastus
```

### File Upload Configuration

```bash
# File Upload Limits
MAX_UPLOAD_SIZE=104857600  # 100 MB
MAX_QUESTION_LENGTH=1000
MAX_ANSWER_LENGTH=10000
```

---

## Dependencies

### Required Python Packages
All dependencies are specified in `pyproject.toml`:
- FastAPI
- MongoDB (Motor/PyMongo)
- Redis
- Qdrant Client
- Structlog
- Pydantic
- And more...

### Optional Dependencies
- `python-magic` - For enhanced MIME type detection
- `faster-whisper` - For Whisper STT
- `vosk` - For Vosk STT
- `elevenlabs` - For ElevenLabs TTS
- `azure-cognitiveservices-speech` - For Azure TTS

### Installation

```bash
# Install dependencies using uv (recommended)
uv sync

# Or using pip
pip install -e .
```

---

## Installation

### 1. Clone Repository

```bash
git clone <repository-url>
cd sitellm_vertebro
```

### 2. Install Dependencies

```bash
# Using uv (recommended)
uv sync

# Or using pip
pip install -e .
pip install -e ".[dev]"  # For development
```

### 3. Configure Environment

```bash
# Copy example env file
cp .env.example .env

# Edit .env with your configuration
nano .env
```

### 4. Initialize Database

```bash
# MongoDB indexes will be created automatically on first run
# Voice schema migration (if needed)
python scripts/migrate_voice_schema.py
```

---

## Configuration

### MongoDB Setup

1. **Create Database and User**:
```javascript
use sitellm
db.createUser({
  user: "sitellm_user",
  pwd: "your_password",
  roles: [{role: "readWrite", db: "sitellm"}]
})
```

2. **Indexes**: Created automatically on application startup

### Redis Setup

1. **Configure Redis**:
```bash
# Redis configuration file
maxmemory 2gb
maxmemory-policy allkeys-lru
```

### Qdrant Setup

1. **Start Qdrant**:
```bash
docker run -p 6333:6333 qdrant/qdrant
```

2. **Create Collection**: Collection created automatically on first use

---

## Security Setup

### SSL/TLS Configuration

1. **Generate Certificates** (development):
```bash
bash scripts/generate_self_signed_cert.sh
```

2. **Production Certificates**:
   - Use certificates from your CA
   - Set `APP_SSL_CERT` and `APP_SSL_KEY` in environment

### Security Headers

All security headers are configured via middleware:
- CSP (Content Security Policy)
- CSRF protection
- Rate limiting
- Input validation

### Admin Authentication

1. **Set Admin Credentials**:
```bash
export ADMIN_USERNAME=admin
export ADMIN_PASSWORD=your-secure-password
```

2. **Change Default**: Never use default credentials in production!

---

## Deployment

### Docker Deployment (Recommended)

```bash
# Build and run with Docker Compose
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

### Manual Deployment

```bash
# Run application
uvicorn app:app --host 0.0.0.0 --port 8000

# Or with SSL
uvicorn app:app --host 0.0.0.0 --port 8000 --ssl-keyfile /path/to/key.pem --ssl-certfile /path/to/cert.pem
```

### Production Deployment

1. **Use Production Server**:
```bash
# Gunicorn with Uvicorn workers
gunicorn app:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

2. **Reverse Proxy** (Nginx example):
```nginx
server {
    listen 80;
    server_name yourdomain.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

3. **Systemd Service**:
```ini
[Unit]
Description=SiteLLM Vertebro API
After=network.target

[Service]
User=sitellm
WorkingDirectory=/opt/sitellm_vertebro
Environment="PATH=/opt/sitellm_vertebro/venv/bin"
ExecStart=/opt/sitellm_vertebro/venv/bin/uvicorn app:app --host 0.0.0.0 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
```

---

## Monitoring

### Health Checks

```bash
# Health endpoint
curl http://localhost:8000/health

# Status endpoint
curl http://localhost:8000/status

# Metrics endpoint
curl http://localhost:8000/metrics
```

### Logging

Logs are structured and output to:
- Console (stdout)
- Log files (if configured)
- Structured format (JSON) for log aggregation

### Metrics

Prometheus metrics available at `/metrics`:
- Request counts
- Request latency
- Cache hit rates
- Database connection pool status

---

## Troubleshooting

### Common Issues

#### MongoDB Connection Failed
```bash
# Check MongoDB is running
mongosh --eval "db.adminCommand('ping')"

# Check connection string
echo $MONGO_HOST $MONGO_PORT
```

#### Redis Connection Failed
```bash
# Check Redis is running
redis-cli ping

# Test connection
redis-cli -h $REDIS_HOST -p $REDIS_PORT ping
```

#### Import Errors
```bash
# Verify dependencies
pip list | grep structlog
pip list | grep fastapi

# Reinstall dependencies
pip install -e .
```

#### Port Already in Use
```bash
# Find process using port
lsof -i :8000

# Kill process or change port
export APP_PORT=8001
```

### Debug Mode

```bash
# Enable debug mode (development only!)
export APP_DEBUG=true

# Run with debug
uvicorn app:app --reload --log-level debug
```

---

## Performance Tuning

### MongoDB

```bash
# Increase connection pool
MONGO_MIN_POOL_SIZE=20
MONGO_MAX_POOL_SIZE=200
```

### Redis

```bash
# Adjust cache TTLs based on usage
CACHE_TTL_LLM_RESULTS=7200  # 2 hours
CACHE_TTL_SEARCH=1800  # 30 minutes
```

### Application

```bash
# Worker processes
gunicorn app:app -w 4 -k uvicorn.workers.UvicornWorker
```

---

## Backup & Recovery

### MongoDB Backup

```bash
# Backup database
mongodump --uri="mongodb://user:pass@host:port/database" --out=/backup/path

# Restore database
mongorestore --uri="mongodb://user:pass@host:port/database" /backup/path
```

### Configuration Backup

```bash
# Backup environment variables
env > .env.backup

# Backup configuration files
cp pyproject.toml pyproject.toml.backup
```

---

## Security Checklist

- [ ] Change all default passwords
- [ ] Use strong passwords for all services
- [ ] Enable SSL/TLS in production
- [ ] Configure firewall rules
- [ ] Set up rate limiting
- [ ] Enable security headers
- [ ] Regular security updates
- [ ] Monitor logs for suspicious activity
- [ ] Backup data regularly
- [ ] Test disaster recovery procedures

---

## Support

For issues and questions:
- Check documentation in `docs/`
- Review `CHANGELOG.md` for recent changes
- Check GitHub issues

---

*Last Updated: 2025-11-16*  
*Version: 1.0*





