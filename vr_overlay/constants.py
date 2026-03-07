"""Project-wide constants and regex patterns.

Copyright (c) 2026 wangjunfan
Author: wangjunfan
Last-Edited: 2026-03-05
"""

from __future__ import annotations

import re

# Namespace used by ElementTree when parsing KML XML.
KML_NS = {"kml": "http://www.opengis.net/kml/2.2"}

# Timestamp format embedded in KML description text.
KML_TIME_PATTERN = re.compile(r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})")

# DJI subtitle telemetry parsing patterns.
SRT_FRAME_PATTERN = re.compile(
    r"FrameCnt:\s*(\d+)\s+(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d{3})"
)
SRT_GEO_PATTERN = re.compile(
    r"\[latitude:\s*([-+]?\d+(?:\.\d+)?)\]\s*\[longitude:\s*([-+]?\d+(?:\.\d+)?)\]"
)
SRT_REL_ABS_ALT_PATTERN = re.compile(
    r"\[rel_alt:\s*([-+]?\d+(?:\.\d+)?)\s+abs_alt:\s*([-+]?\d+(?:\.\d+)?)\]"
)
SRT_GIMBAL_PATTERN = re.compile(
    r"\[gb_yaw:\s*([-+]?\d+(?:\.\d+)?)\s+gb_pitch:\s*([-+]?\d+(?:\.\d+)?)\s+gb_roll:\s*([-+]?\d+(?:\.\d+)?)\]"
)
SRT_FOCAL_PATTERN = re.compile(r"\[focal_len:\s*([-+]?\d+(?:\.\d+)?)\]")

# 35mm-equivalent sensor dimensions used to convert focal length to FOV.
SENSOR_WIDTH_EQ_MM = 36.0
SENSOR_HEIGHT_EQ_MM = 20.25
