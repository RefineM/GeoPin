"""Utility helpers for process execution and ffmpeg-safe text/path handling.

Copyright (c) 2026 wangjunfan
Author: wangjunfan
Last-Edited: 2026-03-05
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path


def run_command(cmd: list[str], check: bool = True) -> subprocess.CompletedProcess[str]:
    """Execute an external command.

    Inputs:
    - cmd: tokenized command list, e.g. `["ffprobe", "-v", "error", ...]`.
    - check: if True, non-zero return code raises RuntimeError.

    Output:
    - `subprocess.CompletedProcess[str]` containing stdout/stderr.

    Raises:
    - RuntimeError when command fails and `check=True`.
    """

    proc = subprocess.run(cmd, text=True, capture_output=True, encoding="utf-8", errors="ignore")
    if check and proc.returncode != 0:
        raise RuntimeError(
            f"Command failed ({proc.returncode}): {' '.join(cmd)}\n"
            f"STDOUT:\n{proc.stdout}\nSTDERR:\n{proc.stderr}"
        )
    return proc


def ensure_tools() -> None:
    """Validate required executables are available in PATH.

    Inputs:
    - None.

    Output:
    - None.

    Raises:
    - RuntimeError if ffmpeg/ffprobe are missing.
    """

    missing = [tool for tool in ("ffmpeg", "ffprobe") if shutil.which(tool) is None]
    if missing:
        raise RuntimeError(f"Missing required tools: {', '.join(missing)}")


def ffmpeg_supports_filter(ffmpeg_bin: str, filter_name: str) -> bool:
    """Check whether a given ffmpeg binary exposes a filter by name."""

    proc = subprocess.run(
        [ffmpeg_bin, "-hide_banner", "-filters"],
        text=True,
        capture_output=True,
        encoding="utf-8",
        errors="ignore",
    )
    if proc.returncode != 0:
        return False

    text = proc.stdout + "\n" + proc.stderr
    for line in text.splitlines():
        fields = line.split()
        if len(fields) >= 2 and fields[1] == filter_name:
            return True
    return False


def list_ffmpeg_candidates() -> list[str]:
    """List candidate ffmpeg binaries from PATH while preserving order."""

    out: list[str] = []
    seen: set[str] = set()

    def _add(path_text: str) -> None:
        if not path_text:
            return
        p = str(Path(path_text).resolve())
        key = p.lower()
        if key in seen:
            return
        seen.add(key)
        out.append(p)

    primary = shutil.which("ffmpeg")
    if primary:
        _add(primary)

    if os.name == "nt":
        where_proc = subprocess.run(
            ["where", "ffmpeg"],
            text=True,
            capture_output=True,
            encoding="utf-8",
            errors="ignore",
        )
        if where_proc.returncode == 0:
            for line in where_proc.stdout.splitlines():
                _add(line.strip())
    else:
        which_proc = subprocess.run(
            ["which", "-a", "ffmpeg"],
            text=True,
            capture_output=True,
            encoding="utf-8",
            errors="ignore",
        )
        if which_proc.returncode == 0:
            for line in which_proc.stdout.splitlines():
                _add(line.strip())

    return out


def resolve_ffmpeg_for_filter(filter_name: str) -> str | None:
    """Find an ffmpeg binary in PATH that supports the given filter."""

    for ffmpeg_bin in list_ffmpeg_candidates():
        if ffmpeg_supports_filter(ffmpeg_bin, filter_name):
            return ffmpeg_bin
    return None


def parse_rate(text: str) -> float:
    """Convert ffprobe framerate text to float fps.

    Inputs:
    - text: either `"num/den"` or decimal string.

    Output:
    - Parsed frames-per-second as float.
    """

    if "/" in text:
        num, den = text.split("/", 1)
        den_f = float(den)
        return float(num) / den_f if den_f else 0.0
    return float(text)


def ffmpeg_escape_filter_path(path: Path) -> str:
    """Escape filesystem path for use inside ffmpeg filter expressions.

    Inputs:
    - path: path to ASS file or other filter argument file.

    Output:
    - Escaped string safe for `-vf "ass='...'"`.
    """

    escaped = path.resolve().as_posix().replace("\\", "/")
    escaped = escaped.replace(":", r"\:")
    escaped = escaped.replace("'", r"\'")
    return escaped
