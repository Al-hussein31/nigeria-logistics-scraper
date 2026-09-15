#!/usr/bin/env python3
"""Create deep query file for USA city - 15 queries, 60 cells"""
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

DEEP_QUERIES = [
    'event planners', 'event organizers', 'event management companies',
    'corporate event planning', 'wedding planners', 'conference organizers',
    'trade show organizers', 'event production companies', 'meeting planners',
    'festival organizers', 'event venues', 'event spaces rental',
    'corporate event venues', 'convention services', 'exhibition organizers',
]

CELL_SIZE_KM = 1.0
MAX_CELLS = 60

def main():
    city_key = sys.argv[1] if len(sys.argv) > 1 else 'miami_fl'
    city = CITIES.get(city_key, CITIES['miami_fl'])
    
    minLat, minLon, maxLat, maxLon = city['bbox']
    center_lat = (minLat + maxLat) / 2
    cell_size = CELL_SIZE_KM
    lat_step = cell_size / 111.0
    lon_step = cell_size / (111.0 * math.cos(math.radians(center_lat)))
    
    cells = []
    lat = minLat + lat_step / 2
    while lat < maxLat and len(cells) < MAX_CELLS:
        lon = minLon + lon_step / 2
        while lon < maxLon and len(cells) < MAX_CELLS:
            cells.append((round(lat, 6), round(lon, 6)))
            lon += lon_step
        lat += lat_step
    
    Path('city_queries').mkdir(exist_ok=True)
    with open(f'city_queries/{city_key}_deep.txt', 'w') as f:
        for lat, lon in cells:
            for q in DEEP_QUERIES:
                f.write(f'{q} {city["name"]} @{lat},{lon}\n')
    
    print(f'Created {len(cells)} cells × {len(DEEP_QUERIES)} queries = {len(cells)*len(DEEP_QUERIES)} lines')

if __name__ == '__main__':
    main()