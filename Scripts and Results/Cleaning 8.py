import json
from collections import defaultdict

INPUT_JSONL = "/Users/ganeshchandrauniyal/Desktop/Summer Project Ideas/PDF to JSONL/ML_READY_V2.jsonl"

def analyze_pm_allocation(jsonl_path):
    pm_stats = defaultdict(lambda: {"count": 0, "dates": []})
    unknown_chunks = []
    
    with open(jsonl_path, 'r', encoding='utf-8') as f:
        for line in f:
            row = json.loads(line)
            pm = row.get("pm_name", "Unknown")
            date = row.get("date", "Unknown")
            
            pm_stats[pm]["count"] += 1
            if date not in ["Unknown", "Compiled Volume", "Unknown Date", ""]:
                pm_stats[pm]["dates"].append(date)
                
            if pm in ["Unknown", ""]:
                unknown_chunks.append({
                    "doc_id": row.get("document_id"),
                    "topic": row.get("topic", "")[:80],
                    "date": date,
                    "snippet": row.get("text_chunk", "")[:150].replace('\n', ' ') + "..."
                })
                
    print("\n" + "="*80)
    print("👤 PRIME MINISTER ALLOCATION REPORT")
    print("="*80)
    print(f"{'PM Name':<25} | {'Chunks':<8} | {'Date Range'}")
    print("-" * 80)
    
    # Sort by earliest date to show chronological order
    sorted_pms = sorted(pm_stats.items(), key=lambda x: min(x[1]["dates"]) if x[1]["dates"] else "9999")
    
    total_assigned = 0
    for pm, stats in sorted_pms:
        count = stats["count"]
        dates = stats["dates"]
        if pm != "Unknown":
            total_assigned += count
            
        if dates:
            date_range = f"{min(dates)} to {max(dates)}"
        else:
            date_range = "No valid dates (Compiled/Unknown)"
            
        print(f"{pm:<25} | {count:<8} | {date_range}")
        
    print("="*80)
    print(f"✅ Total Assigned: {total_assigned} chunks")
    print(f"⚠️ Total Unassigned/Unknown: {pm_stats.get('Unknown', {'count': 0})['count']} chunks")
    
    if unknown_chunks:
        print("\n🔍 SAMPLE OF UNASSIGNED CHUNKS (First 5):")
        for i, chunk in enumerate(unknown_chunks[:5]):
            print(f"\n[{i+1}] Doc: {chunk['doc_id']} | Date: {chunk['date']}")
            print(f"    Topic: {chunk['topic']}")
            print(f"    Text:  {chunk['snippet']}")
            
        # Save unknown chunks to a file for manual review
        out_path = "/Users/ganeshchandrauniyal/Desktop/Summer Project Ideas/PDF to JSONL/unknown_pm_chunks.json"
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(unknown_chunks, f, indent=2, ensure_ascii=False)
        print(f"\n💾 Saved all {len(unknown_chunks)} unassigned chunks to:\n   {out_path}")
        
    print("="*80 + "\n")

if __name__ == "__main__":
    analyze_pm_allocation(INPUT_JSONL)