import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime

from advanced_omi_backend.main import create_app
from advanced_omi_backend.models.user import User
from advanced_omi_backend.auth import current_active_user

# Mock data
MOCK_USER_ID = "test-user-id"
MOCK_CONVERSATION_ID = "test-conversation-id"

@pytest.fixture
def mock_user():
    user = MagicMock(spec=User)
    user.id = MOCK_USER_ID
    user.email = "test@example.com"
    return user

@pytest.fixture
def app(mock_user):
    application = create_app()
    # Override authentication dependency
    application.dependency_overrides[current_active_user] = lambda: mock_user
    return application

@pytest.fixture
async def client(app):
    async with AsyncClient(app=app, base_url="http://test") as c:
        yield c

@pytest.mark.asyncio
async def test_annotation_flow(app, mock_user):
    # Mock DB interactions
    with patch("advanced_omi_backend.routers.modules.annotation_routes.Conversation") as MockConversation, \
         patch("advanced_omi_backend.routers.modules.annotation_routes.TranscriptAnnotation") as MockAnnotation, \
         patch("advanced_omi_backend.routers.modules.annotation_routes.enqueue_memory_processing") as mock_enqueue:

        # Setup mock conversation
        mock_conv = MagicMock()
        mock_conv.conversation_id = MOCK_CONVERSATION_ID
        mock_conv.user_id = MOCK_USER_ID
        mock_conv.client_id = "test-client"
        
        # Setup active transcript
        mock_version = MagicMock()
        mock_version.version_id = "v1"
        mock_version.segments = [MagicMock(text="Original text")]
        mock_conv.active_transcript = mock_version
        mock_conv.transcript_versions = [mock_version]
        
        # Make save awaitable
        mock_conv.save = AsyncMock()
        
        # Configure find_one to return our mock conversation (awaitable)
        MockConversation.find_one.return_value = AsyncMock(return_value=mock_conv)() # Calling AsyncMock returns an awaitable coroutine

        # Mock Annotation insert (awaitable)
        mock_annotation_instance = MagicMock()
        mock_annotation_instance.insert = AsyncMock()
        mock_annotation_instance.id = "test-annotation-id"
        mock_annotation_instance.conversation_id = MOCK_CONVERSATION_ID
        mock_annotation_instance.segment_index = 0
        mock_annotation_instance.original_text = "Original text"
        mock_annotation_instance.corrected_text = "Corrected text"
        mock_annotation_instance.status = "accepted"
        mock_annotation_instance.created_at = datetime.now()
        
        MockAnnotation.return_value = mock_annotation_instance

        # Define the annotation payload
        annotation_data = {
            "conversation_id": MOCK_CONVERSATION_ID,
            "segment_index": 0,
            "original_text": "Original text",
            "corrected_text": "Corrected text",
            "status": "accepted"
        }

        # Make the API call using AsyncClient with ASGITransport
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post("/api/annotations/", json=annotation_data)

        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert data["conversation_id"] == MOCK_CONVERSATION_ID
        assert data["corrected_text"] == "Corrected text"

        # Verify DB interaction
        # 1. Verify conversation lookup was called
        MockConversation.find_one.assert_called()
        
        # 2. Verify annotation creation (MockAnnotation constructor called)
        MockAnnotation.assert_called()
        mock_annotation_instance.insert.assert_called_once()
        
        # 3. Verify transcript update
        assert mock_version.segments[0].text == "Corrected text"
        mock_conv.save.assert_called_once()

        # 4. Verify memory job enqueuing
        mock_enqueue.assert_called_once()
        call_kwargs = mock_enqueue.call_args.kwargs
        assert call_kwargs['conversation_id'] == MOCK_CONVERSATION_ID
        assert call_kwargs['user_id'] == MOCK_USER_ID