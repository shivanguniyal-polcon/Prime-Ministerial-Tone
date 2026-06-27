#!/usr/bin/env python3
"""
Pure-Python OCR Pipeline (Bypasses Homebrew/Tesseract)
======================================================
Uses RapidOCR (ONNX Runtime) which installs via pre-compiled Python wheels.
No system dependencies, no C++ compilation, no Homebrew required.
"""

import os
import re
import json
import fitz  # PyMuPDF
from pathlib import Path
from tqdm import tqdm

try:
    from rapidocr_onnxruntime import RapidOCR
    # Initialize the OCR engine
    ocr_engine = RapidOCR()
    HAS_OCR = True
except ImportError:
    HAS_OCR = False
    print("❌ Missing RapidOCR. Please run: pip3 install rapidocr-onnxruntime")
    exit(1)

# ==========================================
# CONFIGURATION
# ==========================================
TARGET_PDFS = [
    "/Users/ganeshchandrauniyal/Desktop/Summer Project Ideas/PM Speeches/PM_Speeches_Narendra_Modi_Eng_Vol-I_2014-2021.pdf",
    "/Users/ganeshchandrauniyal/Desktop/Summer Project Ideas/PM Speeches/PM_Speeches_Narendra_Modi_Eng_Vol-II_2022-2025.pdf"
]

OUTPUT_JSONL = "/Users/ganeshchandrauniyal/Desktop/Summer Project Ideas/PDF to JSONL/publication_corpus.jsonl"
CHECKPOINT_FILE = "/Users/ganeshchandrauniyal/Desktop/Summer Project Ideas/PDF to JSONL/checkpoint.json"

VOLUME_ID = "PM_Vol"
TARGET_WORDS = 800
OVERLAP_WORDS = 100

def get_start_counter(jsonl_path):
    if not os.path.exists(jsonl_path): return 1
    docs = set()
    with open(jsonl_path, 'r', encoding='utf-8') as f:
        for line in f:
            try: docs.add(json.loads(line).get("document_id"))
            except: continue
    return len(docs) + 1

def clean_ocr_text(text):
    text = re.sub(r'\s+([.,;:!?])', r'\1', text)
    text = re.sub(r'\n+', ' ', text)
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
    print("\n" + "="*60)
    print("🚀 PURE-PYTHON OCR PIPELINE (No Homebrew Required)")
    print("="*60 + "\n")

    doc_counter = get_start_counter(OUTPUT_JSONL)
    total_added = 0
    
    if os.path.exists(CHECKPOINT_FILE):
        with open(CHECKPOINT_FILE, 'r') as f: 
            processed = set(json.load(f).get("processed_pdfs", []))
    else: 
        processed = set()

    with open(OUTPUT_JSONL, 'a', encoding='utf-8') as f_out:
        for pdf_name in TARGET_PDFS:
            pdf_path = Path(pdf_name)
                
            if not pdf_path.exists():
                print(f"⚠️ {pdf_name} not found. Skipping.")
                continue
                
            if pdf_name in processed:
                print(f"✅ {pdf_name} already in checkpoint. Skipping.")
                continue
                
            print(f"📥 Loading {pdf_name} with PyMuPDF...")
            try:
                doc = fitz.open(str(pdf_path))
            except Exception as e:
                print(f"❌ Failed to open {pdf_name}: {e}")
                continue
                
            print(f"🔍 Running RapidOCR on {len(doc)} pages...")
            full_text = ""
            
            for page in tqdm(doc, desc=f"OCR {pdf_name}", unit="page", ncols=80, colour="cyan"):
                # 1. Render page to PNG bytes in memory
                pix = page.get_pixmap(dpi=300)
                img_bytes = pix.tobytes("png")
                
                # 2. Run RapidOCR
                result, _ = ocr_engine(img_bytes)
                
                # 3. Extract text (result is a list of [bbox, text, confidence])
                if result:
                    page_text = "\n".join([line[1] for line in result])
                    full_text += page_text + "\n"
                
            doc.close()
            
            clean = clean_ocr_text(full_text)
            word_count = len(clean.split())
            print(f"✅ Extracted {word_count:,} words via RapidOCR.")
            
            if word_count < 500:
                print(f"⚠️ Too little text extracted. Skipping.")
                processed.add(pdf_name)
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

    with open(CHECKPOINT_FILE, 'w') as f: 
        json.dump({"processed_pdfs": list(processed)}, f, indent=2)
        
    print("="*60)
    print(f"🏆 OCR PIPELINE COMPLETE: Appended {total_added} chunks to {OUTPUT_JSONL}")
    print("="*60 + "\n")

if __name__ == "__main__":
    main()
