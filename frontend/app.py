import streamlit as st
import requests

BACKEND = "http://localhost:8000"

st.set_page_config(page_title="ChatWithRepo", page_icon="🤖", layout="wide")

# Initialize session state variables
if "current_repo_id" not in st.session_state:
    st.session_state.current_repo_id = None
if "current_repo_url" not in st.session_state:
    st.session_state.current_repo_url = None
if "sessions" not in st.session_state:
    st.session_state.sessions = []  # Stores loaded repos: {"id": "...", "url": "..."}
if "messages" not in st.session_state:
    st.session_state.messages = []

def load_history(repo_id):
    """Fetch past chat history from the backend DB for the selected repo."""
    try:
        res = requests.get(f"{BACKEND}/history/{repo_id}")
        if res.status_code == 200:
            history = res.json()
            formatted_msgs = []
            for user_msg, bot_msg in history:
                formatted_msgs.append({"role": "user", "content": user_msg})
                formatted_msgs.append({"role": "assistant", "content": bot_msg})
            st.session_state.messages = formatted_msgs
        else:
            st.session_state.messages = []
    except Exception:
        st.session_state.messages = []

# --- SIDEBAR ---
with st.sidebar:
    # New Chat Button
    if st.button("➕ New Chat", use_container_width=True):
        st.session_state.current_repo_id = None
        st.session_state.current_repo_url = None
        st.session_state.messages = []
        st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("### Chat History")
    
    if not st.session_state.sessions:
        st.caption("No recent chats.")
    else:
        # Display history buttons (newest at the top)
        for session in reversed(st.session_state.sessions):
            # Show just the repository name instead of the full URL
            repo_name = session["url"].split("/")[-1] if "/" in session["url"] else session["url"]
            
            is_active = session["id"] == st.session_state.current_repo_id
            btn_type = "primary" if is_active else "secondary"
            
            if st.button(f"💬 {repo_name}", key=session["id"], use_container_width=True, type=btn_type):
                st.session_state.current_repo_id = session["id"]
                st.session_state.current_repo_url = session["url"]
                load_history(session["id"])
                st.rerun()

# --- MAIN CHAT AREA ---
if st.session_state.current_repo_id is None:
    # "Landing Page" view when no chat is selected (like ChatGPT)
    st.markdown("<h1 style='text-align: center; margin-top: 15vh;'>ChatWithRepo</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #555;'>Enter a GitHub repository URL to start exploring the codebase.</p>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        new_repo_url = st.text_input("GitHub Repo URL", placeholder="https://github.com/user/repo", label_visibility="collapsed")
        
        if st.button("Load Repository", use_container_width=True, type="primary"):
            if new_repo_url:
                with st.spinner("Cloning & processing files into ChromaDB (this may take a moment)..."):
                    try:
                        res = requests.post(f"{BACKEND}/load_repo", json={"repo_url": new_repo_url})
                        if res.status_code == 200:
                            repo_id = res.json()["repo_id"]
                            st.session_state.current_repo_id = repo_id
                            st.session_state.current_repo_url = new_repo_url
                            
                            if not any(s["id"] == repo_id for s in st.session_state.sessions):
                                st.session_state.sessions.append({"id": repo_id, "url": new_repo_url})
                            
                            st.session_state.messages = [] 
                            st.rerun()
                        else:
                            st.error(f"Error: {res.text}")
                    except Exception as e:
                        st.error(f"Failed to connect: {e}")

else:
    # "Active Chat" view
    st.caption(f"📚 **Context:** `{st.session_state.current_repo_url}`")
    st.divider()

    # 1. Display chat messages from history
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # 2. Chat Input Box (pinned to bottom)
    if prompt := st.chat_input("Ask a question about the codebase..."):
        
        # Display user message instantly
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # Generate and display bot response
        with st.chat_message("assistant"):
            message_placeholder = st.empty()
            with st.spinner("Analyzing code..."):
                try:
                    res = requests.post(
                        f"{BACKEND}/chat",
                        json={
                            "repo_id": st.session_state.current_repo_id,
                            "question": prompt
                        }
                    )
                    if res.status_code == 200:
                        response_data = res.json()
                        if "error" in response_data:
                            answer = f"**Error:** {response_data['error']}"
                        else:
                            answer = response_data.get("answer", "No response.")
                    else:
                        answer = f"**Backend Error ({res.status_code}):** {res.text}"
                except Exception as e:
                    answer = f"**Connection Error:** {str(e)}"
            
            message_placeholder.markdown(answer)
            st.session_state.messages.append({"role": "assistant", "content": answer})