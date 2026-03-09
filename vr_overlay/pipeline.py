"""Top-level pipeline orchestration.

Copyright (c) 2026 wangjunfan
Author: wangjunfan
Last-Edited: 2026-03-05
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .ass_overlay import (
    burn_ass,
    generate_ass_events,
    write_ass_header,
    write_report,
)
from .kml_parser import parse_kml_points
from .telemetry_parser import parse_subtitle_telemetry
from .trajectory import build_interpolated_trajectory, write_trajectory_csv
from .utils import ensure_tools
from .video_probe import probe_video


@dataclass(frozen=True)
class PipelineConfig:
    """Configuration for one complete pipeline run.

    Inputs:
    - kml: source KML path.
    - video: source MP4 path.
    - output: rendered output MP4 path.
    - ass: generated ASS subtitle path.
    - trajectory_csv: generated trajectory CSV path.
    - report: generated JSON report path.
    - font_name/font_size: subtitle style controls.
    - max_ground_distance: optional distance cutoff; negative disables cutoff.
    - dry_run: if True, skip final ffmpeg rendering.
    """

    kml: Path
    video: Path
    output: Path
    ass: Path
    trajectory_csv: Path
    report: Path
    font_name: str
    font_size: int
    max_ground_distance: float | None
    dry_run: bool


def run_pipeline(config: PipelineConfig) -> dict[str, object]:
    """Execute full KML-to-video overlay pipeline.

    Input:
    - config: `PipelineConfig` with all file paths and options.

    Output:
    - Report payload dictionary (also written to JSON).

    Raises:
    - RuntimeError/FileNotFoundError for missing inputs or processing failures.
    """

    ensure_tools()
    if not config.kml.exists():
        raise FileNotFoundError(f"KML not found: {config.kml}")
    if not config.video.exists():
        raise FileNotFoundError(f"Video not found: {config.video}")

    print("[1/7] Parsing KML...")
    points = parse_kml_points(config.kml)
    if not points:
        raise RuntimeError("No valid KML points parsed.")
    print(f"  KML points: {len(points)}")

    print("[2/7] Parsing subtitle telemetry...")
    samples = parse_subtitle_telemetry(config.video)
    print(f"  Telemetry samples: {len(samples)}")
    print(f"  Telemetry range: {samples[0].timestamp} -> {samples[-1].timestamp}")

    print("[3/7] Probing video...")
    width, height, fps, frame_count, duration = probe_video(config.video)
    print(f"  Size: {width}x{height}")
    print(f"  FPS: {fps:.6f}")
    print(f"  Frames: {frame_count}")
    print(f"  Duration: {duration:.3f}s")

    print("[4/7] Interpolating per-frame trajectory...")
    traj = build_interpolated_trajectory(samples, frame_count, fps)
    write_trajectory_csv(config.trajectory_csv, traj)
    print(f"  Trajectory CSV: {config.trajectory_csv}")

    print("[5/7] Generating dynamic ASS overlay...")
    write_ass_header(config.ass, width, height, config.font_size, config.font_name)
    stats = generate_ass_events(
        ass_path=config.ass,
        points=points,
        traj=traj,
        width=width,
        height=height,
        fps=fps,
        font_size=config.font_size,
        max_ground_distance_m=config.max_ground_distance,
    )
    print(f"  ASS file: {config.ass}")
    print(f"  ASS events: {stats['events']}")
    print(f"  Visible points: {stats['visible_points']}/{len(points)}")

    report = {
        "video": str(config.video),
        "kml": str(config.kml),
        "output": str(config.output),
        "ass": str(config.ass),
        "trajectory_csv": str(config.trajectory_csv),
        "frame_count": frame_count,
        "fps": fps,
        "video_duration_s": duration,
        "telemetry_start": samples[0].timestamp.isoformat(sep=" "),
        "telemetry_end": samples[-1].timestamp.isoformat(sep=" "),
        "points_total": len(points),
        "ass_events": stats["events"],
        "visible_points": stats["visible_points"],
        "point_stats": stats["point_stats"],
    }
    write_report(config.report, report)
    print(f"[6/7] Report written: {config.report}")

    if config.dry_run:
        print("[7/7] Dry-run enabled, skip rendering.")
        return report

    print("[7/7] Burning ASS onto video...")
    burn_ass(config.video, config.ass, config.output, duration_s=duration)
    print(f"  Output video: {config.output}")
    return report
