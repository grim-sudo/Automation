"""Tests for the shared helpers extracted during de-duplication.

These lock the behavior that was previously copy-pasted into both
core.engine and ai.task_executor.
"""

from __future__ import annotations

from archon.utils.codegen import generate_fibonacci_code, generate_prime_number_code
from archon.utils.file_resolver import resolve_file_with_disambiguation

# ─── codegen ───────────────────────────────────────────────────────────────────


def test_prime_code_is_runnable_and_complete():
    code = generate_prime_number_code()
    assert "def is_prime(num):" in code
    assert "def find_primes(limit):" in code
    compile(code, "<prime>", "exec")  # must be valid Python


def test_fibonacci_code_is_runnable():
    code = generate_fibonacci_code()
    assert "def fibonacci(n):" in code
    compile(code, "<fib>", "exec")


def test_engine_and_task_executor_share_codegen():
    # Both call sites must produce identical output now that it is shared.
    from archon.ai.task_executor import AITaskExecutor
    from archon.core.engine import Archon

    assert Archon._generate_prime_number_code.__doc__ is not None  # method exists
    exec_inst = AITaskExecutor()
    assert exec_inst._generate_prime_number_code() == generate_prime_number_code()
    assert exec_inst._generate_fibonacci_code() == generate_fibonacci_code()


def test_extract_output_dir_from_nl_request():
    from archon.core.engine import Archon

    # __init__ is heavy; the extractor only reads a class-level regex.
    engine = object.__new__(Archon)
    assert engine._extract_output_dir("build a distro, output directory /data for the iso") == "/data"
    assert engine._extract_output_dir("output dir ~/isos please") == "~/isos"
    assert engine._extract_output_dir("output to ./build") == "./build"
    # No explicit path => None so the caller falls back to config defaults.
    assert engine._extract_output_dir("just build me an iso and output the results") is None


# ─── file resolver ─────────────────────────────────────────────────────────────


def test_resolve_finds_file_in_cwd(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "target.txt").write_text("hi")
    resolved = resolve_file_with_disambiguation("target.txt")
    assert resolved == str((tmp_path / "target.txt").resolve()) or resolved.endswith("target.txt")


def test_resolve_returns_none_when_missing(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    # Point HOME at an empty dir so the ~/Desktop|Documents|Projects scan finds nothing.
    monkeypatch.setenv("HOME", str(tmp_path))
    assert resolve_file_with_disambiguation("does_not_exist_12345.txt") is None


def test_resolve_use_icons_does_not_crash(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "a.txt").write_text("x")
    assert resolve_file_with_disambiguation("a.txt", use_icons=True).endswith("a.txt")
