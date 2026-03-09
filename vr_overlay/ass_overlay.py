"""ASS event generation and video burn-in rendering.

Copyright (c) 2026 wangjunfan
Author: wangjunfan
Last-Edited: 2026-03-05
"""

from __future__ import annotations

import json
import math
import subprocess
from pathlib import Path

import numpy as np

from .constants import SENSOR_HEIGHT_EQ_MM, SENSOR_WIDTH_EQ_MM
from .data_models import KmlPoint
from .trajectory import geodetic_to_local_enu
from .utils import ffmpeg_escape_filter_path, list_ffmpeg_candidates, resolve_ffmpeg_for_filter


def ass_escape_text(text: str) -> str:
    """Escape text for ASS dialogue payload.

    Input:
    - text: arbitrary label string.

    Output:
    - String safe for ASS text field.
    """

    out = text.replace("\\", r"\\")
    out = out.replace("{", "(").replace("}", ")")
    out = out.replace("\r", " ").replace("\n", " ")
    return out


def ass_time_from_cs(cs: int) -> str:
    """Convert centiseconds to ASS time format `h:mm:ss.cc`."""

    if cs < 0:
        cs = 0
    h = cs // 360000
    rem = cs % 360000
    m = rem // 6000
    rem %= 6000
    s = rem // 100
    c = rem % 100
    return f"{h}:{m:02d}:{s:02d}.{c:02d}"


def write_ass_header(path: Path, width: int, height: int, font_size: int, font_name: str) -> None:
    """Write ASS script header and style section.

    Inputs:
    - path: target ASS file path.
    - width/height: render resolution used by ffmpeg.
    - font_size/font_name: base style typography.
    """

    header = (
        "[Script Info]\n"
        "ScriptType: v4.00+\n"
        "WrapStyle: 2\n"
        "ScaledBorderAndShadow: yes\n"
        f"PlayResX: {width}\n"
        f"PlayResY: {height}\n"
        "YCbCr Matrix: TV.709\n"
        "\n"
        "[V4+ Styles]\n"
        "Format: Name,Fontname,Fontsize,PrimaryColour,SecondaryColour,OutlineColour,BackColour,"
        "Bold,Italic,Underline,StrikeOut,ScaleX,ScaleY,Spacing,Angle,BorderStyle,Outline,Shadow,"
        "Alignment,MarginL,MarginR,MarginV,Encoding\n"
        f"Style: Marker,{font_name},{font_size},&H00FFFFFF,&H000000FF,&H00000000,&H64000000,"
        "0,0,0,0,100,100,0,0,1,3,0,7,10,10,10,1\n"
        "\n"
        "[Events]\n"
        "Format: Layer,Start,End,Style,Name,MarginL,MarginR,MarginV,Effect,Text\n"
    )
    path.write_text(header, encoding="utf-8")


def build_camera_axes_enu(
    yaw_deg: float,
    pitch_deg: float,
    roll_deg: float,
) -> tuple[float, float, float, float, float, float, float, float, float]:
    """Build camera right/up/forward axes in ENU coordinates.

    Inputs:
    - yaw/pitch/roll: gimbal Euler angles in degrees.

    Output:
    - Tuple of unit vectors:
      (right_e, right_n, right_u, up_e, up_n, up_u, fwd_e, fwd_n, fwd_u)
    """

    yaw = math.radians(yaw_deg)
    pitch = math.radians(pitch_deg)
    roll = math.radians(roll_deg)

    cp = math.cos(pitch)
    fwd_e = math.sin(yaw) * cp
    fwd_n = math.cos(yaw) * cp
    fwd_u = math.sin(pitch)

    fwd_norm = math.sqrt(fwd_e * fwd_e + fwd_n * fwd_n + fwd_u * fwd_u)
    if fwd_norm < 1e-12:
        fwd_e, fwd_n, fwd_u = 0.0, 1.0, 0.0
        fwd_norm = 1.0
    inv_f = 1.0 / fwd_norm
    fwd_e *= inv_f
    fwd_n *= inv_f
    fwd_u *= inv_f

    # right0 = normalize(cross(forward, world_up=[0,0,1]))
    right0_e = fwd_n
    right0_n = -fwd_e
    right0_u = 0.0
    right0_norm = math.sqrt(right0_e * right0_e + right0_n * right0_n + right0_u * right0_u)
    if right0_norm < 1e-12:
        # Forward is near vertical, use world_north as fallback reference.
        right0_e = -fwd_u
        right0_n = 0.0
        right0_u = fwd_e
        right0_norm = math.sqrt(
            right0_e * right0_e + right0_n * right0_n + right0_u * right0_u
        )
    if right0_norm < 1e-12:
        right0_e, right0_n, right0_u = 1.0, 0.0, 0.0
        right0_norm = 1.0
    inv_r0 = 1.0 / right0_norm
    right0_e *= inv_r0
    right0_n *= inv_r0
    right0_u *= inv_r0

    # up0 = normalize(cross(right0, forward))
    up0_e = right0_n * fwd_u - right0_u * fwd_n
    up0_n = right0_u * fwd_e - right0_e * fwd_u
    up0_u = right0_e * fwd_n - right0_n * fwd_e
    up0_norm = math.sqrt(up0_e * up0_e + up0_n * up0_n + up0_u * up0_u)
    if up0_norm < 1e-12:
        up0_e, up0_n, up0_u = 0.0, 0.0, 1.0
        up0_norm = 1.0
    inv_u0 = 1.0 / up0_norm
    up0_e *= inv_u0
    up0_n *= inv_u0
    up0_u *= inv_u0

    cr = math.cos(roll)
    sr = math.sin(roll)
    right_e = right0_e * cr - up0_e * sr
    right_n = right0_n * cr - up0_n * sr
    right_u = right0_u * cr - up0_u * sr
    up_e = right0_e * sr + up0_e * cr
    up_n = right0_n * sr + up0_n * cr
    up_u = right0_u * sr + up0_u * cr

    right_norm = math.sqrt(right_e * right_e + right_n * right_n + right_u * right_u)
    up_norm = math.sqrt(up_e * up_e + up_n * up_n + up_u * up_u)
    if right_norm > 1e-12:
        inv_right = 1.0 / right_norm
        right_e *= inv_right
        right_n *= inv_right
        right_u *= inv_right
    if up_norm > 1e-12:
        inv_up = 1.0 / up_norm
        up_e *= inv_up
        up_n *= inv_up
        up_u *= inv_up

    return right_e, right_n, right_u, up_e, up_n, up_u, fwd_e, fwd_n, fwd_u


def generate_ass_events(
    ass_path: Path,
    points: list[KmlPoint],
    traj: dict[str, object],
    width: int,
    height: int,
    fps: float,
    font_size: int,
    max_ground_distance_m: float | None,
) -> dict[str, object]:
    """Generate dynamic ASS dialogue events for projected points.

    Inputs:
    - ass_path: ASS file path with header already written.
    - points: KML points to render.
    - traj: per-frame trajectory arrays.
    - width/height: frame dimensions.
    - fps: frame rate.
    - font_size: per-point subtitle font size.
    - max_ground_distance_m: optional distance cutoff; <0 disables cutoff.

    Output:
    - Dict with `events`, `visible_points`, `point_stats`.
    """

    if not points:
        with ass_path.open("a", encoding="utf-8"):
            pass
        return {"events": 0, "visible_points": 0, "point_stats": []}

    frame_index: np.ndarray = traj["frame_index"]  # type: ignore[assignment]
    time_s: np.ndarray = traj["time_s"]  # type: ignore[assignment]
    lat: np.ndarray = traj["lat"]  # type: ignore[assignment]
    lon: np.ndarray = traj["lon"]  # type: ignore[assignment]
    alt: np.ndarray = traj["abs_alt"]  # type: ignore[assignment]
    yaw: np.ndarray = traj["yaw"]  # type: ignore[assignment]
    pitch: np.ndarray = traj["pitch"]  # type: ignore[assignment]
    roll: np.ndarray = traj["roll"]  # type: ignore[assignment]
    focal: np.ndarray = traj["focal"]  # type: ignore[assignment]

    ref_lat = float(lat[0])
    ref_lon = float(lon[0])
    ref_alt = float(alt[0])

    p_lat = np.array([p.latitude for p in points], dtype=np.float64)
    p_lon = np.array([p.longitude for p in points], dtype=np.float64)
    p_alt = np.array([p.altitude for p in points], dtype=np.float64)
    p_e, p_n, p_u = geodetic_to_local_enu(p_lat, p_lon, p_alt, ref_lat, ref_lon, ref_alt)
    c_e, c_n, c_u = geodetic_to_local_enu(lat, lon, alt, ref_lat, ref_lon, ref_alt)

    half_w = width * 0.5
    half_h = height * 0.5

    n_points = len(points)
    visible_frames = np.zeros(n_points, dtype=np.int64)
    first_cs = np.full(n_points, -1, dtype=np.int64)
    last_cs = np.full(n_points, -1, dtype=np.int64)
    event_count = 0

    with ass_path.open("a", encoding="utf-8") as file_obj:
        for i in range(len(frame_index)):
            # if i % 4000 == 0:
            #     print(f"  ASS progress: frame {i}/{len(frame_index)}")

            de = p_e - c_e[i]
            dn = p_n - c_n[i]
            du = p_u - c_u[i]
            hdist = np.hypot(de, dn)

            fmm = float(max(focal[i], 1e-3))
            tan_h = SENSOR_WIDTH_EQ_MM / (2.0 * fmm)
            tan_v = SENSOR_HEIGHT_EQ_MM / (2.0 * fmm)

            right_e, right_n, right_u, up_e, up_n, up_u, fwd_e, fwd_n, fwd_u = (
                build_camera_axes_enu(float(yaw[i]), float(pitch[i]), float(roll[i]))
            )
            x_cam = de * right_e + dn * right_n + du * right_u
            y_cam = de * up_e + dn * up_n + du * up_u
            z_cam = de * fwd_e + dn * fwd_n + du * fwd_u
            z_safe = np.maximum(z_cam, 1e-6)

            x_ndc = (x_cam / z_safe) / tan_h
            y_ndc = (y_cam / z_safe) / tan_v

            x_px = half_w + x_ndc * half_w
            y_px = half_h - y_ndc * half_h

            visible = (
                (z_cam > 1e-6)
                & (np.abs(x_ndc) <= 1.0)
                & (np.abs(y_ndc) <= 1.0)
                & (x_px >= 0.0)
                & (x_px < width)
                & (y_px >= 0.0)
                & (y_px < height)
            )
            if max_ground_distance_m is not None and max_ground_distance_m >= 0:
                visible &= hdist <= max_ground_distance_m

            ids = np.nonzero(visible)[0]
            if ids.size == 0:
                continue

            s_cs = int(round(float(time_s[i]) * 100.0))
            e_cs = int(round((float(time_s[i]) + 1.0 / fps) * 100.0))
            if e_cs <= s_cs:
                e_cs = s_cs + 1

            start_ass = ass_time_from_cs(s_cs)
            end_ass = ass_time_from_cs(e_cs)

            for j in ids.tolist():
                px = int(round(float(x_px[j])))
                py = int(round(float(y_px[j])))
                px = max(0, min(width - 4, px))
                py = max(0, min(height - 4, py))

                point = points[j]
                label = ass_escape_text(point.name)
                lonlat = f"{point.longitude:.6f},{point.latitude:.6f}"
                text = (
                    "{"
                    f"\\an7\\pos({px},{py})"
                    f"\\fs{font_size}\\bord3\\shad0"
                    f"\\1c&H{point.color_ass_bgr}&\\3c&H000000&"
                    "}"
                    f"* {label} \\NLonLat:{lonlat}"
                )
                file_obj.write(f"Dialogue: 0,{start_ass},{end_ass},Marker,,0,0,0,,{text}\n")

                event_count += 1
                visible_frames[j] += 1
                if first_cs[j] < 0:
                    first_cs[j] = s_cs
                last_cs[j] = e_cs

    stats: list[dict[str, object]] = []
    visible_points = 0
    for idx, point in enumerate(points):
        vf = int(visible_frames[idx])
        if vf > 0:
            visible_points += 1
        stats.append(
            {
                "point_index": point.index,
                "point_name": point.name,
                "color": point.color_hex,
                "longitude": point.longitude,
                "latitude": point.latitude,
                "visible_frames": vf,
                "first_visible": ass_time_from_cs(int(first_cs[idx])) if first_cs[idx] >= 0 else None,
                "last_visible": ass_time_from_cs(int(last_cs[idx])) if last_cs[idx] >= 0 else None,
            }
        )

    return {"events": event_count, "visible_points": visible_points, "point_stats": stats}


def parse_ffmpeg_time_seconds(text: str) -> float | None:
    """Parse ffmpeg time text `HH:MM:SS.xx` into seconds."""

    parts = text.strip().split(":")
    if len(parts) != 3:
        return None
    try:
        hours = int(parts[0])
        mins = int(parts[1])
        secs = float(parts[2])
    except ValueError:
        return None
    return hours * 3600.0 + mins * 60.0 + secs


def print_render_progress(progress_s: float, duration_s: float | None) -> None:
    """Render one terminal progress line for ffmpeg burn step."""

    if duration_s is not None and duration_s > 0:
        pct = max(0.0, min(100.0, progress_s * 100.0 / duration_s))
        bar_width = 28
        filled = int(round((pct / 100.0) * bar_width))
        bar = "#" * filled + "-" * (bar_width - filled)
        try:
            print(f"\r  Render progress: [{bar}] {pct:5.1f}%", end="", flush=True)
        except OSError:
            pass
        return
    try:
        print(f"\r  Render progress: {progress_s:8.2f}s", end="", flush=True)
    except OSError:
        pass


def burn_ass(
    video_path: Path,
    ass_path: Path,
    output_path: Path,
    duration_s: float | None = None,
) -> None:
    """Burn generated ASS subtitles into video via ffmpeg.

    Inputs:
    - video_path: source video file.
    - ass_path: generated ASS subtitle file.
    - output_path: destination encoded video.
    - duration_s: optional source video duration for progress percentage.
    """

    # Use explicit `filename=` to avoid Windows drive-letter parsing ambiguity.
    ass_expr = f"ass=filename='{ffmpeg_escape_filter_path(ass_path)}'"
    ffmpeg_bin = resolve_ffmpeg_for_filter("ass")
    if ffmpeg_bin is None:
        candidates = list_ffmpeg_candidates()
        candidate_text = "\n".join(f"- {item}" for item in candidates) if candidates else "- (none found)"
        raise RuntimeError(
            "No ffmpeg binary with 'ass' filter found.\n"
            "Your current ffmpeg cannot burn ASS subtitles.\n"
            "Detected ffmpeg candidates:\n"
            f"{candidate_text}\n"
            "Please install/use an ffmpeg build with libass support."
        )

    cmd = [
        ffmpeg_bin,
        "-y",
        "-v",
        "error",
        "-progress",
        "pipe:1",
        "-nostats",
        "-i",
        str(video_path),
        "-map",
        "0:v:0",
        "-vf",
        ass_expr,
        "-c:v",
        "libx264",
        "-preset",
        "veryfast",
        "-crf",
        "18",
        "-pix_fmt",
        "yuv420p",
        "-movflags",
        "+faststart",
        str(output_path),
    ]

    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="ignore",
        bufsize=1,
    )
    assert proc.stdout is not None
    assert proc.stderr is not None

    out_lines: list[str] = []
    last_progress_s: float | None = None

    for raw in proc.stdout:
        out_lines.append(raw)
        line = raw.strip()
        if "=" not in line:
            continue

        key, value = line.split("=", 1)
        progress_s: float | None = None

        if key in ("out_time_us", "out_time_ms"):
            try:
                progress_s = int(value) / 1_000_000.0
            except ValueError:
                progress_s = None
        elif key == "out_time":
            progress_s = parse_ffmpeg_time_seconds(value)

        if progress_s is not None:
            if last_progress_s is None or progress_s - last_progress_s >= 0.2:
                print_render_progress(progress_s, duration_s)
                last_progress_s = progress_s

    return_code = proc.wait()
    stderr_text = proc.stderr.read()
    stdout_text = "".join(out_lines)

    if last_progress_s is not None:
        if duration_s is not None and duration_s > 0:
            print_render_progress(duration_s, duration_s)
        print()

    if return_code != 0:
        raise RuntimeError(f"ffmpeg burn failed:\nSTDOUT:\n{stdout_text}\nSTDERR:\n{stderr_text}")


def write_report(path: Path, payload: dict[str, object]) -> None:
    """Write pipeline run report as UTF-8 JSON."""

    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
