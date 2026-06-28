import json
import re

INPUT_JSONL = "/Users/ganeshchandrauniyal/Desktop/Summer Project Ideas/PDF to JSONL/IPEC_GOLDEN_MASTER.jsonl" # Update to your latest JSONL
OUTPUT_JSONL = "/Users/ganeshchandrauniyal/Desktop/Summer Project Ideas/PDF to JSONL/IPEC_ML_READY_FINAL.jsonl"

# ==========================================
# 1. THE "HARDCODED HERO" TOPIC MAP
# Derived directly from your diagnostic text snippets
# ==========================================
TOPIC_REPAIR_MAP = {
    "PM_Vol_Speech_001": "Address on Election of the Speaker",
    "PM_Vol_Speech_003": "Motion of Thanks to the Speaker",
    "PM_Vol_Speech_017": "Statement on Nuclear Tests and Indo-US Relations",
    "PM_Vol_Speech_018": "Reply on Election of Deputy Speaker",
    "PM_Vol_Speech_019": "Statement on Iraq Situation",
    "PM_Vol_Speech_022": "Statement on Visit to USA",
    "PM_Vol_Speech_023": "Statement on Ayodhya Cases",
    "PM_Vol_Speech_024": "Statement on Ayodhya",
    "PM_Vol_Speech_025": "Statement on Ayodhya",
    "PM_Vol_Speech_026": "Statement on Operational Guidelines",
    "PM_Vol_Speech_027": "Valedictory Reference",
    "PM_Vol_Speech_032": "Valedictory Reference",
    "PM_Vol_Speech_033": "Statement on Attorney General of India",
    "PM_Vol_Speech_037": "Statement on Government Business",
    "PM_Vol_Speech_038": "Valedictory Reference",
    "PM_Vol_Speech_044": "Statement on India-Pakistan Relations",
    "PM_Vol_Speech_048": "Statement on Foreign Visits",
    "PM_Vol_Speech_049": "Statement on Attack on Parliament",
    "PM_Vol_Speech_058": "Address on Election of the Speaker",
    "PM_Vol_Speech_059": "Statement on Drought Situation",
    "PM_Vol_Speech_060": "Statement on Visit of Russian President",
    "PM_Vol_Speech_063": "Statement on Agricultural Loans",
    "PM_Vol_Speech_069": "Statement on Foreign Visits (Evian and China)",
    "PM_Vol_Speech_073": "Statement on Parliament Security",
    "PM_Vol_Speech_207": "Parliamentary Bill",
    "PM_Vol_Speech_225": "Statement Regarding U.S. Military Aid",
    "PM_Vol_Speech_264": "Motion Regarding Dr. Zakir Husain",
    "PM_Vol_Speech_406": "Statement Regarding Visit of Foreign Dignitary",
    "PM_Vol_Speech_421": "Statement Regarding Visit of Foreign Dignitary"
}

# PM Tenure boundaries to prevent extracting historical reference years (like 1947)
PM_YEAR_BOUNDS = {
    "PM_Vol_Speech_439": (2014, 2024), # Modi Vol 1
    "PM_Vol_Speech_440": (2022, 2026), # Modi Vol 2
    "PM_Vol_Speech_441": (1966, 1984)  # Indira Gandhi
}

def extract_safe_year(text, doc_id):
    """Extracts a year from text, but ONLY if it falls within the PM's actual tenure."""
    if doc_id not in PM_YEAR_BOUNDS:
        return None
    
    min_year, max_year = PM_YEAR_BOUNDS[doc_id]
    # Find all 4-digit years in the first 1000 characters
    years = re.findall(r'\b(19|20)\d{2}\b', text[:1000])
    
    for y in years:
        year_int = int(y)
        if min_year <= year_int <= max_year:
            return year_int
            
    # Fallback: If no year found in text, use the midpoint of their tenure
    return (min_year + max_year) // 2

def clean_topic(topic):
    """Strips trailing punctuation and fixes known truncations."""
    # Strip trailing commas, periods, colons
    topic = re.sub(r'[,\.:\;]+$', '', topic).strip()
    return topic

# ==========================================
# MAIN EXECUTION
# ==========================================
print("🔧 Applying Final Metadata Repairs...\n")

records = []
topics_fixed = 0
dates_imputed = 0

with open(INPUT_JSONL, 'r', encoding='utf-8') as f:
    for line in f:
        if not line.strip(): continue
        row = json.loads(line)
        doc_id = row['document_id']
        
        # 1. FIX TRUNCATED TOPICS
        if doc_id in TOPIC_REPAIR_MAP:
            if row['topic'] != TOPIC_REPAIR_MAP[doc_id]:
                row['topic'] = TOPIC_REPAIR_MAP[doc_id]
                topics_fixed += 1
        
        # 2. CLEAN TRAILING PUNCTUATION
        original_topic = row['topic']
        row['topic'] = clean_topic(original_topic)
        
        # 3. IMPUTE "COMPILED VOLUME" DATES
        if row['date'] == 'Compiled Volume':
            text = row.get('text_chunk', '')
            safe_year = extract_safe_year(text, doc_id)
            
            if safe_year:
                # Set to Jan 1st of the extracted year to preserve chronological sorting
                row['date'] = f"{safe_year}-01-01"
                row['date_source'] = "text_year_imputed"
                dates_imputed += 1
            else:
                # Absolute fallback (should rarely happen)
                row['date'] = "1999-01-01" 
                row['date_source'] = "fallback_imputed"
                
        records.append(row)

# Save the final ML-ready corpus
with open(OUTPUT_JSONL, 'w', encoding='utf-8') as f:
    for row in records:
        f.write(json.dumps(row, ensure_ascii=False) + '\n')

# ==========================================
# FINAL VERIFICATION
# ==========================================
print("="*60)
print("🏆 FINAL METADATA REPAIR COMPLETE")
print("="*60)
print(f"📝 Topics Repaired via Map: {topics_fixed}")
print(f"📅 'Compiled Volume' Dates Imputed: {dates_imputed}")
print(f"💾 Saved to: {OUTPUT_JSONL}")

# Quick QA check
remaining_compiled = sum(1 for r in records if r['date'] == 'Compiled Volume')
trailing_punct = sum(1 for r in records if re.search(r'[,\.:\;]$', r['topic']))

print(f"\n🔍 POST-REPAIR QA:")
print(f"   Remaining 'Compiled Volume' dates: {remaining_compiled}")
print(f"   Topics with trailing punctuation: {trailing_punct}")
print("="*60)