from __future__ import annotations

import os
from datetime import datetime, timedelta
from typing import Any, Iterable

from .state import AgentState, Message
from .tools import compute_position_from_tle, extract_satellite_name, get_latest_tle
from .utils import ensure_utc, offset_datetime, parse_prediction_offset_minutes

try:
    from langgraph.graph import END, StateGraph
except ImportError:  # Allows tests to run before optional deps are installed.
    END = "__end__"
    StateGraph = None

ORBIT_KEYWORDS = (
    "位置",
    "在哪里",
    "在哪",
    "坐标",
    "经纬度",
    "高度",
    "轨道",
    "预测",
    "position",
    "location",
    "where",
    "coordinate",
    "altitude",
    "orbit",
)


def should_use_tool(state: AgentState) -> str:
    """Route user input to orbit tools or general response."""

    query = _latest_user_message(state.get("messages", ())).lower()
    if any(keyword in query for keyword in ORBIT_KEYWORDS):
        return "get_tle"
    if parse_prediction_offset_minutes(query) is not None:
        return "get_tle"
    return "respond"


def classify_node(state: AgentState) -> AgentState:
    return {"next_action": should_use_tool(state)}


def route_from_state(state: AgentState) -> str:
    return state.get("next_action", "respond")


def get_tle_node(state: AgentState) -> AgentState:
    """Fetch TLE and compute the current or requested future position."""

    query = _latest_user_message(state.get("messages", ()))
    satellite_name = extract_satellite_name(query)
    offset_minutes = parse_prediction_offset_minutes(query)
    base_time = ensure_utc()
    target_time = offset_datetime(offset_minutes, base_time=base_time)

    tle = get_latest_tle(satellite_name)
    position = compute_position_from_tle(tle, at_time=target_time)
    trajectory = _build_prediction_trajectory(tle, base_time, offset_minutes)
    response = _format_position_response(satellite_name, position, offset_minutes)
    return {
        "satellite_name": satellite_name,
        "tle": tle,
        "position": position,
        "trajectory": trajectory,
        "messages": [("assistant", response)],
    }


def respond_node(state: AgentState) -> AgentState:
    """Handle general conversation with DeepSeek if configured, otherwise locally."""

    query = _latest_user_message(state.get("messages", ()))
    response = _invoke_llm_or_fallback(state.get("messages", ()), query)
    return {"messages": [("assistant", response)]}


def stream_llm_or_fallback(messages: Iterable[Message], query: str) -> Iterable[str]:
    """Stream a general LLM response for UI use."""

    _load_dotenv_if_available()
    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        yield (
            "我是航天任务 AI 助手。你可以问我“国际空间站现在在哪里？”"
            "这类卫星位置问题；配置 DEEPSEEK_API_KEY 后，我也可以处理更开放的任务对话。"
        )
        return

    try:
        from langchain_openai import ChatOpenAI
    except ImportError:
        yield "ERROR: 未安装 langchain-openai，请先运行 pip install -r requirements.txt"
        return

    llm = ChatOpenAI(
        model="deepseek-chat",
        temperature=0,
        openai_api_key=api_key,
        base_url="https://api.deepseek.com/v1",
    )

    yielded = False
    for chunk in llm.stream(_build_chat_messages(messages)):
        content = getattr(chunk, "content", "")
        if isinstance(content, str) and content:
            yielded = True
            yield content

    if not yielded:
        yield ""


def build_agent() -> Any:
    """Build a LangGraph agent, with a small local fallback for missing deps."""

    if StateGraph is None:
        return SimpleSatelliteAgent()

    workflow = StateGraph(AgentState)
    workflow.add_node("classify", classify_node)
    workflow.add_node("get_tle", get_tle_node)
    workflow.add_node("respond", respond_node)
    workflow.set_entry_point("classify")
    workflow.add_conditional_edges(
        "classify",
        route_from_state,
        {
            "get_tle": "get_tle",
            "respond": "respond",
        },
    )
    workflow.add_edge("get_tle", END)
    workflow.add_edge("respond", END)
    return workflow.compile()


class SimpleSatelliteAgent:
    """Minimal invoke/stream-compatible fallback used when LangGraph is absent."""

    def invoke(self, inputs: AgentState) -> AgentState:
        state: AgentState = {"messages": list(inputs.get("messages", ()))}
        state.update(classify_node(state))
        next_action = route_from_state(state)
        update = get_tle_node(state) if next_action == "get_tle" else respond_node(state)
        return _merge_state(state, update)

    def stream(self, inputs: AgentState) -> Iterable[AgentState]:
        yield self.invoke(inputs)


def run_agent(prompt: str, history: list[Message] | None = None) -> str:
    """Convenience helper for tests and Streamlit."""

    messages = list(history or [])
    messages.append(("user", prompt))
    final_state = agent.invoke({"messages": messages})
    return _latest_assistant_message(final_state.get("messages", ()))


def _invoke_llm_or_fallback(messages: Iterable[Message], query: str) -> str:
    _load_dotenv_if_available()
    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        return (
            "我是航天任务 AI 助手。你可以问我“国际空间站现在在哪里？”"
            "这类卫星位置问题；配置 DEEPSEEK_API_KEY 后，我也可以处理更开放的任务对话。"
        )

    try:
        from langchain_openai import ChatOpenAI
    except ImportError:
        return "ERROR: 未安装 langchain-openai，请先运行 pip install -r requirements.txt"

    llm = ChatOpenAI(
        model="deepseek-chat",
        temperature=0,
        openai_api_key=api_key,
        base_url="https://api.deepseek.com/v1",
    )
    response = llm.invoke(_build_chat_messages(messages))
    return getattr(response, "content", str(response))


def _build_chat_messages(messages: Iterable[Message]) -> list[Message]:
    chat_messages: list[Message] = [
        (
            "system",
            "你是航天任务 AI 助手。回答要简洁、准确，并优先使用工具结果处理轨道位置问题。",
        )
    ]
    chat_messages.extend(messages)
    return chat_messages


def _format_position_response(
    satellite_name: str,
    position: dict[str, Any],
    offset_minutes: int | None,
) -> str:
    if error := position.get("error"):
        return f"{satellite_name} 位置计算失败：{error}"

    time_label = "当前" if not offset_minutes else f"{offset_minutes} 分钟后"
    return (
        f"{satellite_name} {time_label}估算位置："
        f"纬度 {position['latitude']:.2f}°，"
        f"经度 {position['longitude']:.2f}°，"
        f"高度 {position['altitude_km']:.1f} km。"
        f"\n\n计算时间 UTC：{position['timestamp_utc']}"
    )


def _build_prediction_trajectory(
    tle: str,
    base_time: datetime,
    offset_minutes: int | None,
) -> list[dict[str, Any]]:
    if not offset_minutes or offset_minutes <= 0:
        return []

    sample_count = min(max(int(offset_minutes // 2) + 1, 8), 61)
    if sample_count < 2:
        sample_count = 2

    step_minutes = offset_minutes / (sample_count - 1)
    samples: list[dict[str, Any]] = []
    for index in range(sample_count):
        sample_time = base_time + timedelta(minutes=step_minutes * index)
        position = compute_position_from_tle(tle, at_time=sample_time)
        if position.get("error"):
            return []
        samples.append(
            {
                "latitude": position["latitude"],
                "longitude": position["longitude"],
                "altitude_km": position["altitude_km"],
                "timestamp_utc": position["timestamp_utc"],
            }
        )
    return samples


def _latest_user_message(messages: Iterable[Message]) -> str:
    for role, content in reversed(list(messages)):
        if role == "user":
            return content
    return ""


def _latest_assistant_message(messages: Iterable[Message]) -> str:
    for role, content in reversed(list(messages)):
        if role == "assistant":
            return content
    return ""


def _merge_state(state: AgentState, update: AgentState) -> AgentState:
    merged = dict(state)
    if "messages" in update:
        merged["messages"] = list(state.get("messages", ())) + list(update["messages"])
    for key, value in update.items():
        if key != "messages":
            merged[key] = value
    return merged


def _load_dotenv_if_available() -> None:
    try:
        from dotenv import load_dotenv
    except ImportError:
        return
    load_dotenv()


agent = build_agent()
