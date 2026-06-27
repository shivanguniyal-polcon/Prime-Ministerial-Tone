#!/usr/bin/env python3
"""
Universal Prime Ministerial Speech Pipeline (Master Edition)
============================================================
Features:
- PyMuPDF spatial extraction (silently ignores embedded images/photos)
- Dynamic Date-Anchor segmentation (handles Indira/Modi structural quirks)
- Deterministic OCR Healing (Shattered suffixes, fused words, block stutters)
- tqdm Progress Bars & Atomic Checkpointing for safe resumption
- Zero LLMs. Zero Cost. 100% Deterministic.
"""

import os
import re
import json
import fitz  # PyMuPDF
from pathlib import Path
from datetime import datetime
from tqdm import tqdm

try:
    import wordninja
    HAS_WORDNINJA = True
except ImportError:
    HAS_WORDNINJA = False
    print("⚠️ wordninja not installed. Run: pip install wordninja")

# ==========================================
# CONFIGURATION
# ==========================================
INPUT_PDF_DIR = "/Users/ganeshchandrauniyal/Desktop/Summer Project Ideas/PM Speeches"
OUTPUT_DIR = "/Users/ganeshchandrauniyal/Desktop/Summer Project Ideas/PDF to JSONL"
CLEAN_JSONL = os.path.join(OUTPUT_DIR, "publication_corpus.jsonl")
REOCR_JSONL = os.path.join(OUTPUT_DIR, "re_ocr_queue.jsonl")
CHECKPOINT_FILE = os.path.join(OUTPUT_DIR, "checkpoint.json")

TARGET_WORDS = 800
OVERLAP_WORDS = 100
VOLUME_ID = "PM_Vol"

os.makedirs(OUTPUT_DIR, exist_ok=True)

# ==========================================
# HELPER: RESUME COUNTER
# ==========================================
def get_start_counter(jsonl_path):
    """Counts existing unique document_ids in the JSONL to resume numbering."""
    if not os.path.exists(jsonl_path):
        return 1
    existing_docs = set()
    with open(jsonl_path, 'r', encoding='utf-8') as f:
        for line in f:
            try:
                row = json.loads(line)
                existing_docs.add(row.get("document_id"))
            except json.JSONDecodeError:
                continue
    return len(existing_docs) + 1

# ==========================================
# STEP 1: TEXT EXTRACTION & PREPROCESSING
# ==========================================
def extract_text_from_pdf(pdf_path):
    """Extracts native digital text layer. Ignores all embedded images."""
    try:
        doc = fitz.open(pdf_path)
    except Exception as e:
        return None, str(e)

    all_lines = []
    for page in doc:
        blocks = page.get_text("dict")["blocks"]
        page_height = page.rect.height
        page_width = page.rect.width

        for b in blocks:
            if b["type"] == 1:  # Skip image blocks
                continue
            for line in b["lines"]:
                y0, y1 = line["bbox"][1], line["bbox"][3]
                x0, x1 = line["bbox"][0], line["bbox"][2]

                # Drop headers (top 6%) and footers (bottom 6%)
                if y1 < (page_height * 0.06) or y0 > (page_height * 0.94):
                    continue

                # Drop narrow marginalia on extreme edges
                line_width = x1 - x0
                if line_width < (page_width * 0.15) and (x0 < page_width * 0.05 or x1 > page_width * 0.95):
                    continue

                text = "".join([span["text"] for span in line["spans"]]).strip()
                if text:
                    all_lines.append(text)
    doc.close()
    return all_lines, None

def preprocess_lines(lines):
    """Drops TOC entries, page numbers, pipe-separated grids, and footnote Q&A."""
    clean = []
    for line in lines:
        line = line.strip()
        if not line: continue
        
        # Standard drops
        if re.match(r'^\d{1,3}\s*\d{0,3}$', line): continue
        if re.match(r'^\(?[ivxlc]+\)?$', line, re.IGNORECASE): continue
        if re.match(r'^xxx\d*$', line, re.IGNORECASE): continue
        if line.upper() in ["CONTENTS", "PREFACE", "SL. YEAR/DATE SUBJECT", "NO.", "PAGE NO.", "NIL"]: continue
        if re.match(r'^\d{1,3}\.$', line): continue
        
        # [Modi] Drop Pipe-Separated TOC Rows
        if '|' in line and re.search(r'(Sl\.|No\.|Page|Subject|Contents)', line, re.IGNORECASE): continue
        if re.match(r'^.*\|.*\|.*$', line) and len(line) < 100: continue
            
        # [Indira] Drop Footnote Q&A Markers
        if re.match(r'^\*{1,3}\s*(Replying to|Responding to)', line): continue
            
        clean.append(line)
    return "\n".join(clean)

# ==========================================
# STEP 2: DYNAMIC DATE-ANCHOR SEGMENTATION
# ==========================================
def segment_speeches(text):
    """Splits text into speeches. Handles Indira's 'New Delhi' prefix and Markdown."""
    toc_end = re.search(
        r'(?:MOTION\s+OF|STATEMENT\s+REGARDING|NO-CONFIDENCE\s+MOTION|MOTION\s+REGARDING|STATEMENT\s+ON|BUDGET|BILL|NATIONAL\s+POLICY|CONSENSUS\s+AND)',
        text, re.IGNORECASE
    )
    if toc_end: text = text[toc_end.start():]

    # Date Pattern: Catches optional "New Delhi," prefix
    date_pattern = re.compile(
        r'^\s*(?:New Delhi\s*,?\s*)?(\d{1,2}\s+(?:January|February|March|April|May|June|July|August|'
        r'September|October|November|December)\w*\s*,?\s*\d{4})\s*$',
        re.MULTILINE | re.IGNORECASE
    )
    matches = list(date_pattern.finditer(text))
    speeches = []

    for i, m in enumerate(matches):
        date_str = m.group(1)
        start_pos = m.end()
        end_pos = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        date_line_start = text.rfind('\n', 0, m.start()) + 1
        title_block = text[max(0, date_line_start - 600):date_line_start].strip()

        title_lines = []
        for line in reversed(title_block.split('\n')):
            line = line.strip()
            if not line: continue
            if re.match(r'^(\d{1,3}|xxx+|i+|v+|x+|NIL|CONTENTS|PREFACE)$', line, re.IGNORECASE): continue
            if "BACK NOTE" in line.upper(): break
            title_lines.insert(0, line)
            if len(title_lines) >= 5: break

        # Topic Cleaning: Strips Indira's Markdown (#) and Footnote (*) markers
        raw_topic = " ".join(title_lines)
        topic = re.sub(r'[*#]', '', raw_topic).strip()
        topic = re.sub(r'\s+', ' ', topic).title()
        
        if not topic or len(topic) < 5: topic = "Parliamentary Speech"

        raw_body = text[start_pos:end_pos]
        raw_body = re.split(r'(?i)\bBACK\s+NOTE\b', raw_body)[0]
        raw_body = re.split(r'(?i)\bQUESTIONS\s+AND\s+ANSWERS\b', raw_body)[0]

        if len(raw_body) > 800:
            speeches.append({'date_str': date_str, 'topic': topic, 'body': raw_body})
    return speeches

# ==========================================
# STEP 3: OCR HEALING ENGINE
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
    'afirst': 'a first', 'alarge': 'a large', 'aclear': 'a clear', 'asober': 'a sober', 
    'aprey': 'a prey', 'ameans': 'a means', 'anote': 'a note', 'abit': 'a bit', 
    'amuch': 'a much', 'awhile': 'a while', 'avital': 'a vital', 'ahigh': 'a high', 
    'acopy': 'a copy', 'aview': 'a view', 'ajoint': 'a joint', 'agood': 'a good', 
    'agreat': 'a great', 'ayear': 'a year', 'anew': 'a new', 'acreed': 'a creed', 
    'aman': 'a man', 'adak': 'a dak', 'areal': 'a real', 'afew': 'a few', 
    'awhole': 'a whole', 'aword': 'a word', 'acoy': 'a coy', 'aplanor': 'a plan or', 
    'avery': 'a very', 'whatis': 'what is', 'neededis': 'needed is', 'producedin': 'produced in', 
    'concentrateon': 'concentrate on', 'withit': 'with it', 'thatit': 'that it', 'lateron': 'later on', 
    'stayin': 'stay in', 'officersor': 'officers or', 'impedimentin': 'impediment in', 
    'problemis': 'problem is', 'solvedor': 'solved or', 'achievedin': 'achieved in', 
    'oneor': 'one or', 'thinkin': 'think in', 'floodsor': 'floods or', 'ayearor': 'a year or', 
    'Whateverit': 'Whatever it', 'Statesor': 'States or', 'thisin': 'this in', 'believein': 'believe in', 
    'workedit': 'worked it', 'aboutit': 'about it', 'peacein': 'peace in', 'hereis': 'here is', 
    'whois': 'who is', 'succeedin': 'succeed in', 'andin': 'and in', 'forit': 'for it', 
    'wasin': 'was in', 'Gandhijior': 'Gandhiji or', 'Whatis': 'What is', 'happeningor': 'happening or', 
    'happenedin': 'happened in', 'Marxin': 'Marx in', 'andit': 'and it', 'saidin': 'said in', 
    'letus': 'let us', 'Letus': 'Let us', 'Letme': 'Let me', 'Khrushchevis': 'Khrushchev is', 
    'theoryin': 'theory in', 'walkon': 'walk on', 'becausein': 'because in', 'workon': 'work on', 
    'dragin': 'drag in', 'followin': 'follow in', 'footstepsin': 'footsteps in', 'Congressin': 'Congress in', 
    'arrangeit': 'arrange it', 'indulgein': 'indulge in', 'raidersin': 'raiders in', 
    'authoritiesin': 'authorities in', 'situationin': 'situation in', 'Kashmiris': 'Kashmir is', 
    'freedomis': 'freedom is', 'Kutchor': 'Kutch or', 'possiblein': 'possible in', 'areply': 'a reply', 
    'takeit': 'take it', 'agreementon': 'agreement on', 'hostilitiesin': 'hostilities in', 
    'fromus': 'from us', 'sentme': 'sent me', 'placedon': 'placed on', 'Nationsin': 'Nations in', 
    'sheis': 'she is', 'thereafteris': 'thereafter is', 'stateon': 'state on', 'aggressionon': 'aggression on', 
    'carryon': 'carry on', 'peoplein': 'people in', 'freedomor': 'freedom or', "Khan'spress": "Khan's press", 
    'thisis': 'this is', 'welcomeit': 'welcome it', 'belatedit': 'belated it', 'experienceis': 'experience is', 
    'followedit': 'followed it', 'Indiain': 'India in', 'subsequentlyin': 'subsequently in', 
    'chapterin': 'chapter in', 'countryis': 'country is', 'madein': 'made in', 'satisfactoryor': 'satisfactory or', 
    'saidit': 'said it', 'tackleit': 'tackle it', 'resolveit': 'resolve it', 'herein': 'here in', 
    'aweekor': 'a week or', 'agreementis': 'agreement is', 'implementit': 'implement it', 'viewin': 'view in', 
    'difficultiesin': 'difficulties in', 'placein': 'place in', 'Burmais': 'Burma is', 'Kathmanduin': 'Kathmandu in', 
    'Indiais': 'India is', 'Ofcourse': 'Of course', 'canin': 'can in', 'thatin': 'that in', 
    'beginningit': 'beginning it', 'frequentlyon': 'frequently on', 'conflictsor': 'conflicts or', 
    'occuron': 'occur on', 'describedit': 'described it', 'thingsin': 'things in', 'commenceon': 'commence on', 
    "other'spoint": "other's point", 'decisionin': 'decision in', 'substantiallyin': 'substantially in', 
    'invitedme': 'invited me', 'Burmaon': 'Burma on', 'Indiaon': 'India on', 'withme': 'with me', 
    'worldin': 'world in', 'thinkit': 'think it', 'forus': 'for us', 'todayon': 'today on', 
    'spendon': 'spend on', 'wereit': 'were it', 'ownon': 'own on', 'alsoin': 'also in', 
    'Thereis': 'There is', 'whereon': 'where on', 'alsoon': 'also on', 'strengthis': 'strength is', 
    'Ceylonis': 'Ceylon is', 'milli on': 'million', 'ltold': 'I told', 'tous': 'to us', 
    'I shell': 'I shall', 'tome': 'to me', 'butit': 'but it', 'Butit': 'But it', 
    'manin': 'man in', 'forme': 'for me', 'Forme': 'For me', 'summ it': 'summit', 
    'beca me': 'became', 'pers on': 'person', 'fashi on': 'fashion', "Gandhiji'stime": "Gandhiji's time", 
    'outor': 'out or', 'Governmentor': 'Government or', 'expertor': 'expert or', 'wheator': 'wheat or', 
    'do itor': 'do it or', 'rightor': 'right or', 'responsibilityin': 'responsibility in', 'getit': 'get it', 
    'eyeon': 'eye on', 'notin': 'not in', 'sayin': 'say in', 'hasin': 'has in', 'yetit': 'yet it', 
    'hadin': 'had in', 'In dia': 'India', 'P ak ist an': 'Pakistan', 'pr od u ction': 'production', 
    'resp on si bi l it y': 'responsibility', 'op i ni on': 'opinion', 'bet ween': 'between', 
    'comi ng': 'coming', 'fr om': 'from'
}

def apply_fused_dictionary(text):
    for bad, good in FUSED_MAP.items():
        text = re.sub(r'\b' + re.escape(bad) + r'\b', good, text, flags=re.IGNORECASE)
    return text

def apply_wordninja(text):
    if not HAS_WORDNINJA: return text
    words = text.split()
    healed = []
    for w in words:
        if len(w) > 14 and re.search(r'[a-z]', w) and not w.startswith('http'):
            split = wordninja.split(w)
            if len(split) > 1:
                healed.append(" ".join(split))
                continue
        healed.append(w)
    return " ".join(healed)

def fix_ocr_swaps(text):
    swaps = {
        r'\breplying lo\b': 'replying to', r'\bmight he able\b': 'might be able',
        r'\bwe fell that\b': 'we felt that', r'\bI fell that\b': 'I felt that',
        r'\bcome pressure\b': 'some pressure', r'\bhand it aver\b': 'hand it over',
        r'\baver to\b': 'over to', r'\bOne thins has\b': 'One thing has',
        r'\btonne- respectively\b': 'tonnes respectively', r'\badds upto\b': 'adds up to',
        r'\b1 greatly\b': 'I greatly', r'\bltold\b': 'I told', r'\b1 have\b': 'I have',
        r"At that' time": 'At that time', r'\bail the\b': 'all the',
        r'bringing; about': 'bringing about', r'note find of': 'note and of',
        r'were it act for': 'were it not for', r'\bareain\b': 'area in',
        r'\bto proved to\b': 'to proceed to', r'\bto be repealed again\b': 'to be repeated again'
    }
    for pattern, replacement in swaps.items():
        text = re.sub(pattern, replacement, text)
    return text

def remove_block_stutters(text):
    words = text.split()
    n = len(words)
    for block_size in range(15, min(81, n // 2)):
        for i in range(n - (2 * block_size)):
            if words[i:i + block_size] == words[i + block_size:i + 2 * block_size]:
                words = words[:i + block_size] + words[i + 2 * block_size:]
                return " ".join(words)
    sentences = re.split(r'(?<=[.!?])\s+', text)
    if len(sentences) >= 2 and sentences[-1].strip() == sentences[-2].strip():
        sentences.pop()
        return " ".join(sentences)
    return " ".join(words)

def heal_text(text):
    text = fix_shattered_suffixes(text)
    text = apply_fused_dictionary(text)
    text = apply_wordninja(text)
    text = fix_ocr_swaps(text)
    text = re.sub(r'\s+([.,;:!?])', r'\1', text)
    text = re.sub(r'Secretary- General', 'Secretary-General', text)
    text = re.sub(r'a\.m\.\s*on\s*at\s*3:30\s*', '', text)
    text = re.sub(r'\s+', ' ', text).strip()
    text = remove_block_stutters(text)
    return text

# ==========================================
# STEP 4: CHUNKING & EXPORT
# ==========================================
NUMERIC_LOSS_PATTERNS = [
    r'\bRs\.\s+(?:to|or)\s+crore\b', r'\babout\s+per\s+cent\s+to\s+per\s+cent\b',
    r'\bby\s+hours\b', r'\bwelfare of the million people\b'
]

def chunk_text(text, max_words, overlap):
    if not text: return []
    words = text.split()
    chunks = []
    step = max_words - overlap
    for i in range(0, len(words), step):
        chunk = words[i:i + max_words]
        if len(chunk) < (max_words // 4) and i > 0:
            if chunks: chunks[-1] += " " + " ".join(chunk)
            break
        chunks.append(" ".join(chunk))
    return chunks

# ==========================================
# MAIN PIPELINE ORCHESTRATOR
# ==========================================
def main():
    print("\n" + "=" * 60)
    print("🏗️  UNIVERSAL PM SPEECH PIPELINE (MASTER EDITION)")
    print("   Zero-LLM | Zero-Cost | Deterministic | Checkpointed")
    print("=" * 60 + "\n")

    # 1. Load Checkpoint
    if os.path.exists(CHECKPOINT_FILE):
        with open(CHECKPOINT_FILE, 'r', encoding='utf-8') as f:
            processed_pdfs = set(json.load(f).get("processed_pdfs", []))
    else:
        processed_pdfs = set()

    pdf_files = sorted(Path(INPUT_PDF_DIR).glob("*.pdf"))
    pdfs_to_process = [p for p in pdf_files if p.name not in processed_pdfs]

    if not pdfs_to_process:
        print("✅ All PDFs have already been processed! (Found in checkpoint)")
        print("   To restart from scratch, delete 'checkpoint.json' and the JSONL files.")
        return

    print(f"🔄 Resuming pipeline... {len(pdfs_to_process)} PDFs left to process out of {len(pdf_files)}.\n")

    # 2. Determine starting document counter
    doc_counter = get_start_counter(CLEAN_JSONL)
    
    total_clean_added = 0
    total_reocr_added = 0

    # 3. Open JSONL in APPEND mode (Atomic Saves)
    with open(CLEAN_JSONL, 'a', encoding='utf-8') as f_clean, \
         open(REOCR_JSONL, 'a', encoding='utf-8') as f_reocr:

        # 4. Progress Bar Loop
        for pdf_path in tqdm(pdfs_to_process, desc="📂 Processing PDFs", unit="pdf", ncols=80, colour="cyan"):
            lines, err = extract_text_from_pdf(str(pdf_path))
            if err or not lines:
                tqdm.write(f"   ⚠️ Skipped {pdf_path.name} (No text layer / Scanned)")
                processed_pdfs.add(pdf_path.name)
                continue

            text = preprocess_lines(lines)
            word_count = len(text.split())
            
            if word_count < 200:
                tqdm.write(f"   ⚠️ Skipped {pdf_path.name} (Too little text)")
                processed_pdfs.add(pdf_path.name)
                continue

            speeches = segment_speeches(text)
            if not speeches:
                tqdm.write(f"   ⚠️ Skipped {pdf_path.name} (No valid speeches found)")
                processed_pdfs.add(pdf_path.name)
                continue
                
            tqdm.write(f"   📑 Found {len(speeches)} speeches in {pdf_path.name}")

            # Process speeches in memory first
            pdf_clean_rows = []
            pdf_reocr_rows = []

            for speech in speeches:
                date_str = speech['date_str'].replace(',', '').strip().title()
                try:
                    iso_date = datetime.strptime(date_str, "%d %B %Y").strftime("%Y-%m-%d")
                except ValueError:
                    iso_date = date_str

                doc_id = f"{VOLUME_ID}_Speech_{doc_counter:03d}"

                if any(re.search(p, speech['body'], re.IGNORECASE) for p in NUMERIC_LOSS_PATTERNS):
                    pdf_reocr_rows.append({
                        "document_id": doc_id, "date": iso_date, "topic": speech['topic'],
                        "reason": "CRITICAL: Numeric Data Loss", "text_chunk": speech['body'][:500] + "..."
                    })
                    doc_counter += 1
                    continue

                clean_body = heal_text(speech['body'])
                chunks = chunk_text(clean_body, TARGET_WORDS, OVERLAP_WORDS)

                # Note: using 'c_text' instead of 'chunk_text' to avoid variable shadowing
                for c_idx, c_text in enumerate(chunks):
                    pdf_clean_rows.append({
                        "document_id": doc_id, "chunk_id": f"{doc_id}_{c_idx}", "date": iso_date,
                        "topic": speech['topic'], "chunk_index": c_idx, "total_chunks": len(chunks),
                        "word_count": len(c_text.split()), "text_chunk": c_text
                    })
                doc_counter += 1

            # Write to disk atomically (ensure_ascii=False preserves Hindi/Sanskrit Unicode)
            for row in pdf_clean_rows:
                f_clean.write(json.dumps(row, ensure_ascii=False) + '\n')
            for row in pdf_reocr_rows:
                f_reocr.write(json.dumps(row, ensure_ascii=False) + '\n')
                
            total_clean_added += len(pdf_clean_rows)
            total_reocr_added += len(pdf_reocr_rows)
            
            tqdm.write(f"   💾 Saved {len(pdf_clean_rows)} chunks for {pdf_path.name}")

            # 5. Update Checkpoint
            processed_pdfs.add(pdf_path.name)
            with open(CHECKPOINT_FILE, 'w', encoding='utf-8') as f_cp:
                json.dump({"processed_pdfs": list(processed_pdfs)}, f_cp, indent=2)

    # Final Summary
    print("\n" + "=" * 60)
    print("🏆 PIPELINE RUN COMPLETE")
    print("=" * 60)
    print(f"📄 Added {total_clean_added:,} new chunks to {CLEAN_JSONL}")
    if total_reocr_added > 0:
        print(f"🚨 Added {total_reocr_added} to Re-OCR Queue: {REOCR_JSONL}")
    print("=" * 60 + "\n")

if __name__ == "__main__":
    main()
