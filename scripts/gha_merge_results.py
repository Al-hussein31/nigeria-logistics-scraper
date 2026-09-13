#!/usr/bin/env python3
"""
Merge GitHub Actions artifact results into 3-tier master files.
"""
import pandas as pd
import glob
import re

def norm_name(s):
    if not s or pd.isna(s): return ''
    return re.sub(r'[^a-z0-9]', '', str(s).lower())

def norm_phone(s):
    if not s or pd.isna(s): return ''
    return re.sub(r'[^0-9]', '', str(s))

master_all = pd.DataFrame()
master_web = pd.DataFrame()
master_email = pd.DataFrame()

for f in glob.glob('artifacts/*_results.csv'):
    try:
        df = pd.read_csv(f)
        if len(df) == 0: continue
        
        if 'place_id' in df.columns:
            df = df.drop_duplicates(subset=['place_id'], keep='first')
        
        city = f.split('/')[-1].split('_')[0]
        df['source_city'] = city
        
        master_all = pd.concat([master_all, df], ignore_index=True)
        web_df = df[df['website'].notna() & (df['website'] != '')]
        if len(web_df) > 0:
            master_web = pd.concat([master_web, web_df], ignore_index=True)
        email_df = df[df['emails'].notna() & (df['emails'] != '')]
        if len(email_df) > 0:
            master_email = pd.concat([master_email, email_df], ignore_index=True)
    except Exception as e:
        print(f'Error {f}: {e}')

# Deduplicate
for name, df in [('all', master_all), ('web', master_web), ('email', master_email)]:
    if len(df) > 0:
        df['_key'] = df['title'].apply(norm_name)
        df = df.drop_duplicates(subset=['_key'], keep='first')
        df = df.drop(columns=['_key'])
        df.to_csv(f'master_leads_{name}.csv', index=False)
        print(f'master_leads_{name}.csv: {len(df)} leads')

print(f'TOTAL: all={len(master_all)}, web={len(master_web)}, email={len(master_email)}')