#!/usr/bin/env python3
import pandas as pd
import glob
import re

def norm_name(s):
    if not s or pd.isna(s): return ''
    return re.sub(r'[^a-z0-9]', '', str(s).lower())

def norm_phone(s):
    if not s or pd.isna(s): return ''
    return re.sub(r'[^0-9]', '', str(s))

try:
    master = pd.read_csv('master_leads.csv')
    master['_key_name'] = master['businessName'].fillna(master['name']).apply(norm_name)
    master['_key_phone'] = master['phone'].apply(norm_phone)
    existing_names = set(master['_key_name'].dropna())
    existing_phones = set(master['_key_phone'].dropna())
    existing_phones.discard('')
    print(f'Loaded master: {len(master)} leads')
except Exception:
    master = pd.DataFrame()
    existing_names = set()
    existing_phones = set()
    print('No existing master, starting fresh')

all_new = []
for f in glob.glob('artifacts/*_results.csv'):
    try:
        df = pd.read_csv(f)
        if len(df) == 0:
            continue

        df['_key_name'] = df['title'].apply(norm_name)
        df['_key_phone'] = df['phone'].apply(norm_phone)
        df = df.drop_duplicates(subset=['_key_name'], keep='first')

        both_match = df[
            (df['_key_name'].isin(existing_names)) &
            (df['_key_phone'].isin(existing_phones) & (df['_key_phone'] != ''))
        ]
        truly_new = df[~df.index.isin(both_match.index)].copy()
        truly_new = truly_new.drop_duplicates(subset=['_key_name'], keep='first')

        if len(truly_new) > 0:
            new_mapped = pd.DataFrame()
            new_mapped['id'] = [f'GHA-{i}' for i in range(len(truly_new))]
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
            new_mapped['source'] = 'github_actions_' + f.split('/')[-1].split('_')[0]
            new_mapped['score'] = ''
            new_mapped['enrichmentLevel'] = 'basic'
            new_mapped['validationStatus'] = 'unverified'
            new_mapped['createdAt'] = pd.Timestamp.now().isoformat()
            new_mapped['slug'] = truly_new['title'].str.lower().str.replace(r'[^a-z0-9]+', '-', regex=True).str.strip('-')
            new_mapped['socialLinks'] = ''
            new_mapped['enriched'] = False
            new_mapped['folder'] = 'logistics/github_actions'
            new_mapped['stage'] = 'discovered'
            new_mapped['whatsapp'] = ''
            new_mapped['review_count'] = truly_new.get('review_count', 0)
            new_mapped['review_rating'] = truly_new.get('review_rating', 0)
            new_mapped['latitude'] = truly_new.get('latitude', 0)
            new_mapped['longitude'] = truly_new.get('longitude', 0)
            new_mapped['place_id'] = truly_new.get('place_id', '')

            all_new.append(new_mapped)
            print(f'  {f}: +{len(truly_new)} new')

            for _, row in truly_new.iterrows():
                existing_names.add(row['_key_name'])
                if row['_key_phone'] != '':
                    existing_phones.add(row['_key_phone'])
    except Exception as e:
        print(f'Error processing {f}: {e}')

if all_new:
    new_df = pd.concat(all_new, ignore_index=True)
    if len(master) > 0:
        combined = pd.concat([master, new_df], ignore_index=True)
    else:
        combined = new_df

    combined['_key_name'] = combined['businessName'].fillna(combined['name']).apply(lambda s: norm_name(s) if pd.notna(s) else '')
    combined['_key_phone'] = combined['phone'].apply(norm_phone)
    combined = combined.drop_duplicates(subset=['_key_name'], keep='first')
    combined = combined.drop(columns=['_key_name', '_key_phone'], errors='ignore')

    combined.to_csv('master_leads.csv', index=False)
    print(f'Master updated: {len(combined)} total leads')
else:
    if len(master) > 0:
        master.to_csv('master_leads.csv', index=False)
        print(f'No new leads, master unchanged: {len(master)}')
