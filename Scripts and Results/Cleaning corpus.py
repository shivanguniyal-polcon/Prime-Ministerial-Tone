import json
import re
import os
from datetime import datetime

INPUT_JSONL = "/Users/ganeshchandrauniyal/Desktop/Summer Project Ideas/PDF to JSONL/publication_corpus.jsonl"
OUTPUT_JSONL = "/Users/ganeshchandrauniyal/Desktop/Summer Project Ideas/PDF to JSONL/publication_corpus_FINAL.jsonl"

# ==========================================
# 1. TOPIC & METADATA CLEANING
# ==========================================
def clean_topic(topic):
    # Fix absolute Mac paths from OCR/Fallback scripts
    if topic.startswith("/Users/") or topic.startswith("/"):
        base = os.path.basename(topic)
        topic = base.replace(".pdf", "").replace("_", " ").replace(" Eng ", " ").replace(" Vol ", " Vol ").strip()
        
    # Fix parliamentary chatter bleed (Look for formal keywords)
    keywords = ["Motion Of", "Statement Regarding", "Reply On Motion", "Motion Regarding", "No-Confidence", "Budget", "Bill", "National Policy", "Consensus And"]
    for kw in keywords:
        if kw.lower() in topic.lower():
            idx = topic.lower().find(kw.lower())
            clean_part = topic[idx:]
            # Cut off at the next sentence or 120 chars
            clean_part = re.split(r'(?<=[.!?])\s+', clean_part)[0]
            return clean_part[:120].strip()
            
    # Fallback: truncate if it's still massive garbage
    if len(topic) > 120:
        return topic[:120].strip() + "..."
        
    return topic.strip()

def recover_date(text, current_date):
    """Attempts to find a year in the text if the date is 'Compiled Volume' or 'Unknown'."""
    if current_date in ["Compiled Volume", "Unknown Date", ""]:
        # Look for standard speech dates (e.g., "15 August, 2015")
        match = re.search(r'(\d{1,2}\s+(?:January|February|March|April|May|June|July|August|September|October|November|December)\w*\s*,?\s*(20\d{2}))', text[:1000], re.IGNORECASE)
        if match:
            try:
                return datetime.strptime(match.group(1).replace(',', ''), "%d %B %Y").strftime("%Y-%m-%d")
            except:
                pass
        
        # Fallback: Just grab the first 4-digit year between 2014 and 2026
        year_match = re.search(r'\b(20[1-2]\d)\b', text[:1000])
        if year_match:
            return f"{year_match.group(1)}-01-01"
            
    return current_date

# ==========================================
# 2. THE HEAVY LBS HEALING ENGINE
# ==========================================
def fix_shattered_suffixes(text):
    text = re.sub(r'(\w+)ti on\b', r'\1tion', text)
    text = re.sub(r'(\w+)si on\b', r'\1sion', text)
    text = re.sub(r'(\w+)o us\b', r'\1ous', text)
    text = re.sub(r'(\w+)t or\b', r'\1tor', text)
    text = re.sub(r'(\w+)a in\b', r'\1ain', text)
    text = re.sub(r'(\w+)o me\b', r'\1ome', text)
    text = re.sub(r'(\w+)m on\b', r'\1mon', text)
    return text

# (Using a condensed version of the FUSED_MAP for the most common OCR/Indira/Modi errors)
FUSED_MAP = {
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

def heal_text_heavy(text):
    text = fix_shattered_suffixes(text)
    for bad, good in FUSED_MAP.items():
        text = re.sub(r'\b' + re.escape(bad) + r'\b', good, text, flags=re.IGNORECASE)
    
    # Fix Spaced Digits (Page number bleed like " 9 7 " or " 1 4 ")
    text = re.sub(r'(?<!\d)(?<!Rs\. )(?<!\.)(\b\d\s\d\b)(?!\d)(?!\s*%)', '', text)
    
    # Fix OCR Swaps
    text = re.sub(r'\breplying lo\b', 'replying to', text)
    text = re.sub(r'\bmight he able\b', 'might be able', text)
    text = re.sub(r'\bwe fell that\b', 'we felt that', text)
    text = re.sub(r'\b1 greatly\b', 'I greatly', text)
    
    # Punctuation & Whitespace
    text = re.sub(r'\s+([.,;:!?])', r'\1', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

# ==========================================
# 3. MAIN EXECUTION
# ==========================================
def main():
    print("🔬 Applying Final Polish, Heavy Healing, and Topic Cleanup...\n")
    
    total = 0
    fixed_topics = 0
    recovered_dates = 0
    
    with open(INPUT_JSONL, 'r', encoding='utf-8') as infile, \
         open(OUTPUT_JSONL, 'w', encoding='utf-8') as outfile:
         
        for line in infile:
            row = json.loads(line)
            total += 1
            
            # 1. Clean Topic
            old_topic = row.get("topic", "")
            new_topic = clean_topic(old_topic)
            if old_topic != new_topic:
                fixed_topics += 1
            row["topic"] = new_topic
            
            # 2. Recover Date
            old_date = row.get("date", "")
            new_date = recover_date(row.get("text_chunk", ""), old_date)
            if old_date != new_date:
                recovered_dates += 1
            row["date"] = new_date
            
            # 3. Heavy Heal Text
            raw_text = row.get("text_chunk", "")
            healed_text = heal_text_heavy(raw_text)
            row["text_chunk"] = healed_text
            row["word_count"] = len(healed_text.split())
            
            outfile.write(json.dumps(row, ensure_ascii=False) + '\n')
            
    print("="*60)
    print("🏆 FINAL POLISH COMPLETE")
    print("="*60)
    print(f"📄 Processed {total:,} chunks.")
    print(f"🧹 Cleaned {fixed_topics} messy/file-path topics.")
    print(f"📅 Recovered {recovered_dates} missing Modi/Compiled dates.")
    print(f"💾 Saved pristine ML-ready corpus to:\n   {OUTPUT_JSONL}")
    print("="*60)

if __name__ == "__main__":
    main()