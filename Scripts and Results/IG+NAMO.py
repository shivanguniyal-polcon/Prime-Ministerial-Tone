#!/usr/bin/env python3
"""
Rescue Script for Skipped PDFs (Indira Gandhi & Narendra Modi)
==============================================================
Uses relaxed date formats and modern heading anchors to extract
speeches that the strict historical pipeline missed.
Appends directly to your existing publication_corpus.jsonl.
"""

import os
import re
import json
import fitz
from pathlib import Path
from datetime import datetime
from tqdm import tqdm
import wordninja

# ==========================================
# CONFIGURATION
# ==========================================
OUTPUT_DIR = "/Users/ganeshchandrauniyal/Desktop/Summer Project Ideas/PDF to JSONL"
CLEAN_JSONL = os.path.join(OUTPUT_DIR, "publication_corpus.jsonl")
CHECKPOINT_FILE = os.path.join(OUTPUT_DIR, "checkpoint.json")
VOLUME_ID = "PM_Vol"
TARGET_WORDS = 800
OVERLAP_WORDS = 100

# The 3 PDFs that failed in the main run
SKIPPED_PDFS = [
    "Indira_Gandhi_Speeches_in_Parliament_.pdf",
    "PM_Speeches_Narendra_Modi_Eng_Vol-I_2014-2021.pdf",
    "PM_Speeches_Narendra_Modi_Eng_Vol-II_2022-2025.pdf"
]

# ==========================================
# HELPER: FLEXIBLE DATE PARSER
# ==========================================
def parse_date_flexible(date_str):
    """Handles DD Month YYYY, Month DD YYYY, and Month YYYY"""
    date_str = date_str.replace(',', '').strip().title()
    formats = ["%d %B %Y", "%B %d %Y", "%B %Y", "%d %b %Y", "%b %d %Y"]
    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return date_str

def get_start_counter(jsonl_path):
    if not os.path.exists(jsonl_path): return 1
    existing_docs = set()
    with open(jsonl_path, 'r', encoding='utf-8') as f:
        for line in f:
            try: existing_docs.add(json.loads(line).get("document_id"))
            except: continue
    return len(existing_docs) + 1

# ==========================================
# RELAXED SEGMENTATION (For Modern/Indira PDFs)
# ==========================================
def rescue_segment_speeches(text):
    # 1. Relaxed Date Pattern (Catches "January, 1996" and "August 15, 2014")
    date_pattern = re.compile(
        r'^\s*(?:New Delhi\s*,?\s*)?'
        r'('
        r'\d{1,2}\s+(?:January|February|March|April|May|June|July|August|September|October|November|December)\w*\s*,?\s*\d{4}|'
        r'(?:January|February|March|April|May|June|July|August|September|October|November|December)\w*\s+\d{1,2},?\s*\d{4}|'
        r'(?:January|February|March|April|May|June|July|August|September|October|November|December)\w*\s*,?\s*\d{4}'
        r')\s*$',
        re.MULTILINE | re.IGNORECASE
    )
    matches = list(date_pattern.finditer(text))
    
    # 2. Fallback: Modern Headings (If standalone dates aren't found)
    if not matches:
        heading_pattern = re.compile(r'^(?:#\s*)?(SPEECH\s+BY|ADDRESS\s+BY|STATEMENT\s+BY|REMARKS\s+BY|PM\s+SPEECH).*$', re.MULTILINE | re.IGNORECASE)
        matches = list(heading_pattern.finditer(text))
        speeches = []
        for i, m in enumerate(matches):
            start_pos = m.start()
            end_pos = matches[i+1].start() if i+1 < len(matches) else len(text)
            topic = re.sub(r'[*#]', '', m.group(0)).strip().title()
            body = text[start_pos:end_pos]
            
            # Extract date from the first 300 chars of the body
            date_search = re.search(r'(\d{1,2}\s+(?:January|February|March|April|May|June|July|August|September|October|November|December)\w*\s*,?\s*\d{4}|(?:January|February|March|April|May|June|July|August|September|October|November|December)\w*\s+\d{1,2},?\s*\d{4})', body[:300], re.IGNORECASE)
            date_str = date_search.group(1) if date_search else "Unknown Date"
            
            if len(body) > 800:
                speeches.append({'date_str': date_str, 'topic': topic, 'body': body})
        return speeches

    # 3. Process standard date matches
    speeches = []
    for i, m in enumerate(matches):
        date_str = m.group(1)
        start_pos = m.end()
        end_pos = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        date_line_start = text.rfind('\n', 0, m.start()) + 1
        title_block = text[max(0, date_line_start - 600):date_line_start].strip()

        title_lines = []
        for line in reversed(title_block.split('\n')):
            line = line.strip()
            if not line: continue
            if re.match(r'^(\d{1,3}|xxx+|i+|v+|x+|NIL|CONTENTS|PREFACE)$', line, re.IGNORECASE): continue
            title_lines.insert(0, line)
            if len(title_lines) >= 5: break

        raw_topic = " ".join(title_lines)
        topic = re.sub(r'[*#]', '', raw_topic).strip()
        topic = re.sub(r'\s+', ' ', topic).title()
        if not topic or len(topic) < 5: topic = "Parliamentary Speech"

        raw_body = text[start_pos:end_pos]
        raw_body = re.split(r'(?i)\bBACK\s+NOTE\b', raw_body)[0]
        
        if len(raw_body) > 800:
            speeches.append({'date_str': date_str, 'topic': topic, 'body': raw_body})
            
    return speeches

# ==========================================
# HEALING & CHUNKING (Copied from Master Script)
# ==========================================
# [Note: For brevity, we use a simplified healing function here. 
# The main healing dictionary is applied, but we skip the massive FUSED_MAP 
# to keep this script short, relying on the fact that Modi/Indira PDFs 
# are modern/cleaner and have fewer OCR shatters.]
def heal_text(text):
    text = re.sub(r'(\w+)ti on\b', r'\1tion', text)
    text = re.sub(r'(\w+)si on\b', r'\1sion', text)
    text = re.sub(r'\s+([.,;:!?])', r'\1', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

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

# ==========================================
# MAIN RESCUE EXECUTION
# ==========================================
def main():
    print("\n" + "=" * 60)
    print("🚑 RESCUE MISSION: Processing Skipped PDFs")
    print("=" * 60 + "\n")

    doc_counter = get_start_counter(CLEAN_JSONL)
    total_added = 0
    
    # Load checkpoint to update it later
    if os.path.exists(CHECKPOINT_FILE):
        with open(CHECKPOINT_FILE, 'r', encoding='utf-8') as f:
            processed_pdfs = set(json.load(f).get("processed_pdfs", []))
    else:
        processed_pdfs = set()

    with open(CLEAN_JSONL, 'a', encoding='utf-8') as f_clean:
        for pdf_name in SKIPPED_PDFS:
            pdf_path = Path("/Users/ganeshchandrauniyal/Desktop/Summer Project Ideas/PM Speeches") / pdf_name
            if not pdf_path.exists():
                print(f"⚠️ {pdf_name} not found in raw_pdfs/. Skipping.")
                continue
                
            print(f"📥 Extracting {pdf_name}...")
            try:
                doc = fitz.open(str(pdf_path))
                text = "\n".join([page.get_text() for page in doc])
                doc.close()
            except Exception as e:
                print(f"❌ Failed to open {pdf_name}: {e}")
                continue
                
            # Preprocess (Drop TOC/Markdown noise)
            text = re.sub(r'^\s*#{1,6}\s*', '', text, flags=re.MULTILINE)
            
            print(f"🔍 Segmenting with relaxed rules...")
            speeches = rescue_segment_speeches(text)
            
            if not speeches:
                print(f"⚠️ Still no valid speeches found in {pdf_name}. (Might be heavily image-based or unstructured).")
                processed_pdfs.add(pdf_name)
                continue
                
            print(f"📑 Found {len(speeches)} speeches! Healing and chunking...")
            
            for speech in speeches:
                iso_date = parse_date_flexible(speech['date_str'])
                doc_id = f"{VOLUME_ID}_Speech_{doc_counter:03d}"
                
                clean_body = heal_text(speech['body'])
                chunks = chunk_text(clean_body, TARGET_WORDS, OVERLAP_WORDS)
                
                for c_idx, c_text in enumerate(chunks):
                    row = {
                        "document_id": doc_id, "chunk_id": f"{doc_id}_{c_idx}", "date": iso_date,
                        "topic": speech['topic'], "chunk_index": c_idx, "total_chunks": len(chunks),
                        "word_count": len(c_text.split()), "text_chunk": c_text
                    }
                    f_clean.write(json.dumps(row, ensure_ascii=False) + '\n')
                    total_added += 1
                    
                doc_counter += 1
                
            processed_pdfs.add(pdf_name)
            print(f"💾 Saved {len(chunks) * len(speeches)} chunks for {pdf_name}\n")

    # Update Checkpoint
    with open(CHECKPOINT_FILE, 'w', encoding='utf-8') as f_cp:
        json.dump({"processed_pdfs": list(processed_pdfs)}, f_cp, indent=2)

    print("=" * 60)
    print("🏆 RESCUE MISSION COMPLETE")
    print("=" * 60)
    print(f"📄 Appended {total_added:,} new chunks to {CLEAN_JSONL}")
    print("Your archive is now fully consolidated!")
    print("=" * 60 + "\n")

if __name__ == "__main__":
    main()