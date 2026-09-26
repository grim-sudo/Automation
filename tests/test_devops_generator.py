"""Tests for the DevOps generator, covering the three actions that were
advertised in ``get_capabilities`` and dispatched in ``execute`` but had no
implementation (``setup_ci_cd_pipeline``, ``create_jenkins_pipeline``,
``create_terraform_config``) — they raised AttributeError before the fix.
"""

from __future__ import annotations

import os

from archon.plugins.devops_generator import DevOpsGeneratorPlugin


def test_every_advertised_action_is_implemented():
    plugin = DevOpsGeneratorPlugin()
    for action in plugin.get_capabilities():
        # setup_monitoring returns files_created; all others exist as methods.
        assert hasattr(plugin, f"_{action}") or action == "setup_monitoring", action


def test_setup_ci_cd_pipeline_writes_gitlab_ci(tmp_path):
    plugin = DevOpsGeneratorPlugin()
    res = plugin.execute("setup_ci_cd_pipeline", {"app_type": "python", "location": str(tmp_path)})
    assert os.path.isfile(res["file_path"])
    assert res["file_path"].endswith(".gitlab-ci.yml")
    assert "pytest" in (tmp_path / ".gitlab-ci.yml").read_text()


def test_create_jenkins_pipeline_writes_jenkinsfile(tmp_path):
    plugin = DevOpsGeneratorPlugin()
    res = plugin.execute("create_jenkins_pipeline", {"app_type": "node", "location": str(tmp_path)})
    content = (tmp_path / "Jenkinsfile").read_text()
    assert os.path.isfile(res["file_path"])
    assert "pipeline {" in content
    assert "npm ci" in content


def test_create_terraform_config_writes_main_and_vars(tmp_path):
    plugin = DevOpsGeneratorPlugin()
    res = plugin.execute("create_terraform_config", {"provider": "aws", "location": str(tmp_path)})
    assert set(res["files_created"]) == {
        str(tmp_path / "main.tf"),
        str(tmp_path / "variables.tf"),
    }
    assert 'provider "aws"' in (tmp_path / "main.tf").read_text()
    assert 'variable "region"' in (tmp_path / "variables.tf").read_text()
