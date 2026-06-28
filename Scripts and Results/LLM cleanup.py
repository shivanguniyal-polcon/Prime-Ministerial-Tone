import json
import os
import time
from openai import OpenAI

# Initialize Groq Client (OpenAI Compatible)
client = OpenAI(
    base_url="https://api.groq.com/openai/v1",
    api_key="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", # Paste your Groq key here
)

INPUT_JSONL = "/Users/ganeshchandrauniyal/Desktop/Summer Project Ideas/PDF to JSONL/CERTIFIED_ML_CORPUS.jsonl"
OUTPUT_JSONL = "/Users/ganeshchandrauniyal/Desktop/Summer Project Ideas/PDF to JSONL/LLM_ENRICHED_CORPUS.jsonl"

def enrich_chunk(chunk):
    """Asks the LLM to fix generic topics and find missing dates."""
    text = chunk.get("text_chunk", "")
    current_topic = chunk.get("topic", "")
    current_date = chunk.get("date", "")
    
    # Only process if the topic is generic or date is missing
    needs_topic_fix = current_topic in ["Parliamentary Speech", "Address By", "Unknown"]
    needs_date_fix = current_date in ["Unknown Date", "Compiled Volume", "Unknown", ""]
    
    if not needs_topic_fix and not needs_date_fix:
        return chunk # Skip LLM call, save tokens!

    prompt = f"""
    You are an expert archivist for the Indian Parliament (Lok Sabha/Rajya Sabha).
    Read the following speech excerpt.
    
    Current Topic: {current_topic}
    Current Date: {current_date}
    
    Tasks:
    1. If the Current Topic is generic (e.g., "Parliamentary Speech"), generate a precise, 3-to-6 word title based on the core subject matter (e.g., "Indo-US Nuclear Deal", "Punjab Agrarian Crisis", "Motion of Thanks").
    2. If the Current Date is missing/unknown, scan the text for a specific date (DD Month YYYY) or a strong contextual year (e.g., "1984"). If none, return "Unknown".
    
    Return ONLY a valid JSON object with keys "new_topic" and "new_date". Do not include markdown formatting.
    
    Excerpt:
    {text[:1500]}...
    """

    try:
        response = client.chat.completions.create(
            messages=[
                {"role": "system", "content": "You are a helpful metadata extraction assistant. Output strictly valid JSON."},
                {"role": "user", "content": prompt}
            ],
            model="llama-3.1-8b-instant", # or "llama3-70b-8192"
            temperature=0.1,
            response_format={ "type": "json_object" }
        )
        
        result = json.loads(response.choices[0].message.content)
        
        if needs_topic_fix and "new_topic" in result:
            chunk["topic"] = result["new_topic"].strip().title()
            chunk["topic_source"] = "LLM_Generated"
            
        if needs_date_fix and "new_date" in result:
            chunk["date"] = result["new_date"].strip()
            chunk["date_source"] = "LLM_Extracted"
            
    except Exception as e:
        print(f"⚠️ LLM Error on chunk {chunk.get('chunk_id')}: {e}")
        
    return chunk

def main():
    print("🤖 Starting Targeted LLM Metadata Triage...")
    
    total_chunks = 0
    llm_calls = 0
    
    with open(INPUT_JSONL, 'r', encoding='utf-8') as infile, \
         open(OUTPUT_JSONL, 'w', encoding='utf-8') as outfile:
         
        for line in infile:
            chunk = json.loads(line)
            total_chunks += 1
            
            # Check if we need to call the LLM
            needs_fix = (chunk.get("topic") in ["Parliamentary Speech", "Address By", "Unknown"] or 
                         chunk.get("date") in ["Unknown Date", "Compiled Volume", "Unknown", ""])
            
            if needs_fix:
                llm_calls += 1
                chunk = enrich_chunk(chunk)
                
                # Respect GitHub Models Rate Limits (e.g., sleep 0.5s between calls)
                time.sleep(0.5) 
                
                if llm_calls % 10 == 0:
                    print(f"⏳ Processed {llm_calls} LLM calls...")
            
            outfile.write(json.dumps(chunk, ensure_ascii=False) + '\n')
            
    print("="*50)
    print("🏆 LLM TRIAGE COMPLETE")
    print(f"📄 Total Chunks Scanned: {total_chunks}")
    print(f"🤖 LLM API Calls Made: {llm_calls}")
    print(f"💾 Saved enriched corpus to: {OUTPUT_JSONL}")
    print("="*50)

if __name__ == "__main__":
    main()