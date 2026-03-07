"""KML parsing functions.

Copyright (c) 2026 wangjunfan
Author: wangjunfan
Last-Edited: 2026-03-05
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path

from .constants import KML_NS, KML_TIME_PATTERN
from .data_models import KmlPoint


def kml_color_to_rgb(color: str) -> tuple[int, int, int]:
    """Convert KML color string to RGB tuple.

    Inputs:
    - color: usually `aabbggrr` format; `rrggbb` is also accepted.

    Output:
    - `(r, g, b)` tuple with values in [0, 255].
    """

    c = (color or "").strip().lower()
    if len(c) == 8:
        bb = int(c[2:4], 16)
        gg = int(c[4:6], 16)
        rr = int(c[6:8], 16)
        return rr, gg, bb
    if len(c) == 6:
        rr = int(c[0:2], 16)
        gg = int(c[2:4], 16)
        bb = int(c[4:6], 16)
        return rr, gg, bb
    return 255, 64, 64


def parse_kml_style_colors(root: ET.Element) -> tuple[dict[str, tuple[str, str]], dict[str, str]]:
    """Parse color lookup maps from KML style/styleMap blocks.

    Inputs:
    - root: ElementTree root of a loaded KML document.

    Outputs:
    - style_colors: style_id -> (`#RRGGBB`, `BBGGRR` for ASS).
    - style_maps: styleMap_id -> referenced style_id for `normal` state.
    """

    style_colors: dict[str, tuple[str, str]] = {}
    style_maps: dict[str, str] = {}

    for style in root.findall(".//kml:Style", KML_NS):
        sid = style.attrib.get("id")
        if not sid:
            continue
        color_text = style.findtext(".//kml:IconStyle/kml:color", default="", namespaces=KML_NS)
        if not color_text:
            color_text = style.findtext(".//kml:LineStyle/kml:color", default="", namespaces=KML_NS)
        r, g, b = kml_color_to_rgb(color_text)
        style_colors[sid] = (f"#{r:02X}{g:02X}{b:02X}", f"{b:02X}{g:02X}{r:02X}")

    for style_map in root.findall(".//kml:StyleMap", KML_NS):
        sid = style_map.attrib.get("id")
        if not sid:
            continue
        normal_url = ""
        for pair in style_map.findall(".//kml:Pair", KML_NS):
            key = (pair.findtext("kml:key", default="", namespaces=KML_NS) or "").strip()
            if key == "normal":
                normal_url = (pair.findtext("kml:styleUrl", default="", namespaces=KML_NS) or "").strip()
                break
        if normal_url.startswith("#"):
            normal_url = normal_url[1:]
        if normal_url:
            style_maps[sid] = normal_url

    return style_colors, style_maps


def parse_kml_points(kml_path: Path) -> list[KmlPoint]:
    """Parse KML placemarks into `KmlPoint` records.

    Inputs:
    - kml_path: KML file path.

    Output:
    - List of parsed points with style/color/timestamp resolved.

    Notes:
    - Timestamp is extracted from description using regex.
    - Missing point names are replaced with `P{index}`.
    """

    root = ET.fromstring(kml_path.read_text(encoding="utf-8"))
    style_colors, style_maps = parse_kml_style_colors(root)
    placemarks = root.findall(".//kml:Placemark", KML_NS)

    points: list[KmlPoint] = []
    default_color_hex = "#FF4040"
    default_ass_bgr = "4040FF"

    for idx, placemark in enumerate(placemarks, start=1):
        coord_text = (
            placemark.findtext(".//kml:coordinates", default="", namespaces=KML_NS) or ""
        ).strip()
        if not coord_text:
            continue
        parts = coord_text.split(",")
        if len(parts) < 2:
            continue

        lon = float(parts[0])
        lat = float(parts[1])
        alt = float(parts[2]) if len(parts) > 2 and parts[2] else 0.0

        name = (placemark.findtext("kml:name", default="", namespaces=KML_NS) or "").strip()
        if not name:
            name = f"P{idx}"

        desc = (placemark.findtext("kml:description", default="", namespaces=KML_NS) or "").strip()
        ts_match = KML_TIME_PATTERN.search(desc)
        ts = datetime.strptime(ts_match.group(1), "%Y-%m-%d %H:%M:%S") if ts_match else None

        style_url = (placemark.findtext("kml:styleUrl", default="", namespaces=KML_NS) or "").strip()
        if style_url.startswith("#"):
            style_url = style_url[1:]
        style_id = style_maps.get(style_url, style_url)
        color_hex, color_ass_bgr = style_colors.get(style_id, (default_color_hex, default_ass_bgr))

        points.append(
            KmlPoint(
                index=idx,
                name=name,
                longitude=lon,
                latitude=lat,
                altitude=alt,
                timestamp=ts,
                style_id=style_id or "default",
                color_hex=color_hex,
                color_ass_bgr=color_ass_bgr,
            )
        )
    return points
