#!/usr/bin/env python3
"""
Google Maps Scraper for Nigerian Logistics Companies
Runs on VPS with Docker + gosom/google-maps-scraper
"""

import os
import re
import json
import subprocess
import time
import pandas as pd
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Set

# ============================================================
# CONFIGURATION
# ============================================================
BASE_DIR = Path("/opt/scraper")
DATA_DIR = BASE_DIR / "data"
OUTPUT_DIR = BASE_DIR / "output"
LOGS_DIR = BASE_DIR / "logs"
SCRIPTS_DIR = BASE_DIR / "scripts"

for d in [DATA_DIR, OUTPUT_DIR, LOGS_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# Nigerian cities with bounding boxes for grid scraping
CITIES = [
    {"key": "lagos", "name": "Lagos", "bbox": (6.35, 3.15, 6.75, 3.65), "queries": 10},
    {"key": "port_harcourt", "name": "Port Harcourt", "bbox": (4.65, 6.95, 5.05, 7.25), "queries": 10},
    {"key": "kano", "name": "Kano", "bbox": (11.90, 8.40, 12.15, 8.70), "queries": 10},
    {"key": "ibadan", "name": "Ibadan", "bbox": (7.25, 3.80, 7.55, 4.10), "queries": 10},
    {"key": "kaduna", "name": "Kaduna", "bbox": (10.45, 7.30, 10.70, 7.60), "queries": 10},
    {"key": "enugu", "name": "Enugu", "bbox": (6.35, 7.40, 6.60, 7.65), "queries": 10},
    {"key": "benin_city", "name": "Benin City", "bbox": (6.25, 5.50, 6.50, 5.75), "queries": 10},
    {"key": "aba", "name": "Aba", "bbox": (5.05, 7.30, 5.20, 7.50), "queries": 10},
    {"key": "onitsha", "name": "Onitsha", "bbox": (6.05, 6.70, 6.25, 6.95), "queries": 10},
    {"key": "owerri", "name": "Owerri", "bbox": (5.35, 6.95, 5.55, 7.15), "queries": 10},
    {"key": "warri", "name": "Warri", "bbox": (5.45, 5.65, 5.65, 5.85), "queries": 10},
    {"key": "calabar", "name": "Calabar", "bbox": (4.85, 8.25, 5.05, 8.45), "queries": 10},
    {"key": "jos", "name": "Jos", "bbox": (9.80, 8.80, 10.00, 9.00), "queries": 10},
    {"key": "maiduguri", "name": "Maiduguri", "bbox": (11.70, 13.00, 11.95, 13.25), "queries": 10},
    {"key": "sokoto", "name": "Sokoto", "bbox": (12.95, 5.10, 13.20, 5.35), "queries": 10},
    {"key": "zaria", "name": "Zaria", "bbox": (11.00, 7.60, 11.20, 7.85), "queries": 10},
    {"key": "ilorin", "name": "Ilorin", "bbox": (8.40, 4.45, 8.60, 4.70), "queries": 10},
    {"key": "abeokuta", "name": "Abeokuta", "bbox": (7.05, 3.25, 7.25, 3.50), "queries": 10},
    {"key": "akure", "name": "Akure", "bbox": (7.15, 5.10, 7.35, 5.30), "queries": 10},
    {"key": "uyo", "name": "Uyo", "bbox": (4.95, 7.85, 5.15, 8.05), "queries": 10},
]

QUERIES_PER_CITY = [
    "logistics companies",
    "freight forwarders",
    "shipping companies",
    "customs brokers",
    "warehouse storage",
    "cold storage",
    "courier services",
    "haulage companies",
    "transport companies",
    "supply chain",
]

CELL_SIZE_KM = 1.0
BATCH_SIZE = 100
DOCKER_IMAGE = "gosom/google-maps-scraper"

# ============================================================
# UTILITIES
# ============================================================
def norm_name(s: str) -> str:
    if not s or pd.isna(s): return ''
    return re.sub(r'[^a-z0-9]', '', str(s).lower())

def norm_phone(s: str) -> str:
    if not s or pd.isna(s): return ''
    return re.sub(r'[^0-9]', '', str(s))

def get_unified_name(row) -> str:
    for col in ['businessName', 'name', 'title']:
        val = row.get(col)
        if pd.notna(val) and str(val).strip():
            return str(val).strip()
    return ''

def log(msg: str):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_msg = f"[{timestamp}] {msg}"
    print(log_msg)
    with open(LOGS_DIR / "scraper.log", "a") as f:
        f.write(log_msg + "\n")

# ============================================================
# GRID CELL GENERATION
# ============================================================
def generate_grid_cells(bbox: tuple, cell_size_km: float) -> List[tuple]:
    """Generate grid cell centers for a bounding box"""
    minLat, minLon, maxLat, maxLon = bbox
    center_lat = (minLat + maxLat) / 2
    
    lat_step = cell_size_km / 111.0
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

# ============================================================
# SCRAPER CLASS
# ============================================================
class NigeriaLogisticsScraper:
    def __init__(self):
        self.master_names: Set[str] = set()
        self.master_phones: Set[str] = set()
        self.total_new = 0
        self.load_master()
    
    def load_master(self):
        """Load existing master for deduplication"""
        master_path = DATA_DIR / "master_leads.parquet"
        if master_path.exists():
            df = pd.read_parquet(master_path)
            df['_key_name'] = df['unified_name'].apply(norm_name)
            df['_key_phone'] = df['phone'].apply(norm_phone)
            self.master_names = set(df['_key_name'].dropna())
            self.master_phones = set(df['_key_phone'].dropna())
            self.master_phones.discard('')
            log(f"Loaded master: {len(self.master_names)} names, {len(self.master_phones)} phones")
        else:
            log("No master file found, starting fresh")
    
    def save_master(self, df: pd.DataFrame):
        """Save master dataset"""
        df.to_parquet(DATA_DIR / "master_leads.parquet", index=False)
        df.to_csv(OUTPUT_DIR / f"master_leads_{datetime.now().strftime('%Y%m%d')}.csv", index=False)
        log(f"Saved master: {len(df)} leads")
    
    def create_query_files(self, city: dict) -> List[Path]:
        """Create query files for a city, split into batches"""
        cells = generate_grid_cells(city["bbox"], CELL_SIZE_KM)
        log(f"{city['name']}: {len(cells)} grid cells")
        
        query_dir = DATA_DIR / "queries" / city["key"]
        query_dir.mkdir(parents=True, exist_ok=True)
        
        batch_files = []
        batch_num = 0
        
        # Create batches of grid cells
        for i in range(0, len(cells), BATCH_SIZE):
            batch_cells = cells[i:i+BATCH_SIZE]
            batch_num += 1
            
            query_file = query_dir / f"batch_{batch_num:04d}.txt"
            with open(query_file, "w") as f:
                for lat, lon in batch_cells:
                    for q in QUERIES_PER_CITY:
                        f.write(f"{q} {city['name']} @{lat},{lon}\n")
            
            batch_files.append(query_file)
        
        log(f"Created {len(batch_files)} batch files for {city['name']}")
        return batch_files
    
    def run_batch(self, city: dict, batch_file: Path, output_csv: Path) -> bool:
        """Run a single batch with gosom scraper"""
        bbox_str = f"{city['bbox'][0]},{city['bbox'][1]},{city['bbox'][2]},{city['bbox'][3]}"
        
        cmd = [
            "docker", "run", "--rm",
            "-v", f"{BASE_DIR}:/data",
            DOCKER_IMAGE,
            "-input", f"/data/{batch_file.relative_to(BASE_DIR)}",
            "-results", f"/data/{output_csv.relative_to(BASE_DIR)}",
            "-grid-bbox", bbox_str,
            "-grid-cell", str(CELL_SIZE_KM),
            "-depth", "5",
            "-c", "2",
            "-exit-on-inactivity", "15m",
            "-zoom", "16"
        ]
        
        log(f"Running batch: {output_csv.name}")
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=1200)
            return result.returncode == 0
        except subprocess.TimeoutExpired:
            log(f"  Timeout: {output_csv.name}")
            return False
        except Exception as e:
            log(f"  Error: {e}")
            return False
    
    def process_results(self, city: dict, output_csv: Path) -> int:
        """Process and deduplicate results"""
        if not output_csv.exists() or output_csv.stat().st_size < 100:
            return 0
        
        try:
            df = pd.read_csv(output_csv)
            if len(df) == 0:
                return 0
            
            # Internal dedup
            df['_key_name'] = df['title'].apply(norm_name)
            df['_key_phone'] = df['phone'].apply(norm_phone)
            df = df.drop_duplicates(subset=['_key_name'], keep='first')
            
            # Filter vs master
            both_match = df[
                (df['_key_name'].isin(self.master_names)) & 
                (df['_key_phone'].isin(self.master_phones) & (df['_key_phone'] != ''))
            ]
            truly_new = df[~df.index.isin(both_match.index)].copy()
            truly_new = truly_new.drop_duplicates(subset=['_key_name'], keep='first')
            
            if len(truly_new) == 0:
                return 0
            
            # Map to master schema
            new_mapped = pd.DataFrame()
            new_mapped['id'] = [f"{city['key'].upper()}-{i}" for i in range(len(truly_new))]
            new_mapped['name'] = truly_new['title']
            new_mapped['businessName'] = truly_new['title']
            new_mapped['sector'] = 'logistics'
            new_mapped['subSector'] = ''
            new_mapped['industry'] = truly_new.get('category', '')
            new_mapped['location'] = truly_new.get('address', '')
            new_mapped['district'] = ''
            new_mapped['phone'] = truly_new['phone']
            new_mapped['email'] = truly_new.get('emails', '')
            new_mapped['website'] = truly_new.get('website', '')
            new_mapped['source'] = f'google_maps_scraper_{city["key"]}'
            new_mapped['score'] = ''
            new_mapped['enrichmentLevel'] = 'basic'
            new_mapped['validationStatus'] = 'unverified'
            new_mapped['createdAt'] = datetime.now().isoformat()
            new_mapped['slug'] = truly_new['title'].str.lower().str.replace(r'[^a-z0-9]+', '-', regex=True).str.strip('-')
            new_mapped['socialLinks'] = ''
            new_mapped['enriched'] = False
            new_mapped['folder'] = f'logistics/{city["key"]}'
            new_mapped['stage'] = 'discovered'
            new_mapped['whatsapp'] = ''
            new_mapped['review_count'] = truly_new.get('review_count', 0)
            new_mapped['review_rating'] = truly_new.get('review_rating', 0)
            new_mapped['latitude'] = truly_new.get('latitude', 0)
            new_mapped['longitude'] = truly_new.get('longitude', 0)
            new_mapped['place_id'] = truly_new.get('place_id', '')
            new_mapped['unified_name'] = truly_new['title']
            
            # Update tracking
            for _, row in truly_new.iterrows():
                self.master_names.add(row['_key_name'])
                if row['_key_phone'] != '':
                    self.master_phones.add(row['_key_phone'])
            
            return len(new_mapped)
            
        except Exception as e:
            log(f"Error processing results: {e}")
            return 0
    
    def scrape_city(self, city: dict):
        """Scrape a single city"""
        log(f"\n{'='*50}")
        log(f"SCRAPING {city['name'].upper()}")
        log(f"{'='*50}")
        
        batch_files = self.create_query_files(city)
        city_new = 0
        
        for batch_file in batch_files:
            batch_num = batch_file.stem
            output_csv = OUTPUT_DIR / f"{city['key']}_{batch_num}.csv"
            
            if self.run_batch(city, batch_file, output_csv):
                new_count = self.process_results(city, output_csv)
                city_new += new_count
                log(f"  {batch_num}: +{new_count} new leads")
            else:
                log(f"  {batch_num}: FAILED")
            
            time.sleep(10)  # Rate limiting between batches
        
        self.total_new += city_new
        log(f"{city['name']} complete: +{city_new} new leads")
        return city_new
    
    def run(self):
        """Main entry point - scrape all cities"""
        log("Starting Nigeria Logistics Scraper")
        log(f"Target cities: {len(CITIES)}")
        
        # Pull latest Docker image
        subprocess.run(["docker", "pull", DOCKER_IMAGE], capture_output=True)
        
        for city in CITIES:
            try:
                self.scrape_city(city)
            except Exception as e:
                log(f"Error scraping {city['name']}: {e}")
                continue
        
        # Save final master
        master_path = DATA_DIR / "master_leads.parquet"
        if master_path.exists():
            final_df = pd.read_parquet(master_path)
            self.save_master(final_df)
        
        log(f"\n{'='*50}")
        log(f"COMPLETE: Total new leads: {self.total_new}")
        log(f"{'='*50}")

if __name__ == "__main__":
    import math
    scraper = NigeriaLogisticsScraper()
    scraper.run()
