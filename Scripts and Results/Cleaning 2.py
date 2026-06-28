import json
import re
import os

INPUT_JSONL = "/Users/ganeshchandrauniyal/Desktop/Summer Project Ideas/PDF to JSONL/publication_corpus_FINAL.jsonl"
OUTPUT_JSONL = "/Users/ganeshchandrauniyal/Desktop/Summer Project Ideas/PDF to JSONL/ML_READY_CORPUS.jsonl"

# ==========================================
# 1. THE HEALING ENGINE (For Idempotency Check)
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

def heal_text(text):
    text = fix_shattered_suffixes(text)
    for bad, good in FUSED_MAP.items():
        text = re.sub(r'\b' + re.escape(bad) + r'\b', good, text, flags=re.IGNORECASE)
    text = re.sub(r'(?<!\d)(?<!Rs\. )(?<!\.)(\b\d\s\d\b)(?!\d)(?!\s*%)', '', text)
    text = re.sub(r'\s+([.,;:!?])', r'\1', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

# ==========================================
# 2. MAIN EXECUTION
# ==========================================
def main():
    print("🧹 Running Ultimate Scrubber & True QA...\n")
    
    total_in = 0
    total_out = 0
    dropped_publisher = 0
    dropped_data_loss = 0
    unhealed_artifacts = 0
    
    with open(INPUT_JSONL, 'r', encoding='utf-8') as infile, \
         open(OUTPUT_JSONL, 'w', encoding='utf-8') as outfile:
         
        for line in infile:
            row = json.loads(line)
            total_in += 1
            text = row.get("text_chunk", "")
            topic = row.get("topic", "")
            
            # 1. DROP PUBLISHER GARBAGE
            if "Jainco Art India" in text or "Publishers Of This Book" in text or "Mis. Jainco" in text:
                dropped_publisher += 1
                continue
                
            # 2. DROP DATA LOSS
            if re.search(r'Rs\.\s+(?:to|or|[a-z])\s+crore|about\s+per\s+cent\s+to\s+per\s+cent|welfare of the million people', text, re.IGNORECASE):
                dropped_data_loss += 1
                continue
                
            # 3. IDEMPOTENCY HEALING CHECK
            # If running the healer changes the text, it means an artifact survived.
            healed_text = heal_text(text)
            if healed_text != text:
                unhealed_artifacts += 1
                # We will overwrite the text with the newly healed version to save it!
                row["text_chunk"] = healed_text
                row["word_count"] = len(healed_text.split())
                
            outfile.write(json.dumps(row, ensure_ascii=False) + '\n')
            total_out += 1

    print("="*60)
    print("🏆 ULTIMATE SCRUBBER & TRUE QA COMPLETE")
    print("="*60)
    print(f"📥 Chunks Analyzed: {total_in:,}")
    print(f"🗑️ Dropped Publisher Garbage: {dropped_publisher} chunks")
    print(f"🗑️ Dropped Data Loss: {dropped_data_loss} chunks")
    print(f"🩹 Auto-Healed Surviving Artifacts: {unhealed_artifacts} chunks")
    print(f"📤 Final ML-Ready Chunks: {total_out:,}")
    print(f"💾 Saved to:\n   {OUTPUT_JSONL}")
    
    if unhealed_artifacts == 0 and dropped_data_loss <= 1:
        print("\n🟢 VERDICT: 100% PUBLICATION GRADE. READY FOR ML PIPELINE.")
    else:
        print("\n🟡 VERDICT: Minor auto-healing applied. Review output.")
    print("="*60)

if __name__ == "__main__":
    main() 