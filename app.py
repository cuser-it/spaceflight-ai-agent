from __future__ import annotations

import streamlit as st

from src.agent import agent


def _latest_assistant_message(messages):
    for role, content in reversed(list(messages)):
        if role == "assistant":
            return content
    return "没有生成回复。"


st.set_page_config(page_title="航天任务 AI 助手", layout="centered")
st.title("卫星任务 AI 助手")
st.caption("示例：国际空间站现在在哪里？")

if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if prompt := st.chat_input("请输入任务指令"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    history = [(message["role"], message["content"]) for message in st.session_state.messages]

    try:
        final_state = agent.invoke({"messages": history})
        reply = _latest_assistant_message(final_state.get("messages", ()))
    except Exception as exc:  # pragma: no cover - UI guardrail
        reply = f"任务执行失败：{exc}"

    with st.chat_message("assistant"):
        st.markdown(reply)
    st.session_state.messages.append({"role": "assistant", "content": reply})
