#!/usr/bin/env python3
import sys
import re
import json
from collections import defaultdict

# editable dials.
# tweak these if new scanner loops or broken documents appear.
FRANKENSTEIN_DOC = "PM_Vol_Speech_438"

REPEATED_PHRASES = [
    "At times the Government banked upon procrastination  ",
    "in order to avoid new areas of dispute and left everything to the  ",
    "judgement of the Courts. Now the courts have started giving  ",
    "verdicts in matters which ought to have been decided by the  ",
    "Executive and the P  ",
    "Parliament. Why cannot the P  ",
    "discharge its duties and responsibilities? Why the Executive cannot  ",
    "should be honest and vibrant and it should not delay matters.  "
]

# fixed logic.
REP_RULES = []
for p in REPEATED_PHRASES:
    REP_RULES.append((re.compile(f"({re.escape(p)}){{3,}}"), p))

INTERRUPTION_RULES = [
    (re.compile(r'(?:[xX]+[\.\s]+){2,}[xX]+[\.\s]*'), '[INTERRUPTION] '),
    (re.compile(r'\b[xX]{3,}\b'), '[INTERRUPTION]'),
    (re.compile(r'\*{3,}'), '[INTERRUPTION]')
]

def clean_text(text):
    for pat, rep in REP_RULES:
        text = pat.sub(rep, text)
    for pat, rep in INTERRUPTION_RULES:
        text = pat.sub(rep, text)
    return re.sub(r'\s+', ' ', text).strip()

def main():
    if len(sys.argv) != 3:
        print("usage: fix.py <in.jsonl> <out.jsonl>")
        sys.exit(1)

    in_path = sys.argv[1]
    out_path = sys.argv[2]

    docs = defaultdict(list)
    with open(in_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            docs[rec['document_id']].append(rec)

    out_records = []
    
    for doc_id in sorted(docs.keys()):
        chunks = docs[doc_id]
        
        # sort by integer index. string sorting puts chunk_10 before chunk_2.
        chunks.sort(key=lambda x: int(x.get('chunk_id', '0').split('_')[-1]))
        
        if doc_id == FRANKENSTEIN_DOC:
            for r in chunks:
                orig_idx = r['chunk_id'].split('_')[-1]
                new_id = f"{doc_id}_S{orig_idx}"
                r['document_id'] = new_id
                r['chunk_id'] = f"{new_id}_0"
                r['chunk_index'] = 0
                r['total_chunks'] = 1
                r['text_chunk'] = clean_text(r.get('text_chunk', ''))
                out_records.append(r)
            continue

        for i, r in enumerate(chunks):
            r['chunk_id'] = f"{doc_id}_{i}"
            r['chunk_index'] = i
            r['total_chunks'] = len(chunks)
            r['text_chunk'] = clean_text(r.get('text_chunk', ''))
            out_records.append(r)

    with open(out_path, 'w', encoding='utf-8') as f:
        for r in out_records:
            f.write(json.dumps(r, ensure_ascii=False) + '\n')

    print(f"wrote {len(out_records)} records.")

if __name__ == "__main__":
    main()