#!/usr/bin/env python3
"""Merge scraper artifact results into the 3-tier master files.

Robust to the actual actions/download-artifact layout:
  artifacts/<city>_deep.csv            (merge-multiple, flattened)
  artifacts/<city>-deep-results/<city>_deep.csv   (non-flattened)
  artifacts/<city>_results.csv / <city>_deep-results.csv   (legacy)
"""
import os
import re
import glob
from pathlib import Path

import pandas as pd

CITY_RE = re.compile(r'\s*copy(?:\(\d+\))?\s*$', re.I)


def city_from_path(f):
    base = os.path.basename(f)
    base = re.sub(r'\.csv$', '', base, flags=re.I)
    base = re.sub(r'[-_](deep-)?results$', '', base, flags=re.I)
    base = re.sub(r'_deep$', '', base, flags=re.I)
    base = CITY_RE.sub('', base)
    return base.strip('_- ')


def find_artifacts():
    """Only the directory the workflow downloads artifacts into."""
    root = os.environ.get('ARTIFACTS_DIR', 'artifacts')
    if not Path(root).exists():
        return []
    return sorted(glob.glob(os.path.join(root, '**', '*.csv'), recursive=True))


def is_real_value(series):
    s = series.astype(str).str.strip()
    return series.notna() & (s != '') & (s != '[]') & (s.str.lower() != 'nan')


def main():
    existing = pd.read_csv('master_leads_all.csv') if Path('master_leads_all.csv').exists() else pd.DataFrame()

    all_new = pd.DataFrame()
    for f in find_artifacts():
        try:
            df = pd.read_csv(f)
            if len(df) == 0:
                continue
            if 'place_id' in df.columns:
                df = df.drop_duplicates(subset=['place_id'], keep='first')
            city = city_from_path(f)
            df['source_city'] = city
            print(f'  + {city}: {len(df)} rows  ({f})')
            all_new = pd.concat([all_new, df], ignore_index=True)
        except Exception as e:
            print(f'Error {f}: {e}')

    if len(all_new) == 0:
        print('No new leads found')
        return

    print(f'New leads from artifacts: {len(all_new)}')

    combined = pd.concat([existing, all_new], ignore_index=True) if len(existing) else all_new
    if 'place_id' in combined.columns:
        combined = combined.drop_duplicates(subset=['place_id'], keep='first')
    else:
        combined = combined.drop_duplicates()

    combined.to_csv('master_leads_all.csv', index=False)

    web_col = 'website' if 'website' in combined.columns else None
    email_col = 'emails' if 'emails' in combined.columns else ('email' if 'email' in combined.columns else None)

    if web_col:
        web_df = combined[is_real_value(combined[web_col])]
        web_df.to_csv('master_leads_with_website.csv', index=False)
    if email_col:
        email_df = combined[is_real_value(combined[email_col])]
        email_df.to_csv('master_leads_with_email.csv', index=False)

    print(f'FINAL: {len(combined)} unique leads')
    if web_col:
        print(f'  With website: {len(web_df)} ({len(web_df) / len(combined) * 100:.0f}%)')
    if email_col:
        print(f'  With email: {len(email_df)} ({len(email_df) / len(combined) * 100:.0f}%)')

    if 'source_city' in combined.columns:
        for city in sorted(combined['source_city'].dropna().unique()):
            cdf = combined[combined['source_city'] == city]
            web = len(cdf[cdf[web_col].notna()]) if web_col else 0
            mail = len(cdf[cdf[email_col].notna()]) if email_col else 0
            print(f'  {city}: {len(cdf)} leads | {web} web | {mail} email')


if __name__ == '__main__':
    main()
