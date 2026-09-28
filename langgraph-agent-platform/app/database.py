import json
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path


DB_PATH = Path(os.getenv("AGENT_DB_PATH", "data/agents.db"))
DB_PATH.parent.mkdir(parents=True, exist_ok=True)
connection = sqlite3.connect(DB_PATH, check_same_thread=False)
connection.row_factory = sqlite3.Row


def now():
    return datetime.now(timezone.utc).isoformat()


def initialize_database():
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS agents (
            id TEXT PRIMARY KEY,
            owner_id TEXT NOT NULL,
            name TEXT NOT NULL,
            system_prompt TEXT NOT NULL,
            tools_json TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS conversations (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            agent_id TEXT NOT NULL,
            messages_json TEXT NOT NULL,
            status TEXT NOT NULL,
            pending_action_json TEXT,
            result TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        """
    )
    connection.execute(
        """
        INSERT OR IGNORE INTO agents
            (id, owner_id, name, system_prompt, tools_json, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            "assistant-demo",
            "team-demo",
            "Assistente do time",
            "Responda de forma curta e ajude o time de demonstracao.",
            json.dumps(["lookup_policy", "send_notification", "read_file"]),
            now(),
        ),
    )
    connection.commit()


def reset_database():
    connection.execute("DELETE FROM conversations")
    connection.execute("DELETE FROM agents")
    connection.commit()
    initialize_database()


def save_agent(agent):
    connection.execute(
        """
        INSERT OR REPLACE INTO agents
            (id, owner_id, name, system_prompt, tools_json, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            agent["id"],
            agent["owner_id"],
            agent["name"],
            agent["system_prompt"],
            json.dumps(agent["tools"]),
            now(),
        ),
    )
    connection.commit()
    return get_agent(agent["id"])


def get_agent(agent_id):
    row = connection.execute("SELECT * FROM agents WHERE id = ?", (agent_id,)).fetchone()
    if not row:
        return None
    item = dict(row)
    item["tools"] = json.loads(item.pop("tools_json"))
    return item


def list_agents():
    rows = connection.execute("SELECT * FROM agents ORDER BY created_at").fetchall()
    result = []
    for row in rows:
        item = dict(row)
        item["tools"] = json.loads(item.pop("tools_json"))
        result.append(item)
    return result


def save_conversation(item):
    old = get_conversation(item["id"])
    created_at = old["created_at"] if old else now()
    connection.execute(
        """
        INSERT OR REPLACE INTO conversations
            (id, user_id, agent_id, messages_json, status,
             pending_action_json, result, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            item["id"],
            item["user_id"],
            item["agent_id"],
            json.dumps(item.get("messages", [])),
            item["status"],
            json.dumps(item.get("pending_action")) if item.get("pending_action") else None,
            item.get("result"),
            created_at,
            now(),
        ),
    )
    connection.commit()
    return get_conversation(item["id"])


def get_conversation(conversation_id):
    row = connection.execute(
        "SELECT * FROM conversations WHERE id = ?", (conversation_id,)
    ).fetchone()
    if not row:
        return None
    item = dict(row)
    item["messages"] = json.loads(item.pop("messages_json"))
    raw_pending = item.pop("pending_action_json")
    item["pending_action"] = json.loads(raw_pending) if raw_pending else None
    return item


initialize_database()

