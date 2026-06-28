import json
import re
from collections import Counter

INPUT_JSONL = "/Users/ganeshchandrauniyal/Desktop/Summer Project Ideas/PDF to JSONL/ABSOLUTE_FINAL_CORPUS.jsonl"

def run_corpus_qa(jsonl_path):
    print(f"🔍 Starting CORRECTED Corpus QA on {jsonl_path}...\n")
    
    total_chunks = 0
    total_words = 0
    doc_ids = set()
    topics = []
    dates = []
    
    # Trackers
    topic_anomalies = []
    shattered_words = []
    spaced_digits = []
    missing_numerics = []
    
    # --- CORRECTED REGEX PATTERNS ---
    # FIX: Requires the prefix to be at least 4 letters so it ignores "to us" (t+o us) and "NDA in" (ND+a in)
    pat_shattered = re.compile(r'\b[a-zA-Z]{4,}(ti on|si on|o us|t or|a in|o me|m on)\b', re.IGNORECASE)
    
    pat_spaced_digits = re.compile(r'(?<!\d)(?<!Rs\. )(?<!\.)\b(\d{1,2}\s\d{1,2})\b(?!\d)(?!\s*%)')
    pat_missing_num = re.compile(r'(Rs\.\s+(?:to|or|[a-z])\s+crore|about\s+per\s+cent\s+to\s+per\s+cent)', re.IGNORECASE)
    pat_topic_garbage = re.compile(r'[*#|]|back\s*note|contents|preface|^\d+$', re.IGNORECASE)
    
    with open(jsonl_path, 'r', encoding='utf-8') as f:
        for line in f:
            row = json.loads(line)
            total_chunks += 1
            doc_ids.add(row.get("document_id"))
            topics.append(row.get("topic", ""))
            dates.append(row.get("date", ""))
            total_words += row.get("word_count", 0)
            text = row.get("text_chunk", "")
            
            if pat_topic_garbage.search(row.get("topic", "")):
                topic_anomalies.append(row.get("document_id"))
            if pat_shattered.search(text):
                shattered_words.append(row.get("document_id"))
            if pat_spaced_digits.search(text):
                spaced_digits.append(row.get("document_id"))
            if pat_missing_num.search(text):
                missing_numerics.append(row.get("document_id"))

    print("="*60)
    print("📊 1. CORPUS INVENTORY")
    print("="*60)
    print(f"📄 Total Unique Speeches: {len(doc_ids)}")
    print(f"🧩 Total Chunks: {total_chunks:,}")
    print(f"📚 Total Word Count: {total_words:,}")
    
    valid_dates = [d for d in dates if d not in ["Unknown Date", "Compiled Volume", ""]]
    if valid_dates:
        print(f"📅 Historical Date Range: {min(valid_dates)} to {max(valid_dates)}")

    print("\n" + "="*60)
    print("🔬 2. LBS STANDARD QA CHECKS (CORRECTED)")
    print("="*60)
    
    if not topic_anomalies: print("✅ Topic Hygiene: PASS")
    else: print(f"⚠️ Topic Hygiene: FAIL ({len(set(topic_anomalies))} anomalies)")
        
    if not shattered_words: print("✅ Shattered Suffixes: PASS (Zero real shatters found)")
    else: print(f"⚠️ Shattered Suffixes: FAIL ({len(set(shattered_words))} documents)")
        
    if not spaced_digits: print("✅ Page Number Bleed: PASS")
    else: print(f"⚠️ Page Number Bleed: FAIL ({len(set(spaced_digits))} documents)")
        
    if not missing_numerics: print("✅ Numeric Preservation: PASS")
    else: print(f"🚨 CRITICAL FAIL: {len(set(missing_numerics))} documents have stripped digits!")

    print("\n" + "="*60)
    if not any([topic_anomalies, shattered_words, spaced_digits, missing_numerics]):
        print("🏆 OVERALL VERDICT: 100% PUBLICATION GRADE. READY FOR ML.")
    else:
        print("⚠️ OVERALL VERDICT: Minor anomalies detected.")
    print("="*60 + "\n")

if __name__ == "__main__":
    run_corpus_qa(INPUT_JSONL)