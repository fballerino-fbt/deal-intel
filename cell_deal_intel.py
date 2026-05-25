import os
import json
import asyncio
import re
from typing import List, Dict, Any
from datetime import datetime
from groq import Groq
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig

# --- ADD THIS TO CHUNK DUE GROQ ---
def chunk_text(text, max_chars=8000):
    return [text[i:i+max_chars] for i in range(0, len(text), max_chars)]

# --- ADD THE PER-CHUNK SUMMARIZATION FUNCTION ---
def summarize_chunk(client, prompt, chunk):
    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[
            {"role": "system", "content": prompt},
            {"role": "user", "content": chunk}
        ],
        response_format={"type": "json_object"}
    )
    return response.choices[0].message.content

# --- ADD THIS TO summariza all chucnks ---    
def summarize_all_chunks(client, prompt, raw_text_stream):
    # Stage 1 — summarize raw chunks
    chunks = chunk_text(raw_text_stream)
    partial_summaries = [summarize_chunk(client, prompt, c) for c in chunks]

    # Combine partial summaries
    combined_text = "\n".join(partial_summaries)

    # Stage 2 — refine in smaller chunks
    refined_chunks = chunk_text(combined_text, max_chars=3000)
    refined_summaries = []

    for rc in refined_chunks:
        refined = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": "Refine this partial summary into structured JSON fragments."},
                {"role": "user", "content": rc}
            ],
            response_format={"type": "json_object"}
        )
        refined_summaries.append(refined.choices[0].message.content)

    # Stage 3 — recursive merge until small enough
    merged = "\n".join(refined_summaries)

    while len(merged) > 3000:
        merge_chunks = chunk_text(merged, max_chars=3000)
        new_merge_parts = []

        for mc in merge_chunks:
            merge_resp = client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[
                    {"role": "system", "content": "Merge these JSON fragments into a smaller JSON fragment."},
                    {"role": "user", "content": mc}
                ],
                response_format={"type": "json_object"}
            )
            new_merge_parts.append(merge_resp.choices[0].message.content)

        merged = "\n".join(new_merge_parts)

    # Final pass — now small enough
    final_response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[
            {"role": "system", "content": "Merge these JSON fragments into one final clean JSON object."},
            {"role": "user", "content": merged}
        ],
        response_format={"type": "json_object"}
    )

    return final_response.choices[0].message.content
    
# Load configurations
with open("config.json", "r") as f:
    CONFIG = json.load(f)

GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

client = Groq(api_key=GROQ_API_KEY)

async def scrape_targets():
    combined_context = ""
    crawl_config = CrawlerRunConfig(
        word_count_threshold=5,
        remove_overlay_elements=True,
        wait_for_images=True  # Dynamic loading protection for image promotions
    )
    
    async with AsyncWebCrawler() as crawler:
        for carrier, urls in CONFIG["targets"].items():
            for url in urls:
                try:
                    print(f"[CRAWL]: Extracting data from -> {url}")
                    res = await crawler.arun(url=url, config=crawl_config)
                    if res.success:
                        if res.markdown:
                            combined_context += f"\n\n--- Source: {url} ---\n\n" + res.markdown
                        
                        # IMAGE/FLYER HANDLING LOGIC: Pulls asset meta tags if text data is missing
                        if hasattr(res, 'media') and 'images' in res.media:
                            combined_context += f"\n[EMBEDDED IMAGE ASSETS ENCOUNTERED ON {carrier}]:\n"
                            for img in res.media['images']:
                                alt_text = img.get('alt', '').strip()
                                if alt_text:
                                    combined_context += f"- Promotion Visual Context: {alt_text}\n"
                except Exception as e:
                    print(f"[BYPASS]: Target endpoint unreachable {url}: {e}")
    return combined_context
    
def query_ai_layer(raw_text_stream):
    # Free Tier Cloud Processing - Uses 0 bytes of local computer storage

    prompt = """
    You are an expert telecom competitor analyst. Analyze this web text data and image context records.
    Extract every smartphone promotion, device discount, and cellular service tier.
    Structure your response into a strict JSON object matching this exact schema:
    {
      "extracted_deals": [
        {"carrier": "Name", "device": "Device Name", "price": "$X or Free", "terms": "Requirements"}
      ],
      "battleground_pitch": "One strict verbal sentence advising a manager how to beat these offers today."
    }
    Return ONLY valid JSON. Avoid conversational introductions or extra code wrappers.
    """

    return summarize_all_chunks(client, prompt, raw_text_stream)

def archive_previous_state():
    os.makedirs("public", exist_ok=True)
    active = "public/index.html"
    backup = "public/backup_yesterday.html"
    if os.path.exists(active):
        if os.path.exists(backup): os.remove(backup)
        os.rename(active, backup)
        print("[FAILSAFE]: Archived active state as yesterday's fallback backup.")

def build_frontend_dashboard(json_string):
    intel = json.loads(json_string)
    timestamp = datetime.now().strftime("%B %d, %Y at %I:%M %p")
    pitch = intel.get("battleground_pitch", "Review current market shifts.")
    pin = CONFIG["settings"]["access_pin"]
    
    html_start = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Wireless Competitive Intelligence Terminal</title>
    <script src="https://tailwindcss.com"></script>
</head>
<body class="bg-slate-950 text-slate-100 min-h-screen font-sans selection:bg-cyan-500 selection:text-slate-900">
    <!-- GATEWAY AUTH LOCK LAYER -->
    <div id="lockScreen" class="fixed inset-0 bg-slate-950 flex flex-col justify-center items-center z-50 px-4">
        <div class="bg-slate-900 p-8 rounded-2xl border border-cyan-500/30 w-full max-w-sm text-center shadow-[0_0_30px_rgba(6,182,212,0.15)]">
            <div class="text-4xl mb-3">🔒</div>
            <h2 class="text-xl font-bold text-cyan-400 mb-1">Secure Intel Access</h2>
            <p class="text-slate-400 text-xs mb-6 font-light">Verification Required for Client Portals</p>
           <input type="password" id="pinInput" placeholder="Enter Secure Pin" class="w-full bg-slate-950 border border-slate-800 rounded-lg p-3 text-center tracking-widest font-mono text-white m[...]
            <button onclick="verifyAccess()" class="w-full bg-cyan-600 hover:bg-cyan-500 text-slate-950 font-bold p-3 rounded-lg transform active:scale-95 transition-all">Authenticate Terminal</bu[...]            <p id="errorMsg" class="text-red-400 text-xs mt-3 hidden">Access Refused. Invalid Authentication Code.</p>
        </div>
    </div>
    <!-- MAIN INTERACTIVE CONTAINER -->
    <div id="appContainer" class="max-w-6xl mx-auto p-4 md:p-8 opacity-0 pointer-events-none transition-opacity duration-700">
        <header class="flex flex-col md:flex-row justify-between items-start md:items-center border-b border-slate-800 pb-6 mb-8 gap-4">
            <div>
                <h1 class="text-3xl font-black tracking-tight bg-gradient-to-r from-cyan-400 to-emerald-400 bg-clip-text text-transparent">📡 TELECOM BATTLEGROUND</h1>
                <p class="text-slate-400 text-xs font-mono mt-1">DATA FLOW FRESHNESS: <span class="text-cyan-400 font-bold">{timestamp}</span></p>
            </div>
           <button onclick="speakBriefing()" class="bg-slate-900 border border-slate-700 text-slate-300 font-medium px-4 py-2 rounded-xl text-xs hover:border-cyan-500/50 flex items-center gap-2"[...]
        <!-- AI TACTICAL COUNTER-PITCH CARD -->
        <div class="bg-slate-900 border border-emerald-500/20 rounded-2xl p-6 mb-6 hover:shadow-[0_0_20px_rgba(16,185,129,0.1)] transition-all">
            <p id="pitchText" class="text-slate-200 text-base font-light italic">"{pitch}"</p>
        </div>
        <!-- INSTANT INTERACTIVE FILTER KEYWORD WRAPPER -->
         <input type="text" id="dealSearch" onkeyup="filterTable()" placeholder="Search devices or carriers..." class="w-full bg-slate-900 border border-slate-800 text-white rounded-xl p-4 focus:o[...]
        <div class="overflow-x-auto bg-slate-900 border border-slate-800 rounded-2xl">
            <table class="w-full text-left border-collapse">
                <thead>
                    <tr class="border-b border-slate-800 bg-slate-950/40 text-slate-400 font-mono text-xs uppercase tracking-wider">
                        <th class="p-4">Carrier</th><th class="p-4">Device</th><th class="p-4">Cost</th><th class="p-4">Requirements</th>
                    </tr>
                </thead>
                <tbody class="divide-y divide-slate-800/60 text-sm font-light text-slate-300">"""

    rows_html = ""
    for deal in intel.get("extracted_deals", []):
        rows_html += f"""
                    <tr class="hover:bg-slate-800/30 transition-colors duration-150">
                        <td class="p-4 font-bold text-cyan-400">{deal.get('carrier')}</td>
                        <td class="p-4 font-medium text-slate-100">{deal.get('device')}</td>
                        <td class="p-4 font-black text-amber-400 font-mono">{deal.get('price')}</td>
                        <td class="p-4 text-slate-400 font-light">{deal.get('terms')}</td>
                    </tr>"""

    html_end = f"""
                </tbody>
            </table>
        </div>
    </div>
    <script>
        function verifyAccess() {{
            if(document.getElementById("pinInput").value === "{pin}") {{
                document.getElementById("lockScreen").classList.add("hidden");
                document.getElementById("appContainer").classList.remove("opacity-0", "pointer-events-none");
            }} else {{ document.getElementById("errorMsg").classList.remove("hidden"); }}
        }}
        function filterTable() {{
            let q = document.getElementById('dealSearch').value.toLowerCase();
            document.querySelectorAll('tbody tr').forEach(r => {{
                r.style.display = r.textContent.toLowerCase().includes(q) ? '' : 'none';
            }});
        }}
        function speakBriefing() {{
            window.speechSynthesis.speak(new SpeechSynthesisUtterance(document.getElementById("pitchText").innerText));
        }}
    </script>
</body>
</html>"""
    
    with open("public/index.html", "w", encoding="utf-8") as f:
        f.write(html_start + rows_html + html_end)
        
    with open("public/latest_payload.json", "w") as f:
        f.write(json_string)

async def main():
    data_stream = await scrape_targets()
    if not data_stream.strip():
        print("[CRITICAL]: Scrape targets returned empty strings. Aborting execution loop to save live dashboard state.")
        return
    archive_previous_state()
    ai_payload_string = query_ai_layer(data_stream)
    build_frontend_dashboard(ai_payload_string)

if __name__ == "__main__":
    asyncio.run(main())
