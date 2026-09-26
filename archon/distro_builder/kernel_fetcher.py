"""
Download and verify Linux kernel source tarballs from kernel.org.

Uses httpx for async downloads and verifies SHA256 checksums.
All blocking I/O (file extraction, patch application) runs in
asyncio.to_thread() to avoid blocking the event loop.
"""

from __future__ import annotations

import asyncio
import hashlib
import subprocess
import tarfile
from pathlib import Path

import httpx
from loguru import logger
from rich.progress import BarColumn, DownloadColumn, Progress, SpinnerColumn, TextColumn

__all__ = [
    "fetch_latest_stable_version",
    "download_kernel",
    "apply_patches",
]

_RELEASES_URL = "https://www.kernel.org/releases.json"


async def fetch_latest_stable_version() -> str:
    """Fetch the current latest stable kernel version from kernel.org.

    Returns:
        Version string, e.g. ``"6.9.3"``.

    Raises:
        RuntimeError: If the API call fails or no stable release is found.
    """
    async with httpx.AsyncClient(timeout=20.0) as client:
        resp = await client.get(_RELEASES_URL)
        resp.raise_for_status()
        data = resp.json()

    for release in data.get("releases", []):
        if release.get("moniker") == "stable":
            version = release["version"]
            logger.info("Latest stable kernel: {}", version)
            return version

    raise RuntimeError("Could not find a stable kernel release at kernel.org")


async def download_kernel(version: str, dest_dir: Path) -> Path:
    """Download and extract the Linux kernel source for *version*.

    Args:
        version:  Kernel version string (e.g. ``"6.9.3"``).
        dest_dir: Directory where the tarball will be saved and extracted.

    Returns:
        Path to the extracted kernel source directory.

    Raises:
        RuntimeError: If SHA256 verification fails.
        httpx.HTTPError: On download failure.
    """
    dest_dir = dest_dir.resolve()
    dest_dir.mkdir(parents=True, exist_ok=True)

    major = version.split(".")[0]
    tarball_name = f"linux-{version}.tar.xz"
    checksum_name = f"linux-{version}.tar.xz.sha256"
    base_url = f"https://cdn.kernel.org/pub/linux/kernel/v{major}.x"

    tarball_path = dest_dir / tarball_name
    extracted_path = dest_dir / f"linux-{version}"

    if extracted_path.exists():
        logger.info("Kernel {} already extracted at {}", version, extracted_path)
        return extracted_path

    # ── Download tarball ──────────────────────────────────────────────────────
    logger.info("Downloading kernel {} …", version)
    with Progress(
        SpinnerColumn(),
        TextColumn("[bold blue]{task.description}"),
        BarColumn(),
        DownloadColumn(),
    ) as progress:
        task = progress.add_task(f"linux-{version}.tar.xz", total=None)

        async with httpx.AsyncClient(timeout=600.0, follow_redirects=True) as client:
            async with client.stream("GET", f"{base_url}/{tarball_name}") as resp:
                resp.raise_for_status()
                total = int(resp.headers.get("content-length", 0)) or None
                progress.update(task, total=total)
                with open(tarball_path, "wb") as f:
                    async for chunk in resp.aiter_bytes(65536):
                        f.write(chunk)
                        progress.advance(task, len(chunk))

    # ── Verify SHA256 ─────────────────────────────────────────────────────────
    logger.info("Verifying SHA256 checksum …")
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.get(f"{base_url}/{checksum_name}")
            resp.raise_for_status()
            expected_hash = resp.text.split()[0].strip()

        actual_hash = await asyncio.to_thread(_sha256_file, tarball_path)
        if actual_hash != expected_hash:
            tarball_path.unlink(missing_ok=True)
            raise RuntimeError(
                f"SHA256 mismatch for {tarball_name}: expected {expected_hash}, got {actual_hash}"
            )
        logger.info("Checksum verified OK.")
    except httpx.HTTPError:
        # Checksum file unavailable — log warning, continue
        logger.warning("Could not fetch checksum file for {}, skipping verification", version)

    # ── Extract ───────────────────────────────────────────────────────────────
    logger.info("Extracting {} …", tarball_name)
    await asyncio.to_thread(_extract_tarball, tarball_path, dest_dir)
    tarball_path.unlink(missing_ok=True)  # clean up tarball after extraction

    logger.info("Kernel source ready at {}", extracted_path)
    return extracted_path


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _extract_tarball(tarball: Path, dest: Path) -> None:
    with tarfile.open(tarball, "r:xz") as tf:
        tf.extractall(dest)


async def apply_patches(kernel_dir: Path, patch_files: list[Path]) -> bool:
    """Apply a list of patch files to the kernel source.

    Args:
        kernel_dir:  Extracted kernel source directory.
        patch_files: List of paths to ``.patch`` files.

    Returns:
        ``True`` if all patches applied cleanly, ``False`` otherwise.
    """
    kernel_dir = kernel_dir.resolve()
    all_ok = True
    for patch in patch_files:
        patch = Path(patch).resolve()
        if not patch.exists():
            logger.warning("Patch file not found: {}", patch)
            all_ok = False
            continue

        logger.info("Applying patch: {}", patch.name)
        result = await asyncio.to_thread(
            subprocess.run,
            ["patch", "-p1", "--input", str(patch)],
            cwd=str(kernel_dir),
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            logger.error("Patch {} failed:\n{}", patch.name, result.stderr)
            all_ok = False
        else:
            logger.info("Patch {} applied OK.", patch.name)

    return all_ok
