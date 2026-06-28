import json
import re
import os
from collections import defaultdict

try:
    import wordninja
    HAS_WORDNINJA = True
except ImportError:
    HAS_WORDNINJA = False

# Read from the previous polished file
INPUT_JSONL = "/Users/ganeshchandrauniyal/Desktop/Summer Project Ideas/PDF to JSONL/ABSOLUTE_FINAL_CORPUS.jsonl"
# Output to the absolute final ML-ready file
OUTPUT_JSONL = "/Users/ganeshchandrauniyal/Desktop/Summer Project Ideas/PDF to JSONL/Very_ML_READY_CORPUS.jsonl"

def heal_text_unrestricted(text):
    # 1. UNRESTRICTED Brute-force shattered suffixes (Matches ANY length before the space)
    text = re.sub(r'(\w+)ti on\b', r'\1tion', text)
    text = re.sub(r'(\w+)si on\b', r'\1sion', text)
    text = re.sub(r'(\w+)o us\b', r'\1ous', text)
    text = re.sub(r'(\w+)t or\b', r'\1tor', text)
    text = re.sub(r'(\w+)a in\b', r'\1ain', text)
    text = re.sub(r'(\w+)o me\b', r'\1ome', text)
    text = re.sub(r'(\w+)m on\b', r'\1mon', text)
    text = re.sub(r'(\w+)t ion\b', r'\1tion', text)
    
    # 2. Brute-force spaced page numbers
    text = re.sub(r'(?<!\d)(?<!Rs\. )(?<!\.)(\b\d\s\d\b)(?!\d)(?!\s*%)', '', text)
    
    # 3. WordNinja for massive fused blocks (>25 chars to pass QA)
    if HAS_WORDNINJA:
        words = text.split()
        new_words = []
        for w in words:
            # If it's massive, not a URL, and doesn't have a hyphen, split it
            if len(w) > 25 and not w.startswith('http') and '-' not in w and re.search(r'[a-z]', w):
                split = wordninja.split(w)
                if len(split) > 1:
                    new_words.extend(split)
                    continue
            new_words.append(w)
        text = " ".join(new_words)
        
    # 4. Final whitespace cleanup
    text = re.sub(r'\s+([.,;:!?])', r'\1', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def main():
    print("☢️ Running FINAL NUKE & REBUILD...\n")
    
    docs = defaultdict(list)
    dropped_garbage = 0
    dropped_data_loss = 0
    
    with open(INPUT_JSONL, 'r', encoding='utf-8') as f:
        for line in f:
            row = json.loads(line)
            text = row.get("text_chunk", "")
            topic = row.get("topic", "")
            
            # 1. DROP PUBLISHER GARBAGE (Check BOTH topic and text!)
            if "Jainco" in topic or "Jainco" in text or "Publishers Of This Book" in topic or "Publishers Of This Book" in text:
                dropped_garbage += 1
                continue
                
            # 2. DROP DATA LOSS
            if re.search(r'Rs\.\s+(?:to|or|[a-z])\s+crore|about\s+per\s+cent\s+to\s+per\s+cent', text, re.IGNORECASE):
                dropped_data_loss += 1
                continue
                
            # 3. Fix Short/Garbage Topics
            if topic == "Bill":
                row["topic"] = "Parliamentary Bill"
            elif "27 May 27 May" in topic:
                row["topic"] = "Motion Of Confidence In The Council Of Ministers"
            elif len(topic) < 5:
                row["topic"] = "Parliamentary Proceedings"
                
            # 4. Heal Text
            row["text_chunk"] = heal_text_unrestricted(text)
            row["word_count"] = len(row["text_chunk"].split())
            
            docs[row["document_id"]].append(row)
            
    # 5. Re-index Chunks to Fix Continuity Errors
    final_rows = []
    for doc_id, chunks in docs.items():
        chunks.sort(key=lambda x: x.get("chunk_index", 0))
        total = len(chunks)
        
        for i, chunk in enumerate(chunks):
            chunk["chunk_index"] = i
            chunk["total_chunks"] = total
            final_rows.append(chunk)
            
    # 6. Write Final Output
    with open(OUTPUT_JSONL, 'w', encoding='utf-8') as f:
        for row in final_rows:
            f.write(json.dumps(row, ensure_ascii=False) + '\n')
            
    print("="*60)
    print("🏆 FINAL NUKE & REBUILD COMPLETE")
    print("="*60)
    print(f"🗑️ Dropped Publisher Garbage: {dropped_garbage} chunks")
    print(f"🗑️ Dropped Data Loss: {dropped_data_loss} chunks")
    print(f"🔄 Re-indexed {len(docs)} documents.")
    print(f"📤 Final ML-Ready Chunks: {len(final_rows):,}")
    print(f"💾 Saved to:\n   {OUTPUT_JSONL}")
    print("="*60)
    
    print("\n⚠️ CRITICAL NEXT STEP:")
    print("You MUST run your QA script on this EXACT new file:")
    print(f'python QA.py "{OUTPUT_JSONL}"')
    print("="*60 + "\n")

if __name__ == "__main__":
    main()