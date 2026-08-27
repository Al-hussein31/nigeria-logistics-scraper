#!/usr/bin/env python3
"""Run city queries sequentially"""

import subprocess
import os
import time
import pandas as pd
import re

CITIES = [
    "Lagos", "Port_Harcourt", "Kano", "Ibadan", "Kaduna", 
    "Enugu", "Benin_City", "Aba", "Onitsha", "Owerri",
    "Warri", "Calabar", "Jos", "Maiduguri", "Sokoto",
    "Zaria", "Ilorin", "Abeokuta", "Akure", "Uyo"
]

WORK_DIR = "/Users/MAC/Desktop/meshgrdy/Real Leads"
QUERY_DIR = os.path.join(WORK_DIR, "city_queries")
OUTPUT_DIR = os.path.join(WORK_DIR, "city_results")
os.makedirs(OUTPUT_DIR, exist_ok=True)

def norm_name(s):
    if pd.isna(s): return ''
    return re.sub(r'[^a-z0-9]', '', str(s).lower())

def norm_phone(s):
    if pd.isna(s): return ''
    return re.sub(r'[^0-9]', '', str(s))

# Load master for dedup
master_path = os.path.join(WORK_DIR, "master_leads_growing.csv")
if os.path.exists(master_path):
    master = pd.read_csv(master_path)
    master['_key_name'] = master['businessName'].fillna(master['name']).apply(norm_name)
    master['_key_phone'] = master['phone'].apply(norm_phone)
    existing_names = set(master['_key_name'].dropna())
    existing_phones = set(master['_key_phone'].dropna())
    existing_phones.discard('')
else:
    existing_names = set()
    existing_phones = set()

total_new = 0

for city in CITIES:
    query_file = os.path.join(QUERY_DIR, f"{city}.txt")
    output_csv = os.path.join(OUTPUT_DIR, f"{city}.csv")
    
    if not os.path.exists(query_file):
        print(f"  Query file not found: {query_file}")
        continue
    
    print(f"\n{'='*50}")
    print(f"Scraping {city.replace('_', ' ')}...")
    print(f"{'='*50}")
    
    cmd = [
        "docker", "run", "--rm",
        "-v", f"{WORK_DIR}:/data",
        "gosom/google-maps-scraper",
        "-input", f"/data/city_queries/{city}.txt",
        "-results", f"/data/city_results/{city}.csv",
        "-depth", "5",
        "-c", "2",
        "-exit-on-inactivity", "10m",
        "-zoom", "16"
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=900)
        if result.returncode != 0:
            print(f"  ✗ Failed: {result.stderr[:200]}")
            continue
    except subprocess.TimeoutExpired:
        print(f"  ✗ Timeout")
        continue
    except Exception as e:
        print(f"  ✗ Error: {e}")
        continue
    
    # Process results
    if os.path.exists(output_csv) and os.path.getsize(output_csv) > 100:
        try:
            df = pd.read_csv(output_csv)
            print(f"  Raw results: {len(df)}")
            
            # Internal dedup
            df['_key_name'] = df['title'].apply(norm_name)
            df['_key_phone'] = df['phone'].apply(norm_phone)
            df = df.drop_duplicates(subset=['_key_name'], keep='first')
            df = df.drop_duplicates(subset=['_key_phone'], keep='first')
            
            # Filter vs master
            truly_new = df[
                (~df['_key_name'].isin(existing_names)) & 
                (~df['_key_phone'].isin(existing_phones) | (df['_key_phone'] == ''))
            ].copy()
            
            print(f"  New unique leads: {len(truly_new)}")
            
            if len(truly_new) > 0:
                # Add to master tracking
                for _, row in truly_new.iterrows():
                    existing_names.add(row['_key_name'])
                    if row['_key_phone'] != '':
                        existing_phones.add(row['_key_phone'])
                total_new += len(truly_new)
                
                # Save city's new leads
                new_file = os.path.join(OUTPUT_DIR, f"{city}_new.csv")
                truly_new.to_csv(new_file, index=False)
                
        except Exception as e:
            print(f"  Error processing: {e}")
    else:
        print(f"  No results or empty file")
    
    # Small delay
    time.sleep(5)

print(f"\n{'='*50}")
print(f"TOTAL NEW LEADS: {total_new}")
print(f"{'='*50}")
