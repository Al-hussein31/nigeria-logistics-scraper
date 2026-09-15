#!/usr/bin/env python3
"""Merge deep mode GitHub Actions artifact results into 3-tier master files"""
import pandas as pd
import glob
import re
from pathlib import Path

def norm_name(s):
    if not s or pd.isna(s): return ''
    return re.sub(r'[^a-z0-9]', '', str(s).lower())

# Load existing masters
existing = pd.read_csv('master_leads_all.csv') if Path('master_leads_all.csv').exists() else pd.DataFrame()
existing_web = pd.read_csv('master_leads_with_website.csv') if Path('master_leads_with_website.csv').exists() else pd.DataFrame()
existing_email = pd.read_csv('master_leads_with_email.csv') if Path('master_leads_with_email.csv').exists() else pd.DataFrame()

all_new = pd.DataFrame()

for f in glob.glob('artifacts/*_deep-results.csv') + glob.glob('artifacts/*_results.csv'):
    try:
        df = pd.read_csv(f)
        if len(df) == 0: continue
        
        if 'place_id' in df.columns:
            df = df.drop_duplicates(subset=['place_id'], keep='first')
        
        city = f.split('/')[-1].split('_')[0]
        df['source_city'] = city
        all_new = pd.concat([all_new, df], ignore_index=True)
    except Exception as e:
        print(f'Error {f}: {e}')

if len(all_new) == 0:
    print('No new leads found')
    exit(0)

print(f'New leads from artifacts: {len(all_new)}')

# Combine with existing
if len(existing) > 0:
    combined = pd.concat([existing, all_new], ignore_index=True)
else:
    combined = all_new

combined = combined.drop_duplicates(subset=['place_id'], keep='first')

# Save 3-tier output
combined.to_csv('master_leads_all.csv', index=False)
web_df = combined[combined['website'].notna() & (combined['website'] != '')]
web_df.to_csv('master_leads_with_website.csv', index=False)
email_df = combined[combined['emails'].notna() & (combined['emails'] != '')]
email_df.to_csv('master_leads_with_email.csv', index=False)

print(f"FINAL: {len(combined)} unique leads")
print(f"  With website: {len(web_df)} ({len(web_df)/len(combined)*100:.0f}%)")
print(f"  With email: {len(email_df)} ({len(email_df)/len(combined)*100:.0f}%)")

# Per city breakdown
for city in combined['source_city'].unique():
    cdf = combined[combined['source_city'] == city]
    print(f"  {city}: {len(cdf)} leads, {cdf['website'].notna().sum()} web, {cdf['emails'].notna().sum()} email")