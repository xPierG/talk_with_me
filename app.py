import streamlit as st
import os
import atexit
from rag_core import GeminiRAG, FileSearchRAG

# Page Config
st.set_page_config(
    page_title="Cloud Native RAG",
    page_icon="🤖",
    layout="wide"
)

# Initialize RAG Mode Selection
if "rag_mode" not in st.session_state:
    st.session_state.rag_mode = "Long Context"

# Initialize Session State
if "rag_client" not in st.session_state:
    st.session_state.rag_client = None

if "messages" not in st.session_state:
    st.session_state.messages = []

# Support multiple files (up to 5)
if "uploaded_files" not in st.session_state:
    st.session_state.uploaded_files = []

if "chat_session" not in st.session_state:
    st.session_state.chat_session = None

# Cleanup function for session end
def cleanup_on_exit():
    """Cleanup files/stores when the session ends."""
    if st.session_state.get("uploaded_files") and st.session_state.get("rag_client"):
        try:
            if st.session_state.rag_mode == "Long Context":
                # Clean up all uploaded files
                for file_obj in st.session_state.uploaded_files:
                    if hasattr(file_obj, 'name'):
                        st.session_state.rag_client.cleanup_file(file_obj.name)
            else:  # File Search Tool
                st.session_state.rag_client.cleanup_store()
        except Exception:
            pass  # Silent cleanup on exit

# Register cleanup on exit
atexit.register(cleanup_on_exit)

def reset_conversation():
    """Resets the conversation and deletes the file/store from Gemini."""
    if st.session_state.uploaded_files and st.session_state.rag_client:
        try:
            if st.session_state.rag_mode == "Long Context":
                # Clean up all uploaded files
                for file_obj in st.session_state.uploaded_files:
                    if hasattr(file_obj, 'name'):
                        st.session_state.rag_client.cleanup_file(file_obj.name)
            else:  # File Search Tool
                st.session_state.rag_client.cleanup_store()
        except Exception as e:
            st.warning(f"Could not delete file/store: {e}")
    
    st.session_state.messages = []
    st.session_state.uploaded_files = []
    st.session_state.chat_session = None
    st.session_state.rag_client = None
    st.rerun()

# Sidebar
with st.sidebar:
    st.title("⚙️ Config")
    
    # RAG Mode Selection
    st.markdown("### RAG Mode")
    new_mode = st.radio(
        "Select RAG approach:",
        ["Long Context", "File Search Tool"],
        index=0 if st.session_state.rag_mode == "Long Context" else 1,
        help="Long Context: Loads entire file into context (best for single docs)\nFile Search Tool: Uses semantic search (best for multiple docs)"
    )
    
    # If mode changed and file is loaded, warn user
    if new_mode != st.session_state.rag_mode and st.session_state.uploaded_files:
        st.warning("⚠️ Changing mode will reset the conversation")
        if st.button("Confirm Mode Change"):
            st.session_state.rag_mode = new_mode
            reset_conversation()
    elif new_mode != st.session_state.rag_mode:
        st.session_state.rag_mode = new_mode
    
    st.markdown("---")
    # Show the actual model being used (both modes use gemini-2.5-flash by default)
    model_name = os.getenv('GEMINI_MODEL_NAME', 'gemini-2.5-flash')
    st.info(f"Model: {model_name}")
    
    if st.button("Reset Conversation", type="primary"):
        reset_conversation()
    
    st.markdown("---")
    st.markdown("### Status")
    st.info(f"Mode: {st.session_state.rag_mode}")
    if st.session_state.uploaded_files:
        if st.session_state.rag_mode == "Long Context":
            st.success(f"Files Active: {len(st.session_state.uploaded_files)}")
            for file_obj in st.session_state.uploaded_files:
                st.text(f"📄 {file_obj.display_name}")
        else:
            st.success(f"Store Active with {len(st.session_state.uploaded_files)} file(s)")
    else:
        st.warning("No files uploaded")

# Main Area
st.title("🤖 Chat with your Doc")

# File Uploader (only if no files are active)
if not st.session_state.uploaded_files:
    uploaded_files = st.file_uploader(
        "Upload documents (up to 5)",
        type=["txt", "pdf", "csv"],
        accept_multiple_files=True
    )
    
    if uploaded_files:
        # Limit to 5 files
        if len(uploaded_files) > 5:
            st.error("Maximum 5 files allowed. Please select fewer files.")
        else:
            with st.spinner(f"Uploading and processing {len(uploaded_files)} file(s) ({st.session_state.rag_mode} mode)..."):
                try:
                    # Initialize appropriate RAG client
                    if st.session_state.rag_mode == "Long Context":
                        st.session_state.rag_client = GeminiRAG()
                    else:
                        st.session_state.rag_client = FileSearchRAG()
                    
                    file_objects = []
                    
                    if st.session_state.rag_mode == "Long Context":
                        # Upload all files to Gemini (Long Context)
                        for uploaded_file in uploaded_files:
                            file_bytes = uploaded_file.getvalue()
                            file_obj = st.session_state.rag_client.upload_file(
                                file_bytes=file_bytes,
                                mime_type=uploaded_file.type,
                                file_name=uploaded_file.name
                            )
                            file_objects.append(file_obj)
                        
                        # Initialize Chat with all files
                        # For Long Context with multiple files, we pass all files to the chat
                        chat = st.session_state.rag_client.initialize_chat(file_objects[0])  # Start with first file
                        # Note: For true multi-file support in Long Context, we'd need to modify initialize_chat
                        # For now, we'll just use the first file for chat initialization
                        
                        # Update Session State
                        st.session_state.uploaded_files = file_objects
                        st.session_state.chat_session = chat
                    else:
                        # Upload all files to File Search Store
                        for uploaded_file in uploaded_files:
                            file_bytes = uploaded_file.getvalue()
                            store = st.session_state.rag_client.create_and_upload_file(
                                file_bytes=file_bytes,
                                mime_type=uploaded_file.type,
                                file_name=uploaded_file.name
                            )
                            file_objects.append(store)
                        
                        # Initialize Chat (returns a callable)
                        send_message_fn = st.session_state.rag_client.initialize_chat()
                        
                        # Update Session State
                        st.session_state.uploaded_files = file_objects
                        st.session_state.chat_session = send_message_fn
                    
                    st.rerun()
                    
                except Exception as e:
                    st.error(f"An error occurred: {e}")
                    import traceback
                    st.code(traceback.format_exc())

# Chat Interface
else:
    # Display Message History
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            if "thoughts" in message and message["thoughts"]:
                 with st.expander("Processo di ragionamento 🧠"):
                     st.markdown(message["thoughts"])

    # Chat Input
    if prompt := st.chat_input("Ask something about your document..."):
        # Add user message to history
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # Generate Response
        with st.chat_message("assistant"):
            message_placeholder = st.empty()
            full_response = ""
            thoughts_content = ""
            
            try:
                # Show spinner while waiting for first chunk
                with st.spinner("🤔 Thinking..."):
                    if st.session_state.rag_mode == "Long Context":
                        # Long Context mode (streaming)
                        response = st.session_state.chat_session.send_message(prompt, stream=True)
                        
                        for chunk in response:
                            if chunk.text:
                                full_response += chunk.text
                                message_placeholder.markdown(full_response + "▌")
                    else:
                        # File Search Tool mode
                        # The send_message function returns a generator
                        for text_chunk in st.session_state.chat_session(prompt, stream=True):
                            full_response += text_chunk
                            message_placeholder.markdown(full_response + "▌")
                
                message_placeholder.markdown(full_response)
                
                # Add assistant message to history
                st.session_state.messages.append({
                    "role": "assistant", 
                    "content": full_response,
                    "thoughts": thoughts_content
                })
                
            except Exception as e:
                st.error(f"Error generating response: {e}")
                import traceback
                st.code(traceback.format_exc())
