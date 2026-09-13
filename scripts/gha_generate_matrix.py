#!/usr/bin/env python3
"""
Generate city query files for GitHub Actions matrix.
Usage: python3 scripts/gha_generate_matrix.py <mode> <selected_cities>
"""
import sys
import json
import math

CITIES = {
    'miami_fl': {'name': 'Miami, FL', 'bbox': (-80.3197600, 25.7090517, -80.1391570, 25.8557827)},
    'atlanta_ga': {'name': 'Atlanta, GA', 'bbox': (-84.5508540, 33.6479187, -84.2895600, 33.8868230)},
    'las_vegas_nv': {'name': 'Las Vegas, NV', 'bbox': (-115.4065750, 36.1295540, -115.0620660, 36.4014810)},
    'orlando_fl': {'name': 'Orlando, FL', 'bbox': (-81.5075377, 28.3480634, -81.1241435, 28.6142830)},
    'new_york_ny': {'name': 'New York, NY', 'bbox': (-74.2588430, 40.4765780, -73.7002330, 40.9176300)},
    'charlotte_nc': {'name': 'Charlotte, NC', 'bbox': (-81.0116951, 35.0105195, -80.6348755, 35.4002508)},
    'denver_co': {'name': 'Denver, CO', 'bbox': (-105.1098845, 39.6143008, -104.5996997, 39.9142087)},
    'san_francisco_ca': {'name': 'San Francisco, CA', 'bbox': (-123.1738250, 37.6403143, -122.2814578, 37.9296678)},
    'phoenix_az': {'name': 'Phoenix, AZ', 'bbox': (-112.3240289, 33.2904827, -111.9255304, 33.9183794)},
    'tampa_fl': {'name': 'Tampa, FL', 'bbox': (-82.6488200, 27.8126539, -82.2538678, 28.1713602)},
    'houston_tx': {'name': 'Houston, TX', 'bbox': (-95.9097419, 29.5370705, -95.0120525, 30.1103506)},
    'los_angeles_ca': {'name': 'Los Angeles, CA', 'bbox': (-118.6681798, 33.6595410, -118.1552983, 34.3373060)},
    'chicago_il': {'name': 'Chicago, IL', 'bbox': (-87.9400876, 41.6445310, -87.5241243, 42.0230529)},
    'dallas_tx': {'name': 'Dallas, TX', 'bbox': (-97.0004820, 32.6132160, -96.4636317, 33.0239366)},
    'washington_dc': {'name': 'Washington, DC', 'bbox': (-77.1197949, 38.7916303, -76.9093660, 38.9959680)},
}

QUICK_QUERIES = [
    'event planners', 'event organizers', 'event management companies',
    'wedding planners', 'corporate event planning',
]

DEEP_QUERIES = QUICK_QUERIES + [
    'conference organizers', 'trade show organizers', 'event production companies',
    'meeting planners', 'festival organizers', 'event venues',
    'event spaces rental', 'corporate event venues', 'convention services',
    'exhibition organizers',
]

def generate_matrix(mode, selected_cities):
    queries = QUICK_QUERIES if mode == 'quick' else DEEP_QUERIES
    
    if not selected_cities or selected_cities == ['']:
        selected_cities = list(CITIES.keys())
    
    matrix = []
    for key in selected_cities:
        if key not in CITIES:
            continue
        city = CITIES[key]
        minLat, minLon, maxLat, maxLon = city['bbox']
        center_lat = (minLat + maxLat) / 2
        cell_size = 1.0
        lat_step = cell_size / 111.0
        lon_step = cell_size / (111.0 * math.cos(math.radians(center_lat)))
        cells = 0
        lat = minLat + lat_step / 2
        while lat < maxLat:
            lon = minLon + lon_step / 2
            while lon < maxLon:
                cells += 1
                lon += lon_step
            lat += lat_step
        
        matrix.append({
            'key': key,
            'name': city['name'],
            'bbox': city['bbox'],
            'cells': cells,
            'queries': len(queries),
            'total': cells * len(queries)
        })
    
    return matrix

if __name__ == '__main__':
    mode = sys.argv[1] if len(sys.argv) > 1 else 'quick'
    selected = sys.argv[2].split(',') if len(sys.argv) > 2 else []
    matrix = generate_matrix(mode, selected)
    print(json.dumps(matrix))