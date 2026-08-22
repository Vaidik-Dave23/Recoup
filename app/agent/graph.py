"""LangGraph definitions for first-pass and retry recovery runs."""

from __future__ import annotations

from functools import partial
from uuid import UUID

from langgraph.graph import END, StateGraph
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.nodes import RecoveryAgentNodes
from app.agent.state import RecoveryState


def _route_after_strategize(state: RecoveryState) -> str:
    return state.get("route", "escalate")


def _build(db: AsyncSession, merchant_id: UUID, *, include_triage: bool):
    nodes = RecoveryAgentNodes(db, merchant_id)
    graph = StateGraph(RecoveryState)
    graph.add_node("strategize", nodes.strategize)
    graph.add_node("generate_content", nodes.generate_content)
    graph.add_node("execute", nodes.execute)
    graph.add_node("escalate", partial(nodes.escalate, trigger="low_confidence"))
    if include_triage:
        graph.add_node("triage", nodes.triage)
        graph.set_entry_point("triage")
        graph.add_edge("triage", "strategize")
    else:
        graph.set_entry_point("strategize")
    graph.add_conditional_edges(
        "strategize", _route_after_strategize,
        {"generate_content": "generate_content", "escalate": "escalate"},
    )
    graph.add_edge("generate_content", "execute")
    graph.add_edge("execute", END)
    graph.add_edge("escalate", END)
    return graph.compile()


def build_first_pass_graph(db: AsyncSession, merchant_id: UUID):
    return _build(db, merchant_id, include_triage=True)


def build_retry_graph(db: AsyncSession, merchant_id: UUID):
    return _build(db, merchant_id, include_triage=False)
