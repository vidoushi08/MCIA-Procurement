import os
import re
from pathlib import Path
from dotenv import load_dotenv
from google import genai

PROJECT_ROOT = Path(__file__).resolve().parents[3]
load_dotenv(PROJECT_ROOT / "config" / ".env")

GEMINI_MODEL = "gemini-2.5-flash"
VERDICT_PATTERN = re.compile(r"^\s*(MISMATCH|MATCH)\b[\s:.,-]*(.*)$", re.IGNORECASE | re.DOTALL)


def _live_api_key():
    key = os.getenv("GEMINI_API_KEY")
    if not key or key == "your_gemini_api_key_here":
        return None
    return key


def parse_verdict(text: str):
    """Return (is_compliant, note). is_compliant is None when the reply has no clear verdict."""
    match = VERDICT_PATTERN.match(text or "")
    if not match:
        return None, "AI reply unclear; manual review advised."
    is_match = match.group(1).upper() == "MATCH"
    return is_match, (match.group(2).strip() or match.group(1).upper())[:255]


def _local_check(requested_item_name: str, quote):
    keyword = requested_item_name.lower().split()[0]
    if keyword in quote.quoted_item_description.lower():
        return True, "Verified match (Local Rule Check)."
    return False, f"WARNING: Quoted item '{quote.quoted_item_description}' may not match '{requested_item_name}'."


def evaluate_quotations(requested_item_name: str, quotes: list):
    if not quotes:
        return []

    api_key = _live_api_key()
    if api_key is None:
        for q in quotes:
            q.is_compliant, q.ai_flag_notes = _local_check(requested_item_name, q)
        return sorted(quotes, key=lambda x: x.total_price)

    client = genai.Client(api_key=api_key)
    for q in quotes:
        prompt = (
            f"You are an MCIA procurement auditor. Requested item: '{requested_item_name}'. "
            f"Supplier quoted: '{q.quoted_item_description}' at MUR {q.total_price}. "
            "Reply with MATCH or MISMATCH as the first word, then one short sentence (max 15 words) "
            "explaining any discrepancy."
        )
        try:
            response = client.models.generate_content(model=GEMINI_MODEL, contents=prompt)
            q.is_compliant, q.ai_flag_notes = parse_verdict(response.text)
        except Exception:
            q.is_compliant = None
            q.ai_flag_notes = "AI check unavailable; manual review advised."

    return sorted(quotes, key=lambda x: x.total_price)
