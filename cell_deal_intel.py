# deal-intel/cell_deal_intel.py
# Final single-file replacement — ready to paste
# - Model ID set to "llama-3.1-8b-instant"
# - Includes groq and crawl4ai imports (not commented)
# - Deterministic JSON-first per-chunk summarization, repair, merging
# - Backwards-compatible wrappers and HTML builder

from __future__ import annotations
import asyncio
import json
import os
import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

# Required imports (present and active)
from groq import Groq
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig

# ---------------------------
# User's Edge browser tabs metadata (kept for context)
# ---------------------------
edge_all_open_tabs = [
    {"pageTitle":"<WebsiteContent_fEgxLHUsWZBkbUbLQXDzG>deal-intel/cell_deal_intel.py at main \u00B7 fballerino-fbt/deal-intel</WebsiteContent_fEgxLHUsWZBkbUbLQXDzG>","pageUrl":"<WebsiteContent_fEgxLHUsWZBkbUbLQXDzG>https://github.com/fballerino-fbt/deal-intel/blob/main/cell_deal_intel.py</WebsiteContent_fEgxLHUsWZBkbUbLQXDzG>","tabId":1917283405,"isCurrent":True},
    {"pageTitle":"<WebsiteContent_fEgxLHUsWZBkbUbLQXDzG>CPALMS | Search Standards</WebsiteContent_fEgxLHUsWZBkbUbLQXDzG>","pageUrl":"<WebsiteContent_fEgxLHUsWZBkbUbLQXDzG>https://www.cpalms.org/standards/FLStandardSearch.aspx</WebsiteContent_fEgxLHUsWZBkbUbLQXDdzG>","tabId":1917283419,"isCurrent":False},
    {"pageTitle":"<WebsiteContent_fEgxLHUsWZBkbUbLQXDzG>FETA - NotebookLM</WebsiteContent_fEgxLHUsWZBkbUbLQXDzG>","pageUrl":"<WebsiteContent_fEgxLHUsWZBkbUbLQXDzG>https://notebooklm.google.com/notebook/12692cfa-323a-4522-b1ee-c01813e568f6</WebsiteContent_fEgxLHUsWZBkbUbLQXDzG>","tabId":1917283425,"isCurrent":False},
    {"pageTitle":"<WebsiteContent_fEgxLHUsWZBkbUbLQXDzG>Dashboard | Claude Platform</WebsiteContent_fEgxLHUsWZBkbUbLQXDdzG>","pageUrl":"<WebsiteContent_fEgxLHUsWZBkbUbLQXDdzG>https://platform.claude.com/dashboard</WebsiteContent_fEgxLHUsWZBkbUbLQXDdzG>","tabId":1917283410,"isCurrent":False},
    {"pageTitle":"<WebsiteContent_fEgxLHUsWZBkbUbLQXDdzG>Home \\ Anthropic</WebsiteContent_fEgxLHUsWZBkbUbLQXDdzG>","pageUrl":"<WebsiteContent_fEgxLHUsWZBkbUbLQXDdzG>https://www.anthropic.com</WebsiteContent_fEgxLHUsWZBkbUbLQXDdzG>","tabId":1917283413,"isCurrent":False},
    {"pageTitle":"<WebsiteContent_fEgxLHUsWZBkbUbLQXDdzG>Claude</WebsiteContent_fEgxLHUsWZBkbUbLQXDdzG>","pageUrl":"<WebsiteContent_fEgxLHUsWZBkbUbLQXDdzG>https://claude.ai/new</WebsiteContent_fEgxLHUsWZBkbUbLQXDdzG>","tabId":1917283434,"isCurrent":False},
    {"pageTitle":"<WebsiteContent_fEgxLHUsWZBkbUbLQXDdzG>Chat - n8n</WebsiteContent_fEgxLHUsWZBkbUbLQXDdzG>","pageUrl":"<WebsiteContent_fEgxLHUsWZBkbUbLQXDdzG>https://fballerino1.app.n8n.cloud/home/chat</WebsiteContent_fEgxLHUsWZBkbUbLQXDdzG>","tabId":1917283416,"isCurrent":False},
    {"pageTitle":"<WebsiteContent_fEgxLHUsWZBkbUbLQXDdzG>Apideck - Platform Admin</WebsiteContent_fEgxLHUsWZBkbUbLQXDdzG>","pageUrl":"<WebsiteContent_fEgxLHUsWZBkbUbLQXDdzG>https://platform.apideck.com/get-started/enable-connectors</WebsiteContent_fEgxLHUsWZBkbUbLQXDdzG>","tabId":1917283378,"isCurrent":False},
    {"pageTitle":"<WebsiteContent_fEgxLHUsWZBkbUbLQXDdzG>Platform Home Page - OpenAI API</WebsiteContent_fEgxLHUsWZBkbUbLQXDdzG>","pageUrl":"<WebsiteContent_fEgxLHUsWZBkbUbLQXDdzG>https://platform.openai.com/home</WebsiteContent_fEgxLHUsWZBkbUbLQXDdzG>","tabId":1917283381,"isCurrent":False},
    {"pageTitle":"<WebsiteContent_fEgxLHUsWZBkbUbLQXDdzG>Discover 1167 Document Ops Automation Workflows from the n8n's Community</WebsiteContent_fEgxLHUsWZBkbUbLQXDdzG>","pageUrl":"<WebsiteContent_fEgxLHUsWZBkbUbLQXDdzG>https://n8n.io/workflows/categories/document-ops</WebsiteContent_fEgxLHUsWZBkbUbLQXDdzG>","tabId":1917282184,"isCurrent":False},
    {"pageTitle":"<WebsiteContent_fEgxLHUsWZBkbUbLQXDdzG>Vercel Academy</WebsiteContent_fEgxLHUsWZBkbUbLQXDdzG>","pageUrl":"<WebsiteContent_fEgxLHUsWZBkbUbLQXDdzG>https://vercel.com/academy</WebsiteContent_fEgxLHUsWZBkbUbLQXDdzG>","tabId":1917280930,"isCurrent":False},
    {"pageTitle":"<WebsiteContent_fEgxLHUsWZBkbUbLQXDdzG>project-uqr3l – Git – Vercel</WebsiteContent_fEgxLHUsWZBkbUbLQXDdzG>","pageUrl":"<WebsiteContent_fEgxLHUsWZBkbUbLQXDdzG>https://vercel.com/fballerino-9769s-projects/project-uqr3l/settings/git</WebsiteContent_fEgxLHUsWZBkbUbLQXDdzG>","tabId":1917280939,"isCurrent":False},
    {"pageTitle":"<WebsiteContent_fEgxLHUsWZBkbUbLQXDdzG>Authentication</WebsiteContent_fEgxLHUsWZBkbUbLQXDdzG>","pageUrl":"<WebsiteContent_fEgxLHUsWZBkbUbLQXDdzG>https://vercel.com/account/settings/authentication</WebsiteContent_fEgxLHUsWZBkbUbLQXDdzG>","tabId":1917280967,"isCurrent":False},
    {"pageTitle":"<WebsiteContent_fEgxLHUsWZBkbUbLQXDdzG>Download GitHub Desktop | GitHub Desktop</WebsiteContent_fEgxLHUsWZBkbUbLQXDdzG>","pageUrl":"<WebsiteContent_fEgxLHUsWZBkbUbLQXDdzG>https://desktop.github.com/download</WebsiteContent_fEgxLHUsWZBkbUbLQXDdzG>","tabId":1917280913,"isCurrent":False},
    {"pageTitle":"<WebsiteContent_fEgxLHUsWZBkbUbLQXDdzG>github login - Search</WebsiteContent_fEgxLHUsWZBkbUbLQXDdzG>","pageUrl":"<WebsiteContent_fEgxLHUsWZBkbUbLQXDdzG>https://www.bing.com/search</WebsiteContent_fEgxLHUsWZBkbUbLQXDdzG>","tabId":1917283374,"isCurrent":False},
    {"pageTitle":"<WebsiteContent_fEgxLHUsWZBkbUbLQXDdzG>Choosing an enterprise type for GitHub Enterprise Cloud - GitHub Enterprise Cloud Docs</WebsiteContent_fEgxLHUsWZBkbUbLQXDdzG>","pageUrl":"<WebsiteContent_fEgxLHUsWZBkbUbLQXDdzG>https://docs.github.com/en/enterprise-cloud@latest/enterprise-onboarding/getting-started-with-your-enterprise/choose-an-enterprise-type</WebsiteContent_fEgxLHUsWZBkbUbLQXDdzG>","tabId":1917283468,"isCurrent":False},
    {"pageTitle":"<WebsiteContent_fEgxLHUsWZBkbUbLQXDdzG>fballerino-fbt.github.io/deal-intel/</WebsiteContent_fEgxLHUsWZBkbUbLQXDdzG>","pageUrl":"<WebsiteContent_fEgxLHUsWZBkbUbLQXDdzG>https://fballerino-fbt.github.io/deal-intel</WebsiteContent_fEgxLHUsWZBkbUbLQXDdzG>","tabId":1917283485,"isCurrent":False},
    {"pageTitle":"<WebsiteContent_fEgxLHUsWZBkbUbLQXDdzG>API Keys - GroqCloud</WebsiteContent_fEgxLHUsWZBkbUbLQXDdzG>","pageUrl":"<WebsiteContent_fEgxLHUsWZBkbUbLQXDdzG>https://console.groq.com/keys</WebsiteContent_fEgxLHUsWZBkbUbLQXDdzG>","tabId":1917283465,"isCurrent":False},
    {"pageTitle":"<WebsiteContent_fEgxLHUsWZBkbUbLQXDdzG>Get API key - Groq - Kerlig™ Help</WebsiteContent_fEgxLHUsWZBkbUbLQXDdzG>","pageUrl":"<WebsiteContent_fEgxLHUsWZBkbUbLQXDdzG>https://www.kerlig.com/help/integrations/groq/get-api-key</WebsiteContent_fEgxLHUsWZBkbUbLQXDdzG>","tabId":1917283462,"isCurrent":False},
    {"pageTitle":"<WebsiteContent_fEgxLHUsWZBkbUbLQXDdzG>is the following model llama3-8b-8192 decommissioned by GROQ already? if yes then what is the free model to be used instead? - Search</WebsiteContent_fEgxLHUsWZBkbUbLQXDdzG>","pageUrl":"<WebsiteContent_fEgxLHUsWZBkbUbLQXDdzG>https://www.bing.com/search</WebsiteContent_fEgxLHUsWZBkbUbLQXDdzG>","tabId":1917283444,"isCurrent":False},
]

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


async def _extract_text_from_response(resp: Any) -> str:
    """
    Generic extractor for model responses. Assumes Groq-like response:
    resp.choices[0].message['content'] or resp.choices[0]['text'] or resp.choices[0].text
    """
    try:
        return resp.choices[0].message["content"]
    except Exception:
        if hasattr(resp, "choices") and len(resp.choices) > 0:
            c = resp.choices[0]
            if isinstance(c, dict) and "text" in c:
                return c["text"]
            if hasattr(c, "text"):
                return c.text
    raise RuntimeError("Unable to extract text from model response")


async def summarize_chunk_as_json(
    client: Any,
    model: str,
    chunk_text: str,
    max_tokens: int = DEFAULT_MAX_TOKENS_PER_CHUNK,
) -> str:
    prompt = STRICT_JSON_PROMPT + "\n\nInput text:\n" + chunk_text
    resp = await client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.0,
        max_tokens=max_tokens,
        top_p=1.0,
        frequency_penalty=0.0,
        presence_penalty=0.0,
    )
    return await _extract_text_from_response(resp)


async def fix_json_with_model(client: Any, model: str, raw_output: str) -> str:
    fix_prompt = (
        "The previous response failed JSON validation. Here is the raw output:\n\n"
        + raw_output
        + "\n\nPlease return a corrected, valid JSON object that exactly matches this schema:\n"
        + STRICT_JSON_PROMPT
        + "\nReturn only the JSON, nothing else."
    )
    resp = await client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": fix_prompt}],
        temperature=0.0,
        max_tokens=2000,
        top_p=1.0,
    )
    return await _extract_text_from_response(resp)


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
    resp = await client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": final_prompt}],
        temperature=0.0,
        max_tokens=2000,
        top_p=1.0,
    )
    final_text = await _extract_text_from_response(resp)
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

    pitch = None
    if isinstance(intel, dict):
        if "battleground_pitch" in intel and isinstance(intel["battleground_pitch"], str):
            pitch = intel["battleground_pitch"]
        else:
            bp = intel.get("battleground_pitches") or []
            if isinstance(bp, list) and len(bp
