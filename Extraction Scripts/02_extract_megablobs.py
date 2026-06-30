#!/usr/bin/env python3
import sys
import os
import re
import json
import fitz
from pathlib import Path
from datetime import datetime

def parse_date(s):
    s = s.replace(',', '').strip().title()
    for fmt in ["%d %B %Y", "%B %d %Y", "%B %Y", "%d %b %Y", "%b %d %Y"]:
        try:
            return datetime.strptime(s, fmt).strftime("%Y-%m-%d")
        except ValueError:
            pass
    return s

def read_pdf(path):
    try:
        doc = fitz.open(path)
    except Exception:
        return ""
    text = "\n".join(page.get_text() for page in doc)
    doc.close()
    return text

def segment(text):
    date_re = re.compile(
        r'^\s*(?:New Delhi\s*,?\s*)?'
        r'('
        r'\d{1,2}\s+(?:January|February|March|April|May|June|July|August|September|October|November|December)\w*\s*,?\s*\d{4}|'
        r'(?:January|February|March|April|May|June|July|August|September|October|November|December)\w*\s+\d{1,2},?\s*\d{4}|'
        r'(?:January|February|March|April|May|June|July|August|September|October|November|December)\w*\s*,?\s*\d{4}'
        r')\s*$',
        re.M | re.I
    )
    
    matches = list(date_re.finditer(text))
    
    # fallback to headings if strict dates fail
    if not matches:
        head_re = re.compile(r'^(?:#\s*)?(SPEECH\s+BY|ADDRESS\s+BY|STATEMENT\s+BY|REMARKS\s+BY|PM\s+SPEECH).*$', re.M | re.I)
        matches = list(head_re.finditer(text))
        
        speeches = []
        for i, m in enumerate(matches):
            start = m.start()
            end = matches[i+1].start() if i+1 < len(matches) else len(text)
            topic = re.sub(r'[*#]', '', m.group(0)).strip().title()
            body = text[start:end]
            
            d_search = re.search(r'(\d{1,2}\s+(?:January|February|March|April|May|June|July|August|September|October|November|December)\w*\s*,?\s*\d{4}|(?:January|February|March|April|May|June|July|August|September|October|November|December)\w*\s+\d{1,2},?\s*\d{4})', body[:300], re.I)
            date_str = d_search.group(1) if d_search else "Unknown Date"
            
            if len(body) > 800:
                speeches.append({'date': date_str, 'topic': topic, 'body': body})
        return speeches

    speeches = []
    for i, m in enumerate(matches):
        date_str = m.group(1)
        start = m.end()
        end = matches[i+1].start() if i+1 < len(matches) else len(text)
        
        line_start = text.rfind('\n', 0, m.start()) + 1
        block = text[max(0, line_start - 600):line_start].strip()
        
        title = []
        for ln in reversed(block.split('\n')):
            ln = ln.strip()
            if not ln: continue
            if re.match(r'^(\d{1,3}|xxx+|i+|v+|x+|NIL|CONTENTS|PREFACE)$', ln, re.I): continue
            title.insert(0, ln)
            if len(title) >= 5: break
            
        topic = re.sub(r'[*#]', '', " ".join(title)).strip()
        topic = re.sub(r'\s+', ' ', topic).title()
        if not topic or len(topic) < 5:
            topic = "Parliamentary Speech"
            
        body = text[start:end]
        body = re.split(r'(?i)\bBACK\s+NOTE\b', body)[0]
        
        if len(body) > 800:
            speeches.append({'date': date_str, 'topic': topic, 'body': body})
            
    return speeches

def heal(text):
    text = re.sub(r'(\w+)ti on\b', r'\1tion', text)
    text = re.sub(r'(\w+)si on\b', r'\1sion', text)
    text = re.sub(r'\s+([.,;:!?])', r'\1', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def chunk(text, max_w, overlap):
    words = text.split()
    res = []
    step = max_w - overlap
    for i in range(0, len(words), step):
        c = words[i:i+max_w]
        if len(c) < max_w // 4 and i > 0:
            if res: res[-1] += " " + " ".join(c)
            break
        res.append(" ".join(c))
    return res

def get_last_id(path):
    if not path.exists() or path.stat().st_size == 0:
        return 0
    with open(path, 'rb') as f:
        try:
            f.seek(-2, os.SEEK_END)
            while f.read(1) != b'\n':
                f.seek(-2, os.SEEK_CUR)
        except OSError:
            f.seek(0)
        last = f.readline().decode()
        if last:
            try:
                return int(json.loads(last)["document_id"].split("_")[-1])
            except:
                pass
    return 0

def main():
    if len(sys.argv) < 3:
        print("usage: rescue.py <in_dir> <out_jsonl>")
        sys.exit(1)

    in_dir = Path(sys.argv[1])
    out_jsonl = Path(sys.argv[2])
    
    targets = [
        "Indira_Gandhi_Speeches_in_Parliament_.pdf",
        "PM_Speeches_Narendra_Modi_Eng_Vol-I_2014-2021.pdf",
        "PM_Speeches_Narendra_Modi_Eng_Vol-II_2022-2025.pdf"
    ]
    
    doc_id = get_last_id(out_jsonl) + 1
    f_out = open(out_jsonl, 'a', encoding='utf-8')
    
    for name in targets:
        pdf = in_dir / name
        if not pdf.exists():
            print(f"skip {name}")
            continue
            
        print(f"read {name}")
        text = read_pdf(pdf)
        if not text:
            continue
            
        text = re.sub(r'^\s*#{1,6}\s*', '', text, flags=re.M)
        speeches = segment(text)
        
        if not speeches:
            print(f"skip {name} (no speeches)")
            continue
            
        print(f"found {len(speeches)} in {name}")
        
        for sp in speeches:
            iso_date = parse_date(sp['date'])
            clean = heal(sp['body'])
            chunks = chunk(clean, 800, 100)
            
            for c_idx, c_text in enumerate(chunks):
                row = {
                    "document_id": f"PM_{doc_id:04d}",
                    "chunk_id": f"PM_{doc_id:04d}_{c_idx}",
                    "date": iso_date,
                    "topic": sp['topic'],
                    "chunk": c_idx,
                    "total": len(chunks),
                    "words": len(c_text.split()),
                    "text": c_text
                }
                f_out.write(json.dumps(row, ensure_ascii=False) + '\n')
            doc_id += 1
            
    f_out.close()
    print("done.")

if __name__ == "__main__":
    main()