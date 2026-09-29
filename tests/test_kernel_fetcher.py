"""Tests for kernel source caching reuse decisions.

These never hit the network: they only exercise the "already extracted" branch
of :func:`download_kernel`, which must reuse a writable cache but refuse a tree
left root-owned/unwritable by an earlier privileged run (else a kernel compile
fails cryptically with mkdir/.tmp Permission denied mid-build).
"""

from __future__ import annotations

import asyncio
import os

import pytest
from archon.distro_builder.kernel_fetcher import download_kernel


def test_reuses_writable_cached_kernel(tmp_path):
    extracted = tmp_path / "linux-7.2.8"
    extracted.mkdir()
    result = asyncio.run(download_kernel("7.2.8", tmp_path))
    assert result == extracted.resolve()


@pytest.mark.skipif(os.geteuid() == 0, reason="root bypasses filesystem permission checks")
def test_refuses_unwritable_cached_kernel(tmp_path):
    extracted = tmp_path / "linux-7.2.8"
    extracted.mkdir()
    extracted.chmod(0o555)  # read/execute only — a build could not write here
    try:
        with pytest.raises(RuntimeError, match="not writable"):
            asyncio.run(download_kernel("7.2.8", tmp_path))
    finally:
        extracted.chmod(0o755)
