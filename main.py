#!/usr/bin/env python3
"""CLI interface entrypoint for the KML-to-video overlay pipeline.

Copyright (c) 2026 wangjunfan
Author: wangjunfan
Last-Edited: 2026-03-07
"""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from vr_overlay.pipeline import PipelineConfig, run_pipeline


def build_config(
    kml: Path,
    video: Path,
    output: Path,
    font_name: str,
    font_size: int,
    max_ground_distance: float,
    limit_kml_by_time: bool,
    dry_run: bool,
) -> PipelineConfig:
    """Build pipeline config from CLI options."""

    output_dir = output
    output_dir.mkdir(parents=True, exist_ok=True)
    video_stem = video.stem

    return PipelineConfig(
        kml=kml,
        video=video,
        output=output_dir / f"{video_stem}_overlay.mp4",
        ass=output_dir / "overlay_dynamic.ass",
        trajectory_csv=output_dir / "flight_trajectory.csv",
        report=output_dir / "overlay_report.json",
        font_name=font_name,
        font_size=font_size,
        max_ground_distance=max_ground_distance,
        limit_kml_by_time=limit_kml_by_time,
        dry_run=dry_run,
    )


def main(
    kml: Annotated[
        Path,
        typer.Option(help="kml file containing placemarks to overlay.", file_okay=True, dir_okay=False),
    ] = Path("input/PIN-waixigou.kml"),
    video: Annotated[
        Path,
        typer.Option(help="original DJI video file with SRT to overlay on.", file_okay=True, dir_okay=False),
    ] = Path("input/DJI_20260301094020_0001_V.MP4"),
    output: Annotated[
        Path,
        typer.Option(help="output folder for generated files.", file_okay=False, dir_okay=True),
    ] = Path("output/DJI_20260301094020_0001_V"),
    font_name: Annotated[str, typer.Option(help="the font name of the overlay text.")] = "Microsoft YaHei",
    font_size: Annotated[int, typer.Option(help="the font size of the overlay text.")] = 60,
    max_ground_distance: Annotated[
        float, typer.Option(help="Optional horizontal distance cutoff in meters. Set negative to disable.")
    ] = 1000.0,
    limit_kml_by_time: Annotated[
        bool, typer.Option(help="Only keep KML points whose timestamp is inside telemetry range.")
    ] = False,
    dry_run: Annotated[bool, typer.Option(help="Skip final ffmpeg render step.")] = False,
) -> None:
    """Per-frame trajectory projection for DJI video + KML marks."""

    config = build_config(
        kml=kml,
        video=video,
        output=output,
        font_name=font_name,
        font_size=font_size,
        max_ground_distance=max_ground_distance,
        limit_kml_by_time=limit_kml_by_time,
        dry_run=dry_run,
    )
    try:
        run_pipeline(config)
    except Exception as exc:  # pragma: no cover - thin CLI wrapper
        typer.echo(f"ERROR: {exc}", err=True)
        raise typer.Exit(code=1)


if __name__ == "__main__":
    typer.run(main)
