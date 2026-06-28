#!/usr/bin/env python3
"""
JSONL Post-Processor: The Blob Splitter
=======================================
Identifies massive "blob" documents in the JSONL, merges them back together,
and re-segments them using Chapter/Markdown headings to restore proper metadata.
"""

import json
import re
import os
from collections import defaultdict

INPUT_JSONL = "/Users/ganeshchandrauniyal/Desktop/Summer Project Ideas/PDF to JSONL/publication_corpus.jsonl"
OUTPUT_JSONL = "/Users/ganeshchandrauniyal/Desktop/Summer Project Ideas/PDF to JSONL/final_corrected_corpus.jsonl"
TARGET_WORDS = 800
OVERLAP_WORDS = 100

def chunk_text(text, max_words, overlap):
    if not text: return []
    words = text.split()
    chunks = []
    step = max_words - overlap
    for i in range(0, len(words), step):
        chunk = words[i:i + max_words]
        if len(chunk) < (max_words // 4) and i > 0:
            if chunks: chunks[-1] += " " + " ".join(chunk)
            break
        chunks.append(" ".join(chunk))
    return chunks

def split_by_chapters(text):
    """Splits text by Markdown (#) or Numbered Chapters (1. , 2. )"""
    # Lookahead for newline, then optional # or Number., then Title Case words
    pattern = re.compile(r'\n(?=(?:#\s*|\d+\.\s+)[A-Z][A-Z\s,]+)')
    sections = pattern.split(text)
    
    speeches = []
    for sec in sections:
        sec = sec.strip()
        if not sec or len(sec) < 200: continue
        
        # Extract title from the first line
        lines = sec.split('\n')
        title = re.sub(r'^(?:#\s*|\d+\.\s+)', '', lines[0]).strip()
        title = re.sub(r'[*#]', '', title).title() # Clean markdown
        
        body = '\n'.join(lines[1:]).strip()
        
        # Filter out pure TOC or Index blocks
        if len(body.split()) > 100:
            speeches.append({'topic': title, 'body': body})
            
    return speeches

def main():
    print("\n" + "=" * 60)
    print("🔪 BLOB SPLITTER: Correcting Over-Chunked Documents")
    print("=" * 60 + "\n")

    # 1. Load and group existing JSONL by document_id
    docs = defaultdict(list)
    with open(INPUT_JSONL, 'r', encoding='utf-8') as f:
        for line in f:
            row = json.loads(line)
            docs[row['document_id']].append(row)

    final_rows = []
    corrected_count = 0
    
    # 2. Process each document
    for doc_id, chunks in docs.items():
        # Sort chunks to ensure correct text reconstruction
        chunks.sort(key=lambda x: x['chunk_index'])
        
        # Identify "Blobs" (Documents with > 50 chunks, or specific names)
        is_blob = len(chunks) > 50 or "Indira" in chunks[0].get('topic', '') or "Modi" in chunks[0].get('topic', '')
        
        if not is_blob:
            # Keep perfectly segmented documents exactly as they are
            final_rows.extend(chunks)
            continue
            
        print(f"🔪 Re-segmenting Blob: {doc_id} ({len(chunks)} chunks -> splitting by chapters)")
        
        # Reconstruct the full text blob
        full_text = " ".join([c['text_chunk'] for c in chunks])
        date = chunks[0]['date']
        
        # Re-segment using Chapter Headings
        speeches = split_by_chapters(full_text)
        
        if not speeches:
            print(f"   ⚠️ No chapter headings found. Keeping original chunks.")
            final_rows.extend(chunks)
            continue
            
        # Generate new chunks with correct topics
        doc_counter = 1
        for speech in speeches:
            speech_chunks = chunk_text(speech['body'], TARGET_WORDS, OVERLAP_WORDS)
            
            for c_idx, c_text in enumerate(speech_chunks):
                final_rows.append({
                    "document_id": f"{doc_id}_Part{doc_counter}",
                    "chunk_id": f"{doc_id}_Part{doc_counter}_{c_idx}",
                    "date": date,
                    "topic": speech['topic'],
                    "chunk_index": c_idx,
                    "total_chunks": len(speech_chunks),
                    "word_count": len(c_text.split()),
                    "text_chunk": c_text
                })
            doc_counter += 1
            corrected_count += 1

    # 3. Save the corrected JSONL
    with open(OUTPUT_JSONL, 'w', encoding='utf-8') as f:
        for row in final_rows:
            f.write(json.dumps(row, ensure_ascii=False) + '\n')

    print("\n" + "=" * 60)
    print("🏆 CORRECTION COMPLETE")
    print("=" * 60)
    print(f"📄 Total Chunks in Final Archive: {len(final_rows):,}")
    print(f"🔪 Corrected {corrected_count} individual speeches from the blobs.")
    print(f"💾 Saved pristine archive to: {OUTPUT_JSONL}")
    print("=" * 60 + "\n")

if __name__ == "__main__":
    main()