# MeetMind API Reference

## Table of Contents
- [Overview](#overview)
- [Base URL](#base-url)
- [Authentication](#authentication)
- [Endpoints](#endpoints)
- [Schemas](#schemas)
- [Error Handling](#error-handling)
- [Rate Limits](#rate-limits)

---

## Overview

The MeetMind API provides RESTful endpoints for uploading meeting audio files and retrieving AI-generated insights including transcripts, summaries, decisions, action items, and key discussion points.

### API Features
- **Automatic Transcription**: Powered by OpenAI Whisper
- **AI Analysis**: LangGraph-based intelligent extraction
- **User Isolation**: Complete data separation between users
- **Large File Support**: Automatic chunking for files >25MB
- **Format Support**: WAV, MP3, WebM, M4A, OGG

---

## Base URL

**Development:**
```
http://localhost:8000
```

**Production:**
```
https://your-domain.com
```

---

## Authentication

> [!WARNING]
> **Current Version**: No authentication required (development only)
> 
> **Production**: Implement JWT or OAuth2 authentication before deployment

### User Identification
All endpoints require a `user_id` parameter for user isolation. This should be a unique identifier for each user.

---

## Endpoints

### 1. Upload Meeting Audio

Upload and process a meeting audio file.

**Endpoint:** `POST /meetings/upload`

**Content-Type:** `multipart/form-data`

**Request Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `user_id` | string | Yes | Unique user identifier (UUID or any string) |
| `audio_file` | file | Yes | Audio file (wav, mp3, webm, m4a, ogg) |

**Request Example (cURL):**
```bash
curl -X POST "http://localhost:8000/meetings/upload" \
  -F "user_id=user-123" \
  -F "audio_file=@/path/to/meeting.mp3"
```

**Request Example (Python):**
```python
import requests

url = "http://localhost:8000/meetings/upload"
files = {"audio_file": open("meeting.mp3", "rb")}
data = {"user_id": "user-123"}

response = requests.post(url, files=files, data=data)
print(response.json())
```

**Request Example (JavaScript):**
```javascript
const formData = new FormData();
formData.append('user_id', 'user-123');
formData.append('audio_file', audioFile);

fetch('http://localhost:8000/meetings/upload', {
  method: 'POST',
  body: formData
})
  .then(response => response.json())
  .then(data => console.log(data));
```

**Response (200 OK):**
```json
{
  "meeting_id": "550e8400-e29b-41d4-a716-446655440000",
  "user_id": "user-123",
  "status": "completed",
  "transcript": "This is the full meeting transcript...",
  "summary": "The meeting discussed project timelines and resource allocation. Key decisions were made regarding the Q2 roadmap.",
  "decisions": [
    "Approved Q2 roadmap with focus on mobile features",
    "Allocated additional budget for infrastructure"
  ],
  "action_items": [
    "John to prepare detailed timeline by Friday",
    "Sarah to review resource requirements",
    "Team to schedule follow-up meeting next week"
  ],
  "key_points": [
    "Mobile app development is top priority",
    "Infrastructure scaling needed for growth",
    "Budget approved for two new hires"
  ],
  "created_at": "2026-02-10T12:30:00"
}
```

**Processing Time:**
- Small files (<25MB): 10-30 seconds
- Large files (>25MB): 1-3 minutes depending on duration

**Error Responses:**

| Status Code | Description | Example |
|-------------|-------------|---------|
| 400 | Invalid file type | `{"detail": "Invalid file type. Allowed: .wav, .mp3, .webm, .m4a, .ogg"}` |
| 413 | File too large | `{"detail": "File too large. Maximum size: 100MB"}` |
| 500 | Processing failed | `{"detail": "Failed to process meeting: <error>"}` |

---

### 2. Get User Meetings

Retrieve all meetings for a specific user.

**Endpoint:** `GET /meetings/user/{user_id}`

**Path Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `user_id` | string | Yes | User identifier |

**Request Example (cURL):**
```bash
curl "http://localhost:8000/meetings/user/user-123"
```

**Request Example (Python):**
```python
import requests

url = "http://localhost:8000/meetings/user/user-123"
response = requests.get(url)
print(response.json())
```

**Response (200 OK):**
```json
{
  "user_id": "user-123",
  "meetings": [
    {
      "meeting_id": "550e8400-e29b-41d4-a716-446655440000",
      "audio_filename": "team-standup.mp3",
      "summary": "Daily standup discussing sprint progress and blockers.",
      "created_at": "2026-02-10T12:30:00"
    },
    {
      "meeting_id": "660e8400-e29b-41d4-a716-446655440001",
      "audio_filename": "client-call.wav",
      "summary": "Client feedback session on new feature designs.",
      "created_at": "2026-02-09T15:00:00"
    }
  ],
  "total": 2
}
```

**Response Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `user_id` | string | User identifier |
| `meetings` | array | List of meeting summaries |
| `meetings[].meeting_id` | string | Unique meeting identifier |
| `meetings[].audio_filename` | string | Original audio filename |
| `meetings[].summary` | string | AI-generated summary |
| `meetings[].created_at` | datetime | Meeting creation timestamp |
| `total` | integer | Total number of meetings |

**Error Responses:**

| Status Code | Description |
|-------------|-------------|
| 200 | Success (returns empty array if no meetings) |

---

### 3. Get Meeting Details

Retrieve detailed information about a specific meeting.

**Endpoint:** `GET /meetings/{meeting_id}`

**Path Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `meeting_id` | string | Yes | Meeting identifier |

**Query Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `user_id` | string | Yes | User identifier (for authorization) |

**Request Example (cURL):**
```bash
curl "http://localhost:8000/meetings/550e8400-e29b-41d4-a716-446655440000?user_id=user-123"
```

**Request Example (Python):**
```python
import requests

url = "http://localhost:8000/meetings/550e8400-e29b-41d4-a716-446655440000"
params = {"user_id": "user-123"}
response = requests.get(url, params=params)
print(response.json())
```

**Response (200 OK):**
```json
{
  "meeting_id": "550e8400-e29b-41d4-a716-446655440000",
  "user_id": "user-123",
  "audio_filename": "team-standup.mp3",
  "transcript": "Full meeting transcript with all spoken words...",
  "summary": "Daily standup discussing sprint progress and blockers.",
  "decisions": [
    "Move feature X to next sprint",
    "Prioritize bug fixes this week"
  ],
  "action_items": [
    "Alice to fix critical bug by EOD",
    "Bob to update documentation",
    "Team to review PRs by tomorrow"
  ],
  "key_points": [
    "Sprint is on track for completion",
    "One critical bug needs immediate attention",
    "Documentation needs updating"
  ],
  "created_at": "2026-02-10T12:30:00"
}
```

**Response Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `meeting_id` | string | Unique meeting identifier |
| `user_id` | string | User identifier |
| `audio_filename` | string | Original audio filename |
| `transcript` | string | Full meeting transcript |
| `summary` | string | AI-generated summary (2-4 sentences) |
| `decisions` | array[string] | Decisions made during meeting |
| `action_items` | array[string] | Action items and tasks |
| `key_points` | array[string] | Key discussion points |
| `created_at` | datetime | Meeting creation timestamp |

**Error Responses:**

| Status Code | Description | Example |
|-------------|-------------|---------|
| 403 | Unauthorized access | `{"detail": "You do not have permission to access this meeting"}` |
| 404 | Meeting not found | `{"detail": "Meeting not found"}` |

---

### 4. Health Check

Check API health status.

**Endpoint:** `GET /health`

**Request Example:**
```bash
curl "http://localhost:8000/health"
```

**Response (200 OK):**
```json
{
  "status": "healthy",
  "service": "MeetMind"
}
```

---

### 5. Root Endpoint

Get API information.

**Endpoint:** `GET /`

**Request Example:**
```bash
curl "http://localhost:8000/"
```

**Response (200 OK):**
```json
{
  "message": "Welcome to MeetMind",
  "version": "1.0.0",
  "status": "running"
}
```

---

## Schemas

### MeetingUploadResponse

Response schema for meeting upload endpoint.

```typescript
interface MeetingUploadResponse {
  meeting_id: string;        // UUID
  user_id: string;           // User identifier
  status: string;            // "completed"
  transcript: string;        // Full transcript
  summary: string;           // 2-4 sentence summary
  decisions: string[];       // List of decisions
  action_items: string[];    // List of action items
  key_points: string[];      // List of key points
  created_at: string;        // ISO 8601 datetime
}
```

### MeetingDetailResponse

Response schema for meeting detail endpoint.

```typescript
interface MeetingDetailResponse {
  meeting_id: string;        // UUID
  user_id: string;           // User identifier
  audio_filename: string;    // Original filename
  transcript: string;        // Full transcript
  summary: string;           // 2-4 sentence summary
  decisions: string[];       // List of decisions
  action_items: string[];    // List of action items
  key_points: string[];      // List of key points
  created_at: string;        // ISO 8601 datetime
}
```

### MeetingListItem

Schema for individual meeting in list.

```typescript
interface MeetingListItem {
  meeting_id: string;        // UUID
  audio_filename: string;    // Original filename
  summary: string;           // 2-4 sentence summary
  created_at: string;        // ISO 8601 datetime
}
```

### UserMeetingsResponse

Response schema for user meetings list.

```typescript
interface UserMeetingsResponse {
  user_id: string;           // User identifier
  meetings: MeetingListItem[]; // List of meetings
  total: number;             // Total count
}
```

---

## Error Handling

### Error Response Format

All errors follow a consistent format:

```json
{
  "detail": "Error message describing what went wrong"
}
```

### HTTP Status Codes

| Code | Meaning | When It Occurs |
|------|---------|----------------|
| 200 | OK | Request successful |
| 400 | Bad Request | Invalid input (file type, validation) |
| 403 | Forbidden | User doesn't own resource |
| 404 | Not Found | Resource doesn't exist |
| 413 | Payload Too Large | File exceeds size limit |
| 500 | Internal Server Error | Server-side error |
| 503 | Service Unavailable | External API failure |

### Common Error Scenarios

#### Invalid File Type
```json
{
  "detail": "Invalid file type. Allowed: .wav, .mp3, .webm, .m4a, .ogg"
}
```

#### File Too Large
```json
{
  "detail": "File too large. Maximum size: 100MB"
}
```

#### Meeting Not Found
```json
{
  "detail": "Meeting not found"
}
```

#### Unauthorized Access
```json
{
  "detail": "You do not have permission to access this meeting"
}
```

#### OpenAI API Error
```json
{
  "detail": "Failed to transcribe audio: <OpenAI error message>"
}
```

---

## Rate Limits

> [!NOTE]
> **Current Version**: No rate limiting implemented
> 
> **Production Recommendation**: Implement rate limiting to prevent abuse

### Recommended Limits for Production

| Endpoint | Limit | Window |
|----------|-------|--------|
| `POST /meetings/upload` | 10 requests | per hour per user |
| `GET /meetings/user/{user_id}` | 100 requests | per hour per user |
| `GET /meetings/{meeting_id}` | 100 requests | per hour per user |

### OpenAI API Limits

The service is subject to OpenAI API rate limits:
- **Whisper API**: Varies by account tier
- **GPT API**: Varies by account tier

Monitor your OpenAI usage dashboard for current limits.

---

## Interactive Documentation

FastAPI provides automatic interactive API documentation:

### Swagger UI
```
http://localhost:8000/docs
```

Features:
- Interactive API testing
- Request/response examples
- Schema documentation
- Try-it-out functionality

### ReDoc
```
http://localhost:8000/redoc
```

Features:
- Clean, readable documentation
- Detailed schema information
- Code examples

---

## Best Practices

### 1. User ID Management
- Use UUIDs for user IDs
- Keep user IDs consistent across requests
- Store user ID mapping securely

### 2. File Upload
- Validate file format before upload
- Check file size client-side
- Use appropriate audio quality (16kHz mono is sufficient)
- Compress large files if possible

### 3. Error Handling
- Always check response status codes
- Implement retry logic for 5xx errors
- Handle timeout scenarios (large files may take time)

### 4. Performance
- Cache meeting lists when possible
- Paginate large result sets (future enhancement)
- Use appropriate timeouts for upload requests

### 5. Security
- Implement authentication in production
- Use HTTPS for all requests
- Validate user_id on client side
- Don't expose internal error details to clients

---

## Code Examples

### Complete Upload Workflow (Python)

```python
import requests
import time

def upload_and_process_meeting(audio_file_path, user_id):
    """Upload meeting and poll for results"""
    
    # Upload meeting
    url = "http://localhost:8000/meetings/upload"
    with open(audio_file_path, "rb") as f:
        files = {"audio_file": f}
        data = {"user_id": user_id}
        response = requests.post(url, files=files, data=data)
    
    if response.status_code != 200:
        raise Exception(f"Upload failed: {response.json()}")
    
    result = response.json()
    print(f"Meeting ID: {result['meeting_id']}")
    print(f"Summary: {result['summary']}")
    print(f"Action Items: {result['action_items']}")
    
    return result

# Usage
result = upload_and_process_meeting("meeting.mp3", "user-123")
```

### Retrieve All Meetings (JavaScript)

```javascript
async function getUserMeetings(userId) {
  const response = await fetch(
    `http://localhost:8000/meetings/user/${userId}`
  );
  
  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }
  
  const data = await response.json();
  console.log(`Found ${data.total} meetings`);
  
  data.meetings.forEach(meeting => {
    console.log(`- ${meeting.audio_filename}: ${meeting.summary}`);
  });
  
  return data;
}

// Usage
getUserMeetings('user-123');
```

### Get Meeting Details (Python)

```python
def get_meeting_details(meeting_id, user_id):
    """Retrieve detailed meeting information"""
    
    url = f"http://localhost:8000/meetings/{meeting_id}"
    params = {"user_id": user_id}
    response = requests.get(url, params=params)
    
    if response.status_code == 404:
        print("Meeting not found")
        return None
    elif response.status_code == 403:
        print("Access denied")
        return None
    
    meeting = response.json()
    
    print(f"Meeting: {meeting['audio_filename']}")
    print(f"\nTranscript:\n{meeting['transcript']}")
    print(f"\nSummary:\n{meeting['summary']}")
    print(f"\nDecisions:")
    for decision in meeting['decisions']:
        print(f"  - {decision}")
    print(f"\nAction Items:")
    for item in meeting['action_items']:
        print(f"  - {item}")
    
    return meeting

# Usage
get_meeting_details("550e8400-e29b-41d4-a716-446655440000", "user-123")
```

---

## Postman Collection

### Import Collection

Create a new Postman collection with these requests:

#### 1. Upload Meeting
- **Method**: POST
- **URL**: `{{base_url}}/meetings/upload`
- **Body**: form-data
  - `user_id`: `test-user-1` (text)
  - `audio_file`: (file)

#### 2. Get User Meetings
- **Method**: GET
- **URL**: `{{base_url}}/meetings/user/test-user-1`

#### 3. Get Meeting Details
- **Method**: GET
- **URL**: `{{base_url}}/meetings/{{meeting_id}}`
- **Params**: `user_id=test-user-1`

#### 4. Health Check
- **Method**: GET
- **URL**: `{{base_url}}/health`

### Environment Variables
- `base_url`: `http://localhost:8000`
- `meeting_id`: (set from upload response)

---

## Changelog

### Version 1.0.0 (Current)
- Initial release
- Audio upload and processing
- Whisper transcription with chunking
- LangGraph analysis pipeline
- User isolation
- RESTful API endpoints

### Planned Features
- Authentication and authorization
- WebSocket support for real-time updates
- Pagination for meeting lists
- Advanced search and filtering
- Export to PDF/DOCX
- Speaker diarization
- Multi-language support
