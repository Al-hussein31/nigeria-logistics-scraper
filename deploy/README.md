# Nigeria Logistics Scraper - Deployment Guide

## Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  GitHub Actions │     │   OCI VPS       │     │   Local Machine │
│  (Free, Parallel)│────▶│  (Continuous)   │◀───▶│  (Orchestration)│
└─────────────────┘     └─────────────────┘     └─────────────────┘
        │                       │                       │
        ▼                       ▼                       ▼
   20 cities ×          Grid scraping          Merge & deduplicate
   10 queries =         1km cells              Master CSV/Parquet
   200 jobs                                           │
                                                       ▼
                                              Outreach / CRM
```

## Quick Start

### 1. Local Test
```bash
cd /Users/MAC/Desktop/meshgrdy/Real Leads
python3 deploy/orchestrator.py test-local --city lagos --queries 3
```

### 2. Deploy to VPS (OCI ARM)
```bash
python3 deploy/orchestrator.py deploy-vps
```

### 3. Trigger GitHub Actions (Free, Parallel)
```bash
# All cities
python3 deploy/orchestrator.py trigger-gh

# Specific cities
python3 deploy/orchestrator.py trigger-gh --cities "lagos,port_harcourt,kano"

# Smaller cells for more coverage
python3 deploy/orchestrator.py trigger-gh --cell-size 0.5 --max-cells 30
```

### 4. Sync & Merge
```bash
# Pull from VPS
python3 deploy/orchestrator.py sync-vps

# Pull from GitHub
python3 deploy/orchestrator.py sync-gh

# Merge all sources
python3 deploy/orchestrator.py merge
```

## VPS Details (OCI ARM)
- **Host**: `oci-a1` (defined in ~/.ssh/config)
- **IP**: 141.148.153.48
- **Specs**: 2 OCPU / 12 GB RAM / 100 GB disk
- **User**: ubuntu
- **Service**: `scraper` (systemd)

### VPS Commands
```bash
# Check status
ssh oci-a1 'sudo systemctl status scraper'

# View logs
ssh oci-a1 'sudo journalctl -u scraper -f'

# Manual run
ssh oci-a1 'sudo -u scraper /opt/scraper/venv/bin/python /opt/scraper/scripts/scraper.py'

# Check data
ssh oci-a1 'ls -la /opt/scraper/data/'
ssh oci-a1 'ls -la /opt/scraper/output/'
```

## GitHub Actions
- **Workflow**: `.github/workflows/scrape-cities.yml`
- **Parallelism**: 5 concurrent jobs (max-parallel: 5)
- **Timeout**: 60 min per job
- **Artifacts**: 7-day retention
- **Auto-commit**: Master CSV committed on main branch

### Trigger from CLI
```bash
gh workflow run scrape-cities.yml \
  -f cities="lagos,port_harcourt,kano,ibadan,kaduna" \
  -f cell_size_km=1.0 \
  -f max_cells_per_job=50
```

### Monitor
```bash
gh run list --workflow=scrape-cities.yml
gh run watch <run-id>
```

## Data Flow

1. **GitHub Actions** runs 200 parallel jobs (20 cities × 10 queries)
2. **VPS** runs continuous grid scraping (1km cells)
3. Both output CSV → uploaded as artifacts / saved to VPS disk
4. **Orchestrator** merges all sources → `MASTER_LEADS_FINAL.csv`
5. **Master** used for outreach, CRM import, etc.

## Estimated Output

| Source | Cities | Queries | Cells/Job | Est. Leads |
|--------|--------|---------|-----------|------------|
| GitHub Actions | 20 | 10 | 50 | 5,000-15,000 |
| VPS (continuous) | 20 | 10 | Full grid | 10,000-30,000 |
| **Combined (deduped)** | | | | **5,000-20,000** |

## Costs

| Component | Cost |
|-----------|------|
| GitHub Actions | Free (public repo) |
| OCI ARM VPS | Free (Always Free tier) |
| Docker Hub | Free |
| **Total** | **$0/month** |

## Troubleshooting

### Scraper stuck
```bash
ssh oci-a1 'sudo systemctl restart scraper'
```

### Out of memory
```bash
# Reduce concurrency in scraper.py: -c 1 instead of -c 2
# Or increase swap
ssh oci-a1 'sudo fallocate -l 4G /swapfile && sudo chmod 600 /swapfile && sudo mkswap /swapfile && sudo swapon /swapfile'
```

### Docker issues
```bash
ssh oci-a1 'docker system prune -af'
```

### GitHub Actions timeout
- Reduce `max_cells_per_job` (default 50)
- Reduce `cell_size_km` for finer grid but more jobs
- Increase `exit-on-inactivity` timeout

## Files Structure

```
deploy/
├── orchestrator.py           # Main deployment script
├── github_actions/
│   └── scrape-cities.yml     # GitHub Actions workflow
├── vps/
│   ├── docker/
│   │   └── Dockerfile        # Scraper container
│   ├── scripts/
│   │   ├── setup_vps.sh      # VPS provisioning
│   │   └── scraper.py        # Main scraper (runs in venv)
│   └── systemd/
│       └── scraper.service   # Systemd service
└── README.md                 # This file
```

## Next Steps

1. **Run local test** → `python3 deploy/orchestrator.py test-local`
2. **Deploy to VPS** → `python3 deploy/orchestrator.py deploy-vps`
3. **Trigger GitHub Actions** → `python3 deploy/orchestrator.py trigger-gh`
4. **Monitor** → Check logs, merge results weekly
5. **Scale** → Add more cities, reduce cell size, add proxies
