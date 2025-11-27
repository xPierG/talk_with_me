import os
import pytest
from unittest.mock import MagicMock, patch
from rag_core import GeminiRAG

# Mock environment variables
@pytest.fixture(autouse=True)
def mock_env_vars():
    with patch.dict(os.environ, {"GOOGLE_API_KEY": "test_api_key"}):
        yield

@pytest.fixture
def gemini_rag():
    return GeminiRAG()

def test_init_raises_error_without_api_key():
    with patch.dict(os.environ, {}, clear=True):
        with pytest.raises(ValueError, match="GOOGLE_API_KEY not found"):
            GeminiRAG()

def test_init_success(gemini_rag):
    assert gemini_rag.api_key == "test_api_key"
    assert gemini_rag.model_name == "gemini-1.5-pro-002"

@patch("rag_core.genai.upload_file")
@patch("rag_core.genai.get_file")
@patch("rag_core.time.sleep") # Mock sleep to speed up tests
def test_upload_file_success(mock_sleep, mock_get_file, mock_upload_file, gemini_rag):
    # Mock file object returned by upload_file
    mock_file_obj = MagicMock()
    mock_file_obj.name = "files/test_file"
    mock_file_obj.state.name = "PROCESSING"
    mock_upload_file.return_value = mock_file_obj

    # Mock file object returned by get_file (polling)
    # First call: PROCESSING, Second call: ACTIVE
    mock_active_file = MagicMock()
    mock_active_file.name = "files/test_file"
    mock_active_file.state.name = "ACTIVE"
    
    mock_get_file.side_effect = [mock_file_obj, mock_active_file]

    file_bytes = b"test content"
    mime_type = "text/plain"
    file_name = "test.txt"

    result = gemini_rag.upload_file(file_bytes, mime_type, file_name)

    assert result.state.name == "ACTIVE"
    mock_upload_file.assert_called_once()
    assert mock_get_file.call_count == 2

@patch("rag_core.genai.upload_file")
@patch("rag_core.genai.get_file")
@patch("rag_core.time.sleep")
def test_upload_file_failed(mock_sleep, mock_get_file, mock_upload_file, gemini_rag):
    mock_file_obj = MagicMock()
    mock_file_obj.state.name = "PROCESSING"
    mock_upload_file.return_value = mock_file_obj

    mock_failed_file = MagicMock()
    mock_failed_file.state.name = "FAILED"
    mock_get_file.return_value = mock_failed_file

    with pytest.raises(ValueError, match="File processing failed"):
        gemini_rag.upload_file(b"content", "text/plain", "test.txt")

@patch("rag_core.caching.CachedContent.create")
@patch("rag_core.genai.GenerativeModel.from_cached_content")
def test_initialize_chat_with_cache_success(mock_from_cached, mock_create_cache, gemini_rag):
    mock_file_obj = MagicMock()
    mock_file_obj.name = "files/test_file"
    
    mock_cache = MagicMock()
    mock_cache.name = "caches/test_cache"
    mock_create_cache.return_value = mock_cache

    mock_model = MagicMock()
    mock_from_cached.return_value = mock_model
    
    mock_chat = MagicMock()
    mock_model.start_chat.return_value = mock_chat

    chat = gemini_rag.initialize_chat(mock_file_obj)

    assert chat == mock_chat
    mock_create_cache.assert_called_once()
    mock_from_cached.assert_called_once_with(cached_content=mock_cache)
    mock_model.start_chat.assert_called_once_with(history=[])

@patch("rag_core.caching.CachedContent.create")
@patch("rag_core.genai.GenerativeModel")
def test_initialize_chat_fallback_no_cache(mock_generative_model, mock_create_cache, gemini_rag):
    mock_file_obj = MagicMock()
    mock_create_cache.side_effect = Exception("Cache creation failed")

    mock_model = MagicMock()
    mock_generative_model.return_value = mock_model
    
    mock_chat = MagicMock()
    mock_model.start_chat.return_value = mock_chat

    chat = gemini_rag.initialize_chat(mock_file_obj)

    assert chat == mock_chat
    mock_create_cache.assert_called_once()
    # Verify fallback to standard model
    mock_generative_model.assert_called_once() 
    # Verify history construction for fallback
    call_args = mock_model.start_chat.call_args
    assert call_args is not None
    history = call_args.kwargs['history']
    assert len(history) == 2
    assert history[0]['role'] == 'user'
    assert history[0]['parts'] == [mock_file_obj]

@patch("rag_core.genai.delete_file")
def test_cleanup_file(mock_delete_file, gemini_rag):
    gemini_rag.cleanup_file("files/test_file")
    mock_delete_file.assert_called_once_with("files/test_file")
