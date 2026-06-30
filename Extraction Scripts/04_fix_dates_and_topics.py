#!/usr/bin/env python3
import sys
import re
import json

# editable maps.
# fix truncated topics and define pm tenures for date imputation.
TOPIC_MAP = {
    "PM_Vol_Speech_001": "Address on Election of the Speaker",
    "PM_Vol_Speech_003": "Motion of Thanks to the Speaker",
    "PM_Vol_Speech_017": "Statement on Nuclear Tests and Indo-US Relations",
    "PM_Vol_Speech_018": "Reply on Election of Deputy Speaker",
    "PM_Vol_Speech_019": "Statement on Iraq Situation",
    "PM_Vol_Speech_022": "Statement on Visit to USA",
    "PM_Vol_Speech_023": "Statement on Ayodhya Cases",
    "PM_Vol_Speech_024": "Statement on Ayodhya",
    "PM_Vol_Speech_025": "Statement on Ayodhya",
    "PM_Vol_Speech_026": "Statement on Operational Guidelines",
    "PM_Vol_Speech_027": "Valedictory Reference",
    "PM_Vol_Speech_032": "Valedictory Reference",
    "PM_Vol_Speech_033": "Statement on Attorney General of India",
    "PM_Vol_Speech_037": "Statement on Government Business",
    "PM_Vol_Speech_038": "Valedictory Reference",
    "PM_Vol_Speech_044": "Statement on India-Pakistan Relations",
    "PM_Vol_Speech_048": "Statement on Foreign Visits",
    "PM_Vol_Speech_049": "Statement on Attack on Parliament",
    "PM_Vol_Speech_058": "Address on Election of the Speaker",
    "PM_Vol_Speech_059": "Statement on Drought Situation",
    "PM_Vol_Speech_060": "Statement on Visit of Russian President",
    "PM_Vol_Speech_063": "Statement on Agricultural Loans",
    "PM_Vol_Speech_069": "Statement on Foreign Visits (Evian and China)",
    "PM_Vol_Speech_073": "Statement on Parliament Security",
    "PM_Vol_Speech_207": "Parliamentary Bill",
    "PM_Vol_Speech_225": "Statement Regarding U.S. Military Aid",
    "PM_Vol_Speech_264": "Motion Regarding Dr. Zakir Husain",
    "PM_Vol_Speech_406": "Statement Regarding Visit of Foreign Dignitary",
    "PM_Vol_Speech_421": "Statement Regarding Visit of Foreign Dignitary"
}

TENURES = {
    "PM_Vol_Speech_439": (2014, 2024),
    "PM_Vol_Speech_440": (2022, 2026),
    "PM_Vol_Speech_441": (1966, 1984)
}

YEAR_RE = re.compile(r'\b(?:19|20)\d{2}\b')
PUNCT_RE = re.compile(r'[,.:;]+$')

def find_year(text, min_y, max_y):
    for m in YEAR_RE.finditer(text[:1000]):
        y = int(m.group(0))
        if min_y <= y <= max_y:
            return y
    return (min_y + max_y) // 2

def main():
    if len(sys.argv) != 3:
        print("usage: fix_meta.py <in.jsonl> <out.jsonl>")
        sys.exit(1)

    in_path = sys.argv[1]
    out_path = sys.argv[2]

    fixed_topics = 0
    imputed_dates = 0
    fallback_dates = 0
    remaining_compiled = 0
    trailing_punct = 0

    with open(in_path, 'r', encoding='utf-8') as fin, \
         open(out_path, 'w', encoding='utf-8') as fout:
        
        for line in fin:
            line = line.strip()
            if not line:
                continue
            
            rec = json.loads(line)
            
            # strip handles trailing spaces from bad pdf extraction
            doc_id = rec.get("document_id", "").strip()
            
            if doc_id in TOPIC_MAP:
                if rec.get("topic") != TOPIC_MAP[doc_id]:
                    rec["topic"] = TOPIC_MAP[doc_id]
                    fixed_topics += 1
            
            topic = rec.get("topic", "")
            clean_topic = PUNCT_RE.sub('', topic).strip()
            if clean_topic != topic:
                rec["topic"] = clean_topic
            
            if rec.get("date") == "Compiled Volume":
                if doc_id in TENURES:
                    min_y, max_y = TENURES[doc_id]
                    y = find_year(rec.get("text_chunk", ""), min_y, max_y)
                    rec["date"] = f"{y}-01-01"
                    rec["date_source"] = "text_year_imputed"
                    imputed_dates += 1
                else:
                    rec["date"] = "1999-01-01"
                    rec["date_source"] = "fallback_imputed"
                    fallback_dates += 1

            if rec.get("date") == "Compiled Volume":
                remaining_compiled += 1
            if PUNCT_RE.search(rec.get("topic", "")):
                trailing_punct += 1

            fout.write(json.dumps(rec, ensure_ascii=False) + '\n')

    print(f"topics fixed: {fixed_topics}")
    print(f"dates imputed: {imputed_dates}")
    print(f"fallback dates used: {fallback_dates}")
    print(f"remaining compiled: {remaining_compiled}")
    print(f"trailing punct: {trailing_punct}")

if __name__ == "__main__":
    main()