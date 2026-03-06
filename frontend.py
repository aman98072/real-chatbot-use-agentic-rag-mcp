import streamlit as st
from datetime import datetime
import time
import requests

# ==============================
# CONFIG
# ==============================
API_URL = "http://127.0.0.1:8000/chat"

st.set_page_config(
    page_title="AI Chatbot",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==============================
# CUSTOM CSS
# ==============================
st.markdown("""
<style>
.main {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}
.stChatMessage {
    background-color: rgba(255, 255, 255, 0.95);
    border-radius: 15px;
    padding: 15px;
    margin: 10px 0;
}
.stChatInputContainer {
    border-radius: 25px;
    background-color: white;
}
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #667eea 0%, #764ba2 100%);
}
h1, h2, h3 {
    color: white;
}
.stats-box {
    background: rgba(255, 255, 255, 0.9);
    border-radius: 15px;
    padding: 20px;
}
</style>
""", unsafe_allow_html=True)

# ==============================
# SESSION STATE
# ==============================
if "messages" not in st.session_state:
    st.session_state.messages = [{
        "role": "assistant",
        "content": "👋 Namaste! Main aapka AI assistant hoon.",
        "time": datetime.now().strftime("%H:%M")
    }]

if "count" not in st.session_state:
    st.session_state.count = 1

# ==============================
# SIDEBAR
# ==============================
with st.sidebar:
    st.markdown("# 🤖 AI Chatbot")
    st.markdown("---")

    st.markdown("### 📊 Stats")
    st.markdown(f"""
    <div class="stats-box">
        <h4>Total Messages</h4>
        <h2>{st.session_state.count}</h2>
    </div>
    """, unsafe_allow_html=True)

    speed = st.slider("Response Speed", 1, 10, 5)

    if st.button("🗑 Clear Chat"):
        st.session_state.messages = [{
            "role": "assistant",
            "content": "👋 Chat cleared. Phir se shuru karein?",
            "time": datetime.now().strftime("%H:%M")
        }]
        st.session_state.count = 1
        st.rerun()

# ==============================
# BACKEND CALL FUNCTION
# ==============================
def get_bot_response(message: str) -> str:
    try:
        res = requests.post(
            API_URL,
            json={"message": message},
            timeout=10
        )

        if res.status_code == 200:
            return res.json().get("response", "❌ Empty response")
        else:
            return f"❌ Backend error {res.status_code}"

    except requests.exceptions.ConnectionError:
        return "❌ Backend not running (start uvicorn)"
    except requests.exceptions.Timeout:
        return "❌ Backend timeout"
    except Exception as e:
        return f"❌ Error: {str(e)}"

# ==============================
# MAIN CHAT UI
# ==============================
st.markdown("# 💬 Smart Chatbot")

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        st.caption(f"🕐 {msg['time']}")

# ==============================
# INPUT
# ==============================
if prompt := st.chat_input("Type your message..."):
    now = datetime.now().strftime("%H:%M")

    # User message
    st.session_state.messages.append({
        "role": "user",
        "content": prompt,
        "time": now
    })
    st.session_state.count += 1

    with st.chat_message("user"):
        st.markdown(prompt)
        st.caption(f"🕐 {now}")

    # Assistant message
    with st.chat_message("assistant"):
        placeholder = st.empty()
        response = get_bot_response(prompt)

        typed = ""
        for ch in response:
            typed += ch
            placeholder.markdown(typed + "▌")
            time.sleep(0.01 * (11 - speed))

        placeholder.markdown(response)
        t = datetime.now().strftime("%H:%M")
        st.caption(f"🕐 {t}")

    st.session_state.messages.append({
        "role": "assistant",
        "content": response,
        "time": t
    })
    st.session_state.count += 1

# ==============================
# FOOTER
# ==============================
st.markdown("---")
st.markdown(
    "<center>🚀 Powered by FastAPI + Streamlit</center>",
    unsafe_allow_html=True
)