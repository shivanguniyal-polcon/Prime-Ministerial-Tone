#!/usr/bin/env python3
import sys
import os
import re
import json
from datetime import datetime

# editable dials.
# tweak these lists to adjust the cleaning heuristics.
KEYWORDS = [
    "Motion Of", "Statement Regarding", "Reply On Motion", "Motion Regarding",
    "No-Confidence", "Budget", "Bill", "National Policy", "Consensus And"
]

FUSED = {
    'whatis': 'what is', 'neededis': 'needed is', 'producedin': 'produced in',
    'concentrateon': 'concentrate on', 'withit': 'with it', 'thatit': 'that it',
    'letus': 'let us', 'Letus': 'Let us', 'Letme': 'Let me', 'Kashmiris': 'Kashmir is',
    'freedomis': 'freedom is', 'fromus': 'from us', 'sentme': 'sent me', 'sheis': 'she is',
    'stateon': 'state on', 'carryon': 'carry on', 'peoplein': 'people in', 'thisis': 'this is',
    'Indiain': 'India in', 'countryis': 'country is', 'madein': 'made in', 'herein': 'here in',
    'Indiais': 'India is', 'Ofcourse': 'Of course', 'Thereis': 'There is', 'milli on': 'million',
    'ltold': 'I told', 'tous': 'to us', 'I shell': 'I shall', 'tome': 'to me', 'butit': 'but it',
    'manin': 'man in', 'forme': 'for me', 'summ it': 'summit', 'beca me': 'became',
    'pers on': 'person', 'fashi on': 'fashion', 'outor': 'out or', 'Governmentor': 'Government or',
    'getit': 'get it', 'eyeon': 'eye on', 'notin': 'not in', 'sayin': 'say in', 'hasin': 'has in',
    'In dia': 'India', 'P ak ist an': 'Pakistan', 'pr od u ction': 'production',
    'resp on si bi l it y': 'responsibility', 'bet ween': 'between', 'fr om': 'from'
}

DATE_RE = re.compile(
    r'(\d{1,2}\s+(?:January|February|March|April|May|June|July|August|September|October|November|December)\w*\s*,?\s*(20\d{2}))',
    re.I
)
YEAR_RE = re.compile(r'\b(20[1-2]\d)\b')

def clean_topic(topic):
    if topic.startswith("/"):
        topic = os.path.basename(topic)
        topic = topic.replace(".pdf", " ").replace("_", " ").replace(" Eng ", " ").replace(" Vol ", " Vol ").strip()

    low = topic.lower()
    for kw in KEYWORDS:
        if kw.lower() in low:
            idx = low.find(kw.lower())
            topic = topic[idx:]
            topic = re.split(r'(?<=[.!?])\s+', topic)[0]
            return topic[:120].strip()

    return topic[:120].strip() if len(topic) > 120 else topic.strip()

def recover_date(text, current_date):
    if current_date not in ["Compiled Volume", "Unknown Date", "Unknown", ""]:
        return current_date

    m = DATE_RE.search(text[:1000])
    if m:
        try:
            return datetime.strptime(m.group(1).replace(',', ''), "%d %B %Y").strftime("%Y-%m-%d")
        except ValueError:
            pass

    y = YEAR_RE.search(text[:1000])
    if y:
        return f"{y.group(1)}-01-01"

    return current_date

def heal(text):
    text = re.sub(r'(\w+)ti on\b', r'\1tion', text)
    text = re.sub(r'(\w+)si on\b', r'\1sion', text)
    text = re.sub(r'(\w+)o us\b', r'\1ous', text)
    text = re.sub(r'(\w+)t or\b', r'\1tor', text)
    text = re.sub(r'(\w+)a in\b', r'\1ain', text)
    text = re.sub(r'(\w+)o me\b', r'\1ome', text)
    text = re.sub(r'(\w+)m on\b', r'\1mon', text)

    for bad, good in FUSED.items():
        text = re.sub(r'\b' + re.escape(bad) + r'\b', good, text, flags=re.I)

    text = re.sub(r'(?<!\d)(?<!Rs\. )(?<!\.)(\b\d\s\d\b)(?!\d)(?!\s*%)', '', text)

    text = re.sub(r'\breplying lo\b', 'replying to', text)
    text = re.sub(r'\bmight he able\b', 'might be able', text)
    text = re.sub(r'\bwe fell that\b', 'we felt that', text)
    text = re.sub(r'\b1 greatly\b', 'I greatly', text)

    text = re.sub(r'\s+([.,;:!?])', r'\1', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def main():
    if len(sys.argv) != 3:
        print("usage: clean.py <in.jsonl> <out.jsonl>")
        sys.exit(1)

    in_path = sys.argv[1]
    out_path = sys.argv[2]

    total = 0
    fixed_topics = 0
    recovered_dates = 0

    with open(in_path, 'r', encoding='utf-8') as fin, \
         open(out_path, 'w', encoding='utf-8') as fout:
        for line in fin:
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            total += 1

            old_topic = rec.get("topic", "")
            new_topic = clean_topic(old_topic)
            if old_topic != new_topic:
                fixed_topics += 1
            rec["topic"] = new_topic

            old_date = rec.get("date", "")
            new_date = recover_date(rec.get("text_chunk", ""), old_date)
            if old_date != new_date:
                recovered_dates += 1
            rec["date"] = new_date

            raw = rec.get("text_chunk", "")
            healed = heal(raw)
            rec["text_chunk"] = healed
            rec["word_count"] = len(healed.split())

            fout.write(json.dumps(rec, ensure_ascii=False) + '\n')

    print(f"processed: {total}")
    print(f"topics fixed: {fixed_topics}")
    print(f"dates recovered: {recovered_dates}")

if __name__ == "__main__":
    main()