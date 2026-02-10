# MeetMind - AI Meeting Assistant Backend

A production-ready FastAPI backend that converts meeting audio into actionable insights using Whisper for transcription and LangGraph for AI-powered analysis.

## 🚀 Features

- **Audio Upload & Processing**: Support for multiple audio formats (WAV, MP3, WebM, M4A, OGG)
- **Smart Chunking**: Large files automatically split into chunks for processing (maintains full quality)
- **Speech-to-Text**: Powered by OpenAI Whisper API (cloud-based)
- **AI Analysis**: LangGraph workflow with 6 reasoning nodes:
  - Transcript cleaning
  - Topic detection
  - Summary generation
  - Decision extraction
  - Action item identification
  - Key discussion points
- **User Isolation**: Each user can only access their own meetings
- **RESTful API**: Clean, well-documented endpoints
- **SQLite Database**: Lightweight, zero-configuration storage

## 📋 Requirements

- Python 3.9+
- OpenAI API key (for both Whisper and LangGraph)

## 🛠️ Installation

### 1. Clone or navigate to the project

```bash
cd /home/coder/Work/My_Projects/MeetMind
```

### 2. Create virtual environment

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment

```bash
cp .env.example .env
```

Edit `.env` and add your OpenAI API key:
```
OPENAI_API_KEY=sk-your-actual-api-key-here
```

## 🚀 Running the Server

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at: `http://localhost:8000`

API Documentation: `http://localhost:8000/docs`

## 📡 API Endpoints

### 1. Upload Meeting Audio

**Endpoint:** `POST /meetings/upload`

**Request:**
- Content-Type: `multipart/form-data`
- Fields:
  - `user_id`: string (UUID or any unique identifier)
  - `audio_file`: file (audio file)

**Example using cURL:**
```bash
curl -X POST "http://localhost:8000/meetings/upload" \
  -F "user_id=user-123" \
  -F "audio_file=@/path/to/meeting.mp3"
```

**Response:**
```json
{
  "meeting_id": "550e8400-e29b-41d4-a716-446655440000",
  "user_id": "user-123",
  "status": "completed",
  "transcript": "Full meeting transcript...",
  "summary": "Meeting summary in 2-4 sentences...",
  "decisions": [
    "Decision 1",
    "Decision 2"
  ],
  "action_items": [
    "Action item 1",
    "Action item 2"
  ],
  "key_points": [
    "Key point 1",
    "Key point 2"
  ],
  "created_at": "2026-02-09T17:00:00"
}
```

---

### 2. Get All User Meetings

**Endpoint:** `GET /meetings/user/{user_id}`

**Example:**
```bash
curl "http://localhost:8000/meetings/user/user-123"
```

**Response:**
```json
{
  "user_id": "user-123",
  "meetings": [
    {
      "meeting_id": "550e8400-e29b-41d4-a716-446655440000",
      "audio_filename": "meeting.mp3",
      "summary": "Meeting summary...",
      "created_at": "2026-02-09T17:00:00"
    }
  ],
  "total": 1
}
```

---

### 3. Get Meeting Details

**Endpoint:** `GET /meetings/{meeting_id}?user_id={user_id}`

**Example:**
```bash
curl "http://localhost:8000/meetings/550e8400-e29b-41d4-a716-446655440000?user_id=user-123"
```

**Response:**
```json
{
  "meeting_id": "550e8400-e29b-41d4-a716-446655440000",
  "user_id": "user-123",
  "audio_filename": "meeting.mp3",
  "transcript": "Full transcript...",
  "summary": "Meeting summary...",
  "decisions": ["Decision 1"],
  "action_items": ["Action 1"],
  "key_points": ["Point 1"],
  "created_at": "2026-02-09T17:00:00"
}
```

## 🧪 Testing with Postman

### Setup

1. Open Postman
2. Create a new collection named "MeetMind"

### Test Upload Endpoint

1. Create new request: `POST http://localhost:8000/meetings/upload`
2. Go to "Body" tab
3. Select "form-data"
4. Add fields:
   - Key: `user_id`, Value: `test-user-1` (Text)
   - Key: `audio_file`, Value: [Select File] (File)
5. Click "Send"

### Test Get User Meetings

1. Create new request: `GET http://localhost:8000/meetings/user/test-user-1`
2. Click "Send"

### Test Get Meeting Details

1. Create new request: `GET http://localhost:8000/meetings/{meeting_id}`
2. Add query parameter:
   - Key: `user_id`, Value: `test-user-1`
3. Replace `{meeting_id}` with actual ID from upload response
4. Click "Send"

## 📁 Project Structure

```
MeetMind/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI app
│   ├── config.py               # Configuration
│   ├── database.py             # Database setup
│   ├── models/
│   │   └── meeting.py          # SQLAlchemy models
│   ├── schemas/
│   │   └── meeting.py          # Pydantic schemas
│   ├── services/
│   │   ├── audio_service.py    # Audio handling
│   │   ├── whisper_service.py  # Speech-to-text
│   │   ├── langgraph_service.py # AI analysis
│   │   └── meeting_service.py  # Orchestration
│   └── routers/
│       └── meetings.py         # API endpoints
├── uploads/                    # Temporary audio files
├── data/                       # SQLite database
├── requirements.txt
├── .env.example
└── README.md
```

## 🔧 Configuration

Edit `.env` file:

```env
# Database
DATABASE_URL=sqlite:///./data/meetmind.db

# Upload settings
UPLOAD_DIR=./uploads
MAX_UPLOAD_SIZE_MB=100

# OpenAI API key (required for both Whisper and LangGraph)
OPENAI_API_KEY=your_key_here

# App settings
APP_NAME=MeetMind
DEBUG=True
```

## 🎯 LangGraph Workflow

The AI analysis pipeline consists of 6 nodes:

```
START
  ↓
Clean Transcript (remove filler words, fix grammar)
  ↓
Detect Topics (identify main discussion topics)
  ↓
  ├─→ Generate Summary
  ├─→ Extract Decisions
  ├─→ Extract Action Items
  └─→ Extract Key Points
  ↓
END
```

## 🔒 Security Features

- **User Isolation**: Users can only access their own meetings
- **File Validation**: Strict audio file type checking
- **Size Limits**: Configurable upload size limits
- **Input Validation**: Pydantic schemas for all inputs
- **Error Handling**: Comprehensive error messages

## ⚠️ Troubleshooting

### OpenAI API Errors

**Whisper API:**
- Ensure `OPENAI_API_KEY` is set correctly in `.env`
- Check API key has sufficient credits
- **File Size Limit**: OpenAI Whisper API has a **25 MB limit per file**
  - **Automatic Chunking**: Large files are split into 10-minute chunks
  - Each chunk is transcribed separately and results are combined
  - **Maintains full audio quality** (no compression)
  - Works for meetings of any length
- Verify audio format is supported (wav, mp3, m4a, webm, ogg)

**LangGraph/GPT API:**
- Same API key is used for both Whisper and LangGraph
- Check for rate limiting or quota issues
- Verify account has sufficient credits

### Database Errors
- Delete `data/meetmind.db` and restart
- Check write permissions on `data/` directory

## 📊 Database Schema

### Users Table
- `id` (UUID, Primary Key)
- `created_at` (Timestamp)

### Meetings Table
- `id` (UUID, Primary Key)
- `user_id` (UUID, Foreign Key)
- `audio_filename` (String)
- `transcript` (Text)
- `summary` (Text)
- `decisions` (JSON)
- `action_items` (JSON)
- `key_points` (JSON)
- `created_at` (Timestamp)

## 🧪 Testing

### Run Tests

```bash
# Install test dependencies
pip install -r requirements-dev.txt

# Run all tests
pytest

# Run with verbose output
pytest -v

# Run with coverage
pytest --cov=app --cov-report=html
```

### Test Coverage

- **Unit Tests**: Models, services, business logic
- **Integration Tests**: API endpoints, workflows
- **Mocked Services**: External API calls (Whisper, LangGraph)

See [TESTING.md](file:///home/coder/Work/My_Projects/MeetMind/TESTING.md) for detailed testing guide.

## 🚀 Production Deployment

For production:

1. Use PostgreSQL instead of SQLite
2. Configure CORS properly
3. Add authentication/authorization
4. Use environment-specific configs
5. Set up logging and monitoring
6. Use a production ASGI server (Gunicorn + Uvicorn)

## 📝 License

MIT License - feel free to use for your hackathon or project!

## 🤝 Contributing

This is a hackathon project. Feel free to extend and improve!

## 📧 Support

For issues or questions, check the API docs at `/docs` endpoint.
