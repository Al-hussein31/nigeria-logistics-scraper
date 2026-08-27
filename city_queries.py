#!/usr/bin/env python3
"""Generate query files for each Nigerian city"""

CITIES = [
    "Lagos", "Port Harcourt", "Kano", "Ibadan", "Kaduna", 
    "Enugu", "Benin City", "Aba", "Onitsha", "Owerri",
    "Warri", "Calabar", "Jos", "Maiduguri", "Sokoto",
    "Zaria", "Ilorin", "Abeokuta", "Akure", "Uyo"
]

QUERIES_PER_CITY = [
    "logistics companies",
    "freight forwarders",
    "shipping companies",
    "customs brokers",
    "warehouse storage",
    "cold storage",
    "courier services",
    "haulage companies",
    "transport companies",
    "supply chain",
]

output_dir = "/Users/MAC/Desktop/meshgrdy/Real Leads/city_queries"
import os
os.makedirs(output_dir, exist_ok=True)

for city in CITIES:
    filepath = os.path.join(output_dir, f"{city.lower().replace(' ', '_')}.txt")
    with open(filepath, "w") as f:
        for q in QUERIES_PER_CITY:
            f.write(f"{q} {city}\n")

print(f"Created {len(CITIES)} query files in {output_dir}")
