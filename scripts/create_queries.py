#!/usr/bin/env python3
import sys, math

bbox_str = sys.argv[1]
city = sys.argv[2]
cell_size = float(sys.argv[3])
max_cells = int(sys.argv[4])

minLat, minLon, maxLat, maxLon = map(float, bbox_str.split(","))
center_lat = (minLat + maxLat) / 2
lat_step = cell_size / 111.0
lon_step = cell_size / (111.0 * math.cos(math.radians(center_lat)))

cells = []
lat = minLat + lat_step / 2
while lat < maxLat:
    lon = minLon + lon_step / 2
    while lon < maxLon:
        cells.append((round(lat, 6), round(lon, 6)))
        lon += lon_step
    lat += lat_step

cells = cells[:max_cells]

queries = [
    "logistics companies", "freight forwarders", "shipping companies",
    "customs brokers", "warehouse storage", "cold storage",
    "courier services", "haulage companies", "transport companies", "supply chain"
]

with open(f"{city}_queries.txt", "w") as f:
    for lat, lon in cells:
        for q in queries:
            f.write(f"{q} {city.replace('_', ' ').title()} @{lat},{lon}\n")

print(f"Generated {len(cells)} cells, {len(cells)*len(queries)} queries")
