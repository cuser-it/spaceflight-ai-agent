from __future__ import annotations

from src import agent as agent_module


def test_should_route_position_question_to_tool():
    state = {"messages": [("user", "国际空间站现在在哪里？")]}

    assert agent_module.should_use_tool(state) == "get_tle"


def test_should_route_general_question_to_response():
    state = {"messages": [("user", "你能做什么？")]}

    assert agent_module.should_use_tool(state) == "respond"


def test_agent_position_reply_contains_coordinates(monkeypatch):
    monkeypatch.setattr(agent_module, "get_latest_tle", lambda satellite_name: "fake tle")
    monkeypatch.setattr(
        agent_module,
        "compute_position_from_tle",
        lambda tle, at_time=None: {
            "latitude": 31.23,
            "longitude": 121.47,
            "altitude_km": 420.5,
            "timestamp_utc": "2024-01-01T00:00:00+00:00",
        },
    )

    test_agent = agent_module.build_agent()
    final_state = test_agent.invoke({"messages": [("user", "国际空间站位置")]})
    reply = final_state["messages"][-1][1]

    assert "纬度 31.23" in reply
    assert "经度 121.47" in reply
    assert "420.5 km" in reply
