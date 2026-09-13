#!/usr/bin/env python3
"""Summarize scrape results"""
import sys
import pandas as pd

def main():
    city = sys.argv[1] if len(sys.argv) > 1 else 'miami_fl'
    fpath = f'city_results/{city}.csv'
    
    try:
        df = pd.read_csv(fpath)
        print(f'Total: {len(df)}')
        print(f'With website: {df["website"].notna().sum()}')
        print(f'With emails: {df["emails"].notna().sum()}')
    except FileNotFoundError:
        print(f'No results file: {fpath}')

if __name__ == '__main__':
    main()