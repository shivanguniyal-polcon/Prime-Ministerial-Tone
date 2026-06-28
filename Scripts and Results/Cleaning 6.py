import json
import re

INPUT = "/Users/ganeshchandrauniyal/Desktop/Summer Project Ideas/PDF to JSONL/TRULY_FINAL_CORPUS.jsonl"
OUTPUT = "/Users/ganeshchandrauniyal/Desktop/Summer Project Ideas/PDF to JSONL/ABSOLUTE_FINAL_CORPUS.jsonl"

with open(INPUT, 'r', encoding='utf-8') as infile, open(OUTPUT, 'w', encoding='utf-8') as outfile:
    for line in infile:
        row = json.loads(line)
        text = row.get("text_chunk", "")
        
        # 1. Fix "11 0'clock" -> "11 o'clock"
        text = re.sub(r'\b(\d{1,2})\s+0(\'|’|)clock\b', r"\1 o'clock", text)
        
        # 2. Delete isolated 2-digit page number pairs from the Index (e.g., " 25 26 ", " 71 12 ")
        # We only delete them if they are surrounded by spaces and NOT part of a year or percentage
        text = re.sub(r'\s\b([1-9]\d)\s([1-9]\d)\b\s', ' ', text)
        
        # 3. Delete fused index page lists (e.g., "696,793,861,871...")
        text = re.sub(r'\b\d{3}(,\d{3}){3,}\b', '', text)
        
        row["text_chunk"] = text.strip()
        row["word_count"] = len(text.split())
        outfile.write(json.dumps(row, ensure_ascii=False) + '\n')

print("✅ Index bleed and minor typos cleaned. Saved to ABSOLUTE_FINAL_CORPUS.jsonl")