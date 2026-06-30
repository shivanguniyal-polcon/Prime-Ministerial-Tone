#!/usr/bin/env python3
import sys
import re
import json

# fixed regexes. 
# compiled once at startup, not inside the loop.
PAT_SHATTER = re.compile(r'\b[a-zA-Z]{4,}(ti on|si on|o us|t or|a in|o me|m on)\b', re.I)
PAT_SPACED = re.compile(r'(?<!\d)(?<!Rs\. )(?<!\.)\b(\d{1,2}\s\d{1,2})\b(?!\d)(?!\s*%)')
PAT_MISSING = re.compile(r'(Rs\.\s+(?:to|or|[a-z])\s+crore|about\s+per\s+cent\s+to\s+per\s+cent)', re.I)
PAT_GARBAGE = re.compile(r'[*#|]|back\s*note|contents|preface|^\d+$', re.I)

BAD_DATES = {"Unknown Date", "Compiled Volume", ""}

def main():
    if len(sys.argv) < 2:
        print("usage: qa.py <corpus.jsonl>")
        sys.exit(1)

    path = sys.argv[1]

    chunks = 0
    words = 0
    docs = set()
    
    bad_topic = set()
    bad_shatter = set()
    bad_spaced = set()
    bad_missing = set()
    
    min_d = None
    max_d = None

    with open(path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
                
            r = json.loads(line)
            chunks += 1
            words += r.get("word_count", 0)
            
            doc_id = r.get("document_id", "")
            docs.add(doc_id)
            
            topic = r.get("topic", "")
            text = r.get("text_chunk", "")
            date = r.get("date", "")

            if PAT_GARBAGE.search(topic):
                bad_topic.add(doc_id)
            if PAT_SHATTER.search(text):
                bad_shatter.add(doc_id)
            if PAT_SPACED.search(text):
                bad_spaced.add(doc_id)
            if PAT_MISSING.search(text):
                bad_missing.add(doc_id)
                
            if date not in BAD_DATES:
                if min_d is None or date < min_d:
                    min_d = date
                if max_d is None or date > max_d:
                    max_d = date

    print(f"speeches: {len(docs)}")
    print(f"chunks: {chunks}")
    print(f"words: {words}")
    if min_d:
        print(f"dates: {min_d} to {max_d}")
        
    print("---")
    
    if not bad_topic: print("topics: pass")
    else: print(f"topics: fail ({len(bad_topic)} docs)")
    
    if not bad_shatter: print("shatters: pass")
    else: print(f"shatters: fail ({len(bad_shatter)} docs)")
    
    if not bad_spaced: print("spaced digits: pass")
    else: print(f"spaced digits: fail ({len(bad_spaced)} docs)")
    
    if not bad_missing: print("numerics: pass")
    else: print(f"numerics: fail ({len(bad_missing)} docs)")

    if not any([bad_topic, bad_shatter, bad_spaced, bad_missing]):
        print("verdict: clean")
    else:
        print("verdict: anomalies detected")

if __name__ == "__main__":
    main()