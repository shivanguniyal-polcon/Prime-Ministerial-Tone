import json
import re
from collections import defaultdict, Counter

def run_corpus_qa(jsonl_path):
    print(f"🔍 Starting Comprehensive Corpus QA on {jsonl_path}...\n")
    
    # --- Metrics & Inventory ---
    total_chunks = 0
    total_words = 0
    doc_ids = set()
    topics = []
    dates = []
    doc_chunks = defaultdict(list)
    
    # --- Error Trackers ---
    topic_anomalies = []
    shattered_words = []
    spaced_digits = []
    missing_numerics = []
    chunk_continuity_errors = []
    long_fused_words = []
    
    # --- Regex Patterns (The LBS Standard) ---
    pat_shattered = re.compile(r'\b\w+(ti on|si on|o us|t or|a in|o me|m on)\b', re.IGNORECASE)
    # Looks for spaced digits like "9 7" or "1 4" but ignores dates like "1965" and "Rs. 15"
    pat_spaced_digits = re.compile(r'(?<!\d)(?<!Rs\. )(?<!\.)\b(\d{1,2}\s\d{1,2})\b(?!\d)(?!\s*%)')
    pat_missing_num = re.compile(r'(Rs\.\s+(?:to|or|[a-z])\s+crore|about\s+per\s+cent\s+to\s+per\s+cent|welfare of the million people)', re.IGNORECASE)
    pat_topic_garbage = re.compile(r'[*#|]|back\s*note|contents|preface|^\d+$', re.IGNORECASE)
    
    with open(jsonl_path, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                print(f"❌ Line {line_num}: Invalid JSON formatting.")
                continue
                
            total_chunks += 1
            doc_id = row.get("document_id", "UNKNOWN")
            topic = row.get("topic", "")
            date = row.get("date", "")
            text = row.get("text_chunk", "")
            c_idx = row.get("chunk_index", -1)
            
            doc_ids.add(doc_id)
            topics.append(topic)
            dates.append(date)
            total_words += row.get("word_count", 0)
            doc_chunks[doc_id].append(c_idx)
            
            # 1. Topic Hygiene Check
            if pat_topic_garbage.search(topic) or len(topic) < 5:
                topic_anomalies.append((doc_id, topic))
                
            # 2. Shattered Suffixes Check
            if pat_shattered.search(text):
                shattered_words.append(doc_id)
                
            # 3. Page Number Bleed Check
            if pat_spaced_digits.search(text):
                spaced_digits.append(doc_id)
                
            # 4. Numeric Preservation Check
            if pat_missing_num.search(text):
                missing_numerics.append(doc_id)
                
            # 5. Fused Words Check
            for w in text.split():
                if len(w) > 25 and not w.startswith('http'):
                    long_fused_words.append((doc_id, w))
                    break

    # 6. Chunk Continuity Check
    for doc_id, indices in doc_chunks.items():
        indices.sort()
        expected = list(range(len(indices)))
        if indices != expected:
            chunk_continuity_errors.append(doc_id)

    # ==========================================
    # PRINT THE AUDIT REPORT
    # ==========================================
    print("="*60)
    print("📊 1. CORPUS INVENTORY & COMPLETENESS")
    print("="*60)
    print(f"📄 Total Unique Speeches (Documents): {len(doc_ids)}")
    print(f"🧩 Total Chunks: {total_chunks:,}")
    print(f"📚 Total Word Count: {total_words:,}")
    
    # Date Range
    valid_dates = [d for d in dates if d != "Unknown Date" and d != "Compiled Volume"]
    if valid_dates:
        print(f"📅 Historical Date Range: {min(valid_dates)} to {max(valid_dates)}")
        
    # Topic Distribution (Sanity Check)
    print(f"\n🗣️ Top 10 Most Frequent Speech Topics:")
    for topic, count in Counter(topics).most_common(10):
        print(f"   • {topic} ({count})")

    print("\n" + "="*60)
    print("🔬 2. LBS STANDARD QA CHECKS")
    print("="*60)
    
    # Topic
    if not topic_anomalies:
        print("✅ Topic Hygiene: PASS (No Markdown, TOC, or Q&A bleed).")
    else:
        print(f"⚠️ Topic Hygiene: FAIL ({len(topic_anomalies)} anomalies found).")
        for doc, t in topic_anomalies[:3]:
            print(f"   - [{doc}] {t}")
            
    # Shattered
    if not shattered_words:
        print("✅ Shattered Suffixes: PASS (Zero instances of 'ti on', 'si on').")
    else:
        print(f"⚠️ Shattered Suffixes: FAIL ({len(set(shattered_words))} documents contain shatters).")
        
    # Spaced Digits
    if not spaced_digits:
        print("✅ Page Number Bleed: PASS (Zero spaced digits like '9 7' found).")
    else:
        print(f"⚠️ Page Number Bleed: FAIL ({len(set(spaced_digits))} documents contain spaced digits).")
        
    # Missing Numerics
    if not missing_numerics:
        print("✅ Numeric Preservation: PASS (All 'Rs. crore' and '%' have digits).")
    else:
        print(f"🚨 CRITICAL FAIL: {len(set(missing_numerics))} documents have stripped digits (Data Loss)!")
        
    # Fused Words
    if not long_fused_words:
        print("✅ Fused Words: PASS (No abnormally long words >25 chars).")
    else:
        print(f"⚠️ Fused Words: FAIL ({len(long_fused_words)} chunks contain massive fused blocks).")
        
    # Continuity
    if not chunk_continuity_errors:
        print("✅ Chunk Continuity: PASS (All indexes map perfectly 0 to N).")
    else:
        print(f"❌ Chunk Continuity: FAIL ({len(chunk_continuity_errors)} documents have missing chunks).")

    print("\n" + "="*60)
    if not any([topic_anomalies, shattered_words, spaced_digits, missing_numerics, long_fused_words, chunk_continuity_errors]):
        print("🏆 OVERALL VERDICT: 100% PUBLICATION GRADE. READY FOR ML.")
    else:
        print("⚠️ OVERALL VERDICT: Minor anomalies detected. Review above.")
    print("="*60 + "\n")

if __name__ == "__main__":
    # Point this to your final consolidated JSONL
    run_corpus_qa("/Users/ganeshchandrauniyal/Desktop/Summer Project Ideas/PDF to JSONL/TRULY_FINAL_CORPUS.jsonl")