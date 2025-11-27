import os
import time
import logging
from pathlib import Path
import google.generativeai as genai
from google.generativeai import caching
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

class GeminiRAG:
    def __init__(self):
        self.api_key = os.getenv("GOOGLE_API_KEY")
        if not self.api_key:
            raise ValueError("GOOGLE_API_KEY not found in environment variables")
        genai.configure(api_key=self.api_key)
        # Use Gemini 2.5 Flash (supports implicit caching by default)
        self.model_name = os.getenv("GEMINI_MODEL_NAME", "gemini-2.5-flash")

    def upload_file(self, file_bytes, mime_type, file_name):
        """
        Uploads a file to Gemini, waiting for it to be active.
        """
        # Save temporarily to /tmp (Cloud Run compatible)
        tmp_path = Path(f"/tmp/{file_name}")
        with open(tmp_path, "wb") as f:
            f.write(file_bytes)
        
        logger.info(f"Uploading file: {file_name}")
        try:
            file_obj = genai.upload_file(path=tmp_path, mime_type=mime_type, display_name=file_name)
        finally:
            # Clean up local temp file
            if tmp_path.exists():
                tmp_path.unlink()

        # Poll for active state
        logger.info(f"Waiting for file processing: {file_obj.name}")
        start_time = time.time()
        timeout_seconds = 60

        while file_obj.state.name == "PROCESSING":
            if time.time() - start_time > timeout_seconds:
                raise TimeoutError(f"File processing timed out after {timeout_seconds} seconds")
            time.sleep(2)
            file_obj = genai.get_file(file_obj.name)

        if file_obj.state.name == "FAILED":
            raise ValueError(f"File processing failed: {file_obj.state.name}")
        
        if file_obj.state.name != "ACTIVE":
             # Should not happen if we exit the loop correctly, but good for safety
             raise ValueError(f"Unexpected file state: {file_obj.state.name}")

        logger.info(f"File active: {file_obj.name}")
        return file_obj

    def initialize_chat(self, file_obj):
        """
        Initializes the chat session, using caching if appropriate/possible.
        """
        # Attempt to use caching for the file
        # Note: Context Caching has a minimum token requirement (approx 32k).
        # We try to create it, and fallback if it fails or if the file is too small.
        
        model = None
        
        try:
            # Create a cache with a TTL of 60 minutes
            logger.info("Attempting to create context cache...")
            cache = caching.CachedContent.create(
                model=self.model_name,
                display_name=f"cache_{file_obj.name}",
                system_instruction="You are a helpful assistant. Answer questions based on the provided document.",
                contents=[file_obj],
                ttl=3600 # 1 hour
            )
            logger.info(f"Cache created: {cache.name}")
            model = genai.GenerativeModel.from_cached_content(cached_content=cache)
        
        except Exception as e:
            logger.warning(f"Could not create context cache (likely file too small or model not supported): {e}")
            logger.info("Falling back to standard file usage.")
            
            # Fallback: Standard model with file in history/context
            # For standard usage, we don't pass the file to the model constructor directly in the same way as cache
            # Instead, we usually pass it in the first message or system instruction, 
            # but for 'chat', passing it in history or system_instruction is best.
            
            model = genai.GenerativeModel(
                model_name=self.model_name,
                system_instruction="You are a helpful assistant. Answer questions based on the provided document."
            )
            
            # We will start the chat with the file in the history effectively by sending it? 
            # Or better, we can just keep the file_obj and pass it in the history of start_chat if supported,
            # but start_chat history expects Content objects.
            # A common pattern for "Chat with Doc" without cache is to include the file in the history.
            
            # However, start_chat history is a list of protos or dicts.
            # Let's try to initialize chat with the file as the first part of the context.
            # But wait, if we use the file in `start_chat`, it persists.
            
            # Let's construct a valid history item for the file.
            # Actually, `start_chat` history argument is convenient.
            # We can put the file in the history as a "user" message.
            
            initial_history = [
                {
                    "role": "user",
                    "parts": [file_obj]
                },
                {
                    "role": "model",
                    "parts": ["Understood. I have processed the document. What would you like to know?"]
                }
            ]
            
            chat = model.start_chat(history=initial_history)
            return chat

        # If cache was successful, we start chat on the cached model
        # The cached content already includes the file, so we don't need to pass it again.
        chat = model.start_chat(history=[])
        return chat

    def cleanup_file(self, file_name):
        """
        Deletes the file from Gemini.
        """
        try:
            logger.info(f"Deleting file: {file_name}")
            genai.delete_file(file_name)
        except Exception as e:
            logger.error(f"Error deleting file {file_name}: {e}")


class FileSearchRAG:
    """
    RAG implementation using Google's File Search Tool (semantic search).
    """
    def __init__(self):
        from google import genai as genai_client
        from google.genai import types
        
        self.api_key = os.getenv("GOOGLE_API_KEY")
        if not self.api_key:
            raise ValueError("GOOGLE_API_KEY not found in environment variables")
        
        self.client = genai_client.Client(api_key=self.api_key)
        self.types = types
        # Use Gemini 2.5 Flash for File Search Tool
        self.model_name = os.getenv("GEMINI_MODEL_NAME", "gemini-2.5-flash")
        self.file_search_store = None
        self.operation = None

    def create_and_upload_file(self, file_bytes, mime_type, file_name):
        """
        Creates a File Search store and uploads the file to it.
        """
        # Save temporarily to /tmp
        tmp_path = Path(f"/tmp/{file_name}")
        with open(tmp_path, "wb") as f:
            f.write(file_bytes)
        
        try:
            # Create File Search store
            logger.info("Creating File Search store...")
            self.file_search_store = self.client.file_search_stores.create(
                config={'display_name': f'store_{file_name}'}
            )
            logger.info(f"File Search store created: {self.file_search_store.name}")
            
            # Upload file to the store
            logger.info(f"Uploading file to File Search store: {file_name}")
            self.operation = self.client.file_search_stores.upload_to_file_search_store(
                file=str(tmp_path),
                file_search_store_name=self.file_search_store.name,
                config={'display_name': file_name}
            )
            
            # Wait for indexing to complete
            logger.info("Waiting for file indexing...")
            start_time = time.time()
            timeout_seconds = 120  # File Search can take longer
            
            while not self.operation.done:
                if time.time() - start_time > timeout_seconds:
                    raise TimeoutError(f"File indexing timed out after {timeout_seconds} seconds")
                time.sleep(5)
                self.operation = self.client.operations.get(self.operation)
            
            logger.info("File indexed successfully")
            return self.file_search_store
            
        finally:
            # Clean up local temp file
            if tmp_path.exists():
                tmp_path.unlink()

    def initialize_chat(self):
        """
        Initializes chat with File Search tool enabled.
        Returns a callable that can be used to send messages.
        """
        if not self.file_search_store:
            raise ValueError("File Search store not created. Call create_and_upload_file first.")
        
        logger.info("Initializing chat with File Search tool...")
        
        # We'll return a wrapper function that uses generateContent with the tool
        def send_message(prompt, stream=True):
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=self.types.GenerateContentConfig(
                    tools=[
                        self.types.Tool(
                            file_search=self.types.FileSearch(
                                file_search_store_names=[self.file_search_store.name]
                            )
                        )
                    ]
                )
            )
            
            if stream:
                # For streaming, we need to handle it differently
                # The new SDK returns a response object, not a generator
                # We'll yield the text in chunks
                yield response.text
            else:
                return response
        
        return send_message

    def cleanup_store(self):
        """
        Deletes the File Search store and all its data.
        """
        if self.file_search_store:
            try:
                logger.info(f"Deleting File Search store: {self.file_search_store.name}")
                # Use config={'force': True} to delete non-empty stores
                self.client.file_search_stores.delete(
                    name=self.file_search_store.name,
                    config={'force': True}
                )
                logger.info("File Search store deleted")
            except Exception as e:
                logger.error(f"Error deleting File Search store: {e}")

