"""dashboard/pages/agent_chat.py - AI Agent conversational interface."""
import streamlit as st
from dashboard.api_client import APIClient


def render():
    st.markdown("""
    <div class="page-header">
        <h1 class="page-title">🤖 AI Agent</h1>
        <p class="page-subtitle">Chat with SpectrumAI — powered by Ollama + RAG</p>
    </div>
    """, unsafe_allow_html=True)

    if "chat_messages" not in st.session_state:
        st.session_state.chat_messages = [
            {
                "role": "assistant",
                "content": (
                    "Hello! I'm **SpectrumAI**, your RF spectrum security analyst. "
                    "I can help you:\n"
                    "- 🔍 Analyze detected jamming or drone signals\n"
                    "- 📊 Summarize current threat status\n"
                    "- 📋 Generate security reports\n"
                    "- 💡 Recommend countermeasures\n\n"
                    "What would you like to know?"
                ),
            }
        ]

    # ── Quick actions ─────────────────────────────────────────────────
    st.markdown("**Quick Actions:**")
    q_cols = st.columns(4)
    quick_questions = [
        "What is the current threat status?",
        "Explain the last jamming detection",
        "What should I do about drone signals?",
        "Generate a threat summary",
    ]
    for i, q in enumerate(quick_questions):
        with q_cols[i]:
            if st.button(q[:30] + "…" if len(q) > 30 else q, key=f"quick_{i}", use_container_width=True):
                st.session_state.chat_messages.append({"role": "user", "content": q})
                st.rerun()

    st.markdown("---")

    # ── Chat history ──────────────────────────────────────────────────
    chat_container = st.container(height=400)
    with chat_container:
        for msg in st.session_state.chat_messages:
            with st.chat_message(msg["role"], avatar="🤖" if msg["role"] == "assistant" else "👤"):
                st.markdown(msg["content"])

    # ── Input ─────────────────────────────────────────────────────────
    user_input = st.chat_input("Ask SpectrumAI anything about your RF environment...")

    if user_input:
        st.session_state.chat_messages.append({"role": "user", "content": user_input})

        client = APIClient()
        with st.spinner("SpectrumAI is analyzing..."):
            result = client.agent_chat(user_input, session_id=st.session_state.get("username", "default"))

        if result:
            answer = result.get("answer", "I couldn't generate a response.")
            model = result.get("model", "unknown")
            st.session_state.chat_messages.append({
                "role": "assistant",
                "content": f"{answer}\n\n<sub>*Model: {model}*</sub>",
            })
        else:
            st.session_state.chat_messages.append({
                "role": "assistant",
                "content": "⚠️ Unable to reach the AI agent. Please check the API connection.",
            })

        st.rerun()

    # ── Clear chat ────────────────────────────────────────────────────
    if st.button("🗑️ Clear Chat", type="secondary"):
        st.session_state.chat_messages = []
        st.rerun()
