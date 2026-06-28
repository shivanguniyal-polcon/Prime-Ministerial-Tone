#!/usr/bin/env python3
"""
Final Metadata Enrichment & Date Correction
============================================
1. Fixes impossible dates (clamps to 1952+)
2. Adds PM Name based on date + source file
3. Aggressively fixes remaining shattered/fused artifacts
4. Outputs the definitive ML-ready corpus
"""

import json
import re
import os
import random
from datetime import datetime

INPUT_JSONL = "/Users/ganeshchandrauniyal/Desktop/Summer Project Ideas/PDF to JSONL/ABSOLUTE_FINAL_CORPUS.jsonl"
OUTPUT_JSONL = "/Users/ganeshchandrauniyal/Desktop/Summer Project Ideas/PDF to JSONL/ML_READY_V2.jsonl"
SAMPLE_OUTPUT = "/Users/ganeshchandrauniyal/Desktop/Summer Project Ideas/PDF to JSONL/validation_sample.json"

# ==========================================
# 1. PM TENURE MAPPING
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
    ("Narendra Modi", "2014-05-26", "2030-12-31"),
]

# Filename-to-PM mapping for compiled volumes
FILENAME_PM_MAP = {
    "Jawaharlal_Nehru": "Jawaharlal Nehru",
    "LB_Shastri": "Lal Bahadur Shastri",
    "Indira_Gandhi": "Indira Gandhi",
    "Morarji_Desai": "Morarji Desai",
    "Rajiv_Gandhi": "Rajiv Gandhi",
    "VP_Singh": "V.P. Singh",
    "Chandra_Shekhar": "Chandra Shekhar",
    "PVN_Rao": "P.V. Narasimha Rao",
    "AB_Vajpayee": "Atal Bihari Vajpayee",
    "HD_Devegowda": "H.D. Deve Gowda",
    "IK_Gujral": "I.K. Gujral",
    "Manmohan_Singh": "Manmohan Singh",
    "Narendra_Modi": "Narendra Modi",
}

def get_pm_by_date(date_str):
    """Returns PM name based on speech date."""
    for pm_name, start, end in PM_TENURES:
        if start <= date_str <= end:
            return pm_name
    return "Unknown"

def get_pm_from_topic(topic):
    """Extracts PM name from the topic/filename field."""
    for key, pm_name in FILENAME_PM_MAP.items():
        if key in topic:
            return pm_name
    return None

def fix_date(date_str, topic, text_chunk):
    """Fixes impossible dates. Returns (fixed_date, pm_name)."""
    
    # 1. Handle completely missing/compiled dates
    if date_str in ["Unknown Date", "Compiled Volume", "", None]:
        pm_from_topic = get_pm_from_topic(topic)
        if pm_from_topic:
            # Use the midpoint of their tenure as a rough date
            for pm_name, start, end in PM_TENURES:
                if pm_name == pm_from_topic:
                    return start[:4] + "-01-01", pm_name
        return "Unknown", "Unknown"
    
    # 2. Handle impossible pre-1952 dates
    if date_str < "1952-01-01":
        # Try to find a real date in the text chunk
        real_date = re.search(
            r'(\d{1,2}\s+(?:January|February|March|April|May|June|July|August|'
            r'September|October|November|December)\w*\s*,?\s*(19[5-9]\d|20\d{2}))',
            text_chunk[:1500], re.IGNORECASE
        )
        if real_date:
            try:
                cleaned = real_date.group(1).replace(',', '').strip().title()
                parsed = datetime.strptime(cleaned, "%d %B %Y").strftime("%Y-%m-%d")
                if parsed >= "1952-01-01":
                    return parsed, get_pm_by_date(parsed)
            except ValueError:
                pass
        
        # If no real date found, use PM from topic
        pm_from_topic = get_pm_from_topic(topic)
        if pm_from_topic:
            for pm_name, start, end in PM_TENURES:
                if pm_name == pm_from_topic:
                    return start[:4] + "-01-01", pm_name
        
        return "1952-01-01", get_pm_by_date("1952-01-01")
    
    # 3. Valid date - just look up PM
    pm = get_pm_by_date(date_str)
    pm_from_topic = get_pm_from_topic(topic)
    
    # Cross-validate: if date says one PM but filename says another, trust filename for compiled vols
    if pm_from_topic and "Compiled Volume" in str(topic):
        return date_str, pm_from_topic
    
    return date_str, pm

# ==========================================
# 2. AGGRESSIVE FINAL HEALING
# ==========================================
def final_heal(text):
    # Shattered suffixes (unrestricted)
    text = re.sub(r'(\w+)ti on\b', r'\1tion', text)
    text = re.sub(r'(\w+)si on\b', r'\1sion', text)
    text = re.sub(r'(\w+)o us\b', r'\1ous', text)
    text = re.sub(r'(\w+)t or\b', r'\1tor', text)
    text = re.sub(r'(\w+)a in\b', r'\1ain', text)
    text = re.sub(r'(\w+)o me\b', r'\1ome', text)
    text = re.sub(r'(\w+)m on\b', r'\1mon', text)
    text = re.sub(r'(\w+)t ion\b', r'\1tion', text)
    
    # Page number bleed (any isolated 2-digit pairs surrounded by spaces)
    text = re.sub(r'(?<![.\d])\s\b(\d{1,2})\s(\d{1,2})\b\s(?![.\d%])', ' ', text)
    
    # OCR character swaps
    swaps = {
        r'\breplying lo\b': 'replying to',
        r'\bmight he able\b': 'might be able',
        r'\bwe fell that\b': 'we felt that',
        r'\bI fell that\b': 'I felt that',
        r'\b1 greatly\b': 'I greatly',
        r'\bltold\b': 'I told',
        r'\b1 have\b': 'I have',
        r'\bcome pressure\b': 'some pressure',
        r"\b11 0'clock\b": "11 o'clock",
        r'\badds upto\b': 'adds up to',
        r'\baver to\b': 'over to',
        r'\bOne thins has\b': 'One thing has',
    }
    for pattern, replacement in swaps.items():
        text = re.sub(pattern, replacement, text)
    
    # Whitespace cleanup
    text = re.sub(r'\s+([.,;:!?])', r'\1', text)
    text = re.sub(r'\s+', ' ', text).strip()
    
    return text

# ==========================================
# 3. MAIN EXECUTION
# ==========================================
def main():
    print("="*60)
    print("🔧 FINAL ENRICHMENT: Dates, PM Names, Healing")
    print("="*60 + "\n")
    
    all_rows = []
    date_fixes = 0
    pm_assigned = 0
    
    with open(INPUT_JSONL, 'r', encoding='utf-8') as f:
        for line in f:
            row = json.loads(line)
            
            old_date = row.get("date", "")
            topic = row.get("topic", "")
            text = row.get("text_chunk", "")
            
            # 1. Fix date and get PM name
            new_date, pm_name = fix_date(old_date, topic, text)
            if old_date != new_date:
                date_fixes += 1
            if pm_name != "Unknown":
                pm_assigned += 1
            
            row["date"] = new_date
            row["pm_name"] = pm_name
            
            # 2. Final healing pass
            healed_text = final_heal(text)
            row["text_chunk"] = healed_text
            row["word_count"] = len(healed_text.split())
            
            all_rows.append(row)
    
    # 3. Write enriched corpus
    with open(OUTPUT_JSONL, 'w', encoding='utf-8') as f:
        for row in all_rows:
            f.write(json.dumps(row, ensure_ascii=False) + '\n')
    
    # 4. Generate validation sample (50 random chunks for manual review)
    sample = random.sample(all_rows, min(50, len(all_rows)))
    with open(SAMPLE_OUTPUT, 'w', encoding='utf-8') as f:
        json.dump(sample, f, indent=2, ensure_ascii=False)
    
    # 5. Print summary
    dates = [r["date"] for r in all_rows if r["date"] not in ["Unknown", ""]]
    pms = set(r["pm_name"] for r in all_rows if r["pm_name"] != "Unknown")
    
    print("="*60)
    print("🏆 ENRICHMENT COMPLETE")
    print("="*60)
    print(f"📄 Total Chunks: {len(all_rows):,}")
    print(f"📅 Dates Fixed: {date_fixes}")
    print(f"👤 PM Names Assigned: {pm_assigned}/{len(all_rows)}")
    print(f"📅 Valid Date Range: {min(dates)} to {max(dates)}" if dates else "📅 No valid dates")
    print(f"🗣️ PMs in Corpus: {', '.join(sorted(pms))}")
    print(f"\n💾 Enriched Corpus: {OUTPUT_JSONL}")
    print(f"📋 Validation Sample (50 chunks): {SAMPLE_OUTPUT}")
    print("="*60)
    
    print("\n📝 NEXT STEP: Open validation_sample.json and manually")
    print("   read through the 50 random chunks to verify quality.")
    print("="*60 + "\n")

if __name__ == "__main__":
    main()