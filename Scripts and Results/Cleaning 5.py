import json
import re
from datetime import datetime

INPUT_JSONL = "/Users/ganeshchandrauniyal/Desktop/Summer Project Ideas/PDF to JSONL/ABSOLUTE_FINAL_CORPUS.jsonl"
OUTPUT_JSONL = "/Users/ganeshchandrauniyal/Desktop/Summer Project Ideas/PDF to JSONL/TRULY_FINAL_CORPUS.jsonl"

TARGET_WORDS = 800
OVERLAP_WORDS = 100

def extract_and_reconstruct(rows):
    """Separates the good chunks from the mislabeled Indira blob."""
    good = []
    blob_text = ""
    for row in rows:
        topic = row.get("topic", "")
        if "Jainco" in topic or "Publishers Of This Book" in topic:
            blob_text += " " + row.get("text_chunk", "")
        else:
            good.append(row)
    return good, blob_text.strip()

def drop_index(text):
    """Cuts off the alphabetical index at the end of the book."""
    # The index starts with alphabetical listings and page numbers
    index_match = re.search(r'\bDepartment of Culture,\s*\d+|E Earthquake|F Family Planning|A\s+Ag[a-z]+,\s*\d+', text)
    if index_match:
        print(f"   ✂️ Dropped {len(text) - index_match.start():,} characters of Index/TOC garbage.")
        return text[:index_match.start()]
    return text

def segment_blob(text):
    """Splits the mega-blob into individual speeches using salutations and known titles."""
    matches = list(re.finditer(
        r'(?:Mr\.\s*(?:Speaker|Deputy\s*(?:Speaker|Chairman)),\s*Sir)|'
        r'(?:Challenges of Economic Backwardness\b)|'
        r'(?:Accord with Sheikh Abdullah\b)|'
        r'(?:Resignation by Shri Gulzarilal Nanda\b)|'
        r'(?:Replying to the debate on the Motion of Thanks\b)',
        text, re.IGNORECASE
    ))
    
    if not matches:
        return [{"topic": "Indira Gandhi Speech", "date": "Unknown Date", "text": text}]
        
    segments = []
    if matches[0].start() > 0:
        segments.append(text[:matches[0].start()])
        
    for i in range(len(matches)):
        start = matches[i].start()
        end = matches[i+1].start() if i+1 < len(matches) else len(text)
        segments.append(text[start:end])
        
    speeches = []
    for seg in segments:
        if len(seg.strip()) < 500: continue
        
        # 1. Extract Topic
        topic = "Parliamentary Speech"
        if "Challenges of Economic Backwardness" in seg[:200]: topic = "Challenges of Economic Backwardness"
        elif "Accord with Sheikh Abdullah" in seg[:200]: topic = "Accord with Sheikh Abdullah"
        elif "Resignation by Shri Gulzarilal Nanda" in seg[:200]: topic = "Resignation by Shri Gulzarilal Nanda"
        elif "Motion of Thanks" in seg[:500]: topic = "Motion of Thanks to President's Address"
        
        # 2. Extract Date (Check first 1000 chars, then check footnotes for years)
        date_str = "Unknown Date"
        date_match = re.search(r'(\d{1,2}\s+(?:January|February|March|April|May|June|July|August|September|October|November|December)\w*\s*,?\s*\d{4})', seg[:1000], re.IGNORECASE)
        if date_match:
            date_str = date_match.group(1)
        else:
            # Look for year in footnotes (e.g., "R.S. Deb., 2 March, 1970")
            year_match = re.search(r'(19\d{2})', seg[:1500])
            if year_match:
                date_str = f"01 January {year_match.group(1)}"
                
        speeches.append({"topic": topic, "date": date_str, "text": seg})
        
    return speeches

def chunk_text(text, max_words, overlap):
    if not text: return []
    words = text.split()
    chunks, step = [], max_words - overlap
    for i in range(0, len(words), step):
        c = words[i:i+max_words]
        if len(c) < (max_words//4) and i > 0:
            if chunks: chunks[-1] += " " + " ".join(c)
            break
        chunks.append(" ".join(c))
    return chunks

def main():
    print("🚑 RESCUING MISLABELED INDIRA GANDHI BLOB...\n")
    
    # 1. Read and Separate
    with open(INPUT_JSONL, 'r', encoding='utf-8') as f:
        all_rows = [json.loads(line) for line in f]
        
    good_rows, blob_text = extract_and_reconstruct(all_rows)
    print(f"📦 Isolated {len(blob_text.split()):,} words from the mislabeled blob.")
    
    # 2. Drop Index
    blob_text = drop_index(blob_text)
    
    # 3. Segment into Speeches
    speeches = segment_blob(blob_text)
    print(f"📑 Successfully split blob into {len(speeches)} distinct speeches.\n")
    
    # 4. Re-chunk the new speeches
    new_rows = []
    for speech in speeches:
        # Parse Date
        date_str = speech['date'].replace(',', '').strip().title()
        try:
            iso_date = datetime.strptime(date_str, "%d %B %Y").strftime("%Y-%m-%d")
        except ValueError:
            iso_date = date_str
            
        chunks = chunk_text(speech['text'], TARGET_WORDS, OVERLAP_WORDS)
        for c_idx, c_text in enumerate(chunks):
            new_rows.append({
                "document_id": "RESCUED_INDIRA", # Temporary ID, will be re-indexed
                "chunk_id": f"RESCUED_INDIRA_{c_idx}",
                "date": iso_date,
                "topic": speech['topic'],
                "chunk_index": c_idx,
                "total_chunks": len(chunks),
                "word_count": len(c_text.split()),
                "text_chunk": c_text
            })
            
    # 5. Merge and Re-index EVERYTHING
    final_corpus = good_rows + new_rows
    
    # Group by original document_id to maintain speech continuity
    from collections import defaultdict
    docs = defaultdict(list)
    for row in final_corpus:
        docs[row["document_id"]].append(row)
        
    final_rows = []
    doc_counter = 1
    for old_doc_id, chunks in docs.items():
        chunks.sort(key=lambda x: x.get("chunk_index", 0))
        new_doc_id = f"PM_Vol_Speech_{doc_counter:03d}"
        total = len(chunks)
        
        for i, chunk in enumerate(chunks):
            chunk["document_id"] = new_doc_id
            chunk["chunk_id"] = f"{new_doc_id}_{i}"
            chunk["chunk_index"] = i
            chunk["total_chunks"] = total
            final_rows.append(chunk)
            
        doc_counter += 1
        
    # 6. Write Final Output
    with open(OUTPUT_JSONL, 'w', encoding='utf-8') as f:
        for row in final_rows:
            f.write(json.dumps(row, ensure_ascii=False) + '\n')
            
    print("="*60)
    print("🏆 BLOB RESCUE & REINTEGRATION COMPLETE")
    print("="*60)
    print(f"📄 Total Unique Speeches: {doc_counter - 1}")
    print(f"🧩 Total Chunks: {len(final_rows):,}")
    print(f"💾 Saved to:\n   {OUTPUT_JSONL}")
    print("="*60)

if __name__ == "__main__":
    main()