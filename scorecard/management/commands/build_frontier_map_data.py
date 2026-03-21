"""
Pre-build frontier map data as a static JSON file for fast loading.
Run: python manage.py build_frontier_map_data
Serves map instantly without hitting Django on each request.
"""
import json
from pathlib import Path

from django.core.management.base import BaseCommand

from scorecard.views.insights import _build_frontier_map_data


def _simplify_coords(coords, precision=4):
    """Round coordinates to reduce file size. precision=4 ~11m accuracy."""
    if isinstance(coords[0], (int, float)):
        return [round(coords[0], precision), round(coords[1], precision)]
    return [_simplify_coords(c, precision) for c in coords]


def _simplify_geometry(geom):
    """Simplify GeoJSON geometry coordinates."""
    if not geom or "coordinates" not in geom:
        return geom
    geom = dict(geom)
    coords = geom["coordinates"]
    if geom["type"] == "Polygon":
        geom["coordinates"] = [[_simplify_coords(p) for p in ring] for ring in coords]
    elif geom["type"] == "MultiPolygon":
        geom["coordinates"] = [
            [[_simplify_coords(p) for p in ring] for ring in poly]
            for poly in coords
        ]
    return geom


class Command(BaseCommand):
    help = "Pre-build frontier map JSON for fast static serving. Run after county changes."

    def add_arguments(self, parser):
        parser.add_argument(
            "--no-simplify",
            action="store_true",
            help="Skip coordinate simplification (larger file)",
        )

    def handle(self, *args, **options):
        data = _build_frontier_map_data()
        geojson = data.get("geojson_data")
        if not geojson or not geojson.get("features"):
            self.stdout.write(self.style.ERROR("No GeoJSON data available."))
            return

        if not options.get("no_simplify"):
            for f in geojson["features"]:
                if "geometry" in f:
                    f["geometry"] = _simplify_geometry(f["geometry"])

        out_dir = Path(__file__).resolve().parent.parent.parent / "static" / "scorecard"
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / "frontier_map_data.json"

        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(data, f, separators=(",", ":"))

        size_kb = out_path.stat().st_size / 1024
        self.stdout.write(self.style.SUCCESS(f"Wrote {out_path} ({size_kb:.1f} KB)"))
