#!/usr/bin/env python3
"""
Orchestrator: Deploys to VPS and/or triggers GitHub Actions
"""

import os
import subprocess
import sys
import argparse
from pathlib import Path

REPO_ROOT = Path("/Users/MAC/Desktop/meshgrdy/Real Leads")
DEPLOY_DIR = REPO_ROOT / "deploy"

def run_cmd(cmd, cwd=None):
    print(f"$ {cmd}")
    result = subprocess.run(cmd, shell=True, cwd=cwd, capture_output=True, text=True)
    if result.stdout: print(result.stdout)
    if result.stderr: print(result.stderr, file=sys.stderr)
    return result.returncode == 0

def deploy_vps():
    """Deploy to OCI VPS"""
    print("=== Deploying to OCI VPS ===")
    
    # SSH into VPS and run setup
    setup_script = DEPLOY_DIR / "vps/scripts/setup_vps.sh"
    if not setup_script.exists():
        print("Setup script not found!")
        return False
    
    # Copy files to VPS
    print("Copying files to VPS...")
    run_cmd(f"scp -r {DEPLOY_DIR}/vps/scripts/ oci-a1:/tmp/scraper_scripts/")
    run_cmd(f"scp -r {REPO_ROOT}/master_leads_growing.csv oci-a1:/tmp/master_leads.csv")
    
    # Run setup on VPS
    print("Running setup on VPS...")
    run_cmd("ssh oci-a1 'sudo bash /tmp/scraper_scripts/setup_vps.sh'")
    
    # Copy application code
    run_cmd("ssh oci-a1 'sudo cp -r /tmp/scraper_scripts/* /opt/scraper/scripts/'")
    run_cmd("ssh oci-a1 'sudo cp /tmp/master_leads.csv /opt/scraper/data/master_leads.csv'")
    run_cmd("ssh oci-a1 'sudo chown -R scraper:scraper /opt/scraper'")
    
    # Start service
    run_cmd("ssh oci-a1 'sudo systemctl start scraper'")
    run_cmd("ssh oci-a1 'sudo systemctl status scraper'")
    
    print("VPS deployment complete!")
    return True

def trigger_github_actions(cities=None, cell_size=1.0, max_cells=50):
    """Trigger GitHub Actions workflow"""
    print("=== Triggering GitHub Actions ===")
    
    # This requires gh CLI authenticated
    cmd = ["gh", "workflow", "run", "scrape-cities.yml"]
    if cities:
        cmd.extend(["-f", f"cities={cities}"])
    cmd.extend(["-f", f"cell_size_km={cell_size}"])
    cmd.extend(["-f", f"max_cells_per_job={max_cells}"])
    
    return run_cmd(" ".join(cmd))

def run_local_test(city="lagos", queries=3):
    """Quick local test"""
    print(f"=== Local test: {city} ===")
    
    query_file = REPO_ROOT / f"test_{city}.txt"
    queries_list = [
        "logistics companies",
        "freight forwarders", 
        "shipping companies"
    ][:queries]
    
    with open(query_file, "w") as f:
        for q in queries_list:
            f.write(f"{q} {city.title()}\n")
    
    cmd = f"docker run --rm -v {REPO_ROOT}:/data gosom/google-maps-scraper -input /data/{query_file.name} -results /data/test_{city}_results.csv -depth 3 -c 1 -exit-on-inactivity 5m -zoom 15"
    return run_cmd(cmd)

def sync_from_vps():
    """Pull latest data from VPS"""
    print("=== Syncing from VPS ===")
    run_cmd("scp oci-a1:/opt/scraper/data/master_leads.parquet /tmp/master_latest.parquet")
    run_cmd(f"cp /tmp/master_latest.parquet {REPO_ROOT}/master_leads_latest.parquet")
    print("Synced! Check master_leads_latest.parquet")

def sync_from_github():
    """Pull latest from GitHub Actions artifact"""
    print("=== Syncing from GitHub ===")
    run_cmd("gh run download -n master-leads -D /tmp/gh_master")
    run_cmd(f"cp /tmp/gh_master/master_leads.csv {REPO_ROOT}/master_leads_gh.csv")
    print("Synced! Check master_leads_gh.csv")

def merge_all():
    """Merge all sources into one master"""
    print("=== Merging all sources ===")
    
    import pandas as pd
    import re
    import glob
    
    def norm_name(s):
        if not s or pd.isna(s): return ''
        return re.sub(r'[^a-z0-9]', '', str(s).lower())
    
    def norm_phone(s):
        if not s or pd.isna(s): return ''
        return re.sub(r'[^0-9]', '', str(s))
    
    files = [
        REPO_ROOT / "master_leads_growing.csv",
        REPO_ROOT / "master_leads_latest.parquet",
        REPO_ROOT / "master_leads_gh.csv",
    ]
    
    combined = pd.DataFrame()
    
    for f in files:
        if f.exists():
            try:
                if f.suffix == '.parquet':
                    df = pd.read_parquet(f)
                else:
                    df = pd.read_csv(f)
                print(f"Loaded {len(df)} from {f.name}")
                combined = pd.concat([combined, df], ignore_index=True)
            except Exception as e:
                print(f"Error loading {f}: {e}")
    
    if len(combined) == 0:
        print("No data to merge!")
        return
    
    # Dedup
    combined['_key_name'] = combined['businessName'].fillna(combined['name']).apply(
        lambda s: re.sub(r'[^a-z0-9]', '', str(s).lower()) if pd.notna(s) else ''
    )
    combined['_key_phone'] = combined['phone'].apply(
        lambda s: re.sub(r'[^0-9]', '', str(s)) if pd.notna(s) else ''
    )
    
    before = len(combined)
    combined = combined.drop_duplicates(subset=['_key_name'], keep='first')
    combined = combined.drop_duplicates(subset=['_key_phone'], keep='first')
    combined = combined.drop(columns=['_key_name', '_key_phone'], errors='ignore')
    
    print(f"Merged: {before} -> {len(combined)} unique leads")
    
    output = REPO_ROOT / "MASTER_LEADS_FINAL.csv"
    combined.to_csv(output, index=False)
    print(f"Saved to {output}")

def main():
    parser = argparse.ArgumentParser(description="Nigeria Logistics Scraper Orchestrator")
    subparsers = parser.add_subparsers(dest='command', required=True)
    
    # VPS deploy
    subparsers.add_parser('deploy-vps', help='Deploy to OCI VPS')
    
    # GitHub Actions
    gh = subparsers.add_parser('trigger-gh', help='Trigger GitHub Actions')
    gh.add_argument('--cities', help='Comma-separated cities')
    gh.add_argument('--cell-size', type=float, default=1.0)
    gh.add_argument('--max-cells', type=int, default=50)
    
    # Local test
    local = subparsers.add_parser('test-local', help='Quick local test')
    local.add_argument('--city', default='lagos')
    local.add_argument('--queries', type=int, default=3)
    
    # Sync
    subparsers.add_parser('sync-vps', help='Pull data from VPS')
    subparsers.add_parser('sync-gh', help='Pull data from GitHub Actions')
    
    # Merge
    subparsers.add_parser('merge', help='Merge all sources')
    
    args = parser.parse_args()
    
    if args.command == 'deploy-vps':
        deploy_vps()
    elif args.command == 'trigger-gh':
        trigger_github_actions(args.cities, args.cell_size, args.max_cells)
    elif args.command == 'test-local':
        run_local_test(args.city, args.queries)
    elif args.command == 'sync-vps':
        sync_from_vps()
    elif args.command == 'sync-gh':
        sync_from_github()
    elif args.command == 'merge':
        merge_all()

if __name__ == "__main__":
    main()
