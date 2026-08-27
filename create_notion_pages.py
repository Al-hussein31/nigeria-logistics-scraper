import json
import subprocess
import time
import tempfile
import os

with open('leads_for_notion.json', 'r') as f:
    leads_data = json.load(f)

COLD_OUTBOUND_PAGE_ID = "3c93c723-099f-81e9-aff0-fdcf76faed4f"
LEADS_PAGE_ID = "3c93c723-099f-8147-aa43-e36a49801e4e"

created_pages = []

for lead in leads_data:
    print(f"Creating page {lead['index']}/100: {lead['title']}")
    
    # Create payload
    payload = {
        "parent": {"page_id": COLD_OUTBOUND_PAGE_ID},
        "properties": {
            "title": {"title": [{"text": {"content": lead['title']}}]}
        },
        "children": lead['blocks']
    }
    
    # Write payload to temp file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(payload, f)
        temp_file = f.name
    
    try:
        # Call the notion API tool using the CLI
        result = subprocess.run([
            'opencode', 'tool', 'notion_API-post-page',
            '--input', temp_file
        ], capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            try:
                response = json.loads(result.stdout)
                page_id = response.get('id')
                if page_id:
                    created_pages.append({"title": lead['title'], "page_id": page_id, "lead_id": lead['id']})
                    print(f"  ✓ Created: {page_id}")
                else:
                    print(f"  ✗ No page_id in response: {result.stdout[:200]}")
            except json.JSONDecodeError:
                print(f"  ✗ Failed to parse response: {result.stdout[:200]}")
        else:
            print(f"  ✗ Error: {result.stderr[:200]}")
    finally:
        os.unlink(temp_file)
    
    time.sleep(0.3)  # Rate limiting

# Save created pages
with open('created_pages.json', 'w') as f:
    json.dump(created_pages, f, indent=2)

print(f"\nCreated {len(created_pages)} pages")
