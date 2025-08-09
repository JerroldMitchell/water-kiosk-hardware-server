# Water Kiosk Hardware Server

Python Flask server that handles HTTP requests from water kiosk hardware for customer verification and water dispensing approval.

## Features

- Customer verification (phone number + PIN)
- Subscription status checking
- Water dispensing approval/denial
- Database operations (query, create, update)
- Scalable HTTP architecture for 600+ kiosks

## Architecture

```
Kiosk Hardware ──HTTP Request──> Flask Server ──HTTP API──> Appwrite Database
```

## Setup

1. Create virtual environment:
```bash
python3 -m venv kiosk-env
source kiosk-env/bin/activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Configure environment variables (optional):
```bash
export APPWRITE_PROJECT_ID="your-project-id"
export APPWRITE_DATABASE_ID="your-database-id"
export APPWRITE_API_KEY="your-api-key"
```

4. Run server:
```bash
python3 water_kiosk_hardware_server.py
```

## Endpoints

- `GET /` - Status page
- `POST /dispense-verification` - Main kiosk verification endpoint
- `POST /database/query` - Database query operations
- `POST /database/create` - Create database documents
- `POST /database/update` - Update database documents
- `POST /test-database` - Database connection test

## Verification Flow

1. Kiosk sends customer phone number + PIN + volume request
2. Server looks up customer in database
3. Verifies PIN matches
4. Checks registration status (`is_registered = true`)
5. Checks subscription status (`active = true`)
6. Returns approval/denial with reason

## Request/Response Format

**Request:**
```json
{
  "kiosk_id": "KIOSK001",
  "user_id": "+254700000000",
  "pin": "1234",
  "volume_ml": 500
}
```

**Response:**
```json
{
  "type": "dispense_response",
  "user_id": "+254700000000",
  "approved": false,
  "reason": "Subscription inactive",
  "timestamp": "2025-08-05T17:20:53Z",
  "kiosk_id": "KIOSK001"
}
```

## Production Deployment

Server runs on port 8080. Use nginx for external routing:

```nginx
location /kiosk/ {
    proxy_pass http://127.0.0.1:8080/;
    proxy_set_header Host $host;
    proxy_pass_request_headers on;
    proxy_pass_request_body on;
}
```

Kiosk hardware endpoint: `http://your-domain/kiosk/dispense-verification`
