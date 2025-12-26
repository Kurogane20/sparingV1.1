# SPARING API Documentation

## Overview

SPARING API is a production-grade FastAPI application for wastewater monitoring and environmental data collection. It provides endpoints for managing sites, devices, sensor data ingestion, and analytics.

**Base URL**: `http://localhost:8000` (development) or `https://your-domain.com` (production)

**API Documentation**: Available at `/docs` (Swagger UI) or `/redoc` (ReDoc)

---

## Authentication

The API uses JWT (JSON Web Token) authentication.

### Login

```http
POST /auth/login
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "yourpassword"
}
```

**Response:**
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "token_type": "bearer"
}
```

### Using Authentication

Include the access token in the `Authorization` header:

```http
Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGc...
```

### Refresh Token

```http
POST /auth/refresh
Content-Type: application/json

{
  "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGc..."
}
```

### Logout

```http
POST /auth/logout
Authorization: Bearer <access_token>
```

---

## User Roles

- **admin**: Full access to all resources
- **operator**: Can create/update sites and devices, ingest data
- **viewer**: Read-only access to assigned sites only

---

## Endpoints

### Health Checks

#### Liveness Probe
```http
GET /healthz
```

**Response:**
```json
{
  "ok": true,
  "status": "healthy",
  "service": "sparing-api"
}
```

#### Readiness Probe
```http
GET /readyz
```

**Response:**
```json
{
  "ok": true,
  "status": "ready",
  "database": "connected"
}
```

---

### Sites Management

#### List Sites
```http
GET /sites
Authorization: Bearer <token>
```

**Query Parameters:**
- `page` (int, default: 1)
- `per_page` (int, default: 50, max: 100)

**Response:**
```json
{
  "items": [
    {
      "id": 1,
      "uid": "aqmsFOEmmEPISI01",
      "name": "Site A",
      "company_name": "Company ABC",
      "lat": -6.2088,
      "lon": 106.8456,
      "is_active": true,
      "created_at": "2024-01-01T00:00:00Z",
      "updated_at": "2024-01-01T00:00:00Z"
    }
  ],
  "total": 1,
  "page": 1,
  "per_page": 50
}
```

#### Get Site by ID
```http
GET /sites/{site_uid}
Authorization: Bearer <token>
```

#### Create Site (admin/operator only)
```http
POST /sites
Authorization: Bearer <token>
Content-Type: application/json

{
  "uid": "aqmsFOEmmEPISI02",
  "name": "Site B",
  "company_name": "Company XYZ",
  "lat": -6.2088,
  "lon": 106.8456,
  "is_active": true
}
```

#### Update Site (admin/operator only)
```http
PATCH /sites/{site_uid}
Authorization: Bearer <token>
Content-Type: application/json

{
  "name": "Site B Updated",
  "is_active": false
}
```

#### Delete Site (admin only)
```http
DELETE /sites/{site_uid}
Authorization: Bearer <token>
```

---

### Devices Management

#### List Devices
```http
GET /devices?site_uid=aqmsFOEmmEPISI01
Authorization: Bearer <token>
```

**Query Parameters:**
- `site_uid` (required)
- `page` (int, default: 1)
- `per_page` (int, default: 50)

#### Create Device (admin/operator only)
```http
POST /devices
Authorization: Bearer <token>
Content-Type: application/json

{
  "site_uid": "aqmsFOEmmEPISI01",
  "name": "pH Sensor",
  "modbus_addr": 1,
  "model": "PHM-100",
  "serial_no": "SN123456",
  "is_active": true
}
```

#### Update Device (admin/operator only)
```http
PATCH /devices/{id}
Authorization: Bearer <token>
Content-Type: application/json

{
  "name": "pH Sensor Updated",
  "is_active": false
}
```

#### Delete Device (admin only)
```http
DELETE /devices/{id}
Authorization: Bearer <token>
```

**Response:**
```json
{
  "ok": true,
  "message": "Device deactivated"
}
```

**Note:** This is a soft delete operation. The device is not removed from the database, but its `is_active` field is set to `false`. This preserves data integrity for historical sensor data.

---

### Data Ingestion

#### Ingest Single Reading
```http
POST /ingest/state
Authorization: Bearer <token>
Content-Type: application/json
Idempotency-Key: unique-key-123 (optional)

{
  "site_uid": "aqmsFOEmmEPISI01",
  "device_id": 1,
  "ts": "2024-01-01T12:00:00+07:00",
  "ph": 7.2,
  "tss": 25.5,
  "debit": 150.0,
  "nh3n": 5.2,
  "cod": 80.0,
  "temp": 28.5,
  "rh": 65.0,
  "wind_speed_kmh": 5.2,
  "wind_deg": 180.0,
  "noise": 55.0,
  "co": 2.5,
  "so2": 0.05,
  "no2": 0.08,
  "o3": 0.06,
  "pm25": 35.0,
  "pm10": 50.0,
  "tvoc": 200.0,
  "voltage": 220.0,
  "current": 5.5,
  "payload": {
    "custom_field": "value"
  }
}
```

**Field Validations:**
- `ph`: 0-14
- `tss`: >= 0
- `debit`: >= 0
- `temp`: -40 to 80°C
- `rh`: 0-100%
- `wind_speed_kmh`: >= 0
- `noise`: >= 0
- `voltage`: 0-1000V
- `current`: 0-1000A

**Response:**
```json
{
  "ok": true,
  "id": 12345
}
```

#### Bulk Ingest
```http
POST /ingest/bulk
Authorization: Bearer <token>
Content-Type: application/json

{
  "bulk": [
    {
      "site_uid": "aqmsFOEmmEPISI01",
      "ts": "2024-01-01T12:00:00+07:00",
      "ph": 7.2,
      "voltage": 220.0
    },
    {
      "site_uid": "aqmsFOEmmEPISI01",
      "ts": "2024-01-01T12:05:00+07:00",
      "ph": 7.3,
      "voltage": 221.0
    }
  ]
}
```

**Note**: Maximum 1000 items per bulk request.

---

### Data Retrieval

#### Query Data
```http
GET /data?site_uid=aqmsFOEmmEPISI01&date_from=2024-01-01&date_to=2024-01-31&page=1&per_page=50&order=desc&fields=ph,tss,voltage
Authorization: Bearer <token>
```

**Query Parameters:**
- `site_uid` (required)
- `date_from` (ISO date, optional)
- `date_to` (ISO date, optional)
- `page` (int, default: 1)
- `per_page` (int, default: 50, max: 500)
- `order` (asc/desc, default: desc)
- `fields` (comma-separated list of fields to include)

**Available Fields:**
`ph`, `tss`, `debit`, `nh3n`, `cod`, `temp`, `rh`, `wind_speed_kmh`, `wind_deg`, `noise`, `co`, `so2`, `no2`, `o3`, `pm25`, `pm10`, `tvoc`, `voltage`, `current`

#### Get Latest Reading
```http
GET /data/last?site_uid=aqmsFOEmmEPISI01
Authorization: Bearer <token>
```

---

### Metrics & Statistics

#### Site Last Seen
```http
GET /sites/{uid}/stats/last-seen
Authorization: Bearer <token>
```

**Response:**
```json
{
  "site_uid": "aqmsFOEmmEPISI01",
  "last_seen_at": "2024-01-01T12:00:00Z",
  "minutes_ago": 5
}
```

#### Site Metrics
```http
GET /sites/{uid}/metrics
Authorization: Bearer <token>
```

**Query Parameters:**
- `date_from` (ISO date, optional)
- `date_to` (ISO date, optional)
- `fields` (comma-separated, default: ph,tss,debit)

**Response:**
```json
{
  "site_uid": "aqmsFOEmmEPISI01",
  "period": {
    "from": "2024-01-01T00:00:00Z",
    "to": "2024-01-31T23:59:59Z"
  },
  "metrics": {
    "ph": {
      "avg": 7.2,
      "min": 6.8,
      "max": 7.5,
      "count": 1440
    },
    "voltage": {
      "avg": 220.5,
      "min": 215.0,
      "max": 225.0,
      "count": 1440
    }
  }
}
```

---

### Admin Endpoints

#### Register User (admin only)
```http
POST /auth/register
Authorization: Bearer <admin_token>
Content-Type: application/json

{
  "name": "New User",
  "email": "newuser@example.com",
  "password": "SecurePass123!",
  "role": "operator"
}
```

#### List Users (admin only)
```http
GET /admin/users
Authorization: Bearer <admin_token>
```

**Response:**
```json
{
  "users": [
    {
      "id": 1,
      "name": "Admin User",
      "email": "admin@example.com",
      "role": "admin",
      "created_at": "2024-01-01T00:00:00Z"
    }
  ]
}
```

#### Update User (admin only)
```http
PATCH /admin/users/{user_id}
Authorization: Bearer <admin_token>
Content-Type: application/json

{
  "name": "Updated Name",
  "email": "newemail@example.com",
  "password": "NewPassword123!",
  "role": "operator"
}
```

**Note:** All fields are optional. Only include fields you want to update.

#### Delete User (admin only)
```http
DELETE /admin/users/{user_id}
Authorization: Bearer <admin_token>
```

**Response:**
```json
{
  "ok": true
}
```

#### Assign Viewer to Site (admin only)
```http
POST /admin/viewer-sites
Authorization: Bearer <admin_token>
Content-Type: application/json

{
  "user_id": 3,
  "site_uid": "aqmsFOEmmEPISI01"
}
```

#### Unassign Viewer from Site (admin only)
```http
DELETE /admin/viewer-sites
Authorization: Bearer <admin_token>
Content-Type: application/json

{
  "user_id": 3,
  "site_uid": "aqmsFOEmmEPISI01"
}
```

#### List Viewer-Site Assignments (admin only)
```http
GET /admin/viewer-sites
Authorization: Bearer <admin_token>
```

**Response:**
```json
{
  "viewer_sites": [
    {
      "user_id": 3,
      "site_id": 1
    }
  ]
}
```

#### List Viewers (admin only)
```http
GET /admin/viewers
Authorization: Bearer <admin_token>
```

**Response:**
```json
{
  "viewers": [
    {
      "id": 3,
      "email": "viewer@example.com"
    }
  ]
}
```

---

## Error Responses

All error responses follow this format:

```json
{
  "detail": "Error message here"
}
```

**Common HTTP Status Codes:**
- `200`: Success
- `201`: Created
- `400`: Bad Request (validation error)
- `401`: Unauthorized (missing/invalid token)
- `403`: Forbidden (insufficient permissions)
- `404`: Not Found
- `422`: Unprocessable Entity (validation error)
- `429`: Too Many Requests (rate limit exceeded)
- `500`: Internal Server Error
- `503`: Service Unavailable (health check failed)

---

## Rate Limiting

The `/ingest/*` endpoints are rate-limited to prevent abuse. Default: 120 requests per minute per IP.

If rate limit is exceeded:
```json
{
  "detail": "Rate limit exceeded"
}
```

---

## Idempotency

For critical data ingestion operations, use the `Idempotency-Key` header to ensure data is not duplicated:

```http
Idempotency-Key: unique-transaction-id-12345
```

If the same key is sent again, the API will return the original response without creating duplicate data.

---

## Timezone Handling

- All timestamps are stored in **UTC** in the database
- You can send timestamps with any timezone offset (e.g., `+07:00` for Jakarta)
- The API automatically converts them to UTC
- Timestamps in responses are always in UTC

**Example:**
```json
{
  "ts": "2024-01-01T12:00:00+07:00"  // Input (Jakarta time)
}
```

Stored as:
```json
{
  "ts": "2024-01-01T05:00:00Z"  // UTC
}
```

---

## Best Practices

1. **Use HTTPS** in production
2. **Store JWT tokens securely** (httpOnly cookies recommended)
3. **Refresh tokens** before they expire
4. **Use idempotency keys** for critical operations
5. **Implement retry logic** with exponential backoff
6. **Monitor rate limits** and adjust if needed
7. **Validate data** on client side before sending
8. **Use bulk ingest** for multiple readings to reduce API calls

---

## Examples

### Python Client Example

```python
import requests
import json
from datetime import datetime

BASE_URL = "http://localhost:8000"

# Login
login_response = requests.post(f"{BASE_URL}/auth/login", json={
    "email": "op@example.com",
    "password": "Op#12345"
})
token = login_response.json()["access_token"]

headers = {
    "Authorization": f"Bearer {token}",
    "Content-Type": "application/json"
}

# Ingest data
data = {
    "site_uid": "aqmsFOEmmEPISI01",
    "ts": datetime.now().isoformat(),
    "ph": 7.2,
    "voltage": 220.5,
    "temp": 28.0
}

response = requests.post(
    f"{BASE_URL}/ingest/state",
    headers=headers,
    json=data
)

print(response.json())
```

### JavaScript/Node.js Example

```javascript
const axios = require('axios');

const BASE_URL = 'http://localhost:8000';

async function ingestData() {
  // Login
  const loginRes = await axios.post(`${BASE_URL}/auth/login`, {
    email: 'op@example.com',
    password: 'Op#12345'
  });

  const token = loginRes.data.access_token;

  // Ingest data
  const data = {
    site_uid: 'aqmsFOEmmEPISI01',
    ts: new Date().toISOString(),
    ph: 7.2,
    voltage: 220.5,
    temp: 28.0
  };

  const response = await axios.post(
    `${BASE_URL}/ingest/state`,
    data,
    {
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      }
    }
  );

  console.log(response.data);
}

ingestData();
```

---

## Support

For issues, questions, or feature requests, please contact the development team or check the project repository.
