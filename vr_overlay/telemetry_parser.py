"""Telemetry parsing from DJI subtitle stream.

Copyright (c) 2026 wangjunfan
Author: wangjunfan
Last-Edited: 2026-03-05
"""

from __future__ import annotations

import subprocess
from datetime import datetime
from pathlib import Path

from .constants import (
    SRT_FOCAL_PATTERN,
    SRT_FRAME_PATTERN,
    SRT_GEO_PATTERN,
    SRT_GIMBAL_PATTERN,
    SRT_REL_ABS_ALT_PATTERN,
)
from .data_models import TelemetrySample


def parse_subtitle_telemetry(video_path: Path) -> list[TelemetrySample]:
    """Extract telemetry samples from subtitle stream 0:s:0.

    Inputs:
    - video_path: path to DJI MP4 file.

    Output:
    - Time-sorted list of `TelemetrySample` records.

    Raises:
    - RuntimeError if ffmpeg extraction fails or no samples are parsed.
    """

    cmd = [
        "ffmpeg",
        "-v",
        "error",
        "-i",
        str(video_path),
        "-map",
        "0:s:0",
        "-f",
        "srt",
        "-",
    ]
    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="ignore",
    )

    assert proc.stdout is not None
    rows: list[TelemetrySample] = []
    pending: tuple[int, datetime] | None = None

    for raw in proc.stdout:
        line = raw.strip()
        if not line:
            continue

        frame_match = SRT_FRAME_PATTERN.search(line)
        if frame_match:
            pending = (
                int(frame_match.group(1)),
                datetime.strptime(frame_match.group(2), "%Y-%m-%d %H:%M:%S.%f"),
            )
            continue

        if pending is None:
            continue

        geo = SRT_GEO_PATTERN.search(line)
        alt = SRT_REL_ABS_ALT_PATTERN.search(line)
        gim = SRT_GIMBAL_PATTERN.search(line)
        focal = SRT_FOCAL_PATTERN.search(line)
        if not (geo and alt and gim and focal):
            continue

        frame_cnt, ts = pending
        pending = None

        rows.append(
            TelemetrySample(
                frame_cnt=frame_cnt,
                timestamp=ts,
                latitude=float(geo.group(1)),
                longitude=float(geo.group(2)),
                abs_alt=float(alt.group(2)),
                yaw=float(gim.group(1)),
                pitch=float(gim.group(2)),
                roll=float(gim.group(3)),
                focal_len=float(focal.group(1)),
            )
        )

    stderr = proc.communicate()[1]
    if proc.returncode != 0:
        raise RuntimeError(f"Failed to parse subtitle telemetry:\n{stderr}")
    if not rows:
        raise RuntimeError("No subtitle telemetry parsed from stream 0:s:0.")

    if len(rows) < 2:
        raise RuntimeError("Telemetry sample count too small for interpolation.")
    return rows
