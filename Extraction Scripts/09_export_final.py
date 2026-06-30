#!/usr/bin/env python3
import sys
import re
import json

DOC_PM = {
    "PM_Vol_Speech_438": "Narendra Modi",
    "PM_Vol_Speech_439": "Narendra Modi",
    "PM_Vol_Speech_440": "Narendra Modi",
    "PM_Vol_Speech_441": "Indira Gandhi"
}

TENURES = [
    ("Jawaharlal Nehru", "1952-01-01", "1964-05-27"),
    ("Gulzarilal Nanda (Acting)", "1964-05-27", "1964-06-09"),
    ("Lal Bahadur Shastri", "1964-06-09", "1966-01-11"),
    ("Gulzarilal Nanda (Acting)", "1966-01-11", "1966-01-24"),
    ("Indira Gandhi", "1966-01-24", "1977-03-24"),
    ("Morarji Desai", "1977-03-24", "1979-07-28"),
    ("Charan Singh", "1979-07-28", "1980-01-14"),
    ("Indira Gandhi", "1980-01-14", "1984-10-31"),
    ("Rajiv Gandhi", "1984-10-31", "1989-12-02"),
    ("V.P. Singh", "1989-12-02", "1990-11-10"),
    ("Chandra Shekhar", "1990-11-10", "1991-06-21"),
    ("P.V. Narasimha Rao", "1991-06-21", "1996-05-16"),
    ("Atal Bihari Vajpayee", "1996-05-16", "1996-06-01"),
    ("H.D. Deve Gowda", "1996-06-01", "1997-04-21"),
    ("I.K. Gujral", "1997-04-21", "1998-03-19"),
    ("Atal Bihari Vajpayee", "1998-03-19", "2004-05-22"),
    ("Manmohan Singh", "2004-05-22", "2014-05-26"),
    ("Narendra Modi", "2014-05-26", "2026-12-31"),
]

SPACED_DIGITS = re.compile(r'\b\d{1,2}\s\d{1,2}\b')
WHITESPACE = re.compile(r'\s+')
ISO_DATE = re.compile(r'^(\d{4})-(\d{2})-(\d{2})$')

def valid_date(d):
    if not d or d in ("Unknown Date", "Compiled Volume", "Unknown", ""):
        return None
    m = ISO_DATE.match(d)
    if m:
        y = int(m.group(1))
        if 1952 <= y <= 2026:
            return d
    return None

def get_pm(doc_id, d):
    if doc_id in DOC_PM:
        return DOC_PM[doc_id]
    if d:
        for pm, start, end in TENURES:
            if start <= d <= end:
                return pm
    return "Unknown"

def get_era(pm, d):
    if d:
        if "1952-01-01" <= d < "1977-03-24": return "Phase 1: Single-Party Dominance", False
        if "1977-03-24" <= d < "1980-01-14": return "Phase 2: Early Coalitions & Instability", True
        if "1980-01-14" <= d < "1989-12-02": return "Phase 2: Early Coalitions & Instability", False
        if "1989-12-02" <= d < "2014-05-26": return "Phase 3: The Coalition Era", True
        if "2014-05-26" <= d < "2024-06-09": return "Phase 4: Single-Party Majorities", False
        if d >= "2024-06-09": return "Phase 5: Return to Coalition", True

    if pm == "Indira Gandhi": return "Phase 1/2: Indira Gandhi Era", False
    if pm == "Narendra Modi": return "Phase 4/5: Narendra Modi Era", False
    if pm in ("Jawaharlal Nehru", "Lal Bahadur Shastri"): return "Phase 1: Single-Party Dominance", False
    if pm in ("Morarji Desai", "Charan Singh"): return "Phase 2: Early Coalitions & Instability", True
    if pm == "Rajiv Gandhi": return "Phase 2: Early Coalitions & Instability", False
    if pm in ("V.P. Singh", "Chandra Shekhar", "P.V. Narasimha Rao", "H.D. Deve Gowda", "I.K. Gujral", "Atal Bihari Vajpayee", "Manmohan Singh"):
        return "Phase 3: The Coalition Era", True
    
    return "Unknown Era", None

def clean_text(t):
    if not t: return ""
    t = SPACED_DIGITS.sub('', t)
    return WHITESPACE.sub(' ', t).strip()

def main():
    if len(sys.argv) < 3:
        print("usage: ipec.py <in.jsonl> <out.jsonl> [out.parquet]")
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

    cols = {
        'document_id': [], 'chunk_id': [], 'date': [], 'pm_name': [],
        'topic': [], 'coalition_gov': [], 'political_era': [], 'text_chunk': []
    }

    with open(in_f, 'r', encoding='utf-8') as fin, \
         open(out_jsonl, 'w', encoding='utf-8') as fout:
        
        for line in fin:
            line = line.strip()
            if not line: continue
            r = json.loads(line)
            
            doc_id = r.get("document_id", r.get("doc_id", ""))
            d = valid_date(r.get("date", ""))
            pm = get_pm(doc_id, d)
            era, coal = get_era(pm, d)
            text = clean_text(r.get("text_chunk", r.get("snippet", "")))
            
            out_r = {
                "document_id": doc_id,
                "chunk_id": r.get("chunk_id", doc_id),
                "date": d if d else "Compiled Volume",
                "pm_name": pm,
                "topic": r.get("topic", ""),
                "coalition_gov": coal,
                "political_era": era,
                "text_chunk": text
            }
            
            fout.write(json.dumps(out_r, ensure_ascii=False) + '\n')
            
            if out_pq:
                cols['document_id'].append(out_r['document_id'])
                cols['chunk_id'].append(out_r['chunk_id'])
                cols['date'].append(out_r['date'])
                cols['pm_name'].append(out_r['pm_name'])
                cols['topic'].append(out_r['topic'])
                cols['coalition_gov'].append(out_r['coalition_gov'])
                cols['political_era'].append(out_r['political_era'])
                cols['text_chunk'].append(out_r['text_chunk'])

    if out_pq and pq:
        table = pa.table(cols)
        pq.write_table(table, out_pq, compression='zstd')

    print("done.")

if __name__ == "__main__":
    main()