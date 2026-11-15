"""Tests for State Store."""

import pytest
from pathlib import Path


class TestStateStore:
    """Tests for StateStore."""

    def test_store_save_load_workflow(self, tmp_path):
        """Test saving and loading a workflow."""
        from mcp_orchestrator.core.store import StateStore
        from mcp_orchestrator.core.models import Workflow, WorkflowMetadata

        store = StateStore(tmp_path / "test.db")
        store.init_db()
        wf = Workflow(
            id="test",
            version="1.0",
            metadata=WorkflowMetadata(name="Test Workflow", description="Test"),
            nodes=[],
            edges=[]
        )
        store.save_workflow(wf)
        loaded = store.load_workflow("test")
        assert loaded.id == "test"
        assert loaded.metadata.name == "Test Workflow"
        assert loaded.version == "1.0"

    def test_store_list_workflows(self, tmp_path):
        """Test listing workflows."""
        from mcp_orchestrator.core.store import StateStore
        from mcp_orchestrator.core.models import Workflow, WorkflowMetadata

        store = StateStore(tmp_path / "test.db")
        store.init_db()

        wf1 = Workflow(id="wf1", version="1.0", metadata=WorkflowMetadata(name="Workflow 1"), nodes=[], edges=[])
        wf2 = Workflow(id="wf2", version="1.0", metadata=WorkflowMetadata(name="Workflow 2"), nodes=[], edges=[])
        store.save_workflow(wf1)
        store.save_workflow(wf2)

        workflows = store.list_workflows()
        assert len(workflows) == 2
        ids = {w.id for w in workflows}
        assert ids == {"wf1", "wf2"}

    def test_store_save_load_run(self, tmp_path):
        """Test saving and loading a run."""
        from mcp_orchestrator.core.store import StateStore
        from mcp_orchestrator.core.models import Run, RunStatus

        store = StateStore(tmp_path / "test.db")
        store.init_db()

        run = Run(
            id="run1",
            workflow_id="test",
            status=RunStatus.RUNNING,
            input_message="Hello",
            current_node=None,
            context={},
            created_at=0,
            updated_at=0
        )
        store.save_run(run)
        loaded = store.load_run("run1")
        assert loaded.id == "run1"
        assert loaded.workflow_id == "test"
        assert loaded.status == RunStatus.RUNNING

    def test_store_conversation_history(self, tmp_path):
        """Test saving and loading conversation history."""
        from mcp_orchestrator.core.store import StateStore
        from mcp_orchestrator.core.models import Conversation, Message

        store = StateStore(tmp_path / "test.db")
        store.init_db()

        conv = Conversation(
            id="conv1",
            provider="darkrouter",
            model="gpt-4o",
            messages=[
                Message(role="user", content="Hello"),
                Message(role="assistant", content="Hi there!")
            ],
            created_at=0,
            updated_at=0
        )
        store.save_conversation(conv)
        loaded = store.load_conversation("conv1")
        assert loaded.id == "conv1"
        assert loaded.provider == "darkrouter"
        assert len(loaded.messages) == 2
        assert loaded.messages[0].content == "Hello"

        history = store.get_conversation_history("darkrouter", "gpt-4o")
        assert len(history) == 1
        assert history[0].id == "conv1"

    def test_store_update_run_status(self, tmp_path):
        """Test updating run status."""
        from mcp_orchestrator.core.store import StateStore
        from mcp_orchestrator.core.models import Run, RunStatus

        store = StateStore(tmp_path / "test.db")
        store.init_db()

        run = Run(
            id="run1",
            workflow_id="test",
            status=RunStatus.RUNNING,
            input_message="Hello",
            current_node=None,
            context={},
            created_at=0,
            updated_at=0
        )
        store.save_run(run)

        store.update_run_status("run1", RunStatus.COMPLETED)
        loaded = store.load_run("run1")
        assert loaded.status == RunStatus.COMPLETED

    def test_store_delete_workflow(self, tmp_path):
        """Test deleting a workflow."""
        from mcp_orchestrator.core.store import StateStore
        from mcp_orchestrator.core.models import Workflow, WorkflowMetadata

        store = StateStore(tmp_path / "test.db")
        store.init_db()

        wf = Workflow(id="test", version="1.0", metadata=WorkflowMetadata(name="Test"), nodes=[], edges=[])
        store.save_workflow(wf)
        assert store.load_workflow("test") is not None

        store.delete_workflow("test")
        assert store.load_workflow("test") is None
