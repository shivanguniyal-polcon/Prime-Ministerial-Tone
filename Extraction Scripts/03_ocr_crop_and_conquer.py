#!/usr/bin/env python3
import sys
import os
import re
import json
import fitz
import numpy as np
from PIL import Image
from io import BytesIO
from datetime import datetime
from rapidocr_onnxruntime import RapidOCR

# editable targets. 
# change these if your document IDs or file names change.
TARGET_PDFS = [
    "PM_Speeches_Narendra_Modi_Eng_Vol-I_2014-2021.pdf",
    "PM_Speeches_Narendra_Modi_Eng_Vol-II_2022-2025.pdf"
]

TARGET_DOC_IDS = {
    "PM_Vol_Speech_439",
    "PM_Vol_Speech_440"
}

BAD_DATES = {"Compiled Volume", "Unknown Date", "Unknown", ""}

# fixed regex and parsing logic
DATE_PATTERNS = [
    re.compile(r'(\d{1,2}[\s\-/](?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec|January|February|March|April|May|June|July|August|September|October|November|December)\w*[\s\-/]\d{4})', re.I),
    re.compile(r'((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec|January|February|March|April|May|June|July|August|September|October|November|December)\w*[\s\-/]\d{1,2}[\s\-/]\d{4})', re.I)
]

DATE_FMTS = [
    "%d %B %Y", "%d %b %Y", "%d-%B-%Y", "%d/%B/%Y",
    "%B %d %Y", "%b %d %Y", "%B-%d-%Y", "%B/%d/%Y",
    "%d %B, %Y", "%B %d, %Y"
]

def parse_date(raw):
    raw = raw.strip().replace(',', '')
    for fmt in DATE_FMTS:
        try:
            dt = datetime.strptime(raw, fmt)
            if 2014 <= dt.year <= 2026:
                return dt.strftime("%Y-%m-%d")
        except ValueError:
            pass
    return None

def extract_dates(pdf_path, ocr):
    doc = fitz.open(pdf_path)
    dates = []
    
    for page_num in range(len(doc)):
        page = doc[page_num]
        pix = page.get_pixmap(dpi=300)
        img = Image.open(BytesIO(pix.tobytes("png")))
        
        w, h = img.size
        top = img.crop((0, 0, w, h // 2))
        
        result, _ = ocr(np.array(top))
        if not result:
            continue
            
        text = " ".join(line[1] for line in result)
        
        found = None
        for pat in DATE_PATTERNS:
            m = pat.search(text)
            if m:
                found = parse_date(m.group(1))
                if found:
                    break
        
        if found:
            dates.append((page_num, found))
            
    doc.close()
    return dates

def main():
    if len(sys.argv) < 4:
        print("usage: fix_dates.py <pdf_dir> <in_jsonl> <out_jsonl>")
        sys.exit(1)

    pdf_dir = sys.argv[1]
    in_jsonl = sys.argv[2]
    out_jsonl = sys.argv[3]

    print("loading ocr...")
    ocr = RapidOCR()

    all_dates = []
    for name in TARGET_PDFS:
        path = os.path.join(pdf_dir, name)
        if not os.path.exists(path):
            print(f"missing {name}")
            continue
        
        print(f"scanning {name}...")
        dates = extract_dates(path, ocr)
        print(f"found {len(dates)} dates")
        all_dates.extend(dates)

    if not all_dates:
        print("no dates found. exiting.")
        sys.exit(0)

    all_dates.sort(key=lambda x: x[0])
    
    print("reading corpus...")
    chunks = []
    with open(in_jsonl, 'r', encoding='utf-8') as f:
        for line in f:
            chunks.append(json.loads(line))

    # strip() handles trailing spaces in the JSONL document_ids
    missing = [
        i for i, c in enumerate(chunks)
        if c.get("document_id", "").strip() in TARGET_DOC_IDS and c.get("date", "").strip() in BAD_DATES
    ]
    
    print(f"updating {len(missing)} chunks with {len(all_dates)} dates...")
    
    updated = 0
    for i, idx in enumerate(missing):
        if i < len(all_dates):
            chunks[idx]["date"] = all_dates[i][1]
            chunks[idx]["date_source"] = "ocr_header"
            updated += 1

    print("writing corpus...")
    with open(out_jsonl, 'w', encoding='utf-8') as f:
        for c in chunks:
            f.write(json.dumps(c, ensure_ascii=False) + '\n')
            
    print(f"done. updated {updated} chunks.")

if __name__ == "__main__":
    main()