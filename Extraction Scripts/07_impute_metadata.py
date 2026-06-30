#!/usr/bin/env python3
import sys
import re
import json

MARKERS = [
    r'18th\s+Lok\s+Sabha', r'18th\s+House', r'third\s+term',
    r'Modi\s+III', r'Modi\s+3\.0', r'2024\s+elections?',
    r'June\s+4', r'Chandrababu', r'Nitish\s+Kumar',
    r'NDA\s+government', r'coalition\s+government',
    r'allies\s+in\s+government', r'\b272\b'
]

PHASE5 = re.compile('|'.join(MARKERS), re.I)

def main():
    if len(sys.argv) < 3:
        print("usage: phase5.py <in.jsonl> <out.jsonl> [out.parquet]")
        sys.exit(1)

    in_f = sys.argv[1]
    out_jsonl = sys.argv[2]
    out_pq = sys.argv[3] if len(sys.argv) > 3 else None

    pq = None
    pa = None
    if out_pq:
        try:
            import pyarrow.parquet as pq
            import pyarrow as pa
        except ImportError:
            print("pyarrow missing, skipping parquet")
            out_pq = None

    recs = []
    fixes = 0

    with open(in_f, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            r = json.loads(line)
            
            if r.get("pm_name") == "Narendra Modi" and r.get("political_era") == "Phase 4: Single-Party Majorities":
                if PHASE5.search(r.get("text_chunk", "")):
                    r["political_era"] = "Phase 5: Return to Coalition"
                    r["coalition_gov"] = True
                    r["date"] = "2024-06-09"
                    fixes += 1
            recs.append(r)

    with open(out_jsonl, 'w', encoding='utf-8') as f:
        for r in recs:
            f.write(json.dumps(r, ensure_ascii=False) + '\n')

    if out_pq and pq:
        cols = {k: [] for k in ['document_id', 'chunk_id', 'date', 'pm_name', 'topic', 
                                'coalition_gov', 'political_era', 'chunk_index', 
                                'total_chunks', 'word_count', 'text_chunk']}
        for r in recs:
            cols['document_id'].append(r.get('document_id', ''))
            cols['chunk_id'].append(r.get('chunk_id', ''))
            cols['date'].append(r.get('date', ''))
            cols['pm_name'].append(r.get('pm_name', ''))
            cols['topic'].append(r.get('topic', ''))
            cols['coalition_gov'].append(bool(r.get('coalition_gov', False)))
            cols['political_era'].append(r.get('political_era', ''))
            cols['chunk_index'].append(int(r.get('chunk_index', 0)))
            cols['total_chunks'].append(int(r.get('total_chunks', 0)))
            cols['word_count'].append(int(r.get('word_count', 0)))
            cols['text_chunk'].append(r.get('text_chunk', ''))
            
        pq.write_table(pa.table(cols), out_pq, compression='zstd')

    print(f"fixed {fixes} records.")

if __name__ == "__main__":
    main()