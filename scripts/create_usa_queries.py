#!/usr/bin/env python3
"""
Create query file for a USA city.
Usage: python3 create_usa_queries.py <city_key>
"""
import sys
import math
from pathlib import Path

CITIES = {
    'miami_fl': {'name': 'Miami, FL', 'bbox': (-80.3197600, 25.7090517, -80.1391570, 25.8557827)},
    'atlanta_ga': {'name': 'Atlanta, GA', 'bbox': (-84.5508540, 33.6479187, -84.2895600, 33.8868230)},
    'las_vegas_nv': {'name': 'Las Vegas, NV', 'bbox': (-115.4065750, 36.1295540, -115.0620660, 36.4014810)},
    'orlando_fl': {'name': 'Orlando, FL', 'bbox': (-81.5075377, 28.3480634, -81.1241435, 28.6142830)},
    'new_york_ny': {'name': 'New York, NY', 'bbox': (-74.2588430, 40.4765780, -73.7002330, 40.9176300)},
}

QUERIES = [
    'event planners', 'event organizers', 'event management companies',
    'corporate event planning', 'wedding planners', 'conference organizers',
    'trade show organizers', 'event production companies', 'meeting planners',
    'festival organizers', 'event venues', 'event spaces rental',
    'corporate event venues', 'convention services', 'exhibition organizers',
]

CELL_SIZE_KM = 1.0

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 create_usa_queries.py <city_key>")
        sys.exit(1)
    
    city_key = sys.argv[1]
    if city_key not in CITIES:
        print(f"Unknown city: {city_key}")
        sys.exit(1)
    
    city = CITIES[city_key]
    minLat, minLon, maxLat, maxLon = city['bbox']
    center_lat = (minLat + maxLat) / 2
    lat_step = CELL_SIZE_KM / 111.0
    lon_step = CELL_SIZE_KM / (111.0 * math.cos(math.radians(center_lat)))

    cells = []
    lat = minLat + lat_step / 2
    while lat < maxLat:
        lon = minLon + lon_step / 2
        while lon < maxLon:
            cells.append((round(lat, 6), round(lon, 6)))
            lon += lon_step
        lat += lat_step

    print(f'{city["name"]}: {len(cells)} cells', file=sys.stderr)
    
    Path('city_queries').mkdir(exist_ok=True)
    with open(f'city_queries/{city_key}.txt', 'w') as f:
        for lat, lon in cells:
            for q in QUERIES:
                f.write(f'{q} {city["name"]} @{lat},{lon}\n')
    
    print(f'Created city_queries/{city_key}.txt with {len(cells) * len(QUERIES)} queries')

if __name__ == '__main__':
    main()