import streamlit as st
import requests

BACKEND = "http://localhost:8000"

st.set_page_config(page_title="ChatWithRepo", page_icon="🤖", layout="wide")

if "current_repo_id" not in st.session_state:
    st.session_state.current_repo_id = None
if "current_repo_url" not in st.session_state:
    st.session_state.current_repo_url = None
if "sessions" not in st.session_state:
    st.session_state.sessions = []  
if "messages" not in st.session_state:
    st.session_state.messages = []

def load_history(repo_id):
    
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

with st.sidebar:
   
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
        
        for session in reversed(st.session_state.sessions):
            
            repo_name = session["url"].split("/")[-1] if "/" in session["url"] else session["url"]
            
            is_active = session["id"] == st.session_state.current_repo_id
            btn_type = "primary" if is_active else "secondary"
            
            if st.button(f"💬 {repo_name}", key=session["id"], use_container_width=True, type=btn_type):
                st.session_state.current_repo_id = session["id"]
                st.session_state.current_repo_url = session["url"]
                load_history(session["id"])
                st.rerun()

if st.session_state.current_repo_id is None:
    
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
    
    st.caption(f"📚 **Context:** `{st.session_state.current_repo_url}`")
    st.divider()

    
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    if prompt := st.chat_input("Ask a question about the codebase..."):
        
        
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        
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