from __future__ import annotations

import operator
from typing import Annotated, Any, Sequence, TypedDict

Message = tuple[str, str]


class AgentState(TypedDict, total=False):
    """LangGraph state shared between routing, tool and response nodes."""

    messages: Annotated[Sequence[Message], operator.add]
    next_action: str
    satellite_name: str
    tle: str
    position: dict[str, Any]
