"""Pure POI data-quality checks for admin QA dashboard."""

from __future__ import annotations

import math
import re
import unicodedata
from dataclasses import dataclass
from typing import Literal

PoiQaIssueType = Literal[
    "wrong_coords",
    "duplicates",
    "missing_hours",
    "missing_duration",
    "missing_embedding",
]

HUE_LAT_MIN = 16.3
HUE_LAT_MAX = 16.6
HUE_LNG_MIN = 107.4
HUE_LNG_MAX = 107.8
DUPLICATE_DISTANCE_M = 50


@dataclass(frozen=True)
class PoiQaRecord:
    uuid: str
    name: str
    category: str
    tags: list[str]
    latitude: float
    longitude: float
    visit_duration_min: int
    open_time: int
    close_time: int
    has_embedding: bool


@dataclass(frozen=True)
class PoiQaSummaryCounts:
    wrong_coords: int
    duplicates: int
    missing_hours: int
    missing_duration: int
    missing_embedding: int


def is_wrong_coords(latitude: float, longitude: float) -> bool:
    if latitude == 0 and longitude == 0:
        return True
    return (
        latitude < HUE_LAT_MIN
        or latitude > HUE_LAT_MAX
        or longitude < HUE_LNG_MIN
        or longitude > HUE_LNG_MAX
    )


def is_missing_hours(open_time: int, close_time: int) -> bool:
    if open_time >= close_time:
        return True
    return open_time == 480 and close_time == 1260


def is_missing_duration(visit_duration_min: int) -> bool:
    return visit_duration_min <= 0


def normalize_poi_name(name: str) -> str:
    lowered = unicodedata.normalize("NFKD", name.strip().lower())
    ascii_only = lowered.encode("ascii", "ignore").decode("ascii")
    return re.sub(r"\s+", " ", ascii_only).strip()


def haversine_meters(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius = 6_371_000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lon2 - lon1)
    a = math.sin(d_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    return 2 * radius * math.asin(math.sqrt(a))


def duplicate_group_map(pois: list[PoiQaRecord]) -> dict[str, str]:
    groups: dict[str, str] = {}
    by_name: dict[str, list[PoiQaRecord]] = {}
    for poi in pois:
        key = normalize_poi_name(poi.name)
        if key:
            by_name.setdefault(key, []).append(poi)

    group_index = 0
    for entries in by_name.values():
        if len(entries) < 2:
            continue

        visited: set[str] = set()
        for seed in entries:
            if seed.uuid in visited:
                continue
            cluster = [seed]
            visited.add(seed.uuid)
            expanded = True
            while expanded:
                expanded = False
                for candidate in entries:
                    if candidate.uuid in visited:
                        continue
                    if any(
                        haversine_meters(candidate.latitude, candidate.longitude, member.latitude, member.longitude)
                        < DUPLICATE_DISTANCE_M
                        for member in cluster
                    ):
                        cluster.append(candidate)
                        visited.add(candidate.uuid)
                        expanded = True

            if len(cluster) >= 2:
                group_id = f"dup-{group_index}"
                group_index += 1
                for member in cluster:
                    groups[member.uuid] = group_id

    return groups


def compute_qa_summary(pois: list[PoiQaRecord]) -> PoiQaSummaryCounts:
    dup_map = duplicate_group_map(pois)
    return PoiQaSummaryCounts(
        wrong_coords=sum(1 for p in pois if is_wrong_coords(p.latitude, p.longitude)),
        duplicates=len(dup_map),
        missing_hours=sum(1 for p in pois if is_missing_hours(p.open_time, p.close_time)),
        missing_duration=sum(1 for p in pois if is_missing_duration(p.visit_duration_min)),
        missing_embedding=sum(1 for p in pois if not p.has_embedding),
    )


def filter_pois_by_issue(
    pois: list[PoiQaRecord],
    issue: PoiQaIssueType,
) -> tuple[list[PoiQaRecord], dict[str, str]]:
    dup_map = duplicate_group_map(pois)
    if issue == "wrong_coords":
        return [p for p in pois if is_wrong_coords(p.latitude, p.longitude)], {}
    if issue == "duplicates":
        return [p for p in pois if p.uuid in dup_map], dup_map
    if issue == "missing_hours":
        return [p for p in pois if is_missing_hours(p.open_time, p.close_time)], {}
    if issue == "missing_duration":
        return [p for p in pois if is_missing_duration(p.visit_duration_min)], {}
    if issue == "missing_embedding":
        return [p for p in pois if not p.has_embedding], {}
    raise ValueError(f"Unknown issue type: {issue}")
