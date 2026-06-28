import json
import os
import time
from openai import OpenAI

# Initialize Groq Client
# PASTE YOUR GROQ API KEY HERE (or use your environment variable)
GROQ_API_KEY = "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" 

client = OpenAI(
    base_url="https://api.groq.com/openai/v1",
    api_key=GROQ_API_KEY,
)

INPUT_JSONL = "/Users/ganeshchandrauniyal/Desktop/Summer Project Ideas/PDF to JSONL/LLM_ENRICHED_CORPUS.jsonl"
OUTPUT_JSONL = "/Users/ganeshchandrauniyal/Desktop/Summer Project Ideas/PDF to JSONL/LLM_ENRICHED_CORPUS_FINAL.jsonl"

# We switch to Llama 3.3 70B to bypass the daily limit on the 8B model
MODEL_NAME = "llama-3.3-70b-versatile" 

generic_topics = ["Parliamentary Speech", "Address By", "Unknown"]
generic_dates = ["Unknown Date", "Compiled Volume", "Unknown", ""]

def enrich_chunk(chunk):
    text = chunk.get("text_chunk", "")
    current_topic = chunk.get("topic", "")
    current_date = chunk.get("date", "")
    
    prompt = f"""
    You are an expert archivist for the Indian Parliament.
    Read the following speech excerpt.
    
    Current Topic: {current_topic}
    Current Date: {current_date}
    
    Tasks:
    1. If the Current Topic is generic, generate a precise, 3-to-6 word title based on the core subject matter.
    2. If the Current Date is missing/unknown, scan the text for a specific date (DD Month YYYY) or a strong contextual year. If none, return "Unknown".
    
    Return ONLY a valid JSON object with keys "new_topic" and "new_date".
    
    Excerpt:
    {text[:1500]}...
    """

    try:
        response = client.chat.completions.create(
            messages=[
                {"role": "system", "content": "You are a helpful metadata extraction assistant. Output strictly valid JSON."},
                {"role": "user", "content": prompt}
            ],
            model=MODEL_NAME,
            temperature=0.1,
            response_format={ "type": "json_object" }
        )
        
        result = json.loads(response.choices[0].message.content)
        
        if current_topic in generic_topics and "new_topic" in result:
            chunk["topic"] = result["new_topic"].strip().title()
            
        if current_date in generic_dates and "new_date" in result:
            chunk["date"] = result["new_date"].strip()
            
    except Exception as e:
        print(f"⚠️ LLM Error on chunk {chunk.get('chunk_id')}: {e}")
        
    return chunk

def main():
    print("🔄 Loading existing enriched corpus...")
    chunks = []
    with open(INPUT_JSONL, 'r', encoding='utf-8') as f:
        for line in f:
            chunks.append(json.loads(line))
            
    print(f"📄 Loaded {len(chunks)} chunks.")
    
    # Identify chunks that still need fixing
    needs_fix = []
    for i, chunk in enumerate(chunks):
        # The failures happened in the latter half of the file (chunks 700+)
        if i >= 700: 
            if chunk.get("topic") in generic_topics or chunk.get("date") in generic_dates:
                needs_fix.append(i)
                
    print(f"🎯 Found {len(needs_fix)} chunks that still need metadata enrichment.")
    
    if not needs_fix:
        print("✅ All chunks are already enriched! Nothing to do.")
        return

    print(f"🤖 Resuming LLM Triage using model: {MODEL_NAME}...")
    fixed_count = 0
    
    for idx in needs_fix:
        chunk = chunks[idx]
        chunks[idx] = enrich_chunk(chunk)
        fixed_count += 1
        
        if fixed_count % 10 == 0:
            print(f"⏳ Processed {fixed_count}/{len(needs_fix)} retries...")
            
        time.sleep(0.5) # Respect rate limits
        
    print("💾 Saving final enriched corpus...")
    with open(OUTPUT_JSONL, 'w', encoding='utf-8') as f:
        for chunk in chunks:
            f.write(json.dumps(chunk, ensure_ascii=False) + '\n')
            
    print("="*50)
    print("🏆 RESUME TRIAGE COMPLETE")
    print(f"🤖 Successfully retried {fixed_count} chunks.")
    print(f"💾 Saved to: {OUTPUT_JSONL}")
    print("="*50)

if __name__ == "__main__":
    main()