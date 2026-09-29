"""Tests for AI-driven multi-file project generation.

The live model isn't exercised; a fake AI locks in the orchestration: a planned
file layout is written under the project dir, a dependency manifest is emitted,
path-traversal escapes are rejected, and offline/no-content cases refuse cleanly.
"""

from __future__ import annotations

import os

import archon.ai.automation_ai as ai_mod
from archon.plugins.project_generator import ProjectGeneratorPlugin


class _FakeAI:
    is_available = True
    last_error = None

    def __init__(self, files=None, code="print('hello')", available=True):
        self._files = files
        self.is_available = available
        self._code = code

    def generate_json(self, prompt, system_prompt=None, max_tokens=1500):
        if self._files is None:
            return {"name": "empty", "language": "python", "files": []}
        return {
            "name": "tformer",
            "language": "python",
            "dependencies": ["torch", "numpy"],
            "files": self._files,
        }

    def generate_code(self, prompt, system_prompt=None, max_tokens=2000):
        return self._code

    def generate_document(self, request, filename=""):
        return "# Project README\n"


def _install_fake(monkeypatch, fake):
    monkeypatch.setattr(ai_mod, "OllamaAutomationAI", lambda *a, **k: fake)


def test_generate_project_writes_planned_files(tmp_path, monkeypatch):
    files = [
        {"path": "model.py", "purpose": "the transformer"},
        {"path": "train.py", "purpose": "training loop"},
        {"path": "README.md", "purpose": "docs"},
    ]
    _install_fake(monkeypatch, _FakeAI(files=files))

    plugin = ProjectGeneratorPlugin()
    result = plugin.execute(
        "generate_project",
        {"description": "a transformer model in pytorch", "location": str(tmp_path)},
    )

    assert result["success"] is True
    created = [os.path.basename(p) for p in result["files_created"]]
    assert {"model.py", "train.py", "README.md"} <= set(created)
    # Dependencies named in the plan produce a requirements.txt.
    assert "requirements.txt" in created
    proj = result["project_path"]
    assert os.path.isfile(os.path.join(proj, "model.py"))


def test_generate_project_rejects_path_traversal(tmp_path, monkeypatch):
    files = [
        {"path": "ok.py", "purpose": "fine"},
        {"path": "../escape.py", "purpose": "malicious"},
        {"path": "/etc/evil", "purpose": "absolute escape"},
    ]
    _install_fake(monkeypatch, _FakeAI(files=files))

    plugin = ProjectGeneratorPlugin()
    result = plugin.execute(
        "generate_project",
        {"description": "x", "name": "proj", "location": str(tmp_path)},
    )

    assert result["success"] is True
    assert "../escape.py" in result["skipped"]
    # Nothing was written outside the project directory.
    assert not (tmp_path / "escape.py").exists()
    assert os.path.isfile(os.path.join(result["project_path"], "ok.py"))


def test_generate_project_single_file_fallback(tmp_path, monkeypatch):
    # Planning returned no files → single-file fallback still produces something.
    _install_fake(monkeypatch, _FakeAI(files=None, code="print('fallback')"))

    plugin = ProjectGeneratorPlugin()
    result = plugin.execute(
        "generate_project",
        {"description": "a python script", "location": str(tmp_path)},
    )

    assert result["success"] is True
    assert len(result["files_created"]) == 1
    assert result["files_created"][0].endswith("main.py")


def test_generate_project_refuses_when_ai_unavailable(tmp_path, monkeypatch):
    _install_fake(monkeypatch, _FakeAI(available=False))

    plugin = ProjectGeneratorPlugin()
    result = plugin.execute(
        "generate_project",
        {"description": "anything", "location": str(tmp_path)},
    )

    assert result["success"] is False
    assert "unavailable" in result["error"].lower()
