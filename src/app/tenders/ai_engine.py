import os
from dotenv import load_dotenv
from google import genai

load_dotenv("config/.env")
API_KEY = os.getenv("GEMINI_API_KEY")

def evaluate_quotations(requested_item_name: str, quotes: list):
    if not quotes:
        return []

    # Fallback check if no live Gemini API key is configured yet
    if not API_KEY or API_KEY == "your_gemini_api_key_here":
        for q in quotes:
            if requested_item_name.lower().split()[0] not in q.quoted_item_description.lower():
                q.ai_flag_notes = f"WARNING: Quoted item '{q.quoted_item_description}' may not match '{requested_item_name}'."
            else:
                q.ai_flag_notes = "Verified match (Local Rule Check)."
        return sorted(quotes, key=lambda x: x.total_price)

    # Live Google Gemini AI Analysis
    client = genai.Client(api_key=API_KEY)
    for q in quotes:
        prompt = (
            f"You are an MCIA procurement auditor. Requested item: '{requested_item_name}'. "
            f"Supplier quoted: '{q.quoted_item_description}' at MUR {q.total_price}. "
            "In one short sentence (max 15 words), state if this matches the requested item or flag any discrepancy."
        )
        try:
            response = client.models.generate_content(model="gemini-2.5-flash", contents=prompt)
            q.ai_flag_notes = response.text.strip()
        except Exception:
            q.ai_flag_notes = "AI check unavailable; manual review advised."

    return sorted(quotes, key=lambda x: x.total_price)
