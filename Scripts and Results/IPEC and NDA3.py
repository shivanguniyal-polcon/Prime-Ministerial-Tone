import json
import re
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

# Point this to your latest finalized JSONL
INPUT_JSONL = "/Users/ganeshchandrauniyal/Desktop/Summer Project Ideas/PDF to JSONL/IPEC_GOLDEN_MASTER.jsonl" 
OUTPUT_JSONL = "/Users/ganeshchandrauniyal/Desktop/Summer Project Ideas/PDF to JSONL/IPEC_ABSOLUTE_FINAL.jsonl"
OUTPUT_PARQUET = "/Users/ganeshchandrauniyal/Desktop/Summer Project Ideas/PDF to JSONL/IPEC_ABSOLUTE_FINAL.parquet"

# Regex patterns that definitively place a speech in the 2024+ Coalition Era
PHASE_5_PATTERNS = [
    r'18th\s+Lok\s+Sabha',
    r'18th\s+House',
    r'third\s+term',
    r'Modi\s+III',
    r'Modi\s+3\.0',
    r'2024\s+elections?',
    r'June\s+4',          # 2024 Election Results Day
    r'Chandrababu',       # TDP Leader
    r'Nitish\s+Kumar',    # JD(U) Leader
    r'NDA\s+government', 
    r'coalition\s+government',
    r'allies\s+in\s+government',
    r'272'                # The majority mark BJP fell short of alone
]

# Compile them into a single regex
phase_5_regex = re.compile('|'.join(PHASE_5_PATTERNS), re.IGNORECASE)

records = []
updates_made = 0

print("🔍 Scanning for 2024+ Coalition Era markers...")

with open(INPUT_JSONL, 'r', encoding='utf-8') as f:
    for line in f:
        row = json.loads(line)
        
        # Target: Modi speeches that were blanket-assigned to Phase 4 due to missing dates
        if row.get("pm_name") == "Narendra Modi" and row.get("political_era") == "Phase 4: Single-Party Majorities":
            text = row.get("text_chunk", "")
            
            # Scan for Phase 5 indicators
            if phase_5_regex.search(text):
                row["political_era"] = "Phase 5: Return to Coalition"
                row["coalition_gov"] = True
                # Anchor the date to the start of the 3rd term
                row["date"] = "2024-06-09" 
                updates_made += 1
                
        records.append(row)

# Export to Parquet
df = pd.DataFrame(records)
schema = pa.schema([
    ('document_id', pa.string()), ('chunk_id', pa.string()), ('date', pa.string()),
    ('pm_name', pa.string()), ('topic', pa.string()), ('coalition_gov', pa.bool_()),
    ('political_era', pa.string()), ('chunk_index', pa.int32()), ('total_chunks', pa.int32()),
    ('word_count', pa.int32()), ('text_chunk', pa.string())
])
table = pa.Table.from_pandas(df, schema=schema)
pq.write_table(table, OUTPUT_PARQUET, compression='zstd')

# Export to JSONL
with open(OUTPUT_JSONL, 'w', encoding='utf-8') as f:
    for r in records:
        f.write(json.dumps(r, ensure_ascii=False) + '\n')

print("="*60)
print("🏆 PHASE 5 RESCUE COMPLETE")
print("="*60)
print(f"✅ Corrected {updates_made} chunks to Phase 5 (Coalition).")
print(f"💾 Saved to: {OUTPUT_PARQUET}")
print("="*60)