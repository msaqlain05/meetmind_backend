# MeetMind Testing Guide

## Overview

Comprehensive test suite for the MeetMind AI Meeting Assistant backend covering:
- **Unit Tests**: Models, services, and business logic
- **Integration Tests**: API endpoints and workflows
- **Mocked External Services**: OpenAI Whisper API and LangGraph LLM

## Test Structure

```
tests/
├── __init__.py
├── conftest.py              # Pytest configuration and fixtures
├── test_models.py           # Database model tests
├── test_audio_service.py    # Audio handling tests
├── test_langgraph_service.py # LangGraph workflow tests
└── test_api.py              # API endpoint integration tests
```

## Setup

### 1. Install Test Dependencies

```bash
pip install -r requirements-dev.txt
```

### 2. Set Environment Variables

```bash
export OPENAI_API_KEY="test-key-for-testing"
```

## Running Tests

### Run All Tests

```bash
pytest
```

### Run with Verbose Output

```bash
pytest -v
```

### Run Specific Test File

```bash
pytest tests/test_models.py
pytest tests/test_api.py
```

### Run Specific Test Class

```bash
pytest tests/test_models.py::TestUserModel
```

### Run Specific Test

```bash
pytest tests/test_api.py::TestMeetingEndpoints::test_upload_meeting_success
```

### Run with Coverage

```bash
pytest --cov=app --cov-report=html
```

## Test Categories

### 1. Model Tests (`test_models.py`)

Tests database models and relationships:
- ✅ User creation
- ✅ Meeting creation
- ✅ User-Meeting relationships
- ✅ Cascade deletion
- ✅ JSON field serialization

**Run:**
```bash
pytest tests/test_models.py -v
```

### 2. Audio Service Tests (`test_audio_service.py`)

Tests audio file handling:
- ✅ File validation (extensions, MIME types)
- ✅ File saving and retrieval
- ✅ Size limit enforcement
- ✅ File deletion and cleanup
- ✅ Error handling

**Run:**
```bash
pytest tests/test_audio_service.py -v
```

### 3. LangGraph Service Tests (`test_langgraph_service.py`)

Tests AI workflow with mocked LLM:
- ✅ Transcript cleaning
- ✅ Topic detection
- ✅ Summary generation
- ✅ Decision extraction
- ✅ Action item extraction
- ✅ Key points extraction
- ✅ Graph building
- ✅ Full workflow integration

**Run:**
```bash
pytest tests/test_langgraph_service.py -v
```

### 4. API Integration Tests (`test_api.py`)

Tests all API endpoints:
- ✅ Health checks
- ✅ Meeting upload (with mocked services)
- ✅ Get user meetings
- ✅ Get meeting details
- ✅ Authorization (user isolation)
- ✅ Validation errors
- ✅ Error handling

**Run:**
```bash
pytest tests/test_api.py -v
```

## Test Fixtures

### Available Fixtures (from `conftest.py`)

- **`test_db`**: Clean test database for each test
- **`client`**: FastAPI test client
- **`sample_user_id`**: Sample user ID ("test-user-123")
- **`sample_transcript`**: Sample meeting transcript

### Using Fixtures

```python
def test_example(client, sample_user_id):
    response = client.get(f"/meetings/user/{sample_user_id}")
    assert response.status_code == 200
```

## Mocking External Services

### Whisper API Mock

```python
with patch('app.services.whisper_service.OpenAI') as mock_openai:
    mock_client = Mock()
    mock_client.audio.transcriptions.create.return_value = Mock(text="Transcript")
    mock_openai.return_value = mock_client
    # Run test
```

### LangGraph LLM Mock

```python
with patch('app.services.langgraph_service.ChatOpenAI') as mock_chat:
    mock_llm = Mock()
    mock_llm.invoke.return_value = Mock(content="Response")
    mock_chat.return_value = mock_llm
    # Run test
```

## Test Coverage

Expected coverage:
- **Models**: 100%
- **Services**: 90%+
- **API Routes**: 95%+
- **Overall**: 90%+

## Common Test Patterns

### Testing API Endpoints

```python
def test_endpoint(client):
    response = client.get("/endpoint")
    assert response.status_code == 200
    data = response.json()
    assert "key" in data
```

### Testing Database Operations

```python
def test_database(test_db):
    from app.models.meeting import User
    user = User(id="test-id")
    test_db.add(user)
    test_db.commit()
    assert user.id == "test-id"
```

### Testing File Uploads

```python
def test_upload(client):
    files = {"audio_file": ("test.mp3", BytesIO(b"data"), "audio/mpeg")}
    data = {"user_id": "user-123"}
    response = client.post("/meetings/upload", files=files, data=data)
    assert response.status_code == 200
```

## Continuous Integration

### GitHub Actions Example

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-python@v2
        with:
          python-version: '3.9'
      - run: pip install -r requirements.txt -r requirements-dev.txt
      - run: pytest --cov=app
```

## Troubleshooting

### Import Errors

Make sure you're in the project root:
```bash
cd /home/coder/Work/My_Projects/MeetMind
pytest
```

### Database Errors

Tests use a separate test database that's cleaned after each test. If issues persist:
```bash
rm -f test_meetmind.db
pytest
```

### Async Test Errors

Make sure `pytest-asyncio` is installed:
```bash
pip install pytest-asyncio
```

## Best Practices

1. **Isolate Tests**: Each test should be independent
2. **Mock External Services**: Don't make real API calls
3. **Clean Up**: Use fixtures to ensure cleanup
4. **Descriptive Names**: Test names should describe what they test
5. **Test Edge Cases**: Include error scenarios
6. **Fast Tests**: Keep tests fast by mocking expensive operations

## Example Test Session

```bash
$ pytest -v

tests/test_models.py::TestUserModel::test_create_user PASSED
tests/test_models.py::TestUserModel::test_user_meetings_relationship PASSED
tests/test_models.py::TestMeetingModel::test_create_meeting PASSED
tests/test_audio_service.py::TestAudioService::test_validate_audio_file_valid_wav PASSED
tests/test_langgraph_service.py::TestLangGraphService::test_clean_transcript PASSED
tests/test_api.py::TestHealthEndpoints::test_root_endpoint PASSED
tests/test_api.py::TestMeetingEndpoints::test_get_user_meetings_empty PASSED

======================== 25 passed in 2.34s ========================
```

## Next Steps

1. Run the full test suite: `pytest -v`
2. Check coverage: `pytest --cov=app --cov-report=html`
3. Add more tests as you add features
4. Set up CI/CD pipeline for automated testing
