"""Data models.

Copyright (c) 2026 wangjunfan
Author: wangjunfan
Last-Edited: 2026-03-05
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class KmlPoint:
    """Single placemark parsed from a KML file.

    Inputs:
    - Values are produced by `parse_kml_points`.
    - Coordinates are geodetic WGS84 lon/lat/alt.

    Outputs:
    - Immutable record consumed by projection and rendering pipeline.
    """

    index: int
    name: str
    longitude: float
    latitude: float
    altitude: float
    timestamp: datetime | None
    style_id: str
    color_hex: str
    color_ass_bgr: str


@dataclass(frozen=True)
class TelemetrySample:
    """Single telemetry sample parsed from DJI subtitle stream.

    Inputs:
    - Parsed line groups from ffmpeg subtitle extraction.

    Outputs:
    - Immutable record consumed by trajectory interpolation.
    """

    frame_cnt: int
    timestamp: datetime
    latitude: float
    longitude: float
    abs_alt: float
    yaw: float
    pitch: float
    roll: float
    focal_len: float
