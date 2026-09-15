#!/usr/bin/env python3
"""Generate grid-scrape inputs for a USA city.

IMPORTANT - how the scraper actually works:

  The input file is a list of QUERY TERMS only, one per line. Geography is
  applied with the scraper's native ``-grid-bbox`` / ``-grid-cell`` flags.
  Appending "@lat,lng" to a query line does NOT work: the parser
  (runner/jobs.go parseQueryLine) only understands "term #!# id", so the
  coordinate becomes literal search text and Google returns an unreliable
  sliver of the metro.

Usage:
    python3 scripts/create_usa_deep.py <city_key>          # write terms + grid env
    python3 scripts/create_usa_deep.py --list              # list valid city keys
    python3 scripts/create_usa_deep.py <city_key> --cells 48 --print
"""
from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

# bbox = (minLon, minLat, maxLon, maxLat)
CITIES = {
    # Tier 1 - highest density event markets
    "miami_fl": {"name": "Miami, FL", "bbox": (-80.3197600, 25.7090517, -80.1391570, 25.8557827)},
    "atlanta_ga": {"name": "Atlanta, GA", "bbox": (-84.5508540, 33.6479187, -84.2895600, 33.8868230)},
    "las_vegas_nv": {"name": "Las Vegas, NV", "bbox": (-115.4065750, 36.1295540, -115.0620660, 36.4014810)},
    "orlando_fl": {"name": "Orlando, FL", "bbox": (-81.5075377, 28.3480634, -81.1241435, 28.6142830)},
    "new_york_ny": {"name": "New York, NY", "bbox": (-74.2588430, 40.4765780, -73.7002330, 40.9176300)},
    # Tier 2
    "charlotte_nc": {"name": "Charlotte, NC", "bbox": (-81.0116951, 35.0105195, -80.6348755, 35.4002508)},
    "denver_co": {"name": "Denver, CO", "bbox": (-105.1098845, 39.6143008, -104.5996997, 39.9142087)},
    "san_francisco_ca": {"name": "San Francisco, CA", "bbox": (-123.1738250, 37.6403143, -122.2814578, 37.9296678)},
    "phoenix_az": {"name": "Phoenix, AZ", "bbox": (-112.3240289, 33.2904827, -111.9255304, 33.9183794)},
    "tampa_fl": {"name": "Tampa, FL", "bbox": (-82.6488200, 27.8126539, -82.2538678, 28.1713602)},
    "seattle_wa": {"name": "Seattle, WA", "bbox": (-122.4593890, 47.4918400, -122.2244010, 47.7341400)},
    "austin_tx": {"name": "Austin, TX", "bbox": (-97.9400000, 30.1700000, -97.6500000, 30.4700000)},
    "nashville_tn": {"name": "Nashville, TN", "bbox": (-86.9300000, 36.0500000, -86.6200000, 36.3000000)},
    "san_diego_ca": {"name": "San Diego, CA", "bbox": (-117.2800000, 32.6600000, -116.9000000, 32.9600000)},
    "boston_ma": {"name": "Boston, MA", "bbox": (-71.1900000, 42.2800000, -70.9900000, 42.4000000)},
    # Tier 3 - major metros (large, so grid cells come out coarse)
    "houston_tx": {"name": "Houston, TX", "bbox": (-95.9097419, 29.5370705, -95.0120525, 30.1103506)},
    "los_angeles_ca": {"name": "Los Angeles, CA", "bbox": (-118.6681798, 33.6595410, -118.1552983, 34.3373060)},
    "chicago_il": {"name": "Chicago, IL", "bbox": (-87.9400876, 41.6445310, -87.5241243, 42.0230529)},
    "dallas_tx": {"name": "Dallas, TX", "bbox": (-97.0004820, 32.6132160, -96.4636317, 33.0239366)},
    "washington_dc": {"name": "Washington, DC", "bbox": (-77.1197949, 38.7916303, -76.9093660, 38.9959680)},
}

# Core terms only. The old 15-term list had heavy synonym overlap ("event
# planners" / "event organizers" / "event management companies" return largely
# the same businesses), and every extra term multiplies the grid cost.
CORE_QUERIES = [
    "event planners",
    "wedding planners",
    "corporate event planning",
    "conference organizers",
    "event production companies",
    "event venues",
    "trade show organizers",
    "party planners",
]

DEFAULT_CELLS = 32


def grid_geometry(bbox, target_cells):
    """Return (grid_bbox_str, cell_km, zoom) covering the whole bbox."""
    min_lon, min_lat, max_lon, max_lat = bbox
    center_lat = (min_lat + max_lat) / 2

    height_km = (max_lat - min_lat) * 111.0
    width_km = (max_lon - min_lon) * 111.0 * math.cos(math.radians(center_lat))
    area_km2 = max(height_km * width_km, 1e-6)

    # Square cells sized so the grid lands near the requested cell budget.
    cell_km = math.sqrt(area_km2 / max(target_cells, 1))
    cell_km = max(1.0, round(cell_km, 2))

    # Pick a zoom whose viewport roughly matches the cell size, so adjacent
    # cells overlap instead of leaving gaps. ~1280px usable viewport width.
    meters_per_px = 156543.03392 * math.cos(math.radians(center_lat))
    ideal_zoom = math.log2(meters_per_px * 1280 / (cell_km * 1000 * 1.2))
    zoom = int(max(12, min(16, round(ideal_zoom))))

    grid_bbox = f"{min_lat:.6f},{min_lon:.6f},{max_lat:.6f},{max_lon:.6f}"
    return grid_bbox, cell_km, zoom, height_km, width_km, area_km2


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("city", nargs="?", help="city key")
    ap.add_argument("--cells", type=int, default=DEFAULT_CELLS, help="target grid cells per city")
    ap.add_argument("--list", action="store_true", help="list city keys and exit")
    ap.add_argument("--print", dest="emit", action="store_true", help="print grid env to stdout")
    args = ap.parse_args()

    if args.list:
        print(",".join(CITIES.keys()))
        return 0

    if not args.city:
        ap.error("city key required (or use --list)")
    if args.city not in CITIES:
        print(f"unknown city {args.city!r}; valid: {','.join(CITIES)}", file=sys.stderr)
        return 2

    city = CITIES[args.city]
    bbox = city["bbox"]
    grid_bbox, cell_km, zoom, h_km, w_km, area = grid_geometry(bbox, args.cells)

    est_cells = max(1, int(round((h_km / cell_km) * (w_km / cell_km))))
    n_queries = est_cells * len(CORE_QUERIES)

    out_dir = Path("city_queries")
    out_dir.mkdir(exist_ok=True)
    terms_file = out_dir / f"{args.city}_terms.txt"
    env_file = out_dir / f"{args.city}_grid.env"

    terms_file.write_text("\n".join(CORE_QUERIES) + "\n")
    city_name = city["name"]
    env_file.write_text(
        f"GRID_BBOX={grid_bbox}\n"
        f"GRID_CELL={cell_km}\n"
        f"ZOOM={zoom}\n"
        f"TERMS={len(CORE_QUERIES)}\n"
        f"CELLS={est_cells}\n"
        f"QUERIES={n_queries}\n"
        f'CITY_NAME="{city_name}"\n'
    )

    lines = [
        f"[{args.city}] {city['name']}",
        f"  metro          : {w_km:.0f} x {h_km:.0f} km ({area:.0f} km2)",
        f"  grid           : ~{est_cells} cells @ {cell_km} km, zoom {zoom}",
        f"  queries        : {len(CORE_QUERIES)} terms x {est_cells} cells = {n_queries}",
        f"  grid-bbox      : {grid_bbox}",
        f"  terms file     : {terms_file}",
        f"  env file       : {env_file}",
    ]
    print("\n".join(lines))

    if args.emit:
        print(env_file.read_text(), end="")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
