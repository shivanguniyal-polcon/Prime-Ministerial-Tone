import json
import re
import os
from collections import defaultdict

try:
    import wordninja
    HAS_WORDNINJA = True
except ImportError:
    HAS_WORDNINJA = False

INPUT_JSONL = "/Users/ganeshchandrauniyal/Desktop/Summer Project Ideas/PDF to JSONL/ML_READY_CORPUS.jsonl"
OUTPUT_JSONL = "/Users/ganeshchandrauniyal/Desktop/Summer Project Ideas/PDF to JSONL/ABSOLUTE_FINAL_CORPUS.jsonl"

def heal_text_brute(text):
    # 1. Brute-force shattered suffixes (Requires 3+ letters before the space)
    text = re.sub(r'(\w{3,})ti on\b', r'\1tion', text)
    text = re.sub(r'(\w{3,})si on\b', r'\1sion', text)
    text = re.sub(r'(\w{3,})o us\b', r'\1ous', text)
    text = re.sub(r'(\w{3,})t or\b', r'\1tor', text)
    text = re.sub(r'(\w{3,})a in\b', r'\1ain', text)
    text = re.sub(r'(\w{3,})o me\b', r'\1ome', text)
    text = re.sub(r'(\w{3,})m on\b', r'\1mon', text)
    text = re.sub(r'(\w{3,})t ion\b', r'\1tion', text)
    
    # 2. Brute-force spaced page numbers (e.g. " 9 7 " or " 1 4 ")
    text = re.sub(r'(?<!\d)(?<!Rs\. )(?<!\.)(\b\d\s\d\b)(?!\d)(?!\s*%)', '', text)
    
    # 3. WordNinja for massive fused blocks (>20 chars)
    if HAS_WORDNINJA:
        words = text.split()
        new_words = []
        for w in words:
            if len(w) > 20 and not w.startswith('http') and '-' not in w and re.search(r'[a-z]', w):
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
    print("🛠️ Running Master Rectification & Re-indexing...\n")
    
    docs = defaultdict(list)
    dropped_publisher = 0
    dropped_data_loss = 0
    
    # 1. Read, Filter, and Heal
    with open(INPUT_JSONL, 'r', encoding='utf-8') as f:
        for line in f:
            row = json.loads(line)
            text = row.get("text_chunk", "")
            topic = row.get("topic", "")
            
            # Drop Publisher Garbage
            if "Jainco Art India" in text or "Publishers Of This Book" in text:
                dropped_publisher += 1
                continue
                
            # Drop Data Loss
            if re.search(r'Rs\.\s+(?:to|or|[a-z])\s+crore|about\s+per\s+cent\s+to\s+per\s+cent', text, re.IGNORECASE):
                dropped_data_loss += 1
                continue
                
            # Fix Short/Garbage Topics
            if topic == "Bill":
                row["topic"] = "Parliamentary Bill"
            elif "27 May 27 May" in topic:
                row["topic"] = "Motion Of Confidence In The Council Of Ministers"
                
            # Heal Text
            row["text_chunk"] = heal_text_brute(text)
            row["word_count"] = len(row["text_chunk"].split())
            
            docs[row["document_id"]].append(row)
            
    # 2. Re-index Chunks to Fix Continuity Errors
    final_rows = []
    for doc_id, chunks in docs.items():
        # Sort by original index just in case
        chunks.sort(key=lambda x: x.get("chunk_index", 0))
        total = len(chunks)
        
        for i, chunk in enumerate(chunks):
            chunk["chunk_index"] = i
            chunk["total_chunks"] = total
            final_rows.append(chunk)
            
    # 3. Write Final Output
    with open(OUTPUT_JSONL, 'w', encoding='utf-8') as f:
        for row in final_rows:
            f.write(json.dumps(row, ensure_ascii=False) + '\n')
            
    print("="*60)
    print("🏆 MASTER RECTIFICATION COMPLETE")
    print("="*60)
    print(f"🗑️ Dropped Publisher Garbage: {dropped_publisher} chunks")
    print(f"🗑️ Dropped Data Loss: {dropped_data_loss} chunks")
    print(f"🔄 Re-indexed {len(docs)} documents to fix continuity errors.")
    print(f"📤 Final ML-Ready Chunks: {len(final_rows):,}")
    print(f"💾 Saved to:\n   {OUTPUT_JSONL}")
    print("="*60)

if __name__ == "__main__":
    main()