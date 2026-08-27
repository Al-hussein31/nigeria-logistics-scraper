#!/usr/bin/env python3
"""Sync leads from master_leads_growing.csv into the Notion Leads database.

For every lead in the CSV that is NOT already in the database:
  1. Creates an individual details page under "Cold outbound"
  2. Creates a row in the "Leads" database
  3. Links the row's Details column to the details page as a native page mention

Idempotent: re-running skips leads that are already present (matched by phone, fallback name).

Usage:
    python3 sync_leads_to_notion.py            # add up to 100 new leads
    python3 sync_leads_to_notion.py --limit 5  # add only the next 5 new leads
    python3 sync_leads_to_notion.py --csv other.csv
"""
import argparse
import csv
import os
import re
import sys
import time

import requests

NOTION_TOKEN = os.environ.get("NOTION_TOKEN") or ""

API = "https://api.notion.com/v1"
VERSION = "2025-09-03"  # new data-source format

LEADS_DB = "3c93c723-099f-804f-a2c8-000bc1368149"   # Leads data source (for query)
LEADS_DB_ID = "3c93c723-099f-80e9-81dd-e154ce8adfd9"  # Leads database_id (for page parent / stats)
LEADS_DETAILS_PAGE = "3c93c723-099f-81d0-ab0a-f6183b138b19"  # parent page for detail pages

HEADERS = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Notion-Version": VERSION,
    "Content-Type": "application/json",
}


def load_token():
    global NOTION_TOKEN
    if NOTION_TOKEN:
        return
    env_path = os.path.expanduser("~/.config/opencode/.env")
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                if line.startswith("NOTION_TOKEN="):
                    NOTION_TOKEN = line.split("=", 1)[1].strip()
                    break
    if not NOTION_TOKEN:
        sys.exit("NOTION_TOKEN not found in env or ~/.config/opencode/.env")


def api(method, path, payload=None):
    url = f"{API}{path}"
    headers = {
        "Authorization": f"Bearer {NOTION_TOKEN}",
        "Notion-Version": VERSION,
        "Content-Type": "application/json",
    }
    r = requests.request(method, url, headers=headers, json=payload)
    if r.status_code >= 400:
        body = r.text[:500]
        raise RuntimeError(f"{method} {path} -> {r.status_code}: {body}")
    return r.json()


def normalize_phone(p):
    if not p:
        return ""
    digits = re.sub(r"\D", "", p)
    if digits.startswith("234") and not digits.startswith("2340"):
        return digits
    if digits.startswith("0"):
        return "234" + digits[1:]
    return digits


def fetch_existing():
    """Return {normalized_phone: name} for all rows already in the Leads DB."""
    existing = {}
    cursor = None
    while True:
        payload = {"page_size": 100}
        if cursor:
            payload["start_cursor"] = cursor
        data = api("POST", f"/data_sources/{LEADS_DB}/query", payload)
        for row in data.get("results", []):
            props = row.get("properties", {})
            phone = ""
            ph = props.get("Phone", {}).get("phone_number")
            if ph:
                phone = normalize_phone(ph)
            name = ""
            title = props.get("Name", {}).get("title", [])
            if title:
                name = title[0].get("plain_text", "")
            if phone:
                existing[phone] = name
            elif name:
                existing["name:" + name.lower().strip()] = name
        cursor = data.get("next_cursor")
        if not cursor or not data.get("has_more"):
            break
    return existing


def read_leads(csv_path):
    leads = []
    with open(csv_path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            name = (row.get("name") or row.get("Name") or "").strip()
            if not name:
                continue
            leads.append({
                "name": name,
                "business": (row.get("businessName") or name).strip(),
                "sector": (row.get("sector") or row.get("Sector") or "").strip(),
                "subsector": (row.get("subSector") or "").strip(),
                "phone": (row.get("phone") or row.get("Phone") or "").strip(),
                "email": (row.get("email") or row.get("Email") or "").strip(),
                "website": (row.get("website") or row.get("Website") or "").strip(),
                "location": (row.get("location") or row.get("Location") or "").strip(),
                "stage": (row.get("stage") or row.get("Stage") or "").strip(),
                "score": (row.get("score") or row.get("Score") or "").strip(),
                "whatsapp": (row.get("whatsapp") or row.get("WhatsApp") or "").strip().upper(),
                "social": (row.get("socialLinks") or "").strip(),
                "source": (row.get("source") or row.get("_source") or row.get("_sources") or "").strip(),
                "enriched": (row.get("enriched") or "").strip(),
                "folder": (row.get("folder") or "").strip(),
                "key_name": (row.get("keyPeople_name") or "").strip(),
                "key_title": (row.get("keyPeople_title") or "").strip(),
                "key_email": (row.get("keyPeople_email") or "").strip(),
                "key_phone": (row.get("keyPeople_phone") or "").strip(),
                "key_linkedin": (row.get("keyPeople_linkedin") or "").strip(),
            })
    return leads


def create_details_page(lead):
    """Create the individual details page under Cold outbound, return its page id."""
    title = lead["business"]
    blocks = [
        {"type": "heading_1", "heading_1": {"rich_text": [{"type": "text", "text": {"content": title}}]}},
        {"type": "paragraph", "paragraph": {"rich_text": [{"type": "text", "text": {"content": desc(lead)}}]}},
        {"type": "heading_2", "heading_2": {"rich_text": [{"type": "text", "text": {"content": "Contact Details"}}]}},
        {"type": "bulleted_list_item", "bulleted_list_item": {"rich_text": [{"type": "text", "text": {"content": f"Phone: {lead['phone']}"}}]}},
    ]
    if lead["email"]:
        blocks.append({"type": "bulleted_list_item", "bulleted_list_item": {"rich_text": [{"type": "text", "text": {"content": f"Email: {lead['email']}"}}]}})
    if lead["website"]:
        blocks.append({"type": "bulleted_list_item", "bulleted_list_item": {"rich_text": [{"type": "text", "text": {"content": f"Website: {lead['website']}"}}]}})
    if lead["location"]:
        blocks.append({"type": "bulleted_list_item", "bulleted_list_item": {"rich_text": [{"type": "text", "text": {"content": f"Location: {lead['location']}"}}]}})
    if lead["social"]:
        blocks.append({"type": "bulleted_list_item", "bulleted_list_item": {"rich_text": [{"type": "text", "text": {"content": f"Social: {lead['social']}"}}]}})

    details_line = " | ".join(
        f"{k}: {v}" for k, v in [
            ("Source", lead["source"]),
            ("Stage", lead["stage"]),
            ("Score", lead["score"]),
            ("Enriched", lead["enriched"]),
            ("WhatsApp", "YES" if lead["whatsapp"] in ("YES", "TRUE", "1") else "NO"),
            ("Folder", lead["folder"]),
        ] if v
    )
    blocks.append({"type": "heading_2", "heading_2": {"rich_text": [{"type": "text", "text": {"content": "Details"}}]}})
    if details_line:
        blocks.append({"type": "paragraph", "paragraph": {"rich_text": [{"type": "text", "text": {"content": details_line}}]}})

    if lead["key_name"] and lead["key_name"] != "Name not publicly listed":
        kc = f"Key Contact: {lead['key_name']}"
        if lead["key_title"]:
            kc += f" ({lead['key_title']})"
        if lead["key_email"]:
            kc += f" | {lead['key_email']}"
        if lead["key_phone"]:
            kc += f" | {lead['key_phone']}"
        if lead["key_linkedin"]:
            kc += f" | {lead['key_linkedin']}"
        blocks.append({"type": "heading_2", "heading_2": {"rich_text": [{"type": "text", "text": {"content": "Key Contact"}}]}})
        blocks.append({"type": "paragraph", "paragraph": {"rich_text": [{"type": "text", "text": {"content": kc}}]}})

    payload = {
        "parent": {"page_id": LEADS_DETAILS_PAGE},
        "properties": {"title": [{"type": "text", "text": {"content": title}}]},
        "children": blocks,
    }
    page = api("POST", "/pages", payload)
    return page["id"]


def create_db_row(lead, page_id):
    props = {
        "Name": {"title": [{"type": "text", "text": {"content": lead["business"]}}]},
        "Business Name": {"rich_text": [{"type": "text", "text": {"content": lead["business"]}}]},
    }
    if lead["sector"]:
        props["Sector"] = {"select": {"name": lead["sector"]}}
    if lead["subsector"]:
        props["Sub Sector"] = {"rich_text": [{"type": "text", "text": {"content": lead["subsector"]}}]}
    if lead["location"]:
        props["Location"] = {"rich_text": [{"type": "text", "text": {"content": lead["location"]}}]}
    if lead["phone"]:
        props["Phone"] = {"phone_number": lead["phone"]}
    if lead["email"]:
        props["Email"] = {"email": lead["email"]}
    if lead["website"]:
        props["Website"] = {"url": lead["website"]}
    if lead["source"]:
        props["Source"] = {"rich_text": [{"type": "text", "text": {"content": lead["source"]}}]}
    if lead["score"]:
        try:
            props["Score"] = {"number": float(lead["score"])}
        except ValueError:
            pass
    if lead["stage"]:
        props["Stage"] = {"select": {"name": lead["stage"]}}
    props["WhatsApp"] = {"checkbox": lead["whatsapp"] in ("YES", "TRUE", "1")}
    props["Description"] = {"rich_text": [{"type": "text", "text": {"content": desc(lead)}}]}
    props["Details"] = {
        "rich_text": [{"type": "mention", "mention": {"type": "page", "page": {"id": page_id}}}]
    }

    payload = {
        "parent": {"type": "database_id", "database_id": LEADS_DB_ID},
        "properties": props,
    }
    row = api("POST", "/pages", payload)
    return row["id"]


def fetch_all_rows():
    """Return list of property dicts for all rows in the Leads DB."""
    rows = []
    cursor = None
    while True:
        payload = {"page_size": 100}
        if cursor:
            payload["start_cursor"] = cursor
        data = api("POST", f"/data_sources/{LEADS_DB}/query", payload)
        rows.extend(data.get("results", []))
        cursor = data.get("next_cursor")
        if not cursor or not data.get("has_more"):
            break
    return rows


def update_stats():
    """Write a colored stats header onto the Leads database page (auto-updates each run)."""
    rows = fetch_all_rows()
    total = len(rows)

    stages, sectors, bands, whatsapp = {}, {}, {}, 0
    has_email = 0
    for row in rows:
        p = row.get("properties", {})
        st = p.get("Stage", {}).get("select") or {}
        if st.get("name"):
            stages[st["name"]] = stages.get(st["name"], 0) + 1
        sec = p.get("Sector", {}).get("select") or {}
        if sec.get("name"):
            sectors[sec["name"]] = sectors.get(sec["name"], 0) + 1
        band = (p.get("Score Band", {}).get("formula") or {}).get("string")
        if band:
            bands[band] = bands.get(band, 0) + 1
        if (p.get("WhatsApp", {}) or {}).get("checkbox"):
            whatsapp += 1
        if (p.get("Email", {}) or {}).get("email"):
            has_email += 1

    color = {"Hot": "red", "Warm": "orange", "Cold": "yellow", "No Score": "gray"}
    parts = []
    parts.append({"type": "text", "text": {"content": "LEADS DASHBOARD"}, "annotations": {"bold": True, "color": "purple"}})
    parts.append({"type": "text", "text": {"content": "  |  "}, "annotations": {"bold": True}})
    parts.append({"type": "text", "text": {"content": f"Total: {total}"}, "annotations": {"bold": True, "color": "blue"}})
    parts.append({"type": "text", "text": {"content": "  |  "}, "annotations": {"bold": True}})
    parts.append({"type": "text", "text": {"content": f"WhatsApp OK: {whatsapp}"}, "annotations": {"bold": True, "color": "green"}})
    parts.append({"type": "text", "text": {"content": "  |  "}, "annotations": {"bold": True}})
    parts.append({"type": "text", "text": {"content": f"With Email: {has_email}"}, "annotations": {"bold": True, "color": "green"}})
    for band, count in sorted(bands.items()):
        parts.append({"type": "text", "text": {"content": "  |  "}, "annotations": {"bold": True}})
        parts.append({"type": "text", "text": {"content": f"{band}: {count}"}, "annotations": {"bold": True, "color": color.get(band, "gray")}})
    for stage, count in sorted(stages.items()):
        parts.append({"type": "text", "text": {"content": "  |  "}, "annotations": {"bold": True}})
        parts.append({"type": "text", "text": {"content": f"{stage}: {count}"}, "annotations": {"bold": True, "color": "orange"}})

    # Update database description (old-style endpoint supports description)
    api("PATCH", f"/databases/{LEADS_DB_ID}", {"description": parts})
    print(f"  Stats header updated: {total} leads total")


def desc(lead):
    parts = [lead["sector"] or "Business", "based in", lead["location"]] if lead["location"] else [lead["sector"] or "Business"]
    return " ".join(parts) if lead["sector"] or lead["location"] else lead["business"]


def main():
    load_token()
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "master_leads_growing.csv"))
    parser.add_argument("--limit", type=int, default=100, help="max new leads to add per run")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    print("Loading existing leads from Notion...")
    existing = fetch_existing()
    print(f"  {len(existing)} rows already in the database")

    leads = read_leads(args.csv)
    print(f"  {len(leads)} leads in CSV\n")

    added = skipped = 0
    for lead in leads:
        if added >= args.limit:
            break
        key = normalize_phone(lead["phone"]) if lead["phone"] else "name:" + lead["name"].lower().strip()
        if key in existing or "name:" + lead["name"].lower().strip() in existing:
            skipped += 1
            continue
        if args.dry_run:
            print(f"  [dry] would add: {lead['business']}")
            added += 1
            continue
        try:
            page_id = create_details_page(lead)
            time.sleep(0.3)
            create_db_row(lead, page_id)
            time.sleep(0.3)
            added += 1
            print(f"  [+] {lead['business']} ({lead['phone']})")
        except Exception as e:
            print(f"  [!] FAILED {lead['business']}: {e}", file=sys.stderr)

    print(f"\nDone. Added: {added} | Skipped (already in DB): {skipped}")

    if not args.dry_run:
        print("Updating dashboard stats...")
        update_stats()


if __name__ == "__main__":
    main()
