# Celery and Redis Deployment Guide

This guide explains how to deploy Celery and Redis for the ETS application using Docker, including configuration options and an overview of the application architecture.

## Table of Contents

- [Architecture Overview](#architecture-overview)
- [Prerequisites](#prerequisites)
- [Docker Compose Setup](#docker-compose-setup)
- [Configuration Settings](#configuration-settings)
- [Running the Services](#running-the-services)
- [Scaling for High Load](#scaling-for-high-load)
- [Monitoring and Maintenance](#monitoring-and-maintenance)
- [Troubleshooting](#troubleshooting)

## Architecture Overview

The ETS application uses the following components for asynchronous OPC polling:

```
┌─────────────────┐      ┌──────────────┐      ┌─────────────────────────┐
│   Django App    │──────│    Redis     │──────│  Celery Workers          │
│   (Daphne/Gunicorn)│    │  (Broker)    │      │  - opc_scheduler queue   │
└─────────────────┘      └──────────────┘      │  - opc_polling queue     │
         │                      │              │  - default queue         │
         │                      │              └─────────────────────────┘
         │                      │                       │
         │                      │                       ▼
         │                      │              ┌─────────────────────────┐
         │                      │              │  Celery Beat             │
         │                      │              │  (Scheduler)             │
         │                      │              └─────────────────────────┘
         │                      │
         ▼                      ▼
┌─────────────────┐      ┌──────────────┐
│   PostgreSQL    │      │   OPC UA    │
│   (Database)    │      │   Servers   │
└─────────────────┘      └──────────────┘
```

### Component Roles

- **Django App**: Main web application serving REST APIs and managing OPC connections
- **Redis**: Message broker for Celery (task queue) and result backend
- **Celery Workers**: Execute asynchronous tasks (OPC polling) from dedicated queues
- **Celery Beat**: Scheduler that triggers periodic tasks (poll_due_opc_connections every 60s)
- **PostgreSQL**: Stores OPC connections, nodes, live values, and historical data
- **OPC UA Servers**: External industrial servers providing real-time data

### Task Queue Architecture

The application uses dedicated queues to isolate different types of work:

- **opc_scheduler**: Queue for the scheduler task (poll_due_opc_connections)
- **opc_polling**: Queue for individual OPC connection polling tasks
- **default**: Queue for general application tasks (if any)

This separation ensures that:
- The scheduler is never blocked by polling tasks
- Polling tasks can be scaled independently
- Different priorities can be assigned to different task types

## Prerequisites

- Docker and Docker Compose installed
- PostgreSQL database running (can be in Docker or external)
- Python 3.9+ (for local development)

## Docker Compose Setup

Create a `docker-compose.yml` file in your project root:

```yaml
version: '3.8'

services:
  redis:
    image: redis:7-alpine
    container_name: ets_redis
    ports:
      - "6379:6379"
    command: redis-server --appendonly yes
    volumes:
      - redis_data:/data
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 3s
      retries: 5

  celery-beat:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: ets_celery_beat
    command: celery -A q4s_connect.celery_app:app beat -l info --scheduler django_celery_beat.schedulers:DatabaseScheduler
    volumes:
      - .:/app
    depends_on:
      - redis
      - postgres
    environment:
      - CELERY_BROKER_URL=redis://redis:6379/0
      - CELERY_RESULT_BACKEND=redis://redis:6379/0
      - DJANGO_SETTINGS_MODULE=q4s_connect.settings
    restart: unless-stopped

  celery-worker-scheduler:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: ets_celery_worker_scheduler
    command: celery -A q4s_connect.celery_app:app worker -l info -Q opc_scheduler -n scheduler@%%h -c 1
    volumes:
      - .:/app
    depends_on:
      - redis
      - postgres
    environment:
      - CELERY_BROKER_URL=redis://redis:6379/0
      - CELERY_RESULT_BACKEND=redis://redis:6379/0
      - DJANGO_SETTINGS_MODULE=q4s_connect.settings
    restart: unless-stopped

  celery-worker-polling:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: ets_celery_worker_polling
    command: celery -A q4s_connect.celery_app:app worker -l info -Q opc_polling -n polling@%%h -c 8
    volumes:
      - .:/app
    depends_on:
      - redis
      - postgres
    environment:
      - CELERY_BROKER_URL=redis://redis:6379/0
      - CELERY_RESULT_BACKEND=redis://redis:6379/0
      - DJANGO_SETTINGS_MODULE=q4s_connect.settings
    restart: unless-stopped

  celery-worker-default:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: ets_celery_worker_default
    command: celery -A q4s_connect.celery_app:app worker -l info -Q default -n default@%%h -c 2
    volumes:
      - .:/app
    depends_on:
      - redis
      - postgres
    environment:
      - CELERY_BROKER_URL=redis://redis:6379/0
      - CELERY_RESULT_BACKEND=redis://redis:6379/0
      - DJANGO_SETTINGS_MODULE=q4s_connect.settings
    restart: unless-stopped

  postgres:
    image: postgres:15-alpine
    container_name: ets_postgres
    ports:
      - "5432:5432"
    environment:
      - POSTGRES_DB=mydb
      - POSTGRES_USER=admin
      - POSTGRES_PASSWORD=admin123
    volumes:
      - postgres_data:/var/lib/postgresql/data
    restart: unless-stopped

volumes:
  redis_data:
  postgres_data:
```

### Dockerfile

Create a `Dockerfile` in your project root:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Collect static files (optional)
RUN python manage.py collectstatic --noinput

# Run the application
CMD ["gunicorn", "q4s_connect.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "4"]
```

## Configuration Settings

### Django Settings (ETS/settings.py)

Key Celery configuration options in `settings.py`:

```python
# Broker and Result Backend
CELERY_BROKER_URL = "redis://localhost:6379/0"
CELERY_RESULT_BACKEND = "redis://localhost:6379/0"

# Serialization
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"

# Timezone
CELERY_TIMEZONE = TIME_ZONE  # Should match Django TIME_ZONE

# Performance Optimization
CELERY_TASK_IGNORE_RESULT = True  # Disable result storage (use DB as source of truth)
CELERY_WORKER_CONCURRENCY = 4  # Default worker concurrency (can be overridden per worker)

# Queue Configuration
CELERY_TASK_DEFAULT_QUEUE = "default"
CELERY_TASK_DEFAULT_EXCHANGE = "default"
CELERY_TASK_DEFAULT_ROUTING_KEY = "default"

CELERY_TASK_QUEUES = {
    "default": {
        "exchange": "default",
        "binding_key": "default",
    },
    "opc_scheduler": {
        "exchange": "opc_scheduler",
        "binding_key": "opc_scheduler",
    },
    "opc_polling": {
        "exchange": "opc_polling",
        "binding_key": "opc_polling",
    },
}

# Task Routing
CELERY_TASK_ROUTES = {
    "opc.opc_polling_tasks.poll_due_opc_connections": {
        "queue": "opc_scheduler",
        "routing_key": "opc_scheduler",
    },
    "opc.opc_polling_tasks.poll_opc_connection": {
        "queue": "opc_polling",
        "routing_key": "opc_polling",
    },
}

# Celery Beat Schedule
CELERY_BEAT_SCHEDULE = {
    "poll-due-opc-connections": {
        "task": "opc.opc_polling_tasks.poll_due_opc_connections",
        "schedule": 60.0,  # every 60 seconds
    },
}

# Broker Resiliency
CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP = True
CELERY_BROKER_POOL_LIMIT = 10
```

### Configurable Settings

You can adjust these settings based on your deployment requirements:

#### 1. **CELERY_WORKER_CONCURRENCY**
- **Purpose**: Number of concurrent processes per worker
- **Default**: 4
- **Recommendation**: 
  - For opc_polling workers: 8-16 (CPU-bound tasks)
  - For opc_scheduler workers: 1 (lightweight scheduling)
  - For default workers: 2-4 (general tasks)
- **How to change**: Set in `settings.py` or override via environment variable

#### 2. **CELERY_BEAT_SCHEDULE**
- **Purpose**: Frequency of polling scheduler
- **Default**: 60 seconds
- **Recommendation**: 
  - 60s is suitable for 10-minute polling rates
  - Reduce to 30s for faster polling rates (e.g., 1-5 minutes)
  - Increase to 120s for slower polling rates (e.g., 30+ minutes)
- **How to change**: Modify the `schedule` value in `CELERY_BEAT_SCHEDULE`

#### 3. **CELERY_BROKER_URL**
- **Purpose**: Redis connection string
- **Default**: `redis://localhost:6379/0`
- **Recommendation**: 
  - Use separate Redis databases for broker and results in production
  - Example: `redis://localhost:6379/0` for broker, `redis://localhost:6379/1` for results
- **How to change**: Set environment variable or update in `settings.py`

#### 4. **CELERY_TASK_IGNORE_RESULT**
- **Purpose**: Disable storing task results in Redis
- **Default**: `True`
- **Recommendation**: Keep `True` for high-load scenarios to reduce Redis memory usage
- **How to change**: Set to `False` if you need task results for debugging

#### 5. **Worker Queue Concurrency**
- **Purpose**: Number of worker processes per queue
- **Default**: 
  - opc_scheduler: 1
  - opc_polling: 8
  - default: 2
- **Recommendation**: 
  - Scale opc_polling workers based on connection count
  - For 700 connections: 4-8 workers with 8-16 concurrency each
- **How to change**: Modify the `-c` flag in docker-compose.yml

## Running the Services

### Start All Services

```bash
docker-compose up -d
```

### Start Specific Services

```bash
# Start only Redis and PostgreSQL
docker-compose up -d redis postgres

# Start Celery services
docker-compose up -d celery-beat celery-worker-scheduler celery-worker-polling celery-worker-default
```

### View Logs

```bash
# View all logs
docker-compose logs -f

# View specific service logs
docker-compose logs -f celery-worker-polling
docker-compose logs -f celery-beat
```

### Stop Services

```bash
docker-compose down
```

### Stop Services and Remove Volumes

```bash
docker-compose down -v
```

## Scaling for High Load

For the target scale of **700 OPC connections** with **~10 nodes each** (7000 total nodes) polling every **10 minutes**:

### Recommended Configuration

```yaml
# Scale opc_polling workers to handle the load
celery-worker-polling:
  # ... other config ...
  command: celery -A q4s_connect.celery_app:app worker -l info -Q opc_polling -n polling@%%h -c 16
  deploy:
    replicas: 4  # 4 workers x 16 concurrency = 64 concurrent polling tasks
```

### Load Calculation

- **Total connections**: 700
- **Polling interval**: 10 minutes (600 seconds)
- **Connections per second**: 700 / 600 ≈ 1.2 connections/second
- **Nodes per connection**: ~10
- **Total node reads per second**: 1.2 * 10 = 12 node reads/second
- **Required concurrency**: 64 workers can handle this easily with headroom

### Scaling Strategy

1. **Horizontal Scaling**: Add more worker containers
   ```bash
   docker-compose up -d --scale celery-worker-polling=4
   ```

2. **Vertical Scaling**: Increase concurrency per worker
   ```yaml
   command: celery -A q4s_connect.celery_app:app worker -l info -Q opc_polling -n polling@%%h -c 32
   ```

3. **Redis Scaling**: For very high loads, use Redis Cluster or separate broker/result backends

### Monitoring Resource Usage

```bash
# Check worker stats
docker exec ets_celery_worker_polling celery -A q4s_connect.celery_app:app inspect active

# Check queue length
docker exec ets_redis redis-cli llen opc_polling
```

## Monitoring and Maintenance

### Health Checks

The docker-compose.yml includes health checks for Redis. You can add similar checks for Celery:

```yaml
celery-worker-polling:
  # ... other config ...
  healthcheck:
    test: ["CMD", "celery", "-A", "q4s_connect.celery_app:app", "inspect", "ping"]
    interval: 30s
    timeout: 10s
    retries: 3
```

### Monitoring Tools

- **Flower**: Celery monitoring web UI
  ```bash
  pip install flower
  celery -A q4s_connect.celery_app:app flower
  ```
  Access at http://localhost:5555

- **Redis CLI**: Monitor Redis operations
  ```bash
  docker exec -it ets_redis redis-cli
  > INFO stats
  > CLIENT LIST
  ```

- **Django Admin**: Monitor OPC connection status and last polled times

### Maintenance Tasks

1. **Clear Stale Tasks**: If tasks get stuck
   ```bash
   docker exec ets_redis redis-cli FLUSHDB
   ```

2. **Restart Workers**: After code changes
   ```bash
   docker-compose restart celery-worker-polling
   ```

3. **Backup Redis**: Before major changes
   ```bash
   docker exec ets_redis redis-cli BGSAVE
   ```

## Troubleshooting

### Common Issues

#### 1. Workers Not Starting

**Symptoms**: Workers exit immediately or fail to connect to Redis

**Solutions**:
- Check Redis is running: `docker-compose logs redis`
- Verify broker URL: Check `CELERY_BROKER_URL` in settings
- Check network connectivity: Workers must be able to reach Redis

#### 2. Tasks Not Executing

**Symptoms**: Tasks are queued but not processed

**Solutions**:
- Check worker is consuming the correct queue: `celery inspect active_queues`
- Verify task routing: Check `CELERY_TASK_ROUTES` in settings
- Check for errors in worker logs: `docker-compose logs celery-worker-polling`

#### 3. High Memory Usage

**Symptoms**: Redis or workers consuming excessive memory

**Solutions**:
- Ensure `CELERY_TASK_IGNORE_RESULT = True` to avoid storing results
- Reduce worker concurrency: Lower `-c` flag
- Use separate Redis databases for broker and results
- Enable Redis maxmemory policy: `redis.conf` -> `maxmemory-policy allkeys-lru`

#### 4. Polling Spikes

**Symptoms**: All connections poll simultaneously causing load spikes

**Solutions**:
- Jitter is already implemented in `poll_due_opc_connections` (0-30s random countdown)
- Increase the jitter range in `opc_polling_tasks.py`
- Reduce Celery Beat schedule frequency if polling rate is slow

#### 5. Connection Timeouts

**Symptoms**: OPC connections failing with timeout errors

**Solutions**:
- Increase `timeout_seconds` in OPCConnection model
- Check network connectivity to OPC servers
- Verify OPC server is not overloaded
- Add retry logic in `opcua_client.py`

### Debug Mode

Enable verbose logging for debugging:

```yaml
celery-worker-polling:
  command: celery -A q4s_connect.celery_app:app worker -l debug -Q opc_polling -n polling@%%h -c 8
```

## Production Considerations

### Security

1. **Redis Authentication**: Enable Redis password
   ```yaml
   redis:
     command: redis-server --requirepass yourpassword --appendonly yes
   ```
   Update `CELERY_BROKER_URL`: `redis://:yourpassword@redis:6379/0`

2. **Network Isolation**: Use Docker networks to isolate services
   ```yaml
   networks:
     backend:
       driver: bridge
   ```

3. **Environment Variables**: Store sensitive data in environment variables or secrets manager

### Persistence

1. **Redis Persistence**: AOF (Append Only File) is enabled in the docker-compose.yml
2. **PostgreSQL Persistence**: Volume mount is configured
3. **Backups**: Regular backups of PostgreSQL and Redis AOF file

### High Availability

1. **Redis Sentinel**: For Redis high availability
2. **Multiple Workers**: Deploy workers across multiple hosts
3. **Load Balancer**: Use nginx or HAProxy for Django app

## Summary

This deployment provides:
- **Scalable architecture** with dedicated queues for different task types
- **High-load support** for 700+ OPC connections with 7000+ nodes
- **Resilient configuration** with connection retries and health checks
- **Monitoring capabilities** via Flower and Redis CLI
- **Production-ready** with persistence, security, and HA options

For questions or issues, refer to the Celery documentation: https://docs.celeryproject.org/
