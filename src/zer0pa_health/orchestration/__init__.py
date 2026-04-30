"""L6 orchestration core (PRD section 5).

Defines a LangGraph-shaped state graph, a Prefect-shaped flow interface, and
a Parsl-shaped dispatch interface — all as plain Python protocols/classes that
real LangGraph/Prefect/Parsl bind into. Stays import-light on the originating
Mac (no LangGraph/Prefect/Parsl required for the CPU-side build).
"""

from zer0pa_health.orchestration.state_graph import (
    StateGraph,
    StateNode,
    StateTransition,
    Decision,
    BackEdgeQueue,
)
from zer0pa_health.orchestration.flow import Flow, FlowResult, FlowStep
from zer0pa_health.orchestration.dispatch import DispatchInterface, NoOpDispatcher
from zer0pa_health.orchestration.runpod_dispatcher import RunpodSimDispatcher
from zer0pa_health.orchestration.router import L6Router

__all__ = [
    "StateGraph",
    "StateNode",
    "StateTransition",
    "Decision",
    "BackEdgeQueue",
    "Flow",
    "FlowResult",
    "FlowStep",
    "DispatchInterface",
    "NoOpDispatcher",
    "RunpodSimDispatcher",
    "L6Router",
]
