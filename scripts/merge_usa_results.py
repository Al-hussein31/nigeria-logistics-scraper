#!/usr/bin/env python3
"""
Merge USA Event Planners results from GitHub Actions artifacts.
Outputs THREE master files:
1. master_leads_all.csv - ALL leads (preserves everything)
2. master_leads_with_website.csv - Only leads with website
3. master_leads_with_email.csv - Only leads with email
"""
import pandas as pd
import glob
import re
from pathlib import Path

def norm_name(s):
    if not s or pd.isna(s): return ''
    return re.sub(r'[^a-z0-9]', '', str(s).lower())

def norm_phone(s):
    if not s or pd.isna(s): return ''
    return re.sub(r'[^0-9]', '', str(s))

# Load existing masters if they exist
masters = {}
for key, fname in [
    ('all', 'master_leads_all.csv'),
    ('web', 'master_leads_with_website.csv'),
    ('email', 'master_leads_with_email.csv'),
]:
    try:
        df = pd.read_csv(fname)
        df['_key_name'] = df['businessName'].fillna(df['name']).apply(norm_name)
        df['_key_phone'] = df['phone'].apply(norm_phone)
        masters[key] = {
            'df': df,
            'names': set(df['_key_name'].dropna()),
            'phones': set(df['_key_phone'].dropna()) - {''}
        }
        print(f'Loaded {key}: {len(df)} leads')
    except Exception:
        masters[key] = {'df': pd.DataFrame(), 'names': set(), 'phones': set()}
        print(f'No existing {key} master, starting fresh')

all_new = {'all': [], 'web': [], 'email': []}

for f in glob.glob('artifacts/*_results.csv'):
    try:
        df = pd.read_csv(f)
        if len(df) == 0:
            continue

        city = f.split('/')[-1].split('_')[0]
        print(f'Processing {city}: {len(df)} raw rows')

        # Dedupe within this city
        df['_key_name'] = df['title'].apply(norm_name)
        df['_key_phone'] = df['phone'].apply(norm_phone)
        df = df.drop_duplicates(subset=['_key_name'], keep='first')

        # Check against ALL master (most inclusive)
        existing_names = masters['all']['names']
        existing_phones = masters['all']['phones']
        
        both_match = df[
            (df['_key_name'].isin(existing_names)) &
            (df['_key_phone'].isin(existing_phones) & (df['_key_phone'] != ''))
        ]
        truly_new = df[~df.index.isin(both_match.index)].copy()
        truly_new = truly_new.drop_duplicates(subset=['_key_name'], keep='first')

        if len(truly_new) == 0:
            print(f'  {city}: 0 new')
            continue

        # Map to standard schema
        new_mapped = pd.DataFrame()
        new_mapped['id'] = [f'USA-{city.upper()}-{i}' for i in range(len(truly_new))]
        new_mapped['name'] = truly_new['title']
        new_mapped['businessName'] = truly_new['title']
        new_mapped['sector'] = 'events'
        new_mapped['subSector'] = truly_new.get('category', '')
        new_mapped['industry'] = truly_new.get('category', '')
        new_mapped['location'] = truly_new.get('address', '')
        new_mapped['district'] = ''
        new_mapped['phone'] = truly_new['phone']
        new_mapped['email'] = truly_new.get('emails', '')
        new_mapped['website'] = truly_new.get('website', '')
        new_mapped['source'] = f'github_actions_{city}'
        new_mapped['score'] = ''
        new_mapped['enrichmentLevel'] = 'basic'
        new_mapped['validationStatus'] = 'unverified'
        new_mapped['createdAt'] = pd.Timestamp.now().isoformat()
        new_mapped['slug'] = truly_new['title'].str.lower().str.replace(r'[^a-z0-9]+', '-', regex=True).str.strip('-')
        new_mapped['socialLinks'] = ''
        new_mapped['enriched'] = False
        new_mapped['folder'] = f'events/{city}'
        new_mapped['stage'] = 'discovered'
        new_mapped['whatsapp'] = ''
        new_mapped['review_count'] = truly_new.get('review_count', 0)
        new_mapped['review_rating'] = truly_new.get('review_rating', 0)
        new_mapped['latitude'] = truly_new.get('latitude', 0)
        new_mapped['longitude'] = truly_new.get('longitude', 0)
        new_mapped['place_id'] = truly_new.get('place_id', '')

        # Split into three categories
        with_web = new_mapped[new_mapped['website'].notna() & (new_mapped['website'] != '')]
        with_email = new_mapped[new_mapped['email'].notna() & (new_mapped['email'] != '')]

        all_new['all'].append(new_mapped)
        if len(with_web) > 0:
            all_new['web'].append(with_web)
        if len(with_email) > 0:
            all_new['email'].append(with_email)

        print(f'  {city}: +{len(new_mapped)} new | {len(with_web)} web | {len(with_email)} email')

        # Update tracking sets
        for _, row in truly_new.iterrows():
            masters['all']['names'].add(row['_key_name'])
            if row['_key_phone'] != '':
                masters['all']['phones'].add(row['_key_phone'])

    except Exception as e:
        print(f'Error processing {f}: {e}')

# Save each master
for key, fname in [
    ('all', 'master_leads_all.csv'),
    ('web', 'master_leads_with_website.csv'),
    ('email', 'master_leads_with_email.csv'),
]:
    if all_new[key]:
        new_df = pd.concat(all_new[key], ignore_index=True)
        if len(masters[key]['df']) > 0:
            combined = pd.concat([masters[key]['df'], new_df], ignore_index=True)
        else:
            combined = new_df
    else:
        combined = masters[key]['df']

    if len(combined) > 0:
        combined['_key_name'] = combined['businessName'].fillna(combined['name']).apply(lambda s: norm_name(s) if pd.notna(s) else '')
        combined['_key_phone'] = combined['phone'].apply(norm_phone)
        combined = combined.drop_duplicates(subset=['_key_name'], keep='first')
        combined = combined.drop(columns=['_key_name', '_key_phone'], errors='ignore')
        combined.to_csv(fname, index=False)
        print(f'Saved {key}: {len(combined)} leads → {fname}')
    else:
        print(f'No data for {key}')

print('\n=== SUMMARY ===')
for key, fname in [
    ('all', 'master_leads_all.csv'),
    ('web', 'master_leads_with_website.csv'),
    ('email', 'master_leads_with_email.csv'),
]:
    try:
        df = pd.read_csv(fname)
        print(f'{fname}: {len(df)} leads')
    except:
        print(f'{fname}: NOT CREATED')