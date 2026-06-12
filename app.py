from __future__ import annotations

import streamlit as st

from src.agent import agent
from src.globe import render_globe


def _latest_assistant_message(messages):
    for role, content in reversed(list(messages)):
        if role == "assistant":
            return content
    return "没有生成回复。"


st.set_page_config(page_title="航天任务 AI 助手", layout="wide")
st.markdown(
    """
    <style>
      [data-testid="stAppViewContainer"] {
        background: #07090d;
        color: #f6f8fb;
      }
      [data-testid="stHeader"],
      [data-testid="stToolbar"],
      .stDeployButton,
      #MainMenu,
      footer {
        display: none;
      }
      .block-container {
        max-width: 1380px;
        padding-top: 1.5rem;
        padding-bottom: 1.5rem;
      }
      h1 {
        color: #f6f8fb;
        font-size: 2.4rem !important;
        line-height: 1.1;
        letter-spacing: 0;
        margin-bottom: 1rem;
      }
      [data-testid="stChatMessage"] {
        background: rgba(255, 255, 255, 0.055);
        border: 1px solid rgba(255, 255, 255, 0.09);
        border-radius: 8px;
        color: #f6f8fb;
      }
      [data-testid="stMarkdownContainer"],
      [data-testid="stMarkdownContainer"] p {
        color: #f6f8fb !important;
      }
      [data-testid="stChatInput"] {
        background: transparent;
      }
      [data-testid="stChatInput"] > div {
        background: rgba(13, 17, 23, 0.96) !important;
        border: 1px solid rgba(255, 255, 255, 0.18) !important;
        border-radius: 8px !important;
        box-shadow: none !important;
      }
      [data-testid="stChatInput"] [data-baseweb="textarea"],
      [data-testid="stChatInput"] [data-baseweb="base-input"],
      [data-testid="stChatInput"] [data-baseweb="base-input"] > div {
        background: #0d1117 !important;
        color: #f6f8fb !important;
        -webkit-text-fill-color: #f6f8fb !important;
        border-color: rgba(255, 255, 255, 0.18) !important;
        box-shadow: none !important;
      }
      [data-testid="stChatInput"] textarea,
      [data-testid="stChatInput"] textarea:focus,
      [data-testid="stChatInput"] textarea:active {
        background: #0d1117 !important;
        color: #f6f8fb !important;
        caret-color: #35d3ff !important;
        -webkit-text-fill-color: #f6f8fb !important;
        font-size: 0.98rem !important;
        line-height: 1.45 !important;
        border: 0 !important;
        box-shadow: none !important;
        outline: none !important;
      }
      [data-testid="stChatInput"] textarea::placeholder {
        color: rgba(246, 248, 251, 0.58) !important;
        -webkit-text-fill-color: rgba(246, 248, 251, 0.58) !important;
      }
      [data-testid="stChatInput"] button {
        background: rgba(53, 211, 255, 0.14) !important;
        color: #f6f8fb !important;
        border-radius: 6px !important;
      }
      [data-testid="stChatInput"] button svg {
        fill: #f6f8fb !important;
        stroke: #f6f8fb !important;
      }
      @media (max-width: 760px) {
        .block-container {
          padding: 1rem;
        }
        h1 {
          font-size: 2rem !important;
        }
      }
    </style>
    """,
    unsafe_allow_html=True,
)
st.title("卫星任务 AI 助手")

if "messages" not in st.session_state:
    st.session_state.messages = []
if "last_position" not in st.session_state:
    st.session_state.last_position = None
if "last_satellite_name" not in st.session_state:
    st.session_state.last_satellite_name = "卫星"
if "last_position_error" not in st.session_state:
    st.session_state.last_position_error = None
if "last_trajectory" not in st.session_state:
    st.session_state.last_trajectory = []

globe_column, chat_column = st.columns([1.35, 1], gap="large")

with globe_column:
    render_globe(
        st.session_state.last_position,
        st.session_state.last_satellite_name,
        trajectory=st.session_state.last_trajectory,
    )
    if st.session_state.last_position_error:
        st.warning(st.session_state.last_position_error)

with chat_column:
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    if prompt := st.chat_input("请输入任务指令"):
        st.session_state.messages.append({"role": "user", "content": prompt})

        history = [(message["role"], message["content"]) for message in st.session_state.messages]

        try:
            final_state = agent.invoke({"messages": history})
            reply = _latest_assistant_message(final_state.get("messages", ()))
            position = final_state.get("position")
            if isinstance(position, dict):
                if position.get("error"):
                    st.session_state.last_position_error = f"位置更新失败：{position['error']}"
                    st.session_state.last_trajectory = []
                else:
                    st.session_state.last_position = position
                    st.session_state.last_satellite_name = final_state.get("satellite_name", "卫星")
                    st.session_state.last_trajectory = final_state.get("trajectory", [])
                    st.session_state.last_position_error = None
        except Exception as exc:  # pragma: no cover - UI guardrail
            reply = f"任务执行失败：{exc}"

        st.session_state.messages.append({"role": "assistant", "content": reply})
        st.rerun()
