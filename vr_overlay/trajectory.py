"""Trajectory interpolation and coordinate conversion.

Copyright (c) 2026 wangjunfan
Author: wangjunfan
Last-Edited: 2026-03-05
"""

from __future__ import annotations

import csv
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pymap3d as pm

from .data_models import TelemetrySample


def interp_angle_deg(key_t: np.ndarray, key_deg: np.ndarray, query_t: np.ndarray) -> np.ndarray:
    """Interpolate angle series in degrees with unwrap handling.

    Inputs:
    - key_t: strictly increasing sample times in seconds.
    - key_deg: angle values in degrees at key_t.
    - query_t: target times for interpolation.

    Output:
    - Angle array in range [-180, 180).
    """

    key_rad = np.unwrap(np.deg2rad(key_deg))
    q_rad = np.interp(query_t, key_t, key_rad)
    q_deg = np.rad2deg(q_rad)
    return (q_deg + 180.0) % 360.0 - 180.0


def build_interpolated_trajectory(
    samples: list[TelemetrySample],
    frame_count: int,
    fps: float,
) -> dict[str, object]:
    """Build per-frame trajectory arrays from sparse telemetry samples.

    Inputs:
    - samples: time-ordered telemetry samples.
    - frame_count: total frame count of target video.
    - fps: target frame rate.

    Output:
    - Dict with keys: base_ts, frame_index, time_s, lat, lon, abs_alt, yaw, pitch, roll, focal.
    """

    if frame_count <= 0:
        raise RuntimeError("Invalid frame_count for trajectory building.")
    _ = fps  # Kept for API compatibility; frame alignment now uses sample order.

    base_ts = samples[0].timestamp
    sample_count = len(samples)

    frame_idx = np.arange(frame_count, dtype=np.int64)
    key_idx = np.arange(sample_count, dtype=np.float64)

    key_t = np.array([(s.timestamp - base_ts).total_seconds() for s in samples], dtype=np.float64)
    key_lat = np.array([s.latitude for s in samples], dtype=np.float64)
    key_lon = np.array([s.longitude for s in samples], dtype=np.float64)
    key_alt = np.array([s.abs_alt for s in samples], dtype=np.float64)
    key_yaw = np.array([s.yaw for s in samples], dtype=np.float64)
    key_pitch = np.array([s.pitch for s in samples], dtype=np.float64)
    key_roll = np.array([s.roll for s in samples], dtype=np.float64)
    key_focal = np.array([s.focal_len for s in samples], dtype=np.float64)

    if sample_count == frame_count:
        return {
            "base_ts": base_ts,
            "frame_index": frame_idx,
            "time_s": key_t.copy(),
            "lat": key_lat.copy(),
            "lon": key_lon.copy(),
            "abs_alt": key_alt.copy(),
            "yaw": key_yaw.copy(),
            "pitch": key_pitch.copy(),
            "roll": key_roll.copy(),
            "focal": key_focal.copy(),
        }

    if sample_count == 1 or frame_count == 1:
        query_idx = np.zeros(frame_count, dtype=np.float64)
    else:
        # Align trajectory by frame order, only stretching when counts differ.
        scale = (sample_count - 1.0) / (frame_count - 1.0)
        query_idx = frame_idx.astype(np.float64) * scale

    return {
        "base_ts": base_ts,
        "frame_index": frame_idx,
        "time_s": np.interp(query_idx, key_idx, key_t),
        "lat": np.interp(query_idx, key_idx, key_lat),
        "lon": np.interp(query_idx, key_idx, key_lon),
        "abs_alt": np.interp(query_idx, key_idx, key_alt),
        "yaw": interp_angle_deg(key_idx, key_yaw, query_idx),
        "pitch": interp_angle_deg(key_idx, key_pitch, query_idx),
        "roll": interp_angle_deg(key_idx, key_roll, query_idx),
        "focal": np.interp(query_idx, key_idx, key_focal),
    }


def write_trajectory_csv(path: Path, traj: dict[str, object]) -> None:
    """Persist per-frame trajectory to CSV.

    Inputs:
    - path: destination CSV file.
    - traj: trajectory dictionary from `build_interpolated_trajectory`.

    Output:
    - None. Writes file as UTF-8 CSV.
    """

    base_ts: datetime = traj["base_ts"]  # type: ignore[assignment]
    frame_index = traj["frame_index"]  # type: ignore[assignment]
    time_s = traj["time_s"]  # type: ignore[assignment]
    lat = traj["lat"]  # type: ignore[assignment]
    lon = traj["lon"]  # type: ignore[assignment]
    abs_alt = traj["abs_alt"]  # type: ignore[assignment]
    yaw = traj["yaw"]  # type: ignore[assignment]
    pitch = traj["pitch"]  # type: ignore[assignment]
    roll = traj["roll"]  # type: ignore[assignment]
    focal = traj["focal"]  # type: ignore[assignment]

    with path.open("w", encoding="utf-8", newline="") as file_obj:
        writer = csv.writer(file_obj)
        writer.writerow(
            [
                "frame_index",
                "time_s",
                "timestamp",
                "latitude",
                "longitude",
                "abs_alt",
                "yaw",
                "pitch",
                "roll",
                "focal_len",
            ]
        )
        for i in range(len(frame_index)):
            ts = base_ts + timedelta(seconds=float(time_s[i]))
            writer.writerow(
                [
                    int(frame_index[i]),
                    f"{float(time_s[i]):.6f}",
                    ts.isoformat(sep=" "),
                    f"{float(lat[i]):.9f}",
                    f"{float(lon[i]):.9f}",
                    f"{float(abs_alt[i]):.6f}",
                    f"{float(yaw[i]):.6f}",
                    f"{float(pitch[i]):.6f}",
                    f"{float(roll[i]):.6f}",
                    f"{float(focal[i]):.6f}",
                ]
            )


def geodetic_to_local_enu(
    lat: np.ndarray,
    lon: np.ndarray,
    alt: np.ndarray,
    ref_lat: float,
    ref_lon: float,
    ref_alt: float,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Convert geodetic coordinates to local ENU using `pymap3d`.

    Inputs:
    - lat/lon/alt: arrays of WGS84 coordinates.
    - ref_lat/ref_lon/ref_alt: ENU origin.

    Outputs:
    - east, north, up arrays in meters as float64.
    """

    east, north, up = pm.geodetic2enu(
        lat,
        lon,
        alt,
        ref_lat,
        ref_lon,
        ref_alt,
        deg=True,
    )
    return (
        np.asarray(east, dtype=np.float64),
        np.asarray(north, dtype=np.float64),
        np.asarray(up, dtype=np.float64),
    )


def wrap_angle_np(angle_deg: np.ndarray) -> np.ndarray:
    """Normalize angle array into range [-180, 180)."""

    return (angle_deg + 180.0) % 360.0 - 180.0
