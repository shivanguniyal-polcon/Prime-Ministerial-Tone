#!/usr/bin/env python3
"""
Fallback Chunker for Unstructured/Modern PM Volumes
====================================================
Bypasses date/heading segmentation. Cleans text and splits
the entire PDF into publication-ready overlapping chunks.
"""
import os, re, json, fitz
from pathlib import Path
from tqdm import tqdm

INPUT_PDF_DIR = "/Users/ganeshchandrauniyal/Desktop/Summer Project Ideas/PM Speeches"
OUTPUT_JSONL = "/Users/ganeshchandrauniyal/Desktop/Summer Project Ideas/PDF to JSONL/publication_corpus.jsonl"
CHECKPOINT_FILE = "/Users/ganeshchandrauniyal/Desktop/Summer Project Ideas/PDF to JSONL/checkpoint.json"
VOLUME_ID = "PM_Vol"
TARGET_WORDS = 800
OVERLAP_WORDS = 100

# Target only the stubborn Modi volumes
TARGET_PDFS = [
    "PM_Speeches_Narendra_Modi_Eng_Vol-I_2014-2021.pdf",
    "PM_Speeches_Narendra_Modi_Eng_Vol-II_2022-2025.pdf"
]

def get_start_counter(jsonl_path):
    if not os.path.exists(jsonl_path): return 1
    docs = set()
    with open(jsonl_path, 'r', encoding='utf-8') as f:
        for line in f:
            try: docs.add(json.loads(line).get("document_id"))
            except: continue
    return len(docs) + 1

def clean_modi_text(text):
    # Drop TOC pipes, page numbers, roman numerals, publisher noise
    text = re.sub(r'^\s*\d{1,3}\s*$', '', text, flags=re.MULTILINE)
    text = re.sub(r'^\s*\(?[ivxlc]+\)?\s*$', '', text, flags=re.MULTILINE | re.IGNORECASE)
    text = re.sub(r'^.*\|.*\|.*$', '', text, flags=re.MULTILINE)
    text = re.sub(r'(Sl\. No\.|Subject|Page|Contents|Foreword|Preface|Publisher).*', '', text, flags=re.IGNORECASE)
    # Normalize whitespace & punctuation
    text = re.sub(r'\s+([.,;:!?])', r'\1', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

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
    print("\n📦 FALLBACK CHUNKER: Processing Modern/Unstructured Volumes\n")
    doc_counter = get_start_counter(OUTPUT_JSONL)
    total_added = 0
    
    if os.path.exists(CHECKPOINT_FILE):
        with open(CHECKPOINT_FILE, 'r') as f: processed = set(json.load(f).get("processed_pdfs", []))
    else: processed = set()

    with open(OUTPUT_JSONL, 'a', encoding='utf-8') as f_out:
        for pdf_name in TARGET_PDFS:
            pdf_path = Path(INPUT_PDF_DIR) / pdf_name
            if not pdf_path.exists() or pdf_name in processed:
                continue
                
            print(f"📥 Extracting & chunking {pdf_name}...")
            doc = fitz.open(str(pdf_path))
            full_text = "\n".join([page.get_text() for page in doc])
            doc.close()
            
            clean = clean_modi_text(full_text)
            if len(clean.split()) < 500:
                print(f"⚠️ Too little text in {pdf_name}. Skipping.")
                continue
                
            chunks = chunk_text(clean, TARGET_WORDS, OVERLAP_WORDS)
            doc_id = f"{VOLUME_ID}_Speech_{doc_counter:03d}"
            
            for c_idx, c_text in enumerate(chunks):
                row = {
                    "document_id": doc_id, "chunk_id": f"{doc_id}_{c_idx}",
                    "date": "Compiled Volume", "topic": pdf_name.replace(".pdf","").replace("_"," "),
                    "chunk_index": c_idx, "total_chunks": len(chunks),
                    "word_count": len(c_text.split()), "text_chunk": c_text
                }
                f_out.write(json.dumps(row, ensure_ascii=False) + '\n')
                total_added += 1
                
            doc_counter += 1
            processed.add(pdf_name)
            print(f"💾 Saved {len(chunks)} chunks for {pdf_name}\n")

    with open(CHECKPOINT_FILE, 'w') as f: json.dump({"processed_pdfs": list(processed)}, f, indent=2)
    
    print("="*50)
    print(f"🏆 FALLBACK COMPLETE: Appended {total_added} chunks to {OUTPUT_JSONL}")
    print("="*50)

if __name__ == "__main__":
    main()