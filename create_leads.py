import requests
import json
import time

NOTION_TOKEN = "secret_xxx"  # Will use the MCP tool instead

# Since we can't use the token directly, we'll generate the API calls
# and run them via the notion_API_post_page and notion_API_patch_block_children tools

leads = []
with open('master_leads_growing.csv', 'r') as f:
    import csv
    reader = csv.DictReader(f)
    for i, row in enumerate(reader):
        if i >= 100:
            break
        leads.append({
            'idx': i,
            'name': row.get('name', '') or row.get('businessName', '') or row.get('Name', ''),
            'business': row.get('businessName', '') or row.get('name', '') or row.get('Name', ''),
            'sector': row.get('sector', '') or row.get('Sector', ''),
            'phone': row.get('phone', '') or row.get('Phone', ''),
            'email': row.get('email', '') or row.get('Email', ''),
            'location': row.get('location', '') or row.get('Location', ''),
            'stage': row.get('stage', '') or row.get('Stage', ''),
            'score': row.get('score', '') or row.get('Score', ''),
            'whatsapp': row.get('whatsapp', '') or row.get('WhatsApp', ''),
            'folder': row.get('folder', ''),
            'social': row.get('socialLinks', ''),
            'source': row.get('source', '') or row.get('_source', '') or row.get('_sources', ''),
            'enriched': row.get('enriched', '') or row.get('Enriched', ''),
            'key_name': row.get('keyPeople_name', ''),
            'key_title': row.get('keyPeople_title', ''),
            'key_email': row.get('keyPeople_email', ''),
            'key_linkedin': row.get('keyPeople_linkedin', ''),
            'key_phone': row.get('keyPeople_phone', ''),
            'key_source': row.get('keyPeople_source', ''),
        })

# Generate the commands to run
for ld in leads:
    title = ld['business'] or ld['name']
    
    # Create individual lead page
    page_data = {
        "properties": {"title": [{"type": "text", "text": {"content": title}}]},
        "parent": {"page_id": "3c93c723-099f-81e9-aff0-fdcf76faed4f"}
    }
    
    # Build content blocks
    blocks = [
        {"type": "heading_1", "heading_1": {"rich_text": [{"type": "text", "text": {"content": title}}]}},
        {"type": "paragraph", "paragraph": {"rich_text": [{"type": "text", "text": {"content": f"{ld['sector']} company based in {ld['location']}"}}]}},
        {"type": "heading_2", "heading_2": {"rich_text": [{"type": "text", "text": {"content": "Contact Details"}}]}},
        {"type": "bulleted_list_item", "bulleted_list_item": {"rich_text": [{"type": "text", "text": {"content": f"Phone: {ld['phone']}"}}]}},
    ]
    
    if ld['email']:
        blocks.append({"type": "bulleted_list_item", "bulleted_list_item": {"rich_text": [{"type": "text", "text": {"content": f"Email: {ld['email']}"}}]}})
    if ld['location']:
        blocks.append({"type": "bulleted_list_item", "bulleted_list_item": {"rich_text": [{"type": "text", "text": {"content": f"Location: {ld['location']}"}}]}})
    if ld['social']:
        blocks.append({"type": "bulleted_list_item", "bulleted_list_item": {"rich_text": [{"type": "text", "text": {"content": f"Social: {ld['social']}"}}]}})
    
    blocks.extend([
        {"type": "heading_2", "heading_2": {"rich_text": [{"type": "text", "text": {"content": "Details"}}]}},
        {"type": "paragraph", "paragraph": {"rich_text": [{"type": "text", "text": {"content": f"Source: {ld['source']} | Stage: {ld['stage']} | Score: {ld['score']} | Enriched: {ld['enriched']} | WhatsApp: {ld['whatsapp']}"}}]}},
    ])
    
    if ld['key_name']:
        blocks.append({"type": "paragraph", "paragraph": {"rich_text": [{"type": "text", "text": {"content": f"Key Contact: {ld['key_name']} ({ld['key_title']})"}}]}})
    
    print(f"CREATE PAGE: {json.dumps(page_data)}")
    print(f"ADD BLOCKS: {json.dumps({'block_id': 'PLACEHOLDER', 'children': blocks})}")
    print("---")

# Also generate the bulleted list for the Leads page
print("\nLEADS PAGE BULLETS:")
for ld in leads:
    title = ld['business'] or ld['name']
    print(f"- {title} ({ld['phone']}) - [link to individual page]")