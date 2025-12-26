# Monitoring & Logging Guide

This guide covers monitoring, logging, and observability best practices for SPARING API in production.

---

## Table of Contents

1. [Logging Strategy](#logging-strategy)
2. [Metrics & Monitoring](#metrics--monitoring)
3. [Alerting](#alerting)
4. [Distributed Tracing](#distributed-tracing)
5. [Dashboard Examples](#dashboard-examples)
6. [Troubleshooting Guide](#troubleshooting-guide)

---

## Logging Strategy

### Current Logging Implementation

The API uses structured JSON logging with request IDs for correlation.

**Log Format:**
```json
{
  "timestamp": "2024-01-01T12:00:00.000Z",
  "level": "INFO",
  "logger": "app.api.routers.ingest",
  "message": "Data ingested successfully",
  "request_id": "abc123-def456-ghi789",
  "user_id": 42,
  "site_uid": "aqmsFOEmmEPISI01",
  "extra": {}
}
```

### Log Levels

Configure via `LOG_LEVEL` environment variable:

- **debug**: Detailed information for debugging (development only)
- **info**: General informational messages (default for staging)
- **warning**: Warning messages (recommended for production)
- **error**: Error messages that need attention
- **critical**: Critical errors requiring immediate action

**Production Recommendation**: Use `warning` or `error` level to reduce noise.

### Log Sources

1. **Application Logs**
   - Location: stdout (containerized) or `/var/log/sparing/app.log`
   - Contains: API requests, errors, business logic events

2. **Access Logs** (via Gunicorn)
   - Location: stdout or `/var/log/sparing/access.log`
   - Contains: HTTP requests, response codes, latency

3. **Database Logs** (MySQL)
   - Location: `/var/log/mysql/error.log`
   - Contains: Slow queries, connection errors

4. **Nginx Logs** (if using reverse proxy)
   - Access: `/var/log/nginx/sparing-api-access.log`
   - Error: `/var/log/nginx/sparing-api-error.log`

### Centralized Logging

#### Option 1: ELK Stack (Elasticsearch, Logstash, Kibana)

**docker-compose.logging.yml:**
```yaml
version: '3.8'

services:
  elasticsearch:
    image: docker.elastic.co/elasticsearch/elasticsearch:8.11.0
    environment:
      - discovery.type=single-node
      - "ES_JAVA_OPTS=-Xms512m -Xmx512m"
    ports:
      - "9200:9200"
    volumes:
      - es_data:/usr/share/elasticsearch/data

  kibana:
    image: docker.elastic.co/kibana/kibana:8.11.0
    ports:
      - "5601:5601"
    depends_on:
      - elasticsearch

  filebeat:
    image: docker.elastic.co/beats/filebeat:8.11.0
    volumes:
      - ./filebeat.yml:/usr/share/filebeat/filebeat.yml
      - /var/lib/docker/containers:/var/lib/docker/containers:ro
      - /var/run/docker.sock:/var/run/docker.sock:ro
    depends_on:
      - elasticsearch

volumes:
  es_data:
```

**filebeat.yml:**
```yaml
filebeat.inputs:
  - type: container
    paths:
      - '/var/lib/docker/containers/*/*.log'
    processors:
      - add_docker_metadata: ~
      - decode_json_fields:
          fields: ["message"]
          target: "json"

output.elasticsearch:
  hosts: ["elasticsearch:9200"]
  index: "sparing-api-%{+yyyy.MM.dd}"

setup.kibana:
  host: "kibana:5601"
```

#### Option 2: Loki + Grafana

**docker-compose.loki.yml:**
```yaml
version: '3.8'

services:
  loki:
    image: grafana/loki:latest
    ports:
      - "3100:3100"
    volumes:
      - ./loki-config.yml:/etc/loki/local-config.yaml
      - loki_data:/loki

  promtail:
    image: grafana/promtail:latest
    volumes:
      - ./promtail-config.yml:/etc/promtail/config.yml
      - /var/log:/var/log
      - /var/lib/docker/containers:/var/lib/docker/containers:ro

  grafana:
    image: grafana/grafana:latest
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
    volumes:
      - grafana_data:/var/lib/grafana

volumes:
  loki_data:
  grafana_data:
```

#### Option 3: Cloud Services

- **AWS CloudWatch**: Use awslogs driver
- **Google Cloud Logging**: Use gcplogs driver
- **Azure Monitor**: Use Azure Log Analytics
- **Datadog**: Use Datadog agent

**Example (CloudWatch):**
```yaml
services:
  api:
    logging:
      driver: awslogs
      options:
        awslogs-region: us-east-1
        awslogs-group: sparing-api
        awslogs-stream: api
```

### Log Retention

**Recommended Retention Periods:**
- **Access Logs**: 30 days
- **Error Logs**: 90 days
- **Audit Logs**: 1+ year (compliance dependent)
- **Debug Logs**: 7 days (only in non-production)

**Implement Log Rotation:**
```bash
# /etc/logrotate.d/sparing-api
/var/log/sparing/*.log {
    daily
    rotate 30
    compress
    delaycompress
    notifempty
    create 0640 www-data www-data
    sharedscripts
    postrotate
        systemctl reload sparing-api
    endscript
}
```

---

## Metrics & Monitoring

### Built-in Prometheus Metrics

The API exposes Prometheus metrics at `/metrics`:

**Available Metrics:**
- `http_requests_total` - Total HTTP requests (by method, path, status)
- `http_request_duration_seconds` - Request latency histogram
- `http_requests_in_progress` - Current active requests
- `process_cpu_seconds_total` - CPU usage
- `process_resident_memory_bytes` - Memory usage
- `db_connections_active` - Active database connections

### Prometheus Setup

**prometheus.yml:**
```yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'sparing-api'
    static_configs:
      - targets: ['localhost:8000']
    metrics_path: /metrics

  - job_name: 'mysql'
    static_configs:
      - targets: ['localhost:9104']  # MySQL exporter

  - job_name: 'nginx'
    static_configs:
      - targets: ['localhost:9113']  # Nginx exporter

  - job_name: 'node'
    static_configs:
      - targets: ['localhost:9100']  # Node exporter
```

**docker-compose.monitoring.yml:**
```yaml
version: '3.8'

services:
  prometheus:
    image: prom/prometheus:latest
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus_data:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.retention.time=30d'

  grafana:
    image: grafana/grafana:latest
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
    volumes:
      - grafana_data:/var/lib/grafana
      - ./grafana-dashboards:/etc/grafana/provisioning/dashboards
      - ./grafana-datasources:/etc/grafana/provisioning/datasources

  mysql-exporter:
    image: prom/mysqld-exporter:latest
    environment:
      - DATA_SOURCE_NAME=exporter:password@(mysql:3306)/
    ports:
      - "9104:9104"

  node-exporter:
    image: prom/node-exporter:latest
    ports:
      - "9100:9100"
    volumes:
      - /proc:/host/proc:ro
      - /sys:/host/sys:ro
    command:
      - '--path.procfs=/host/proc'
      - '--path.sysfs=/host/sys'

volumes:
  prometheus_data:
  grafana_data:
```

### Key Metrics to Monitor

#### Application Metrics

1. **Request Rate**
   - Query: `rate(http_requests_total[5m])`
   - Alert if: sudden spike or drop

2. **Error Rate**
   - Query: `rate(http_requests_total{status=~"5.."}[5m])`
   - Alert if: > 1% of requests

3. **Response Time (p95, p99)**
   - Query: `histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))`
   - Alert if: > 1 second

4. **Active Requests**
   - Query: `http_requests_in_progress`
   - Alert if: sustained high load

#### Infrastructure Metrics

1. **CPU Usage**
   - Query: `rate(process_cpu_seconds_total[5m]) * 100`
   - Alert if: > 80% sustained

2. **Memory Usage**
   - Query: `process_resident_memory_bytes / 1024 / 1024`
   - Alert if: > 80% of available RAM

3. **Database Connections**
   - Query: `db_connections_active`
   - Alert if: near pool limit

4. **Disk Usage**
   - Query: `(node_filesystem_size_bytes - node_filesystem_free_bytes) / node_filesystem_size_bytes * 100`
   - Alert if: > 85%

#### Business Metrics

1. **Data Ingest Rate**
   - Query: `rate(http_requests_total{path="/ingest/state"}[5m])`

2. **Failed Ingestions**
   - Query: `rate(http_requests_total{path="/ingest/state",status="400"}[5m])`

3. **Active Sites**
   - Custom metric or database query

4. **Average Readings per Site**
   - Custom metric or database query

### Custom Application Metrics

Add custom metrics in your code:

```python
from prometheus_client import Counter, Histogram, Gauge

# Counter example
ingest_counter = Counter(
    'sensor_data_ingested_total',
    'Total sensor data records ingested',
    ['site_uid', 'status']
)

# Histogram example
ingest_duration = Histogram(
    'sensor_data_ingest_duration_seconds',
    'Time spent processing sensor data'
)

# Gauge example
active_sites = Gauge(
    'active_sites_total',
    'Number of active sites'
)

# Usage
@ingest_duration.time()
async def ingest_data(site_uid: str, data: dict):
    # ... processing logic ...
    ingest_counter.labels(site_uid=site_uid, status='success').inc()
```

---

## Alerting

### Alertmanager Configuration

**alertmanager.yml:**
```yaml
global:
  resolve_timeout: 5m
  smtp_smarthost: 'smtp.gmail.com:587'
  smtp_from: 'alerts@yourdomain.com'
  smtp_auth_username: 'alerts@yourdomain.com'
  smtp_auth_password: 'your-app-password'

route:
  group_by: ['alertname', 'cluster', 'service']
  group_wait: 10s
  group_interval: 10s
  repeat_interval: 12h
  receiver: 'team-email'
  routes:
    - match:
        severity: critical
      receiver: 'pagerduty'
    - match:
        severity: warning
      receiver: 'slack'

receivers:
  - name: 'team-email'
    email_configs:
      - to: 'team@yourdomain.com'
        headers:
          Subject: '[SPARING API] {{ .GroupLabels.alertname }}'

  - name: 'slack'
    slack_configs:
      - api_url: 'https://hooks.slack.com/services/YOUR/WEBHOOK/URL'
        channel: '#alerts'
        title: '{{ .GroupLabels.alertname }}'
        text: '{{ range .Alerts }}{{ .Annotations.description }}{{ end }}'

  - name: 'pagerduty'
    pagerduty_configs:
      - service_key: 'your-pagerduty-key'
```

### Alert Rules

**alert-rules.yml:**
```yaml
groups:
  - name: sparing_api_alerts
    interval: 30s
    rules:
      # High error rate
      - alert: HighErrorRate
        expr: rate(http_requests_total{status=~"5.."}[5m]) > 0.05
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "High error rate detected"
          description: "Error rate is {{ $value | humanizePercentage }} over the last 5 minutes"

      # API down
      - alert: APIDown
        expr: up{job="sparing-api"} == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "API is down"
          description: "SPARING API has been down for more than 1 minute"

      # High response time
      - alert: HighResponseTime
        expr: histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m])) > 1
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "High response time"
          description: "95th percentile response time is {{ $value }}s"

      # Database connection issues
      - alert: DatabaseConnectionHigh
        expr: db_connections_active > 80
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High database connections"
          description: "Active DB connections: {{ $value }}"

      # Disk space
      - alert: DiskSpaceLow
        expr: (node_filesystem_avail_bytes / node_filesystem_size_bytes) * 100 < 15
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Low disk space"
          description: "Disk space is {{ $value | humanizePercentage }} available"

      # Memory usage
      - alert: HighMemoryUsage
        expr: (process_resident_memory_bytes / 1024 / 1024) > 1024
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "High memory usage"
          description: "Memory usage is {{ $value }}MB"

      # Failed ingestions
      - alert: HighIngestFailureRate
        expr: rate(http_requests_total{path="/ingest/state",status="400"}[5m]) > 0.1
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High ingest failure rate"
          description: "Ingest failure rate is {{ $value | humanizePercentage }}"
```

### Alert Channels

1. **Email**: For non-critical alerts
2. **Slack/Discord**: For team notifications
3. **PagerDuty/OpsGenie**: For critical alerts requiring immediate action
4. **SMS**: For critical production outages

---

## Distributed Tracing

### OpenTelemetry Integration

For microservices or complex request flows:

```python
from opentelemetry import trace
from opentelemetry.exporter.jaeger.thrift import JaegerExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

# Configure tracer
jaeger_exporter = JaegerExporter(
    agent_host_name="localhost",
    agent_port=6831,
)

trace.set_tracer_provider(TracerProvider())
trace.get_tracer_provider().add_span_processor(
    BatchSpanProcessor(jaeger_exporter)
)

# Instrument FastAPI
FastAPIInstrumentor.instrument_app(app)
```

**Jaeger Setup (docker-compose):**
```yaml
services:
  jaeger:
    image: jaegertracing/all-in-one:latest
    ports:
      - "5775:5775/udp"
      - "6831:6831/udp"
      - "6832:6832/udp"
      - "5778:5778"
      - "16686:16686"
      - "14268:14268"
      - "9411:9411"
```

Access Jaeger UI at: http://localhost:16686

---

## Dashboard Examples

### Grafana Dashboard JSON

Save as `grafana-dashboards/sparing-api.json`:

```json
{
  "dashboard": {
    "title": "SPARING API Overview",
    "panels": [
      {
        "title": "Request Rate",
        "targets": [
          {
            "expr": "rate(http_requests_total[5m])"
          }
        ]
      },
      {
        "title": "Error Rate",
        "targets": [
          {
            "expr": "rate(http_requests_total{status=~\"5..\"}[5m])"
          }
        ]
      },
      {
        "title": "Response Time (p95)",
        "targets": [
          {
            "expr": "histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))"
          }
        ]
      },
      {
        "title": "Active Requests",
        "targets": [
          {
            "expr": "http_requests_in_progress"
          }
        ]
      }
    ]
  }
}
```

### Key Dashboard Panels

1. **Overview Panel**
   - Total requests/sec
   - Error rate %
   - Average response time
   - Active connections

2. **Performance Panel**
   - Response time percentiles (p50, p95, p99)
   - Request duration heatmap
   - Throughput graph

3. **Errors Panel**
   - Error rate by endpoint
   - 4xx vs 5xx errors
   - Error logs (recent)

4. **Infrastructure Panel**
   - CPU usage
   - Memory usage
   - Disk I/O
   - Network I/O

5. **Business Metrics Panel**
   - Data ingestion rate
   - Active sites
   - Failed ingestions
   - Top sites by activity

---

## Troubleshooting Guide

### Common Issues & Solutions

#### 1. High Response Time

**Investigate:**
```promql
# Slow endpoints
topk(5, sum by (path) (rate(http_request_duration_seconds_sum[5m])))

# Database query time
mysql_global_status_slow_queries
```

**Solutions:**
- Add database indexes
- Optimize queries
- Implement caching
- Scale horizontally

#### 2. Memory Leaks

**Investigate:**
```bash
# Monitor memory over time
docker stats sparing_api

# Python memory profiling
pip install memory_profiler
python -m memory_profiler app/main.py
```

**Solutions:**
- Review database connection handling
- Check for circular references
- Implement connection pooling limits

#### 3. Database Connection Pool Exhausted

**Investigate:**
```sql
-- Show current connections
SHOW PROCESSLIST;

-- Show max connections
SHOW VARIABLES LIKE 'max_connections';
```

**Solutions:**
- Increase pool size in DB_URL
- Fix connection leaks
- Implement connection timeout
- Scale database

#### 4. High CPU Usage

**Investigate:**
```bash
# Profile Python application
pip install py-spy
py-spy top --pid <PID>
```

**Solutions:**
- Optimize hot code paths
- Add caching
- Reduce worker count
- Use async operations

### Debug Logging

Enable debug logging temporarily:

```bash
# Update environment
LOG_LEVEL=debug

# Restart service
docker compose restart api

# View logs
docker compose logs -f api | grep "DEBUG"
```

**Remember to set back to `warning` after debugging!**

---

## Best Practices

1. **Structured Logging**: Always use JSON format with context
2. **Request IDs**: Track requests across services
3. **Metric Naming**: Use consistent naming conventions
4. **Alert Fatigue**: Set appropriate thresholds to avoid noise
5. **Dashboard Organization**: Group related metrics
6. **Log Sampling**: Sample high-volume logs in production
7. **Retention Policies**: Balance storage costs with compliance
8. **Regular Reviews**: Review dashboards and alerts monthly

---

## Checklist

Production monitoring setup:

- [ ] Centralized logging configured (ELK/Loki/CloudWatch)
- [ ] Prometheus metrics exported
- [ ] Grafana dashboards created
- [ ] Alert rules configured
- [ ] Alertmanager channels set up (email, Slack, PagerDuty)
- [ ] Log rotation configured
- [ ] Retention policies set
- [ ] Tracing enabled (optional)
- [ ] Team trained on dashboards
- [ ] Runbooks created for common alerts

---

**Last Updated**: 2024-01-01
**Version**: 1.0.0
