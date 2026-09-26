"""Tests for the n8n GUI gateway shaping and the distro config→profile map.

These lock the two thin backend seams the GUI depends on: the model→dict
shaping in :class:`N8nGateway` and the wizard-config→:class:`DistroProfile`
mapping on the engine. Both are pure, offline, and don't touch the network.
"""

from __future__ import annotations

from archon.plugins.n8n_bridge.gateway import N8nGateway
from archon.plugins.n8n_bridge.models import N8nNode, N8nWorkflow


def test_gateway_shapes_workflow_to_gui_dict():
    gw = N8nGateway(url="http://localhost:5678", api_key="k")
    wf = N8nWorkflow(
        id="abc",
        name="My Flow",
        active=True,
        nodes=[N8nNode(name="Webhook", type="n8n-nodes-base.webhook")],
    )
    d = gw._to_dict(wf)
    assert d == {
        "id": "abc",
        "name": "My Flow",
        "active": True,
        "trigger": "Webhook",
        "executionCount": 0,
    }


def test_gateway_trigger_label_falls_back_to_manual():
    gw = N8nGateway(url="http://localhost:5678", api_key="k")
    wf = N8nWorkflow(name="Plain", nodes=[N8nNode(name="Set", type="n8n-nodes-base.set")])
    assert gw._to_dict(wf)["trigger"] == "manual"


def test_distro_config_maps_to_profile():
    from archon.core.engine import Archon

    eng = Archon()
    try:
        profile = eng._gui_config_to_profile(
            {
                "base": "Arch Linux",
                "distro_type": "Security",
                "apps": ["wireshark nmap", "firefox"],
                "hardening": True,
                "hostname": "testbox",
            }
        )
    finally:
        eng.shutdown()

    assert profile.base == "arch"
    assert profile.hostname == "testbox"
    assert profile.name == "archon-security"
    # Space-packed bundles are split; hardening adds security packages.
    assert "wireshark" in profile.packages
    assert "nmap" in profile.packages
    assert "firefox" in profile.packages
    assert "nftables" in profile.packages
