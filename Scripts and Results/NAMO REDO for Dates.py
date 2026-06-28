import json
import re
import fitz  # PyMuPDF
import numpy as np
from PIL import Image
import io
from rapidocr_onnxruntime import RapidOCR
from dateutil import parser as date_parser
import os

# ==========================================
# CONFIGURATION
# ==========================================
PDF_DIR = "/Users/ganeshchandrauniyal/Desktop/Summer Project Ideas/PM Speeches" # Update to your actual PDF directory
TARGET_PDFS = [
    "PM_Speeches_Narendra_Modi_Eng_Vol-I_2014-2021.pdf",
    "PM_Speeches_Narendra_Modi_Eng_Vol-II_2022-2025.pdf"
]
INPUT_JSONL = "/Users/ganeshchandrauniyal/Desktop/Summer Project Ideas/PDF to JSONL/IPEC_GOLDEN_MASTER.jsonl" # Update to your latest JSONL
OUTPUT_JSONL = "/Users/ganeshchandrauniyal/Desktop/Summer Project Ideas/PDF to JSONL/IPEC_DATES_RECOVERED_50.jsonl"

# Initialize OCR
print("🧠 Initializing RapidOCR...")
ocr_engine = RapidOCR()

# ==========================================
# 1. PDF DATE EXTRACTION (50% CROP & CONQUER)
# ==========================================
def extract_dates_from_pdf(pdf_path):
    """
    Scans the PDF, crops the top 50% of every page to avoid QR codes,
    and extracts dates. Returns a list of (page_number, date_str).
    """
    print(f"📖 Scanning {os.path.basename(pdf_path)} for hidden header dates (Top 50% crop)...")
    doc = fitz.open(pdf_path)
    page_dates = []
    
    for page_num in range(len(doc)):
        page = doc[page_num]
        
        # 1. Render page to image at 300 DPI
        pix = page.get_pixmap(dpi=300)
        img = Image.open(io.BytesIO(pix.tobytes("png")))
        width, height = img.size
        
        # 2. CROP THE TOP 50% (Safely eliminates QR codes in the lower half!)
        top_crop = img.crop((0, 0, width, int(height * 0.50)))
        
        # 3. Convert to numpy array for RapidOCR
        img_array = np.array(top_crop)
        
        # 4. Run OCR
        result, _ = ocr_engine(img_array)
        
        if result:
            # Combine all detected text on the cropped header
            header_text = " ".join([line[1] for line in result])
            
            # 5. Hunt for Dates using Regex
            date_patterns = [
                r'(\d{1,2}[\s\-/](?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec|January|February|March|April|May|June|July|August|September|October|November|December)\w*[\s\-/]\d{4})',
                r'((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec|January|February|March|April|May|June|July|August|September|October|November|December)\w*[\s\-/]\d{1,2}[\s\-/]\d{4})'
            ]
            
            for pattern in date_patterns:
                match = re.search(pattern, header_text, re.IGNORECASE)
                if match:
                    raw_date = match.group(1)
                    try:
                        # Normalize to YYYY-MM-DD
                        dt = date_parser.parse(raw_date, fuzzy=True)
                        if 2014 <= dt.year <= 2026:
                            page_dates.append((page_num, dt.strftime("%Y-%m-%d")))
                            break
                    except Exception:
                        continue
                        
    doc.close()
    print(f"✅ Found {len(page_dates)} distinct date headers in the PDF.")
    return page_dates

# ==========================================
# 2. MAP DATES TO JSONL CHUNKS
# ==========================================
def map_dates_to_corpus(all_dates, jsonl_in, jsonl_out):
    """
    Reads the JSONL and assigns the recovered dates to Modi chunks 
    that are currently missing dates, in chronological order.
    """
    print("🗺️ Mapping recovered dates to the JSONL corpus...")
    
    chunks = []
    with open(jsonl_in, 'r', encoding='utf-8') as f:
        for line in f:
            chunks.append(json.loads(line))
            
    # Filter for Modi chunks that need dates
    target_doc_ids = ["PM_Vol_Speech_439", "PM_Vol_Speech_440"]
    missing_date_indices = [
        i for i, c in enumerate(chunks) 
        if c.get("document_id") in target_doc_ids and c.get("date") in ["Compiled Volume", "Unknown Date", "Unknown", ""]
    ]
    
    print(f"🎯 Found {len(missing_date_indices)} Modi chunks missing dates.")
    print(f"📅 We have {len(all_dates)} recovered dates to assign.")
    
    # Assign dates sequentially (since the books are chronological)
    updated_count = 0
    date_idx = 0
    
    for chunk_idx in missing_date_indices:
        if date_idx < len(all_dates):
            _, new_date = all_dates[date_idx]
            chunks[chunk_idx]["date"] = new_date
            chunks[chunk_idx]["date_source"] = "OCR_Header_Hunter_50"
            updated_count += 1
            date_idx += 1
        else:
            break # Ran out of recovered dates
            
    # Save the updated JSONL
    with open(jsonl_out, 'w', encoding='utf-8') as f:
        for chunk in chunks:
            f.write(json.dumps(chunk, ensure_ascii=False) + '\n')
            
    print(f"✅ Successfully updated {updated_count} chunks with recovered dates.")

# ==========================================
# 3. MAIN EXECUTION
# ==========================================
if __name__ == "__main__":
    all_recovered_dates = []
    
    for pdf_name in TARGET_PDFS:
        pdf_path = os.path.join(PDF_DIR, pdf_name)
        if os.path.exists(pdf_path):
            dates = extract_dates_from_pdf(pdf_path)
            all_recovered_dates.extend(dates)
        else:
            print(f"⚠️ PDF not found: {pdf_path}")
            
    if all_recovered_dates:
        # Sort by page number just in case
        all_recovered_dates.sort(key=lambda x: x[0])
        map_dates_to_corpus(all_recovered_dates, INPUT_JSONL, OUTPUT_JSONL)
        
        print("\n" + "="*60)
        print("🏆 HEADER HUNTER (50% CROP) COMPLETE")
        print("="*60)
        print(f"💾 Saved recovered corpus to: {OUTPUT_JSONL}")
        print("="*60)
    else:
        print("❌ No dates found. The QR codes might be higher, or the text is too faint.")