import json
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
from dateutil import parser as date_parser
import re

# ==========================================
# 1. CONFIGURATION
# ==========================================
INPUT_JSONL = "/Users/ganeshchandrauniyal/Desktop/Summer Project Ideas/PDF to JSONL/PM_CORPUS_FINAL_SEALED.jsonl" # Update to your source file
OUTPUT_PARQUET = "/Users/ganeshchandrauniyal/Desktop/Summer Project Ideas/PDF to JSONL/IPEC_GOLDEN_MASTER.parquet"
OUTPUT_JSONL = "/Users/ganeshchandrauniyal/Desktop/Summer Project Ideas/PDF to JSONL/IPEC_GOLDEN_MASTER.jsonl"

# ==========================================
# 2. THE GOLDEN PATCH (Doc ID Overrides)
# ==========================================
DOC_PM_MAP = {
    "PM_Vol_Speech_438": "Narendra Modi",
    "PM_Vol_Speech_439": "Narendra Modi",
    "PM_Vol_Speech_440": "Narendra Modi",
    "PM_Vol_Speech_441": "Indira Gandhi"
}

# ==========================================
# 3. PM TENURES (For Daily Transcripts)
# ==========================================
PM_TENURES = [
    ("Jawaharlal Nehru", "1952-01-01", "1964-05-27"),
    ("Gulzarilal Nanda (Acting)", "1964-05-27", "1964-06-09"),
    ("Lal Bahadur Shastri", "1964-06-09", "1966-01-11"),
    ("Gulzarilal Nanda (Acting)", "1966-01-11", "1966-01-24"),
    ("Indira Gandhi", "1966-01-24", "1977-03-24"),
    ("Morarji Desai", "1977-03-24", "1979-07-28"),
    ("Charan Singh", "1979-07-28", "1980-01-14"),
    ("Indira Gandhi", "1980-01-14", "1984-10-31"),
    ("Rajiv Gandhi", "1984-10-31", "1989-12-02"),
    ("V.P. Singh", "1989-12-02", "1990-11-10"),
    ("Chandra Shekhar", "1990-11-10", "1991-06-21"),
    ("P.V. Narasimha Rao", "1991-06-21", "1996-05-16"),
    ("Atal Bihari Vajpayee", "1996-05-16", "1996-06-01"),
    ("H.D. Deve Gowda", "1996-06-01", "1997-04-21"),
    ("I.K. Gujral", "1997-04-21", "1998-03-19"),
    ("Atal Bihari Vajpayee", "1998-03-19", "2004-05-22"),
    ("Manmohan Singh", "2004-05-22", "2014-05-26"),
    ("Narendra Modi", "2014-05-26", "2026-12-31"),
]

# ==========================================
# 4. CORE LOGIC FUNCTIONS
# ==========================================
def clean_and_validate_date(raw_date):
    """Rejects impossible dates (1947, 2047) and normalizes valid ones."""
    if not raw_date or raw_date in ["Unknown Date", "Compiled Volume", "Unknown", ""]:
        return None
        
    if re.match(r'^\d{4}-\d{2}-\d{2}$', raw_date):
        year = int(raw_date.split('-')[0])
        if 1952 <= year <= 2026: return raw_date
        else: return None # Reject 1947, 2047
        
    try:
        dt = date_parser.parse(raw_date, fuzzy=True)
        if 1952 <= dt.year <= 2026: return dt.strftime("%Y-%m-%d")
        else: return None
    except:
        return None

def assign_pm(doc_id, valid_date):
    """Golden Patch first, then Tenure fallback."""
    if doc_id in DOC_PM_MAP:
        return DOC_PM_MAP[doc_id]
    if valid_date:
        for pm, start, end in PM_TENURES:
            if start <= valid_date <= end: return pm
    return "Unknown"

def assign_era_coalition(pm_name, valid_date):
    """Maps to the 5-Phase Schema."""
    # If we have a valid date, use exact historical bounds
    if valid_date:
        if "1952-01-01" <= valid_date < "1977-03-24": return "Phase 1: Single-Party Dominance", False
        if "1977-03-24" <= valid_date < "1980-01-14": return "Phase 2: Early Coalitions & Instability", True
        if "1980-01-14" <= valid_date < "1989-12-02": return "Phase 2: Early Coalitions & Instability", False
        if "1989-12-02" <= valid_date < "2014-05-26": return "Phase 3: The Coalition Era", True
        if "2014-05-26" <= valid_date < "2024-06-09": return "Phase 4: Single-Party Majorities", False
        if valid_date >= "2024-06-09": return "Phase 5: Return to Coalition", True
        
    # If date is missing (Compiled Volumes), impute based on PM
    if pm_name == "Indira Gandhi": return "Phase 1/2: Indira Gandhi Era", False
    if pm_name == "Narendra Modi": return "Phase 4/5: Narendra Modi Era", False
    if pm_name in ["Jawaharlal Nehru", "Lal Bahadur Shastri"]: return "Phase 1: Single-Party Dominance", False
    if pm_name in ["Morarji Desai", "Charan Singh"]: return "Phase 2: Early Coalitions & Instability", True
    if pm_name == "Rajiv Gandhi": return "Phase 2: Early Coalitions & Instability", False
    if pm_name in ["V.P. Singh", "Chandra Shekhar", "P.V. Narasimha Rao", "H.D. Deve Gowda", "I.K. Gujral", "Atal Bihari Vajpayee", "Manmohan Singh"]: return "Phase 3: The Coalition Era", True
        
    return "Unknown Era", None

def clean_text_artifacts(text):
    """Removes OCR shattering and spaced digits from the text body."""
    if not text: return ""
    text = re.sub(r'\b\d{1,2}\s\d{1,2}\b', '', text) # Removes spaced digits like '11 0'
    text = re.sub(r'\s+', ' ', text).strip()
    return text

# ==========================================
# 5. MAIN EXECUTION
# ==========================================
def main():
    print("🏗️ Running IPEC Golden Master Pipeline...\n")
    records = []
    valid_dates = []
    
    with open(INPUT_JSONL, 'r', encoding='utf-8') as f:
        for line in f:
            row = json.loads(line)
            doc_id = row.get("document_id", row.get("doc_id", ""))
            
            # 1. Validate Date (Kills 1947 and 2047)
            valid_date = clean_and_validate_date(row.get("date", ""))
            if valid_date: valid_dates.append(valid_date)
            
            # 2. Assign PM (Golden Patch)
            pm_name = assign_pm(doc_id, valid_date)
            
            # 3. Assign Era & Coalition
            era, coalition = assign_era_coalition(pm_name, valid_date)
            
            # 4. Clean Text
            clean_text = clean_text_artifacts(row.get("text_chunk", row.get("snippet", "")))
            
            records.append({
                "document_id": doc_id,
                "chunk_id": row.get("chunk_id", doc_id),
                "date": valid_date if valid_date else "Compiled Volume",
                "pm_name": pm_name,
                "topic": row.get("topic", ""),
                "coalition_gov": coalition,
                "political_era": era,
                "text_chunk": clean_text
            })
            
    df = pd.DataFrame(records)
    
    # Export Parquet
    schema = pa.schema([
        ('document_id', pa.string()), ('chunk_id', pa.string()), ('date', pa.string()),
        ('pm_name', pa.string()), ('topic', pa.string()), ('coalition_gov', pa.bool_()),
        ('political_era', pa.string()), ('text_chunk', pa.string())
    ])
    table = pa.Table.from_pandas(df, schema=schema)
    pq.write_table(table, OUTPUT_PARQUET, compression='zstd')
    
    # Export JSONL
    with open(OUTPUT_JSONL, 'w', encoding='utf-8') as f:
        for r in records: f.write(json.dumps(r, ensure_ascii=False) + '\n')
        
    # Print Summary
    print("="*60)
    print("🏆 IPEC GOLDEN MASTER DATASET CREATED")
    print("="*60)
    print(f"📊 Total Chunks: {len(df):,}")
    if valid_dates:
        print(f"📅 True Chronological Range: {min(valid_dates)} to {max(valid_dates)}")
        
    print("\n🏛️ DISTRIBUTION BY POLITICAL ERA:")
    for era, count in df['political_era'].value_counts().sort_index().items():
        print(f"   • {era}: {count} chunks")
        
    print("\n🤝 DISTRIBUTION BY GOVERNMENT TYPE:")
    coalition_counts = df['coalition_gov'].value_counts()
    print(f"   • Single-Party Govs (False): {coalition_counts.get(False, 0):,} chunks")
    print(f"   • Coalition Govs (True):     {coalition_counts.get(True, 0):,} chunks")
    
    unknown_eras = df[df['political_era'] == "Unknown Era"].shape[0]
    unknown_pms = df[df['pm_name'] == "Unknown"].shape[0]
    print(f"\n⚠️ Remaining Unknown Eras: {unknown_eras}")
    print(f"⚠️ Remaining Unknown PMs: {unknown_pms}")
    print("="*60)

if __name__ == "__main__":
    main()