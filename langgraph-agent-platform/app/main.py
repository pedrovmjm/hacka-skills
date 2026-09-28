import os
import re
import sqlite3
import uuid
from pathlib import Path
from typing import Any, TypedDict

from fastapi import FastAPI, HTTPException
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt
from pydantic import BaseModel

from . import database


class AgentState(TypedDict, total=False):
    conversation_id: str
    user_id: str
    agent_id: str
    message: str
    messages: list[dict[str, str]]
    status: str
    pending_action: dict[str, Any] | None
    result: str | None


class AgentInput(BaseModel):
    id: str
    owner_id: str
    name: str
    system_prompt: str
    tools: list[str]


class ConversationInput(BaseModel):
    user_id: str
    agent_id: str
    message: str
    conversation_id: str | None = None


class ApprovalInput(BaseModel):
    user_id: str
    approved: bool


def lookup_policy(topic):
    policies = {
        "travel": "Viagens precisam ser registradas com sete dias de antecedencia.",
        "security": "Nao compartilhe tokens ou dados pessoais em mensagens.",
    }
    return policies.get(topic, "Politica nao encontrada.")


def send_notification(recipient, text):
    return f"Notificacao enviada para {recipient}: {text}"


def read_file(path):
    return Path(path).read_text(encoding="utf-8")


TOOLBOX = {
    "lookup_policy": lookup_policy,
    "send_notification": send_notification,
    "read_file": read_file,
}
ACTIVE_AGENT = {}


def fake_model(text, agent):
    value = text.strip()
    lowered = value.lower()
    if lowered.startswith("policy ") and "lookup_policy" in agent["tools"]:
        topic = value.split(" ", 1)[1]
        return {"result": lookup_policy(topic), "pending_action": None}
    if lowered.startswith("read ") and "read_file" in agent["tools"]:
        path = value.split(" ", 1)[1]
        return {"result": read_file(path), "pending_action": None}
    if lowered.startswith("send ") and "send_notification" in agent["tools"]:
        match = re.match(r"send\s+([^:]+):\s*(.+)", value, re.IGNORECASE)
        if not match:
            return {"result": "Use: send destinatario: mensagem", "pending_action": None}
        return {
            "result": None,
            "pending_action": {
                "tool": "send_notification",
                "recipient": match.group(1),
                "text": match.group(2),
            },
        }
    return {
        "result": f"[{agent['name']}] modelo-simulado: {value}",
        "pending_action": None,
    }


def plan_message(state):
    agent = ACTIVE_AGENT
    decision = fake_model(state["message"], agent)
    messages = list(state.get("messages", []))
    messages.append({"role": "user", "content": state["message"]})
    if decision["pending_action"]:
        messages.append({"role": "assistant", "content": "Acao aguardando aprovacao."})
        return {
            "messages": messages,
            "pending_action": decision["pending_action"],
            "status": "pending_approval",
            "result": None,
        }
    messages.append({"role": "assistant", "content": decision["result"]})
    return {
        "messages": messages,
        "pending_action": None,
        "status": "completed",
        "result": decision["result"],
    }


def route_after_plan(state):
    return "approval" if state.get("pending_action") else END


def wait_for_approval(state):
    decision = interrupt(
        {
            "conversation_id": state["conversation_id"],
            "action": state["pending_action"],
            "question": "Autorizar a execucao desta ferramenta?",
        }
    )
    messages = list(state.get("messages", []))
    if decision.get("approved"):
        action = state["pending_action"]
        output = TOOLBOX[action["tool"]](action["recipient"], action["text"])
        messages.append({"role": "tool", "content": output})
        return {
            "messages": messages,
            "pending_action": None,
            "status": "completed",
            "result": output,
        }
    messages.append({"role": "tool", "content": "Acao recusada."})
    return {
        "messages": messages,
        "pending_action": None,
        "status": "rejected",
        "result": "Acao recusada.",
    }


checkpoint_path = Path(os.getenv("AGENT_CHECKPOINT_PATH", "data/checkpoints.db"))
checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
checkpoint_connection = sqlite3.connect(checkpoint_path, check_same_thread=False)
checkpoint = SqliteSaver(checkpoint_connection)
builder = StateGraph(AgentState)
builder.add_node("plan", plan_message)
builder.add_node("approval", wait_for_approval)
builder.add_edge(START, "plan")
builder.add_conditional_edges("plan", route_after_plan, ["approval", END])
builder.add_edge("approval", END)
graph = builder.compile(checkpointer=checkpoint)

app = FastAPI(title="Legacy Agent Platform", version="0.1.0")


def public_conversation(item):
    return {
        "id": item["id"],
        "user_id": item["user_id"],
        "agent_id": item["agent_id"],
        "messages": item["messages"],
        "status": item["status"],
        "pending_action": item["pending_action"],
        "result": item["result"],
        "created_at": item["created_at"],
        "updated_at": item["updated_at"],
    }


@app.get("/health")
async def health():
    return {"status": "ok", "model": "simulated"}


@app.get("/api/agents")
async def agents():
    return database.list_agents()


@app.put("/api/agents/{agent_id}")
async def put_agent(agent_id: str, body: AgentInput):
    data = body.model_dump()
    data["id"] = agent_id
    return database.save_agent(data)


@app.post("/api/conversations")
async def run_conversation(body: ConversationInput):
    global ACTIVE_AGENT
    try:
        agent = database.get_agent(body.agent_id)
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")
        ACTIVE_AGENT = agent
        conversation_id = body.conversation_id or str(uuid.uuid4())
        previous = database.get_conversation(conversation_id)
        messages = previous["messages"] if previous else []
        state = {
            "conversation_id": conversation_id,
            "user_id": body.user_id,
            "agent_id": body.agent_id,
            "message": body.message,
            "messages": messages,
            "status": "running",
            "pending_action": None,
            "result": None,
        }
        print("agent-run", body.user_id, body.message)
        output = graph.invoke(
            state,
            config={"configurable": {"thread_id": conversation_id}},
        )
        saved = database.save_conversation({**output, "id": conversation_id})
        return public_conversation(saved)
    except HTTPException:
        raise
    except Exception as error:
        raise HTTPException(status_code=500, detail=str(error)) from error


@app.get("/api/conversations/{conversation_id}")
async def get_conversation(conversation_id: str):
    item = database.get_conversation(conversation_id)
    if not item:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return public_conversation(item)


@app.post("/api/approvals/{conversation_id}")
async def approve(conversation_id: str, body: ApprovalInput):
    item = database.get_conversation(conversation_id)
    if not item:
        raise HTTPException(status_code=404, detail="Conversation not found")
    if item["status"] != "pending_approval":
        raise HTTPException(status_code=409, detail="Conversation is not waiting for approval")
    try:
        output = graph.invoke(
            Command(resume={"approved": body.approved, "reviewer": body.user_id}),
            config={"configurable": {"thread_id": conversation_id}},
        )
        merged = {**item, **output}
        saved = database.save_conversation(merged)
        return public_conversation(saved)
    except Exception as error:
        raise HTTPException(status_code=500, detail=str(error)) from error
