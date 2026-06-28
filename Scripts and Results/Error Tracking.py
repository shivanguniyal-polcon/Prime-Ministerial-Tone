import json
import re

INPUT_JSONL = "/Users/ganeshchandrauniyal/Desktop/Summer Project Ideas/PDF to JSONL/TRULY_FINAL_CORPUS.jsonl"
OUTPUT_JSON = "/Users/ganeshchandrauniyal/Desktop/Summer Project Ideas/PDF to JSONL/error_snippets.json"

pat_shattered = re.compile(r'\b\w+(ti on|si on|o us|t or|a in|o me|m on)\b', re.IGNORECASE)
pat_spaced_digits = re.compile(r'(?<!\d)(?<!Rs\. )(?<!\.)\b(\d{1,2}\s\d{1,2})\b(?!\d)(?!\s*%)')

# Known English words that trigger false positives
FALSE_POSITIVES = {
    'certain', 'mountain', 'captain', 'curtain', 'stain', 'tremendous', 'enormous', 
    'doctor', 'tractor', 'monitor', 'factor', 'remainder', 'attain', 'contain', 
    'obtain', 'maintain', 'fountain', 'bargain', 'villain', 'cushion', 'mansion'
}

snippets = []

with open(INPUT_JSONL, 'r', encoding='utf-8') as f:
    for line in f:
        row = json.loads(line)
        text = row.get("text_chunk", "")
        date = row.get("date", "")
        doc_id = row.get("document_id", "")
        topic = row.get("topic", "")[:60] # Truncate topic for readability
        
        # 1. IMPOSSIBLE / BAD DATES
        if date < "1952-01-01" or "Unknown" in date or "Compiled" in date or "1947" in date:
            snippets.append({
                "doc_id": doc_id, "topic": topic, "date": date,
                "anomaly": "IMPOSSIBLE_DATE",
                "snippet": text[:200].replace('\n', ' ') + "..."
            })
            
        # 2. SHATTERED SUFFIXES
        for match in pat_shattered.finditer(text):
            word = match.group(0).lower()
            if word not in FALSE_POSITIVES:
                start = max(0, match.start() - 50)
                end = min(len(text), match.end() + 50)
                snippets.append({
                    "doc_id": doc_id, "topic": topic, "date": date,
                    "anomaly": f"SHATTERED: '{match.group(0)}'",
                    "snippet": "..." + text[start:end].replace('\n', ' ') + "..."
                })
                break # One example per chunk is enough
                
        # 3. SPACED DIGITS
        match = pat_spaced_digits.search(text)
        if match:
            start = max(0, match.start() - 50)
            end = min(len(text), match.end() + 50)
            snippets.append({
                "doc_id": doc_id, "topic": topic, "date": date,
                "anomaly": f"SPACED_DIGIT: '{match.group(0)}'",
                "snippet": "..." + text[start:end].replace('\n', ' ') + "..."
            })
            
        # 4. FUSED WORDS
        for w in text.split():
            if len(w) > 25 and not w.startswith('http') and '-' not in w and '.' not in w:
                idx = text.find(w)
                start = max(0, idx - 50)
                end = min(len(text), idx + len(w) + 50)
                snippets.append({
                    "doc_id": doc_id, "topic": topic, "date": date,
                    "anomaly": f"FUSED_WORD: '{w[:40]}...'",
                    "snippet": "..." + text[start:end].replace('\n', ' ') + "..."
                })
                break

with open(OUTPUT_JSON, 'w', encoding='utf-8') as f:
    json.dump(snippets, f, indent=2, ensure_ascii=False)

print(f"✅ Extracted {len(snippets)} specific error snippets.")
print(f"💾 Saved to: {OUTPUT_JSON}")
print("👉 Please open this file and paste its contents back here!")