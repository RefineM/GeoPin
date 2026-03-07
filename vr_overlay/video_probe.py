"""Video stream probing logic.

Copyright (c) 2026 wangjunfan
Author: wangjunfan
Last-Edited: 2026-03-05
"""

from __future__ import annotations

import json
from pathlib import Path

from .utils import parse_rate, run_command


def probe_video(video_path: Path) -> tuple[int, int, float, int, float]:
    """Probe video dimensions, frame rate, frame count, and duration.

    Inputs:
    - video_path: input MP4 path.

    Outputs:
    - width: frame width in pixels.
    - height: frame height in pixels.
    - fps: floating-point frame rate.
    - frame_count: total frame count (from metadata or estimated).
    - duration: total duration in seconds.

    Raises:
    - RuntimeError when no video stream is found or FPS is invalid.
    """

    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-select_streams",
        "v:0",
        "-show_entries",
        "stream=width,height,avg_frame_rate,r_frame_rate,nb_frames:format=duration",
        "-of",
        "json",
        str(video_path),
    ]
    data = json.loads(run_command(cmd).stdout)
    streams = data.get("streams", [])
    if not streams:
        raise RuntimeError("No video stream found.")
    stream = streams[0]

    width = int(stream["width"])
    height = int(stream["height"])

    fps = parse_rate(str(stream.get("avg_frame_rate", "0/0")))
    if fps <= 0:
        fps = parse_rate(str(stream.get("r_frame_rate", "0/0")))
    if fps <= 0:
        raise RuntimeError("Invalid FPS parsed from video.")

    duration = float(data.get("format", {}).get("duration", 0.0) or 0.0)
    nb_frames_txt = str(stream.get("nb_frames", "") or "").strip()
    frame_count = int(nb_frames_txt) if nb_frames_txt.isdigit() else 0
    if frame_count <= 0:
        frame_count = max(1, int(round(duration * fps)))
    if duration <= 0:
        duration = frame_count / fps

    return width, height, fps, frame_count, duration
