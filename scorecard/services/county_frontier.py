"""
Centralized county name/region/slug handling for map and analytics.

GeoJSON and external sources use variant spellings (e.g. "Murang'a" vs "Muranga",
"Taita-Taveta" vs "Taita Taveta"). This module provides a single place for
alias resolution and region/slug maps so frontier map and insights stay consistent.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

# Aliases seen in GeoJSON or external data -> canonical County name in DB
COUNTY_NAME_ALIASES: List[Tuple[str, str]] = [
    ("Muranga", "Murang'a"),
    ("Tharaka Nithi", "Tharaka-Nithi"),
    ("Transzoia", "Trans Nzoia"),
    ("Trans-Nzoia", "Trans Nzoia"),
    ("Tharaka", "Tharaka-Nithi"),
    ("Keiyo-Marakwet", "Elgeyo-Marakwet"),
    ("Taita Taveta", "Taita-Taveta"),
    ("Elgeyo Marakwet", "Elgeyo-Marakwet"),
]

# Default region for aliases or same-name fallback when county missing from DB
COUNTY_ALIAS_DEFAULT_REGION: Dict[str, str] = {
    "Muranga": "central",
    "Tharaka Nithi": "eastern",
    "Tharaka": "eastern",
    "Elgeyo Marakwet": "rift_valley",
    "Transzoia": "rift_valley",
    "Trans-Nzoia": "rift_valley",
    "Keiyo-Marakwet": "rift_valley",
    "Taita Taveta": "coast",
    "Uasin Gishu": "rift_valley",
    "Homa Bay": "nyanza",
    "West Pokot": "rift_valley",
    "Trans Nzoia": "rift_valley",
}

FRONTIER_COLORS: Dict[str, str] = {
    "coast": "#0284c7",
    "eastern": "#059669",
    "central": "#7c3aed",
    "rift_valley": "#d97706",
    "nyanza": "#db2777",
    "western": "#0891b2",
    "north_eastern": "#65a30d",
    "interests": "#64748b",
    "other": "#475569",
}


def build_county_maps(
    counties: List[Dict[str, Any]],
) -> Tuple[Dict[str, str], Dict[str, str]]:
    """
    Build county_region_map and county_slug_map from a list of county dicts
    with keys "name", "region", "slug". Applies aliases so GeoJSON variants
    resolve to the same region/slug as canonical names.

    Returns (county_region_map, county_slug_map).
    """
    county_region_map = {c["name"]: c["region"] for c in counties}
    county_slug_map = {c["name"]: c["slug"] for c in counties if c.get("slug")}

    # Add alias -> region (from canonical or default)
    for alias, canonical in COUNTY_NAME_ALIASES:
        region = county_region_map.get(canonical) or COUNTY_ALIAS_DEFAULT_REGION.get(alias)
        if region:
            county_region_map[alias] = region
        if canonical in county_slug_map and alias not in county_slug_map:
            county_slug_map[alias] = county_slug_map[canonical]

    # Same-name defaults (when DB has no row for this spelling)
    for name, region in COUNTY_ALIAS_DEFAULT_REGION.items():
        if name not in county_region_map:
            county_region_map[name] = region

    return county_region_map, county_slug_map


def resolve_region(county_raw: Optional[str], county_region_map: Dict[str, str]) -> Optional[str]:
    """
    Resolve a raw county name (e.g. from GeoJSON properties) to a frontier/region slug.
    Uses exact match, then normalized variants (hyphens, " County"/" City" stripped),
    then fuzzy prefix/substring match for known names.
    """
    if not county_raw:
        return None
    c = county_raw.strip()
    # Exact and normalized matches
    r = (
        county_region_map.get(c)
        or county_region_map.get(c.replace("-", " "))
        or county_region_map.get(c.replace(" County", "").replace(" City", ""))
    )
    if r:
        return r
    c_lower = c.lower()
    for name, region in county_region_map.items():
        if not region:
            continue
        name_lower = name.lower()
        if (
            c_lower == name_lower
            or c_lower.startswith(name_lower + " ")
            or name_lower.startswith(c_lower + " ")
            or (len(c_lower) >= 4 and name_lower.startswith(c_lower))
        ):
            return region
    return None
