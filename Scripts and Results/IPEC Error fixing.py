import json
import re

INPUT = "/Users/ganeshchandrauniyal/Desktop/Summer Project Ideas/PDF to JSONL/IPEC_ML_READY_FINAL.jsonl" 
OUTPUT = "/Users/ganeshchandrauniyal/Desktop/Summer Project Ideas/PDF to JSONL/IPEC_PUBLICATION_READY.jsonl"

fixed_dates = 0
fixed_text = 0

with open(INPUT, 'r', encoding='utf-8') as fin, \
     open(OUTPUT, 'w', encoding='utf-8') as fout:
     
    for line in fin:
        rec = json.loads(line)
        text = rec['text_chunk']
        
        # 1. FIX YEAR REPETITION ARTIFACTS (e.g., ", 1996, 1996, 1996, 1996")
        # Matches a comma and year repeated 3 or more times
        new_text = re.sub(r'(,\s*\d{4}){3,}', '', text)
        if new_text != text:
            fixed_text += 1
            text = new_text
            
        # 2. CLAMP FUTURE DATES (Modi's "Vision 2026/2047" references)
        # If the date is beyond the current historical reality, clamp it.
        date_str = rec['date']
        if date_str > '2025-12-31':
            rec['date'] = '2024-06-09' # Clamp to start of Phase 5 (18th Lok Sabha)
            rec['date_source'] = 'clamped_future_reference'
            fixed_dates += 1
            
        rec['text_chunk'] = text
        fout.write(json.dumps(rec, ensure_ascii=False) + '\n')

print("="*60)
print("🏆 PUBLICATION POLISH COMPLETE")
print("="*60)
print(f"🔧 Fixed Year Repetition Artifacts: {fixed_text}")
print(f"📅 Clamped Future Dates (Vision 2026/2047): {fixed_dates}")
print(f"💾 Saved to: {OUTPUT}")
print("\n✅ NOTE: 'xxx' and '***' markers were INTENTIONALLY PRESERVED.")
print("   These are official Lok Sabha notation for interruptions.")
print("   Use them to calculate your Procedural Chaos Index (PCI)!")
print("="*60)