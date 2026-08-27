#!/usr/bin/env python3
"""
Grid-based Google Maps scraper for Nigerian logistics companies.
Splits cities into batches of ~100 cells to avoid timeouts.
"""

import json
import math
import subprocess
import os
import time
from datetime import datetime
from pathlib import Path

# Nigerian cities with bounding boxes
CITIES = {
    "lagos": {"name": "Lagos", "bbox": (6.35, 3.15, 6.75, 3.65), "query": "logistics companies"},
    "port_harcourt": {"name": "Port Harcourt", "bbox": (4.65, 6.95, 5.05, 7.25), "query": "logistics companies"},
    "kano": {"name": "Kano", "bbox": (11.90, 8.40, 12.15, 8.70), "query": "logistics companies"},
    "ibadan": {"name": "Ibadan", "bbox": (7.25, 3.80, 7.55, 4.10), "query": "logistics companies"},
    "kaduna": {"name": "Kaduna", "bbox": (10.45, 7.30, 10.70, 7.60), "query": "logistics companies"},
    "enugu": {"name": "Enugu", "bbox": (6.35, 7.40, 6.60, 7.65), "query": "logistics companies"},
    "benin_city": {"name": "Benin City", "bbox": (6.25, 5.50, 6.50, 5.75), "query": "logistics companies"},
    "aba": {"name": "Aba", "bbox": (5.05, 7.30, 5.20, 7.50), "query": "logistics companies"},
    "onitsha": {"name": "Onitsha", "bbox": (6.05, 6.70, 6.25, 6.95), "query": "logistics companies"},
    "owerri": {"name": "Owerri", "bbox": (5.35, 6.95, 5.55, 7.15), "query": "logistics companies"},
    "warri": {"name": "Warri", "bbox": (5.45, 5.65, 5.65, 5.85), "query": "logistics companies"},
    "calabar": {"name": "Calabar", "bbox": (4.85, 8.25, 5.05, 8.45), "query": "logistics companies"},
    "jos": {"name": "Jos", "bbox": (9.80, 8.80, 10.00, 9.00), "query": "logistics companies"},
    "maiduguri": {"name": "Maiduguri", "bbox": (11.70, 13.00, 11.95, 13.25), "query": "logistics companies"},
    "sokoto": {"name": "Sokoto", "bbox": (12.95, 5.10, 13.20, 5.35), "query": "logistics companies"},
    "zaria": {"name": "Zaria", "bbox": (11.00, 7.60, 11.20, 7.85), "query": "logistics companies"},
    "ilorin": {"name": "Ilorin", "bbox": (8.40, 4.45, 8.60, 4.70), "query": "logistics companies"},
    "abeokuta": {"name": "Abeokuta", "bbox": (7.05, 3.25, 7.25, 3.50), "query": "logistics companies"},
    "akure": {"name": "Akure", "bbox": (7.15, 5.10, 7.35, 5.30), "query": "logistics companies"},
    "uyo": {"name": "Uyo", "bbox": (4.95, 7.85, 5.15, 8.05), "query": "logistics companies"},
}

CELL_SIZE_KM = 1.0
BATCH_SIZE = 100
WORK_DIR = Path("/Users/MAC/Desktop/meshgrdy/Real Leads")
OUTPUT_DIR = WORK_DIR / "grid_output"
OUTPUT_DIR.mkdir(exist_ok=True)

def haversine_km(lat1, lon1, lat2, lon2):
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))

def generate_grid_cells(bbox, cell_size_km):
    """Generate grid cell centers for a bounding box"""
    minLat, minLon, maxLat, maxLon = bbox
    center_lat = (minLat + maxLat) / 2
    
    # Calculate steps
    lat_step = cell_size_km / 111.0  # ~111 km per degree latitude
    lon_step = cell_size_km / (111.0 * math.cos(math.radians(center_lat)))
    
    cells = []
    lat = minLat + lat_step / 2
    while lat < maxLat:
        lon = minLon + lon_step / 2
        while lon < maxLon:
            cells.append((round(lat, 6), round(lon, 6)))
            lon += lon_step
        lat += lat_step
    return cells

def create_batch_files():
    """Create query files for each batch"""
    batch_files = []
    batch_num = 0
    
    for city_key, city in CITIES.items():
        cells = generate_grid_cells(city["bbox"], CELL_SIZE_KM)
        print(f"{city['name']}: {len(cells)} cells")
        
        # Split into batches
        for i in range(0, len(cells), BATCH_SIZE):
            batch_cells = cells[i:i+BATCH_SIZE]
            batch_num += 1
            
            # Create query file (same query for all cells, geo varies)
            query_file = OUTPUT_DIR / f"batch_{batch_num:04d}_{city_key}.txt"
            with open(query_file, "w") as f:
                for lat, lon in batch_cells:
                    f.write(f"{city['query']} @{lat},{lon}\n")
            
            batch_files.append({
                "batch_num": batch_num,
                "city": city_key,
                "city_name": city["name"],
                "query_file": str(query_file),
                "cell_count": len(batch_cells),
                "bbox": city["bbox"],
                "query": city["query"]
            })
    
    return batch_files

def run_batch(batch_info, output_csv):
    """Run a single batch with gosom scraper"""
    query_file = batch_info["query_file"]
    bbox_str = f"{batch_info['bbox'][0]},{batch_info['bbox'][1]},{batch_info['bbox'][2]},{batch_info['bbox'][3]}"
    
    cmd = [
        "docker", "run", "--rm",
        "-v", f"{WORK_DIR}:/data",
        "gosom/google-maps-scraper",
        "-input", f"/data/{query_file}",
        "-results", f"/data/{output_csv}",
        "-grid-bbox", bbox_str,
        "-grid-cell", str(CELL_SIZE_KM),
        "-depth", "5",
        "-c", "2",
        "-exit-on-inactivity", "10m",
        "-zoom", "16"
    ]
    
    print(f"\n[Batch {batch_info['batch_num']:04d}] {batch_info['city_name']} - {batch_info['cell_count']} cells")
    print(f"  Output: {output_csv}")
    print(f"  CMD: {' '.join(cmd[:8])} ...")
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=900)  # 15 min timeout
        if result.returncode == 0:
            print(f"  ✓ Success")
            return True
        else:
            print(f"  ✗ Failed (code {result.returncode})")
            print(f"  stderr: {result.stderr[:500]}")
            return False
    except subprocess.TimeoutExpired:
        print(f"  ✗ Timeout")
        return False
    except Exception as e:
        print(f"  ✗ Error: {e}")
        return False

def deduplicate_csv(csv_path):
    """Remove duplicates from CSV by place_id"""
    import pandas as pd
    if not os.path.exists(csv_path) or os.path.getsize(csv_path) < 100:
        return 0
    try:
        df = pd.read_csv(csv_path)
        if 'place_id' in df.columns:
            before = len(df)
            df = df.drop_duplicates(subset=['place_id'], keep='first')
            after = len(df)
            df.to_csv(csv_path, index=False)
            return after
        return len(df)
    except:
        return 0

def merge_all_results():
    """Merge all batch CSVs into master"""
    import pandas as pd
    all_dfs = []
    for f in OUTPUT_DIR.glob("batch_*.csv"):
        try:
            df = pd.read_csv(f)
            if len(df) > 0:
                all_dfs.append(df)
        except:
            pass
    
    if all_dfs:
        master = pd.concat(all_dfs, ignore_index=True)
        if 'place_id' in master.columns:
            master = master.drop_duplicates(subset=['place_id'], keep='first')
        master_path = WORK_DIR / "grid_master_leads.csv"
        master.to_csv(master_path, index=False)
        print(f"\n✓ Merged {len(master)} unique leads to {master_path}")
        return len(master)
    return 0

def main():
    print("=" * 60)
    print("GRID BATCH SCRAPER - Nigerian Logistics")
    print("=" * 60)
    
    # Create batch files
    print("\n1. Creating batch files...")
    batches = create_batch_files()
    print(f"   Total batches: {len(batches)}")
    
    # Save batch manifest
    manifest = OUTPUT_DIR / "batch_manifest.json"
    with open(manifest, "w") as f:
        json.dump(batches, f, indent=2)
    
    # Run batches
    print("\n2. Running batches...")
    successful = 0
    failed = 0
    
    for i, batch in enumerate(batches):
        output_csv = OUTPUT_DIR / f"batch_{batch['batch_num']:04d}_{batch['city']}.csv"
        
        if run_batch(batch, output_csv.name):
            count = deduplicate_csv(output_csv)
            print(f"  → {count} unique leads")
            successful += 1
        else:
            failed += 1
        
        # Progress
        print(f"  Progress: {i+1}/{len(batches)} | Success: {successful} | Failed: {failed}")
        
        # Small delay between batches
        time.sleep(5)
    
    # Merge all
    print("\n3. Merging results...")
    total = merge_all_results()
    
    print(f"\n{'='*60}")
    print(f"COMPLETE: {successful} successful, {failed} failed")
    print(f"Total unique leads: {total}")
    print(f"Results in: {OUTPUT_DIR}")
    print(f"{'='*60}")

if __name__ == "__main__":
    main()
