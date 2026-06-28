import json
import re
from collections import defaultdict

INPUT_JSONL = "/Users/ganeshchandrauniyal/Desktop/Summer Project Ideas/PDF to JSONL/IPEC_PUBLICATION_READY.jsonl"
OUTPUT_JSONL = "/Users/ganeshchandrauniyal/Desktop/Summer Project Ideas/PDF to JSONL/IPEC_FINAL_CORRECTED.jsonl"

print("🔧 Applying Final Publication Remediations...\n")

records = []
with open(INPUT_JSONL, 'r', encoding='utf-8') as f:
    for line in f:
        if line.strip():
            records.append(json.loads(line))

# ==========================================
# FIX 1: Split PM_Vol_Speech_438 (Frankenstein Doc)
# ==========================================
new_records = []
for r in records:
    if r['document_id'] == 'PM_Vol_Speech_438':
        # Extract the chunk index from the chunk_id (e.g., 'PM_Vol_Speech_438_0' -> '0')
        chunk_idx = r['chunk_id'].split('_')[-1]
        
        # Create a new unique document ID for each chunk
        new_doc_id = f"PM_Vol_Speech_438_S{chunk_idx}"
        
        # Update the record
        r['document_id'] = new_doc_id
        r['chunk_id'] = f"{new_doc_id}_0"
        
    new_records.append(r)

records = new_records

# ==========================================
# FIX 2: Clean up repetition artifacts and standardize 'xxx'
# ==========================================
# These are the exact phrases that were repeated 5 times consecutively in the QA report
repeated_phrases = [
    "At times the Government banked upon procrastination ",
    "in order to avoid new areas of dispute and left everything to the ",
    "judgement of the Courts. Now the courts have started giving ",
    "verdicts in matters which ought to have been decided by the ",
    "Executive and the P ",
    "Parliament. Why cannot the P ",
    "discharge its duties and responsibilities? Why the Executive cannot ",
    "should be honest and vibrant and it should not delay matters. "
]

for r in records:
    text = r['text_chunk']
    
    # 2a. Fix consecutive repetition artifacts
    for phrase in repeated_phrases:
        # If the phrase appears 3 or more times consecutively, replace with a single instance
        pattern = re.compile(f"({re.escape(phrase)}){{3,}}")
        text = pattern.sub(phrase, text)
        
    # 2b. Standardize 'xxx' and '***' truncation markers to [INTERRUPTION]
    # Replace blocks of 'xxx' and dots (e.g., 'xxx.......... xxx..........')
    text = re.sub(r'(?:[xX]+[\.\s]+){2,}[xX]+[\.\s]*', '[INTERRUPTION] ', text)
    # Catch standalone 'xxx' or '***'
    text = re.sub(r'\b[xX]{3,}\b', '[INTERRUPTION]', text)
    text = re.sub(r'\*{3,}', '[INTERRUPTION]', text)
    
    # Clean up extra spaces created by replacements
    text = re.sub(r'\s+', ' ', text).strip()
    
    r['text_chunk'] = text

# ==========================================
# FIX 3: Renumber PM_Vol_Speech_441 to fix missing chunks
# ==========================================
doc_441 = [r for r in records if r['document_id'] == 'PM_Vol_Speech_441']
doc_441.sort(key=lambda x: int(x['chunk_id'].split('_')[-1]))

for i, r in enumerate(doc_441):
    r['chunk_id'] = f"PM_Vol_Speech_441_{i}"

# ==========================================
# FIX 4: Ensure all records have chunk_index and total_chunks
# ==========================================
doc_chunks = defaultdict(list)
for r in records:
    doc_chunks[r['document_id']].append(r)

for doc_id, chunks in doc_chunks.items():
    # Sort by chunk_id to ensure correct order
    chunks.sort(key=lambda x: x['chunk_id'])
    total = len(chunks)
    for i, r in enumerate(chunks):
        r['chunk_index'] = i
        r['total_chunks'] = total
        # Ensure chunk_id matches the new index (except for 441 which was already renumbered)
        if doc_id != 'PM_Vol_Speech_441':
            r['chunk_id'] = f"{doc_id}_{i}"

# Flatten back to a single list
final_records = []
for doc_id in sorted(doc_chunks.keys()):
    final_records.extend(doc_chunks[doc_id])

# ==========================================
# Save the corrected dataset
# ==========================================
with open(OUTPUT_JSONL, 'w', encoding='utf-8') as f:
    for r in final_records:
        f.write(json.dumps(r, ensure_ascii=False) + '\n')

print("="*60)
print("🏆 FINAL PUBLICATION REMEDIATIONS COMPLETE")
print("="*60)
print(f"📄 Total Records: {len(final_records)}")
print(f"🔧 Split PM_Vol_Speech_438 into 6 separate documents.")
print(f"🔧 Renumbered PM_Vol_Speech_441 to fix missing chunks.")
print(f"🔧 Cleaned repetition artifacts and standardized 'xxx' markers.")
print(f"💾 Saved to: {OUTPUT_JSONL}")
print("="*60)