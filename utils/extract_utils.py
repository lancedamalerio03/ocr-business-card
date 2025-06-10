# utils/extract_utils.py

import os
import json
from openai import OpenAI

SYSTEM_PROMPT = """
You are a business-card parser specialized for Philippine contacts.
Given raw text lines from one or more business cards, return a JSON array of objects,
one per card, with EXACTLY these keys (use null if not found):
  - name
  - company
  - position
  - landline_number
  - mobile_number
  - email
  - website
  - address

IMPORTANT RULES:
1. Do not treat partial name fragments (like "Hubert" or "Henry") as separate cards.
2. If two consecutive lines look like they belong to the same name (e.g., both capitalized, no other fields in between), merge them into one "name" before outputting the JSON.
3. **ONE BUSINESS CARD = ONE JSON OBJECT** - Do not split a single business card into multiple entries even if it has multiple addresses or phone numbers. Combine all information into one entry.
4. If a business card has multiple locations/addresses, put the primary address in the "address" field.
5. If multiple phone numbers exist on the same card, choose the most relevant mobile and landline numbers.

Phone-number rules:
1. Philippine mobile numbers are 10 digits starting with 090–099 (or in +63 format, e.g. +63 917 xxx xxxx).
   These go into mobile_number.
2. Philippine landlines:
   a) If an area code is written (e.g. "(02) 1234-5678" or "02-12345678"), put the whole thing in landline_number.
   b) **If only a 7-digit number appears** (e.g. "7003-0087") **and no mobile prefix**, assume it's a landline_number.
3. Do not swap them. If a number matches a mobile prefix, even with hyphens or spaces, it belongs in mobile_number.
4. Output **only** the JSON array, nothing else.
"""

def parse_with_gpt(text_lines: list[str], api_key: str, model: str = 'gpt-4o-mini') -> list[dict]:
    # Create OpenAI client with the provided API key
    client = OpenAI(api_key=api_key)
    
    prompt = (
        "Here are the lines I extracted from the image(s):\n\n"
        + "\n".join(f"- {line}" for line in text_lines)
        + "\n\nPlease parse them into business-card JSON as specified."
    )

    try:
        resp = client.chat.completions.create(
            model=model,  # Use the provided model
            messages=[
                {"role": "system",  "content": SYSTEM_PROMPT},
                {"role": "user",    "content": prompt},
            ],
            temperature=0.0,
            max_tokens=1024,
        )

        raw = resp.choices[0].message.content.strip()
        
        # Debug: Print what we got from GPT
        print(f"GPT Response: {raw}")
        
        if not raw:
            print("Empty response from GPT")
            return []
        
        # Try to clean up common JSON issues
        if raw.startswith('```json'):
            raw = raw.replace('```json', '').replace('```', '').strip()
        
        try:
            cards = json.loads(raw)
            # Ensure it's a list
            if isinstance(cards, dict):
                cards = [cards]
            return cards
        except json.JSONDecodeError as e:
            print(f"JSON decode error: {e}")
            print(f"Raw response: {raw}")
            # Try to extract JSON from the response if it's wrapped in text
            import re
            json_match = re.search(r'\[.*\]', raw, re.DOTALL)
            if json_match:
                try:
                    cards = json.loads(json_match.group())
                    if isinstance(cards, dict):
                        cards = [cards]
                    return cards
                except:
                    pass
            
            # If all else fails, return empty list
            return []
            
    except Exception as e:
        print(f"API call error: {e}")
        return []