# GeoPin

[中文](./README.md) | [English](./README_EN.md)

![Typer CLI](https://img.shields.io/badge/CLI-Typer-2E8B57?logo=python&logoColor=white)
![Pixi Env](https://img.shields.io/badge/Env-Pixi-7B61FF)
![Compile Passing](https://img.shields.io/badge/Compile-Passing-brightgreen)

GeoPin combines DJI video telemetry with KML landmarks to generate dynamic ASS overlays and burn them into the output video.

## 1. Features

1. Parse `Placemark` points from KML (lon/lat/alt, name, style color, optional timestamp).
2. Extract telemetry from DJI subtitle stream `0:s:0` (time, coordinates, gimbal attitude, focal length).
3. Probe video resolution, FPS, duration, and frame count.
4. Interpolate sparse telemetry into per-frame trajectory and export `flight_trajectory.csv`.
5. Compute per-frame visibility and pixel projection for landmarks, then generate `overlay_dynamic.ass`.
6. Generate run report `overlay_report.json`.
7. Burn ASS overlay into video with ffmpeg to produce final MP4.

## 2. Environment Setup

### 2.1 Requirements

- Install `pixi`

### 2.2 Initialize

```powershell
cd <project-root>
pixi install
pixi shell
```

## 3. Usage

### 3.1 Quick Start

```powershell
pixi run geopin
  --kml input/my_points.kml
  --video input/my_dji_video.MP4
  --output output/my_run
```

### 3.2 Arguments

Show help:

```powershell
pixi run geopin --help
```

| Argument | Description | Default |
| --- | --- | --- |
| `--kml` | KML landmark file path | `input/PIN-waixigou.kml` |
| `--video` | DJI source video path (must contain subtitle telemetry stream) | `input/DJI_20260301094020_0001_V.MP4` |
| `--output` | Output directory path | `output/DJI_20260301094020_0001_V` |
| `--font-name` | ASS font name | `Microsoft YaHei` |
| `--font-size` | ASS font size | `60` |
| `--max-ground-distance` | Max horizontal ground distance in meters; negative disables filtering | `1000.0` |
| `--limit-kml-by-time` | Keep only KML points within telemetry time range | off |
| `--dry-run` | Skip final ffmpeg burn step | off |

## 4. Input and Output

### 4.1 Input

1. Video file (`--video`)
- Format: MP4 (or any ffmpeg-readable format)
- Required: subtitle stream `0:s:0`
- Required telemetry fields in subtitles: `FrameCnt`, `latitude/longitude`, `rel_alt/abs_alt`, `gb_yaw/gb_pitch/gb_roll`, `focal_len`

2. KML file (`--kml`)
- Uses `Placemark` + `coordinates` (longitude, latitude, altitude)
- Optional `name` (auto fallback: `P{index}`)
- Optional `styleUrl/Style/StyleMap` for color
- Optional timestamp in `description`: `YYYY-MM-DD HH:MM:SS`

3. Output directory (`--output`)
- Created automatically if it does not exist

### 4.2 Output

Generated under `--output`:

1. `<video_stem>_overlay.mp4`
- Final overlaid video
- Generated only when not using `--dry-run`

2. `overlay_dynamic.ass`
- Dynamic ASS subtitle script

3. `flight_trajectory.csv`
- Per-frame trajectory data
- Columns:
  - `frame_index,time_s,timestamp,latitude,longitude,abs_alt,yaw,pitch,roll,focal_len`

4. `overlay_report.json`
- Run summary and statistics
- Main fields:
  - Paths: `video,kml,output,ass,trajectory_csv`
  - Video metadata: `frame_count,fps,video_duration_s`
  - Telemetry time range: `telemetry_start,telemetry_end`
  - Visibility stats: `points_total,ass_events,visible_points`
  - Per-point stats: `point_stats[]` with `visible_frames/first_visible/last_visible`

## 5. Citation

Plain text:

```text
wangjunfan. GeoPin: Dynamic Overlay Tool for DJI Video and KML Landmarks (Version 0.1.0) [Computer software]. 2026.
```

BibTeX:

```bibtex
@software{geopin_2026,
  author  = {wangjunfan},
  title   = {GeoPin: DJI 视频与 KML 地标动态叠加工具},
  version = {0.1.0},
  year    = {2026},
  url     = {https://github.com/RefineM/GeoPin}
}
```
