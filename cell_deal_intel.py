# deal-intel/cell_deal_intel.py
# Clean single-file module — ready to paste
# - Model ID set to "llama-3.1-8b-instant"
# - Active imports for Groq and crawl4ai
# - Secure client instantiation from environment variables (no secrets in source)
# - Deterministic JSON-first per-chunk summarization, repair, merging
# - Backwards-compatible wrappers and HTML builder

from __future__ import annotations
import asyncio
import json
import os
import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

# Required active imports
from groq import Groq
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig

# ---------------------------
# Instantiate clients from environment (secure, no secrets in source)
# ---------------------------

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY:
    raise RuntimeError("Missing GROQ_API_KEY environment variable. Set it before running the app.")
groq_client: Groq = Groq(api_key=GROQ_API_KEY)

CRAWL4AI_API_KEY = os.getenv("CRAWL4AI_API_KEY")
crawler: Optional[AsyncWebCrawler] = None
if CRAWL4AI_API_KEY:
    crawler = AsyncWebCrawler(api_key=CRAWL4AI_API_KEY)

# ---------------------------
# Configuration / Schema
# ---------------------------

MODEL_ID = "llama-3.1-8b-instant"
DEFAULT_CHUNK_SIZE = 8000
DEFAULT_MAX_TOKENS_PER_CHUNK = 2000

STRICT_JSON_PROMPT = """
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

# ---------------------------
# Chunking helpers
# ---------------------------


def chunk_text(text: str, max_chars: int = DEFAULT_CHUNK_SIZE) -> List[str]:
    if not text:
        return []
    paragraphs = text.split("\n\n")
    chunks: List[str] = []
    current: List[str] = []
    current_len = 0
    for p in paragraphs:
        p = p.strip()
        if not p:
            continue
        p_len = len(p) + 2
        if current_len + p_len <= max_chars:
            current.append(p)
            current_len += p_len
        else:
            if current:
                chunks.append("\n\n".join(current))
            if p_len > max_chars:
                start = 0
                while start < len(p):
                    end = start + max_chars
                    chunks.append(p[start:end])
                    start = end
                current = []
                current_len = 0
            else:
                current = [p]
                current_len = p_len
    if current:
        chunks.append("\n\n".join(current))
    return chunks


# ---------------------------
# JSON repair / validation helpers
# ---------------------------


def remove_trailing_commas(s: str) -> str:
    return re.sub(r',\s*(\}|])', r'\1', s)


def wrap_multiple_top_level_objects(s: str) -> str:
    if '}\n{' in s:
        s = '[' + s.replace('}\n{', '},\n{') + ']'
    elif '}{' in s:
        s = '[' + s.replace('}{', '},\n{') + ']'
    return s


def repair_json_heuristic(s: str) -> str:
    s = remove_trailing_commas(s)
    s = wrap_multiple_top_level_objects(s)
    return s


def validate_json_text(s: str) -> Tuple[bool, Optional[str]]:
    try:
        obj = json.loads(s)
    except json.JSONDecodeError as e:
        return False, f"JSONDecodeError: {e}"
    if isinstance(obj, dict) or isinstance(obj, list):
        return True, None
    return False, "Top-level JSON is not an object or array"


# ---------------------------
# Model interaction wrappers
# ---------------------------


def _extract_text_from_response_sync(resp: Any) -> str:
    """
    Synchronous extractor for model responses. Handles Groq-like response shapes:
    resp.choices[0].message['content'] or resp.choices[0]['text'] or resp.choices[0].text
    """
    try:
        # Some SDKs return nested message content
        return resp.choices[0].message["content"]
    except Exception:
        if hasattr(resp, "choices") and len(resp.choices) > 0:
            c = resp.choices[0]
            if isinstance(c, dict) and "text" in c:
                return c["text"]
            if hasattr(c, "text"):
                return c.text
    raise RuntimeError("Unable to extract text from model response (sync)")



async def summarize_chunk_as_json(
    client: Any,
    model: str,
    chunk_text: str,
    max_tokens: int = DEFAULT_MAX_TOKENS_PER_CHUNK,
) -> str:
    prompt = STRICT_JSON_PROMPT + "\n\nInput text:\n" + chunk_text
    # Call the SDK synchronously (some SDKs return a non-awaitable object)
    resp = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.0,
        max_tokens=max_tokens,
        top_p=1.0,
        frequency_penalty=0.0,
        presence_penalty=0.0,
    )
    # Extract synchronously
    return _extract_text_from_response_sync(resp)


async def fix_json_with_model(client: Any, model: str, raw_output: str) -> str:
    fix_prompt = (
        "The previous response failed JSON validation. Here is the raw output:\n\n"
        + raw_output
        + "\n\nPlease return a corrected, valid JSON object that exactly matches this schema:\n"
        + STRICT_JSON_PROMPT
        + "\nReturn only the JSON, nothing else."
    )
    resp = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": fix_prompt}],
        temperature=0.0,
        max_tokens=2000,
        top_p=1.0,
    )
    return _extract_text_from_response_sync(resp)



# ---------------------------
# Merge / combine helpers
# ---------------------------


def merge_partial_jsons(partial_texts: List[str]) -> Dict[str, Any]:
    combined: Dict[str, Any] = {"extracted_deals": [], "battleground_pitches": [], "battleground_pitch": None}
    for raw in partial_texts:
        if raw is None:
            continue
        raw = raw.strip()
        if not raw:
            continue
        parsed = None
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            repaired = repair_json_heuristic(raw)
            try:
                parsed = json.loads(repaired)
            except json.JSONDecodeError:
                raise ValueError("Partial JSON parse failed after heuristic repair.")
        if isinstance(parsed, dict):
            if "battleground_pitch" in parsed and isinstance(parsed["battleground_pitch"], str):
                if not combined["battleground_pitch"]:
                    combined["battleground_pitch"] = parsed["battleground_pitch"]
            if "battleground_pitches" in parsed and isinstance(parsed["battleground_pitches"], list):
                for p in parsed["battleground_pitches"]:
                    if isinstance(p, dict) and "pitch" in p:
                        if not combined["battleground_pitch"]:
                            combined["battleground_pitch"] = p.get("pitch")
                        combined["battleground_pitches"].append(p)
            extracted = parsed.get("extracted_deals", []) or []
            if isinstance(extracted, list):
                combined["extracted_deals"].extend(extracted)
            if "extracted_deals" not in parsed and "battleground_pitches" not in parsed and "battleground_pitch" not in parsed:
                if "pitch" in parsed:
                    if not combined["battleground_pitch"]:
                        combined["battleground_pitch"] = parsed.get("pitch")
                else:
                    combined["extracted_deals"].append(parsed)
        elif isinstance(parsed, list):
            for item in parsed:
                if isinstance(item, dict) and "pitch" in item:
                    if not combined["battleground_pitch"]:
                        combined["battleground_pitch"] = item.get("pitch")
                    combined["battleground_pitches"].append(item)
                else:
                    combined["extracted_deals"].append(item)
    if combined.get("battleground_pitch") and not any(isinstance(p, dict) and p.get("pitch") == combined["battleground_pitch"] for p in combined["battleground_pitches"]):
        combined["battleground_pitches"].insert(0, {"id": 1, "pitch": combined["battleground_pitch"]})
    return combined


# ---------------------------
# High-level orchestration
# ---------------------------


async def summarize_text_to_deals(
    client: Any,
    model: str,
    raw_text: str,
    *,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    max_tokens_per_chunk: int = DEFAULT_MAX_TOKENS_PER_CHUNK,
    attempt_model_fix_on_failure: bool = True,
) -> Dict[str, Any]:
    chunks = chunk_text(raw_text, max_chars=chunk_size)
    if not chunks:
        return {"extracted_deals": [], "battleground_pitches": [], "battleground_pitch": None}

    partial_texts: List[str] = []
    for i, chunk in enumerate(chunks):
        raw = await summarize_chunk_as_json(client, model, chunk, max_tokens=max_tokens_per_chunk)
        ok, err = validate_json_text(raw)
        if ok:
            partial_texts.append(raw)
            continue
        repaired = repair_json_heuristic(raw)
        ok2, err2 = validate_json_text(repaired)
        if ok2:
            partial_texts.append(repaired)
            continue
        if attempt_model_fix_on_failure:
            fixed = await fix_json_with_model(client, model, raw)
            ok3, err3 = validate_json_text(fixed)
            if ok3:
                partial_texts.append(fixed)
                continue
            raise RuntimeError(
                "Chunk JSON invalid after heuristic repair and model-based fix. "
                f"Chunk index: {i}, initial_error: {err}, repaired_error: {err2}, fix_error: {err3}"
            )
        else:
            raise RuntimeError(f"Chunk JSON invalid and model fix disabled. Error: {err}")

    final_obj = merge_partial_jsons(partial_texts)

    combined_json_text = json.dumps(final_obj, ensure_ascii=False)
    final_prompt = (
        STRICT_JSON_PROMPT
        + "\n\nHere is the combined data (JSON):\n"
        + combined_json_text
        + "\n\nReturn only the final validated JSON object that matches the schema."
    )
    resp = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": final_prompt}],
        temperature=0.0,
        max_tokens=2000,
        top_p=1.0,
    )
    final_text = _extract_text_from_response_sync(resp)
    
    ok_final, err_final = validate_json_text(final_text)

    if ok_final:
        final_obj = json.loads(final_text)
        if "battleground_pitches" not in final_obj:
            final_obj["battleground_pitches"] = []
        if "battleground_pitch" not in final_obj:
            bp = final_obj.get("battleground_pitches") or []
            if isinstance(bp, list) and len(bp) > 0 and isinstance(bp[0].get("pitch"), str):
                final_obj["battleground_pitch"] = bp[0]["pitch"]
            else:
                final_obj["battleground_pitch"] = None
    else:
        raise RuntimeError(f"Final model compaction produced invalid JSON: {err_final}")

    return final_obj


# ---------------------------
# Disk write helper
# ---------------------------


def write_and_validate_json(obj: Dict[str, Any], path: str) -> None:
    text = json.dumps(obj, ensure_ascii=False, indent=2)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
    with open(path, "r", encoding="utf-8") as f:
        s = f.read()
    try:
        json.loads(s)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"Wrote JSON but validation failed: {e}")


# ---------------------------
# Backwards-compatible wrappers and HTML builder
# ---------------------------


async def query_ai_layer(client: Any, model: str, raw_text_stream: str) -> Dict[str, Any]:
    result = await summarize_text_to_deals(
        client=client,
        model=model,
        raw_text=raw_text_stream,
        chunk_size=DEFAULT_CHUNK_SIZE,
        max_tokens_per_chunk=DEFAULT_MAX_TOKENS_PER_CHUNK,
        attempt_model_fix_on_failure=True,
    )
    return result


def archive_previous_state(public_dir: str = "public", active_filename: str = "index.html", backup_filename: str = "backup_yesterday.html") -> None:
    os.makedirs(public_dir, exist_ok=True)
    active = os.path.join(public_dir, active_filename)
    backup = os.path.join(public_dir, backup_filename)
    if os.path.exists(active):
        if os.path.exists(backup):
            os.remove(backup)
        os.rename(active, backup)
        print("[FAILSAFE]: Archived active state as yesterday's fallback backup.")


def build_frontend_dashboard(json_input: Any, config: Optional[Dict[str, Any]] = None) -> str:
    if isinstance(json_input, str):
        try:
            intel = json.loads(json_input)
        except Exception:
            intel = {"extracted_deals": [], "battleground_pitches": [], "battleground_pitch": None}
    elif isinstance(json_input, dict):
        intel = json_input
    else:
        intel = {"extracted_deals": [], "battleground_pitches": [], "battleground_pitch": None}

    # Determine pitch text (backwards-compatible)
    pitch = None
    if isinstance(intel, dict):
        if "battleground_pitch" in intel and isinstance(intel["battleground_pitch"], str):
            pitch = intel["battleground_pitch"]
        else:
            bp = intel.get("battleground_pitches") or []
            if isinstance(bp, list) and len(bp) > 0 and isinstance(bp[0].get("pitch"), str):
                pitch = bp[0]["pitch"]
    if not pitch:
        pitch = "Review current market shifts."

    timestamp = datetime.now().strftime("%B %d, %Y at %I:%M %p")
    pin = None
    if config and isinstance(config, dict):
        pin = config.get("settings", {}).get("access_pin")
    pin = pin or "0000"

    # Build table rows
    rows_html = ""
    for deal in intel.get("extracted_deals", []) if isinstance(intel.get("extracted_deals", []), list) else []:
        carrier = deal.get("carrier") or ""
        device = deal.get("device") or ""
        price = deal.get("price") or ""
        terms = deal.get("terms") or ""
        rows_html += f"""
                    <tr class="hover:bg-slate-800/30 transition-colors duration-150">
                        <td class="p-4 font-bold text-cyan-400">{carrier}</td>
                        <td class="p-4 font-medium text-slate-100">{device}</td>
                        <td class="p-4 font-black text-amber-400 font-mono">{price}</td>
                        <td class="p-4 text-slate-400 font-light">{terms}</td>
                    </tr>"""

    # Full HTML template (self-contained)
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>Wireless Competitive Intelligence Terminal</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <style>
    body {{ background-color: #0f172a; color: #e6eef8; font-family: Inter, ui-sans-serif, system-ui, -apple-system, "Segoe UI", Roboto, "Helvetica Neue", Arial; }}
    .container {{ max-width: 1100px; margin: 2rem auto; padding: 1rem; }}
    .card {{ background: #0b1220; border: 1px solid rgba(6,182,212,0.08); border-radius: 12px; padding: 1rem; }}
  </style>
</head>
<body>
  <div class="container">
    <header class="mb-6">
      <h1 style="font-size:28px; font-weight:800; background:linear-gradient(90deg,#06b6d4,#10b981); -webkit-background-clip:text; color:transparent;">📡 TELECOM BATTLEGROUND</h1>
      <p style="color:#94a3b8; font-family:monospace; font-size:12px;">DATA FLOW FRESHNESS: <span style="color:#06b6d4; font-weight:700;">{timestamp}</span></p>
    </header>

    <div class="card" style="margin-bottom:1rem;">
      <p id="pitchText" style="font-style:italic; color:#e6eef8;">"{pitch}"</p>
    </div>

    <div style="margin-bottom:1rem;">
      <input id="dealSearch" type="text" placeholder="Search devices or carriers..." style="width:100%; padding:12px; border-radius:10px; background:#071029; border:1px solid #0b1220; color:#e6eef8;" onkeyup="filterTable()" />
    </div>

    <div class="card" style="overflow-x:auto;">
      <table style="width:100%; border-collapse:collapse;">
        <thead>
          <tr style="background:rgba(15,23,42,0.6); color:#94a3b8; font-family:monospace; font-size:12px; text-transform:uppercase;">
            <th style="padding:12px; text-align:left;">Carrier</th>
            <th style="padding:12px; text-align:left;">Device</th>
            <th style="padding:12px; text-align:left;">Cost</th>
            <th style="padding:12px; text-align:left;">Requirements</th>
          </tr>
        </thead>
        <tbody id="dealsTable" style="font-size:14px; color:#cbd5e1;">
{rows_html}
        </tbody>
      </table>
    </div>
  </div>

  <script>
    function filterTable() {{
      const q = document.getElementById('dealSearch').value.toLowerCase();
      const rows = document.querySelectorAll('#dealsTable tr');
      rows.forEach(r => {{
        const text = r.innerText.toLowerCase();
        r.style.display = text.includes(q) ? '' : 'none';
      }});
    }}
    function verifyAccess() {{
      const pin = '{pin}';
      const input = prompt('Enter secure pin:');
      if (input === pin) {{
        alert('Access granted');
      }} else {{
        alert('Access refused');
      }}
    }}
  </script>
</body>
</html>"""
    return html

# When run as a script, generate the dashboard HTML into ./public/index.html
if __name__ == "__main__":
    import asyncio
    from groq import Groq

    # Use environment SAMPLE_TEXT to override the sample input if desired
    sample_text = os.environ.get("SAMPLE_TEXT", "Sample promotional text")

    # Instantiate client from env; this mirrors how the module expects to be used
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        print("ERROR: GROQ_API_KEY not set in environment")
        raise SystemExit(1)
    client = Groq(api_key=api_key)

    try:
        # Run the async pipeline to get the final object, then build HTML and write it
        final_obj = asyncio.run(query_ai_layer(client, MODEL_ID, sample_text))
        html = build_frontend_dashboard(final_obj)
        os.makedirs("public", exist_ok=True)
        with open("public/index.html", "w", encoding="utf-8") as f:
            f.write(html)
        print("Wrote dashboard to public/index.html")
    except Exception as e:
        print("ERROR: failed to generate public/index.html:", e)
        raise


# ---------------------------
# Example quick-run helper (not executed on import)
# ---------------------------


def _example_run_sync(client: Any, model: str, sample_text: str, output_html_path: str = "public/index.html"):
    archive_previous_state(public_dir="public", active_filename="index.html", backup_filename="backup_yesterday.html")
    final_obj = asyncio.run(query_ai_layer(client, model, sample_text))
    html = build_frontend_dashboard(final_obj)
    os.makedirs("public", exist_ok=True)
    with open(output_html_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"Wrote dashboard to {output_html_path}")
