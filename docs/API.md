# VoiceTV Service - API Documentation

## Overview

The VoiceTV Service API provides comprehensive endpoints for searching streaming services, controlling TVs, and managing voice commands. All endpoints follow RESTful conventions and return JSON responses.

## Authentication

### API Key Authentication

All endpoints support optional API key authentication via:

1. **Authorization Header** (Recommended):
   ```
   Authorization: Bearer YOUR_API_KEY
   ```

2. **X-API-Key Header**:
   ```
   X-API-Key: YOUR_API_KEY
   ```

3. **Query Parameter**:
   ```
   GET /api/search/all?query=breaking+bad&api_key=YOUR_API_KEY
   ```

### Default Development Key

For development, use: `dev-key-12345`

### Production Setup

Set the `VOICETV_API_KEYS` environment variable with comma-separated keys:
```bash
export VOICETV_API_KEYS="key1,key2,key3"
```

## Base URL

```
http://localhost:5002
```

## Response Format

All successful responses return:
```json
{
  "status": "success",
  "data": { ... }
}
```

Error responses return:
```json
{
  "status": "error",
  "error": "Error type",
  "message": "Human-readable error message"
}
```

## Search Endpoints

### Search All Streaming Services

Search across all 9 streaming services simultaneously.

**Endpoint:**
```
GET /api/search/all
```

**Query Parameters:**
- `query` (required): Search term (1-256 characters)
- `content_type` (optional): `all` | `show` | `movie` | `sports` (default: `all`)
- `api_key` (optional): API key if not using headers

**Example:**
```bash
curl "http://localhost:5002/api/search/all?query=breaking+bad&content_type=show"
```

**Response (200 OK):**
```json
{
  "status": "success",
  "query": "breaking bad",
  "content_type": "show",
  "total": 1,
  "results": [
    {
      "id": "YouTubeTV_breaking_bad",
      "title": "Breaking Bad",
      "type": "show",
      "description": "A high school chemistry teacher...",
      "poster": "https://via.placeholder.com/150x225",
      "source_service": "YouTubeTV",
      "available_services": ["YouTubeTV"],
      "available_tvs": ["big_screen", "upper_left", ...],
      "imdb_rating": 9.5,
      "release_year": 2008
    }
  ],
  "search_time_ms": 105,
  "service_breakdown": {
    "YouTubeTV": 1,
    "Peacock": 0,
    "ESPN+": 0,
    ...
  },
  "timestamp": "2026-03-15T18:57:18.450448"
}
```

**Error Responses:**
- `400 Bad Request`: Missing query or invalid content_type
- `504 Gateway Timeout`: Search took too long
- `500 Internal Server Error`: Server error during search

---

### Search Specific Service

Search a specific streaming service.

**Endpoints:**
```
GET /api/search/youtube-tv
GET /api/search/peacock
GET /api/search/espn-plus
GET /api/search/amazon-prime
GET /api/search/hbo-max
GET /api/search/youtube
GET /api/search/fandango
GET /api/search/vudu
GET /api/search/justwatch
```

**Query Parameters:**
- `query` (required): Search term
- `content_type` (optional): `all` | `show` | `movie` | `sports`

**Example:**
```bash
curl "http://localhost:5002/api/search/peacock?query=office"
```

**Response (200 OK):**
```json
{
  "service": "Peacock",
  "query": "office",
  "results": [ ... ],
  "total": 5
}
```

---

## TV Control Endpoints

### Get Available TVs

**Endpoint:**
```
GET /api/tvs
```

**Response (200 OK):**
```json
{
  "tvs": [
    {
      "id": "big_screen",
      "name": "Big Screen",
      "size": "75\"",
      "type": "Samsung Smart TV",
      "position": "center",
      "status": "online"
    },
    {
      "id": "upper_left",
      "name": "Upper Left",
      "size": "32\"",
      "type": "Amazon Fire TV",
      "position": "upper_left",
      "status": "online"
    }
    ...
  ]
}
```

---

### Launch Content on TV

Launch a streaming app and play content.

**Endpoint:**
```
POST /api/tv/launch
```

**Request Body:**
```json
{
  "tv_id": "big_screen",
  "content_id": "breaking_bad",
  "service": "YouTubeTV"
}
```

**Response (200 OK):**
```json
{
  "status": "success",
  "message": "Launching YouTubeTV on Big Screen",
  "tv_id": "big_screen",
  "tv_name": "Big Screen",
  "content_id": "breaking_bad",
  "service": "YouTubeTV",
  "device_info": {
    "device_type": "Samsung Smart TV",
    "is_connected": true
  }
}
```

**Error Responses:**
- `400 Bad Request`: Missing required fields
- `404 Not Found`: TV not found
- `500 Internal Server Error`: Failed to launch content

---

### Control TV Power

Turn TV on or off.

**Endpoint:**
```
POST /api/tv/power
```

**Request Body:**
```json
{
  "tv_id": "big_screen",
  "action": "on"
}
```

**Parameters:**
- `action`: `on` | `off`

**Response (200 OK):**
```json
{
  "status": "success",
  "message": "Big Screen is now on",
  "tv_id": "big_screen",
  "tv_name": "Big Screen"
}
```

---

### Control TV Volume

Set or adjust TV volume.

**Endpoint:**
```
POST /api/tv/volume
```

**Request Body:**
```json
{
  "tv_id": "big_screen",
  "level": 50
}
```

**Parameters:**
- `level`: 0-100 (percentage)

**Response (200 OK):**
```json
{
  "status": "success",
  "message": "Volume set to 50% on Big Screen",
  "tv_id": "big_screen",
  "tv_name": "Big Screen",
  "volume": 50
}
```

---

### Change TV Input

Change the input source on a TV.

**Endpoint:**
```
POST /api/tv/input
```

**Request Body:**
```json
{
  "tv_id": "big_screen",
  "input_source": "HDMI 1"
}
```

**Response (200 OK):**
```json
{
  "status": "success",
  "message": "Input changed on Big Screen",
  "tv_id": "big_screen",
  "tv_name": "Big Screen",
  "input_source": "HDMI 1"
}
```

---

### Get TV Status

Get the current status of a TV or all TVs.

**Endpoints:**
```
GET /api/tv/status
GET /api/tv/status/{tv_id}
```

**Response (200 OK):**
```json
{
  "status": "success",
  "devices": {
    "big_screen": {
      "status": "success",
      "device_id": "big_screen",
      "device_name": "Big Screen",
      "device_type": "Samsung Smart TV",
      "power_state": "on",
      "volume": 50,
      "current_app": "YouTubeTV",
      "is_connected": true
    }
  },
  "total_devices": 1
}
```

---

## Voice Control Endpoints

### Transcribe Audio

Convert audio file to text using speech-to-text.

**Endpoint:**
```
POST /api/voice/transcribe
```

**Request (multipart/form-data):**
```
Content-Type: multipart/form-data

file: audio.wav
```

Or with base64-encoded audio:
```json
{
  "audio_data": "base64_encoded_audio_string"
}
```

**Response (200 OK):**
```json
{
  "status": "success",
  "transcript": "Put Breaking Bad on the big screen",
  "confidence": 0.95
}
```

---

### Parse Voice Command

Parse a voice transcript into a structured command.

**Endpoint:**
```
POST /api/voice/command
```

**Request Body:**
```json
{
  "transcript": "Put Breaking Bad on the big screen"
}
```

**Response (200 OK):**
```json
{
  "status": "success",
  "transcript": "Put Breaking Bad on the big screen",
  "command": {
    "status": "success",
    "intent": "play_content",
    "content_name": "breaking bad",
    "tv_id": "big_screen",
    "service": null
  }
}
```

**Supported Intents:**
- `play_content`: "Put X on Y TV"
- `search`: "Search for X"
- `control_volume`: "Set volume to X on Y TV"
- `control_power`: "Turn on/off X TV"

---

### Execute Voice Command

Execute a parsed voice command with full automation.

**Endpoint:**
```
POST /api/voice/execute
```

**Request Body:**
```json
{
  "transcript": "Put Breaking Bad on the big screen",
  "intent": "play_content",
  "content_name": "Breaking Bad",
  "tv_id": "big_screen"
}
```

Or with just transcript (auto-parses):
```json
{
  "transcript": "Put Breaking Bad on the big screen"
}
```

**Response (200 OK):**
```json
{
  "status": "success",
  "message": "Launching YouTubeTV on Big Screen",
  "voice_response": "Now playing Breaking Bad on Big Screen"
}
```

The `voice_response` is automatically spoken through Sonos speakers.

---

### Sonos Speaker Status

Get status of all Sonos speakers.

**Endpoint:**
```
GET /api/voice/sonos/status
```

**Response (200 OK):**
```json
{
  "status": "success",
  "devices": {
    "living_room_sonos": {
      "device_id": "living_room_sonos",
      "device_name": "Living Room Speaker",
      "is_connected": true,
      "is_playing": false,
      "volume": 50
    }
  },
  "total_devices": 1
}
```

---

### Make Sonos Speak

Have a Sonos speaker speak text (text-to-speech).

**Endpoint:**
```
POST /api/voice/sonos/speak
```

**Request Body:**
```json
{
  "device_id": "living_room_sonos",
  "text": "Hello, the movie is now playing"
}
```

**Response (200 OK):**
```json
{
  "status": "success",
  "message": "Sonos speaker speaking...",
  "device_id": "living_room_sonos",
  "text": "Hello, the movie is now playing"
}
```

---

## Health & System Endpoints

### Health Check

Check if the service is running.

**Endpoint:**
```
GET /health
```

**Response (200 OK):**
```json
{
  "status": "healthy",
  "service": "VoiceTV Service",
  "version": "0.2.0"
}
```

---

## Rate Limiting

API endpoints are rate-limited per client IP:

- **Health**: 100 requests/minute
- **Search**: 30 requests/minute, 300/hour
- **TV Control**: 10-20 requests/minute depending on action
- **Voice**: 15-30 requests/minute depending on operation

**Rate Limit Headers** (included in responses):
```
X-RateLimit-Limit: 30
X-RateLimit-Remaining: 29
X-RateLimit-Reset: 1647375600
```

**Rate Limit Exceeded (429):**
```json
{
  "status": "error",
  "error": "Too many requests",
  "message": "Rate limit exceeded. Please try again later."
}
```

---

## Error Codes

| Code | Meaning | Solution |
|------|---------|----------|
| 400 | Bad Request | Check request parameters and format |
| 401 | Unauthorized | Provide valid API key |
| 403 | Forbidden | Check permissions for the resource |
| 404 | Not Found | Resource (TV, content) doesn't exist |
| 429 | Too Many Requests | Wait before making another request |
| 500 | Internal Server Error | Check server logs, try again later |
| 504 | Gateway Timeout | Request took too long, try simpler query |

---

## Examples

### Search and Launch Content

```bash
# 1. Search for content
curl "http://localhost:5002/api/search/all?query=breaking+bad" \
  -H "X-API-Key: dev-key-12345"

# 2. Launch on TV (using result)
curl -X POST "http://localhost:5002/api/tv/launch" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: dev-key-12345" \
  -d '{
    "tv_id": "big_screen",
    "content_id": "breaking_bad",
    "service": "YouTubeTV"
  }'
```

### Voice Command Flow

```bash
# 1. Transcribe audio
curl -X POST "http://localhost:5002/api/voice/transcribe" \
  -H "X-API-Key: dev-key-12345" \
  -F "audio_file=@audio.wav"

# 2. Parse command
curl -X POST "http://localhost:5002/api/voice/command" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: dev-key-12345" \
  -d '{"transcript": "Put Breaking Bad on big screen"}'

# 3. Execute command
curl -X POST "http://localhost:5002/api/voice/execute" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: dev-key-12345" \
  -d '{
    "transcript": "Put Breaking Bad on big screen",
    "intent": "play_content",
    "content_name": "Breaking Bad",
    "tv_id": "big_screen"
  }'
```

---

## Changelog

### v0.2.0 (Production Ready)
- Added structured logging to all endpoints
- Implemented input validation and sanitization
- Added rate limiting (30-100 req/min depending on endpoint)
- Implemented API key authentication
- Added bounded caching with TTL
- Added comprehensive error handling
- Added production-ready CORS configuration

### v0.1.0 (Initial Release)
- Basic search across 9 streaming services
- TV control (Samsung SmartThings, Fire TV)
- Voice command processing
- Sonos speaker integration

---

## Support

For issues or questions:
1. Check the logs at `/home/orangepi/Apps/VoiceTVService/logs/`
2. Enable debug logging with `FLASK_ENV=development`
3. Check endpoint examples above
4. Verify API key is correct
