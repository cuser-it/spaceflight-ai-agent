from __future__ import annotations

import html
import os

import streamlit as st

from src.agent import agent, should_use_tool, stream_llm_or_fallback
from src.globe import render_globe


def _latest_assistant_message(messages):
    for role, content in reversed(list(messages)):
        if role == "assistant":
            return content
    return "没有生成回复。"


def _message_html(role: str, content: str) -> str:
    role_class = "user" if role == "user" else "assistant"
    avatar = "U" if role == "user" else "AI"
    safe_content = html.escape(content).replace("\n", "<br>")
    return f"""
        <div class="message-row {role_class}">
          <div class="message-avatar">{avatar}</div>
          <div class="message-body">{safe_content}</div>
        </div>
        """


def _render_chat_message(role: str, content: str) -> None:
    st.markdown(_message_html(role, content), unsafe_allow_html=True)


def _sync_orbit_state(final_state) -> None:
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


def _process_pending_response(assistant_placeholder) -> None:
    history = [(message["role"], message["content"]) for message in st.session_state.messages]
    latest_query = history[-1][1] if history else ""

    try:
        if should_use_tool({"messages": history}) == "get_tle":
            assistant_placeholder.markdown(
                _message_html("assistant", "正在查询轨道数据..."),
                unsafe_allow_html=True,
            )
            final_state = agent.invoke({"messages": history})
            reply = _latest_assistant_message(final_state.get("messages", ()))
            _sync_orbit_state(final_state)
        else:
            reply = ""
            assistant_placeholder.markdown(
                _message_html("assistant", "正在连接模型..."),
                unsafe_allow_html=True,
            )
            for chunk in stream_llm_or_fallback(history, latest_query):
                reply += chunk
                assistant_placeholder.markdown(
                    _message_html("assistant", reply or "正在生成..."),
                    unsafe_allow_html=True,
                )
            if not reply:
                reply = "没有生成回复。"
    except Exception as exc:  # pragma: no cover - UI guardrail
        reply = f"任务执行失败：{exc}"

    assistant_placeholder.markdown(_message_html("assistant", reply), unsafe_allow_html=True)
    st.session_state.messages.append({"role": "assistant", "content": reply})
    st.session_state.pending_response = False
    st.rerun()


st.set_page_config(page_title="航天任务 AI 助手", layout="wide")

model_connected = bool(os.getenv("DEEPSEEK_API_KEY"))
model_status_class = "connected" if model_connected else "offline"
model_status_text = "已连接" if model_connected else "未连接"

st.markdown(
    """
    <style>
      html,
      body,
      .stApp,
      [data-testid="stAppViewContainer"] {
        height: 100vh;
        overflow: hidden;
        background: #07090d;
        color: #f6f8fb;
      }
      [data-testid="stAppViewContainer"] > .main {
        height: 100vh;
        overflow: hidden;
      }
      [data-testid="stHeader"],
      [data-testid="stToolbar"],
      .stDeployButton,
      #MainMenu,
      footer {
        display: none;
      }
      .block-container {
        width: 100%;
        max-width: none;
        height: 100vh;
        padding: 0;
        overflow: hidden;
      }
      .block-container > div[data-testid="stVerticalBlock"] {
        height: 100%;
        gap: 0 !important;
      }
      .block-container div[data-testid="stHorizontalBlock"] {
        width: 100%;
        height: 100vh;
        align-items: stretch;
        gap: 0;
      }
      .block-container div[data-testid="stHorizontalBlock"] > div[data-testid="stColumn"] {
        flex: 0 0 50% !important;
        width: 50% !important;
        max-width: 50% !important;
        min-width: 0 !important;
      }
      .block-container div[data-testid="stHorizontalBlock"] > div[data-testid="stColumn"]:nth-child(2),
      .block-container div[data-testid="stHorizontalBlock"] > div[data-testid="stColumn"]:nth-child(2) > div {
        background: #07090d;
      }
      .model-status {
        position: fixed;
        top: 20px;
        right: 24px;
        z-index: 1000;
        display: inline-flex;
        align-items: center;
        gap: 9px;
        padding: 8px 12px;
        border: 1px solid rgba(255, 255, 255, 0.14);
        border-radius: 8px;
        background: rgba(9, 13, 19, 0.74);
        color: rgba(246, 248, 251, 0.70);
        font-size: 12px;
        line-height: 1;
        letter-spacing: 0;
        backdrop-filter: blur(14px);
      }
      .model-status strong {
        color: #62d98f;
        font-weight: 700;
      }
      .model-status.offline strong {
        color: #ffc857;
      }
      .model-status .dot {
        width: 7px;
        height: 7px;
        border-radius: 50%;
        background: #62d98f;
        box-shadow: 0 0 12px rgba(98, 217, 143, 0.72);
      }
      .model-status.offline .dot {
        background: #ffc857;
        box-shadow: 0 0 12px rgba(255, 200, 87, 0.72);
      }
      .st-key-globe_panel {
        width: 100%;
        height: 100vh;
        display: flex;
        align-items: center;
        justify-content: center;
        overflow: hidden;
      }
      .st-key-globe_panel [data-testid="stElementContainer"],
      .st-key-globe_panel [data-testid="stIFrame"] {
        width: 100% !important;
        height: 100vh !important;
      }
      .st-key-chat_panel {
        width: 100%;
        height: 100vh !important;
        min-height: 100vh !important;
        display: flex;
        flex-direction: column;
        justify-content: center;
        overflow: hidden;
        padding: 56px 48px 34px;
        border: 0;
        border-radius: 0;
        background: transparent;
        box-sizing: border-box;
      }
      .st-key-chat_scroll {
        border: 0 !important;
        border-radius: 0;
        background: transparent;
        padding: 0 8px 0 0;
        overflow-y: auto;
        scrollbar-width: thin;
        scrollbar-color: rgba(98, 217, 143, 0.48) rgba(255, 255, 255, 0.04);
      }
      .message-row {
        display: grid;
        grid-template-columns: 32px minmax(0, 1fr);
        gap: 12px;
        align-items: start;
        margin: 0 0 14px;
      }
      .message-avatar {
        width: 32px;
        height: 32px;
        display: flex;
        align-items: center;
        justify-content: center;
        border-radius: 8px;
        color: #ffffff;
        font-size: 11px;
        font-weight: 800;
        letter-spacing: 0;
        box-sizing: border-box;
      }
      .message-row.user .message-avatar {
        background: #ff4b5c;
      }
      .message-row.assistant .message-avatar {
        background: #ffab2d;
      }
      .message-body {
        min-height: 32px;
        padding: 8px 0 10px;
        border-bottom: 1px solid rgba(255, 255, 255, 0.08);
        color: #f6f8fb;
        font-size: 15px;
        line-height: 1.65;
        letter-spacing: 0;
        overflow-wrap: anywhere;
      }
      .message-row:last-child .message-body {
        border-bottom-color: transparent;
      }
      [data-testid="stChatMessage"] {
        background: transparent;
        border: 0;
        border-radius: 8px;
        color: #f6f8fb;
      }
      [data-testid="stMarkdownContainer"],
      [data-testid="stMarkdownContainer"] p {
        color: #f6f8fb !important;
      }
      [data-baseweb="modal"],
      [data-baseweb="popover"],
      [data-baseweb="menu"] {
        color: #f6f8fb !important;
      }
      [data-testid="stThemeSwitcher"],
      [data-testid="stMainMenuItem-print"],
      [data-testid="stMainMenuItem-recordScreencast"] {
        display: none !important;
      }
      [data-testid="stMainMenuPopover"] {
        min-width: 180px !important;
      }
      [data-testid="stMainMenuItem-rerun"] [data-testid="stMainMenuItemLabel"],
      [data-testid="stMainMenuItem-clearCache"] [data-testid="stMainMenuItemLabel"] {
        font-size: 0 !important;
        line-height: 0 !important;
      }
      [data-testid="stMainMenuItem-rerun"] [data-testid="stMainMenuItemLabel"]::before {
        content: "重新运行";
        font-size: 14px;
        line-height: 1.4;
      }
      [data-testid="stMainMenuItem-clearCache"] [data-testid="stMainMenuItemLabel"]::before {
        content: "清除缓存";
        font-size: 14px;
        line-height: 1.4;
      }
      [data-baseweb="modal"] > div,
      [data-baseweb="popover"] > div,
      [data-baseweb="menu"] {
        background: #0b0f16 !important;
        border: 1px solid rgba(255, 255, 255, 0.14) !important;
        box-shadow: 0 18px 48px rgba(0, 0, 0, 0.48) !important;
      }
      [role="dialog"] {
        background: #0b0f16 !important;
        color: #f6f8fb !important;
        border: 1px solid rgba(255, 255, 255, 0.14) !important;
        border-radius: 8px !important;
      }
      [role="dialog"] h1,
      [role="dialog"] h2,
      [role="dialog"] h3,
      [role="dialog"] p,
      [role="dialog"] span,
      [role="dialog"] div,
      [data-baseweb="popover"] *,
      [data-baseweb="menu"] * {
        color: #f6f8fb !important;
        -webkit-text-fill-color: #f6f8fb !important;
      }
      [role="dialog"] button,
      [data-baseweb="popover"] button,
      [data-baseweb="menu"] button {
        border-radius: 6px !important;
      }
      [role="dialog"] button:not([kind="primary"]) {
        background: rgba(255, 255, 255, 0.07) !important;
        color: #f6f8fb !important;
        border: 1px solid rgba(255, 255, 255, 0.12) !important;
      }
      [role="dialog"] button[kind="primary"],
      [role="dialog"] button[data-testid="baseButton-primary"] {
        background: rgba(98, 217, 143, 0.18) !important;
        color: #62d98f !important;
        border: 1px solid rgba(98, 217, 143, 0.36) !important;
      }
      [data-testid="stDialog"] [role="dialog"] > div:first-child {
        font-size: 0 !important;
        color: transparent !important;
      }
      [data-testid="stDialog"] [role="dialog"] > div:first-child::before {
        content: "清除缓存";
        color: #f6f8fb;
        font-size: 1.25rem;
        font-weight: 700;
        line-height: 1.4;
      }
      [data-testid="stDialog"] [data-testid="stMarkdownContainer"] p,
      [data-testid="stDialog"] [data-testid="stMarkdownContainer"] strong,
      [data-testid="stDialog"] [data-testid="stMarkdownContainer"] code {
        font-size: 0 !important;
        line-height: 0 !important;
        color: transparent !important;
        -webkit-text-fill-color: transparent !important;
      }
      [data-testid="stDialog"] [data-testid="stMarkdownContainer"] p::before {
        content: "确定要清除应用的函数缓存吗？\\A这会移除使用 @st.cache_data 和 @st.cache_resource 的缓存条目。";
        white-space: pre-line;
        display: block;
        color: #f6f8fb;
        -webkit-text-fill-color: #f6f8fb;
        font-size: 1rem;
        line-height: 1.6;
      }
      [data-testid="stDialog"] [data-testid="stBaseButton-ghost"],
      [data-testid="stDialog"] [data-testid="stBaseButton-secondary"] {
        font-size: 0 !important;
        line-height: 0 !important;
      }
      [data-testid="stDialog"] [data-testid="stBaseButton-ghost"]::before {
        content: "取消";
        font-size: 0.95rem;
        line-height: 1.2;
      }
      [data-testid="stDialog"] [data-testid="stBaseButton-secondary"]::before {
        content: "清除缓存";
        font-size: 0.95rem;
        line-height: 1.2;
      }
      [data-testid="stChatInput"] {
        background: transparent;
        width: 100%;
        max-width: 700px;
        height: 52px !important;
        margin-left: auto;
        margin-right: auto;
      }
      [data-testid="stChatInput"] > div {
        min-height: 52px !important;
        height: 52px !important;
        display: flex !important;
        flex-direction: row !important;
        align-items: center !important;
        gap: 10px !important;
        padding: 8px 10px 8px 16px !important;
        background: rgba(11, 15, 22, 0.98) !important;
        border: 1px solid rgba(255, 255, 255, 0.16) !important;
        border-radius: 8px !important;
        box-shadow: none !important;
      }
      [data-testid="stChatInput"] > div > div:first-child {
        width: 100% !important;
        height: 36px !important;
        display: flex !important;
        flex-direction: row !important;
        align-items: center !important;
        justify-content: space-between !important;
        gap: 8px !important;
      }
      [data-testid="stChatInput"] > div > div:first-child > div:first-child {
        flex: 1 1 auto !important;
        min-width: 0 !important;
        height: 32px !important;
        display: flex !important;
        align-items: center !important;
      }
      [data-testid="stChatInput"] > div > div:first-child > div:last-child {
        flex: 0 0 36px !important;
        width: 36px !important;
        height: 36px !important;
        display: flex !important;
        align-items: center !important;
      }
      [data-testid="stChatInput"] [data-baseweb="textarea"],
      [data-testid="stChatInput"] [data-baseweb="base-input"],
      [data-testid="stChatInput"] [data-baseweb="base-input"] > div {
        min-height: 32px !important;
        height: 32px !important;
        background: #0b0f16 !important;
        color: #f6f8fb !important;
        -webkit-text-fill-color: #f6f8fb !important;
        border-color: rgba(255, 255, 255, 0.18) !important;
        box-shadow: none !important;
      }
      [data-testid="stChatInput"] textarea,
      [data-testid="stChatInput"] textarea:focus,
      [data-testid="stChatInput"] textarea:active {
        background: #0b0f16 !important;
        color: #f6f8fb !important;
        caret-color: #35d3ff !important;
        -webkit-text-fill-color: #f6f8fb !important;
        font-size: 0.98rem !important;
        line-height: 1.45 !important;
        min-height: 32px !important;
        height: 32px !important;
        max-height: 32px !important;
        border: 0 !important;
        box-shadow: none !important;
        outline: none !important;
        resize: none !important;
        overflow: hidden !important;
        white-space: nowrap !important;
      }
      [data-testid="stChatInput"] textarea::placeholder {
        color: rgba(246, 248, 251, 0.58) !important;
        -webkit-text-fill-color: rgba(246, 248, 251, 0.58) !important;
      }
      [data-testid="stChatInput"] button {
        width: 36px !important;
        height: 36px !important;
        flex: 0 0 36px !important;
        background: rgba(53, 211, 255, 0.16) !important;
        color: #f6f8fb !important;
        border-radius: 6px !important;
      }
      [data-testid="stChatInput"] button svg {
        fill: #f6f8fb !important;
        stroke: #f6f8fb !important;
      }
      @media (max-width: 900px) {
        html,
        body,
        .stApp,
        [data-testid="stAppViewContainer"],
        [data-testid="stAppViewContainer"] > .main {
          height: auto;
          overflow: auto;
        }
        .block-container {
          height: auto;
          padding: 16px;
          overflow: visible;
        }
        .block-container div[data-testid="stHorizontalBlock"] {
          height: auto;
          gap: 16px;
        }
        .block-container div[data-testid="stHorizontalBlock"] > div[data-testid="stColumn"] {
          flex: 1 1 100% !important;
          width: 100% !important;
          max-width: 100% !important;
        }
        .model-status {
          top: 10px;
          right: 12px;
        }
        .st-key-globe_panel,
        .st-key-chat_panel {
          height: auto !important;
          min-height: auto !important;
          padding: 16px 0;
          border: 0;
          background: transparent;
        }
      }
    </style>
    """,
    unsafe_allow_html=True,
)
st.markdown(
    f"""
    <div class="model-status {model_status_class}">
      <span class="dot"></span>
      <span>模型状态</span>
      <strong>{model_status_text}</strong>
    </div>
    """,
    unsafe_allow_html=True,
)

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
if "pending_response" not in st.session_state:
    st.session_state.pending_response = False

globe_column, chat_column = st.columns([1.05, 0.95], gap="large", vertical_alignment="top")

with globe_column:
    with st.container(key="globe_panel"):
        render_globe(
            st.session_state.last_position,
            st.session_state.last_satellite_name,
            trajectory=st.session_state.last_trajectory,
            height=900,
        )
        if st.session_state.last_position_error:
            st.warning(st.session_state.last_position_error)

with chat_column:
    with st.container(key="chat_panel"):
        assistant_placeholder = None
        if st.session_state.messages:
            with st.container(height=560, key="chat_scroll", border=False, autoscroll=True):
                for message in st.session_state.messages:
                    _render_chat_message(message["role"], message["content"])
                if st.session_state.pending_response:
                    assistant_placeholder = st.empty()

        if prompt := st.chat_input("请输入任务指令", disabled=st.session_state.pending_response):
            st.session_state.messages.append({"role": "user", "content": prompt})
            st.session_state.pending_response = True
            st.rerun()

        if st.session_state.pending_response and assistant_placeholder is not None:
            _process_pending_response(assistant_placeholder)
