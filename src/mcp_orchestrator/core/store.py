"""SQLite state store for workflows, runs, and conversations."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from mcp_orchestrator.core.models import (
    Workflow, WorkflowMetadata, AgentNode, AgentConfig, Edge,
    Run, RunStatus, Conversation, Message
)


class StateStore:
    """SQLite-backed state store for the orchestrator."""

    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self._conn: sqlite3.Connection | None = None

    def init_db(self) -> None:
        """Initialize the database schema."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self.db_path))
        self._conn.row_factory = sqlite3.Row

        cursor = self._conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS workflows (
                id TEXT PRIMARY KEY,
                version TEXT NOT NULL,
                metadata_json TEXT NOT NULL,
                nodes_json TEXT NOT NULL,
                edges_json TEXT NOT NULL,
                created_at REAL NOT NULL,
                updated_at REAL NOT NULL
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS runs (
                id TEXT PRIMARY KEY,
                workflow_id TEXT NOT NULL,
                status TEXT NOT NULL,
                input_message TEXT NOT NULL,
                current_node TEXT,
                context_json TEXT NOT NULL,
                created_at REAL NOT NULL,
                updated_at REAL NOT NULL,
                completed_at REAL,
                error_message TEXT,
                FOREIGN KEY (workflow_id) REFERENCES workflows (id)
            )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_runs_workflow_id ON runs (workflow_id)")

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                id TEXT PRIMARY KEY,
                provider TEXT NOT NULL,
                model TEXT NOT NULL,
                messages_json TEXT NOT NULL,
                created_at REAL NOT NULL,
                updated_at REAL NOT NULL
            )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_conversations_provider_model ON conversations (provider, model)")

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                name TEXT,
                tool_calls_json TEXT,
                tool_call_id TEXT,
                created_at REAL NOT NULL,
                FOREIGN KEY (conversation_id) REFERENCES conversations (id)
            )
        """)

        self._conn.commit()

    def _ensure_connected(self) -> None:
        if self._conn is None:
            self.init_db()

    def save_workflow(self, workflow: Workflow) -> None:
        self._ensure_connected()
        cursor = self._conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO workflows (id, version, metadata_json, nodes_json, edges_json, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            workflow.id,
            workflow.version,
            json.dumps({
                "name": workflow.metadata.name,
                "description": workflow.metadata.description,
                "tags": workflow.metadata.tags,
                "created_at": workflow.metadata.created_at,
                "updated_at": workflow.metadata.updated_at,
            }),
            json.dumps([
                {
                    "id": n.id,
                    "type": n.type,
                    "label": n.label,
                    "config": {
                        "provider": n.config.provider,
                        "model": n.config.model,
                        "system_prompt": n.config.system_prompt,
                        "temperature": n.config.temperature,
                        "max_tokens": n.config.max_tokens,
                        "tools": n.config.tools,
                        "builtin_tools": n.config.builtin_tools,
                        "fallback_model": n.config.fallback_model,
                        "conversation_id": n.config.conversation_id,
                        "share_conversation": n.config.share_conversation,
                    },
                    "position": n.position,
                }
                for n in workflow.nodes
            ]),
            json.dumps([
                {
                    "id": e.id,
                    "source": e.source,
                    "target": e.target,
                    "source_handle": e.source_handle,
                    "target_handle": e.target_handle,
                    "type": e.type,
                }
                for e in workflow.edges
            ]),
            workflow.metadata.created_at,
            workflow.metadata.updated_at,
        ))
        self._conn.commit()

    def load_workflow(self, workflow_id: str) -> Workflow | None:
        self._ensure_connected()
        cursor = self._conn.cursor()
        cursor.execute("SELECT * FROM workflows WHERE id = ?", (workflow_id,))
        row = cursor.fetchone()
        if row is None:
            return None

        metadata = WorkflowMetadata(
            name=json.loads(row["metadata_json"])["name"],
            description=json.loads(row["metadata_json"]).get("description", ""),
            tags=json.loads(row["metadata_json"]).get("tags", []),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )
        nodes = []
        for n in json.loads(row["nodes_json"]):
            config = AgentConfig(
                provider=n["config"]["provider"],
                model=n["config"]["model"],
                system_prompt=n["config"].get("system_prompt", ""),
                temperature=n["config"].get("temperature", 0.7),
                max_tokens=n["config"].get("max_tokens", 4096),
                tools=n["config"].get("tools", []),
                builtin_tools=n["config"].get("builtin_tools", []),
                fallback_model=n["config"].get("fallback_model"),
                conversation_id=n["config"].get("conversation_id"),
                share_conversation=n["config"].get("share_conversation", False),
            )
            nodes.append(AgentNode(
                id=n["id"],
                type=n.get("type", "agent"),
                label=n.get("label", ""),
                config=config,
                position=n.get("position", {"x": 0, "y": 0}),
            ))
        edges = []
        for e in json.loads(row["edges_json"]):
            edges.append(Edge(
                id=e["id"],
                source=e["source"],
                target=e["target"],
                source_handle=e.get("source_handle"),
                target_handle=e.get("target_handle"),
                type=e.get("type", "default"),
            ))
        return Workflow(
            id=row["id"],
            version=row["version"],
            metadata=metadata,
            nodes=nodes,
            edges=edges,
        )

    def list_workflows(self) -> list[Workflow]:
        self._ensure_connected()
        cursor = self._conn.cursor()
        cursor.execute("SELECT * FROM workflows ORDER BY updated_at DESC")
        rows = cursor.fetchall()
        return [self.load_workflow(row["id"]) for row in rows]

    def delete_workflow(self, workflow_id: str) -> None:
        self._ensure_connected()
        cursor = self._conn.cursor()
        cursor.execute("DELETE FROM workflows WHERE id = ?", (workflow_id,))
        self._conn.commit()

    def save_run(self, run: Run) -> None:
        self._ensure_connected()
        cursor = self._conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO runs (id, workflow_id, status, input_message, current_node, context_json, created_at, updated_at, completed_at, error_message)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            run.id,
            run.workflow_id,
            run.status.value,
            run.input_message,
            run.current_node,
            json.dumps(run.context),
            run.created_at,
            run.updated_at,
            run.completed_at,
            run.error_message,
        ))
        self._conn.commit()

    def load_run(self, run_id: str) -> Run | None:
        self._ensure_connected()
        cursor = self._conn.cursor()
        cursor.execute("SELECT * FROM runs WHERE id = ?", (run_id,))
        row = cursor.fetchone()
        if row is None:
            return None
        return Run(
            id=row["id"],
            workflow_id=row["workflow_id"],
            status=RunStatus(row["status"]),
            input_message=row["input_message"],
            current_node=row["current_node"],
            context=json.loads(row["context_json"]),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            completed_at=row["completed_at"],
            error_message=row["error_message"],
        )

    def update_run_status(self, run_id: str, status: RunStatus, error_message: str | None = None) -> None:
        self._ensure_connected()
        cursor = self._conn.cursor()
        import time
        now = time.time()
        if status in (RunStatus.COMPLETED, RunStatus.FAILED, RunStatus.CANCELLED):
            cursor.execute("""
                UPDATE runs SET status = ?, updated_at = ?, completed_at = ?, error_message = ? WHERE id = ?
            """, (status.value, now, now, error_message, run_id))
        else:
            cursor.execute("""
                UPDATE runs SET status = ?, updated_at = ?, error_message = ? WHERE id = ?
            """, (status.value, now, error_message, run_id))
        self._conn.commit()

    def save_conversation(self, conversation: Conversation) -> None:
        self._ensure_connected()
        cursor = self._conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO conversations (id, provider, model, messages_json, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            conversation.id,
            conversation.provider,
            conversation.model,
            json.dumps([
                {
                    "role": m.role,
                    "content": m.content,
                    "name": m.name,
                    "tool_calls": m.tool_calls,
                    "tool_call_id": m.tool_call_id,
                }
                for m in conversation.messages
            ]),
            conversation.created_at,
            conversation.updated_at,
        ))

        cursor.execute("DELETE FROM messages WHERE conversation_id = ?", (conversation.id,))
        for msg in conversation.messages:
            cursor.execute("""
                INSERT INTO messages (conversation_id, role, content, name, tool_calls_json, tool_call_id, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                conversation.id,
                msg.role,
                msg.content,
                msg.name,
                json.dumps(msg.tool_calls) if msg.tool_calls else None,
                msg.tool_call_id,
                conversation.updated_at,
            ))

        self._conn.commit()

    def load_conversation(self, conversation_id: str) -> Conversation | None:
        self._ensure_connected()
        cursor = self._conn.cursor()
        cursor.execute("SELECT * FROM conversations WHERE id = ?", (conversation_id,))
        row = cursor.fetchone()
        if row is None:
            return None
        return Conversation(
            id=row["id"],
            provider=row["provider"],
            model=row["model"],
            messages=[
                Message(
                    role=m["role"],
                    content=m["content"],
                    name=m.get("name"),
                    tool_calls=m.get("tool_calls"),
                    tool_call_id=m.get("tool_call_id"),
                )
                for m in json.loads(row["messages_json"])
            ],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    def get_conversation_history(self, provider: str, model: str) -> list[Conversation]:
        self._ensure_connected()
        cursor = self._conn.cursor()
        cursor.execute("""
            SELECT * FROM conversations WHERE provider = ? AND model = ? ORDER BY updated_at DESC
        """, (provider, model))
        rows = cursor.fetchall()
        return [
            Conversation(
                id=row["id"],
                provider=row["provider"],
                model=row["model"],
                messages=[
                    Message(
                        role=m["role"],
                        content=m["content"],
                        name=m.get("name"),
                        tool_calls=m.get("tool_calls"),
                        tool_call_id=m.get("tool_call_id"),
                    )
                    for m in json.loads(row["messages_json"])
                ],
                created_at=row["created_at"],
                updated_at=row["updated_at"],
            )
            for row in rows
        ]

    def close(self) -> None:
        if self._conn:
            self._conn.close()
            self._conn = None

    def __enter__(self) -> StateStore:
        self.init_db()
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.close()