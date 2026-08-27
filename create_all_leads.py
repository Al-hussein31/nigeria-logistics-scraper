import csv
import json
import time
import requests

NOTION_TOKEN = "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"  # Replace with actual token
HEADERS = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Notion-Version": "2022-06-28",
    "Content-Type": "application/json"
}

COLD_OUTBOUND_PAGE_ID = "3c93c723-099f-81e9-aff0-fdcf76faed4f"
LEADS_PAGE_ID = "3c93c723-099f-8147-aa43-e36a49801e4e"

def create_page(title):
    url = "https://api.notion.com/v1/pages"
    data = {
        "parent": {"page_id": COLD_OUTBOUND_PAGE_ID},
        "properties": {"title": [{"type": "text", "text": {"content": title}}]}
    }
    response = requests.post(url, headers=HEADERS, json=data)
    return response.json()

def add_blocks(block_id, blocks):
    url = f"https://api.notion.com/v1/blocks/{block_id}/children"
    data = {"children": blocks}
    response = requests.patch(url, headers=HEADERS, json=data)
    return response.json()

def build_blocks(lead):
    title = lead['business'] or lead['name']
    blocks = [
        {"type": "heading_1", "heading_1": {"rich_text": [{"type": "text", "text": {"content": title}}]}},
        {"type": "paragraph", "paragraph": {"rich_text": [{"type": "text", "text": {"content": f"{lead['sector']} company based in {lead['location']}"}}]}},
        {"type": "heading_2", "heading_2": {"rich_text": [{"type": "text", "text": {"content": "Contact Details"}}]}},
        {"type": "bulleted_list_item", "bulleted_list_item": {"rich_text": [{"type": "text", "text": {"content": f"Phone: {lead['phone']}"}}]}},
    ]
    if lead['email']:
        blocks.append({"type": "bulleted_list_item", "bulleted_list_item": {"rich_text": [{"type": "text", "text": {"content": f"Email: {lead['email']}"}}]}})
    if lead['location']:
        blocks.append({"type": "bulleted_list_item", "bulleted_list_item": {"rich_text": [{"type": "text", "text": {"content": f"Location: {lead['location']}"}}]}})
    if lead['social']:
        blocks.append({"type": "bulleted_list_item", "bulleted_list_item": {"rich_text": [{"type": "text", "text": {"content": f"Social: {lead['social']}"}}]}})
    
    blocks.extend([
        {"type": "heading_2", "heading_2": {"rich_text": [{"type": "text", "text": {"content": "Details"}}]}},
        {"type": "paragraph", "paragraph": {"rich_text": [{"type": "text", "text": {"content": f"Source: {lead['source']} | Stage: {lead['stage']} | Score: {lead['score']} | Enriched: {lead['enriched']} | WhatsApp: {lead['whatsapp']}"}}]}},
    ])
    
    if lead['key_name']:
        key_info = f"Key Contact: {lead['key_name']}"
        if lead['key_title']:
            key_info += f" ({lead['key_title']})"
        blocks.append({"type": "paragraph", "paragraph": {"rich_text": [{"type": "text", "text": {"content": key_info}}]}})
    
    return blocks

def add_bullet_to_leads_page(lead):
    title = lead['business'] or lead['name']
    blocks = [{"type": "bulleted_list_item", "bulleted_list_item": {"rich_text": [{"type": "text", "text": {"content": f"{title} ({lead['phone']})"}}]}}]
    return add_blocks(LEADS_PAGE_ID, blocks)

def main():
    leads = []
    with open('master_leads_growing.csv', 'r') as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader):
            if i >= 100:
                break
            leads.append({
                'idx': i,
                'name': row.get('name', '') or row.get('businessName', ''),
                'business': row.get('businessName', '') or row.get('name', ''),
                'sector': row.get('sector', '') or row.get('subSector', '') or row.get('industry', ''),
                'phone': row.get('phone', ''),
                'email': row.get('email', ''),
                'location': row.get('location', ''),
                'stage': row.get('stage', ''),
                'score': row.get('score', ''),
                'whatsapp': row.get('whatsapp', ''),
                'folder': row.get('folder', ''),
                'social': row.get('socialLinks', ''),
                'source': row.get('source', '') or row.get('_source', '') or row.get('_sources', ''),
                'enriched': row.get('enriched', ''),
                'key_name': row.get('keyPeople_name', ''),
                'key_title': row.get('keyPeople_title', ''),
                'key_email': row.get('keyPeople_email', ''),
                'key_linkedin': row.get('keyPeople_linkedin', ''),
                'key_phone': row.get('keyPeople_phone', ''),
                'key_source': row.get('keyPeople_source', ''),
            })

    print(f"Processing {len(leads)} leads...")
    
    for i, lead in enumerate(leads):
        title = lead['business'] or lead['name']
        print(f"[{i+1}/100] Creating page for: {title}")
        
        try:
            # Create page
            page = create_page(title)
            if 'id' not in page:
                print(f"  ERROR creating page: {page}")
                continue
            
            page_id = page['id']
            print(f"  Created page: {page_id}")
            
            # Add content blocks
            blocks = build_blocks(lead)
            result = add_blocks(page_id, blocks)
            if 'results' not in result:
                print(f"  ERROR adding blocks: {result}")
            
            # Add bullet to Leads page
            add_bullet_to_leads_page(lead)
            print(f"  Added bullet to Leads page")
            
        except Exception as e:
            print(f"  ERROR: {e}")
        
        # Rate limiting
        time.sleep(0.5)

    print("Done!")

if __name__ == "__main__":
    main()