"""
tools.py

The three required FitFindr tools. Each tool is a standalone function that
can be called and tested independently before being wired into the agent loop.

Complete and test each tool before moving to agent.py.

Tools:
    search_listings(description, size, max_price)  → list[dict]
    suggest_outfit(new_item, wardrobe)              → str
    create_fit_card(outfit, new_item)               → str
"""

import os
import re

from dotenv import load_dotenv
from groq import Groq

from utils.data_loader import load_listings

load_dotenv()


# ── Groq client ───────────────────────────────────────────────────────────────

def _get_groq_client():
    """Initialize and return a Groq client using GROQ_API_KEY from .env."""
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise ValueError(
            "GROQ_API_KEY not set. Add it to a .env file in the project root."
        )
    return Groq(api_key=api_key)


# ── Tool 1: search_listings ───────────────────────────────────────────────────

def search_listings(
    description: str,
    size: str | None = None,
    max_price: float | None = None,
) -> list[dict]:
    """
    Search the mock listings dataset for items matching the description,
    optional size, and optional price ceiling.

    Args:
        description: Keywords describing what the user is looking for
                     (e.g., "vintage graphic tee").
        size:        Size string to filter by, or None to skip size filtering.
                     Matching is case-insensitive (e.g., "M" matches "S/M").
        max_price:   Maximum price (inclusive), or None to skip price filtering.

    Returns:
        A list of matching listing dicts, sorted by relevance (best match first).
        Returns an empty list if nothing matches — does NOT raise an exception.

    Each listing dict has the following fields:
        id, title, description, category, style_tags (list), size,
        condition, price (float), colors (list), brand, platform

    TODO:
        1. Load all listings with load_listings().
        2. Filter by max_price and size (if provided).
        3. Score each remaining listing by keyword overlap with `description`.
        4. Drop any listings with a score of 0 (no relevant matches).
        5. Sort by score, highest first, and return the listing dicts.

    Before writing code, fill in the Tool 1 section of planning.md.
    """
    listings = load_listings()

    # Tokenize the query into lowercased keywords (alphanumeric runs only).
    keywords = re.findall(r"[a-z0-9]+", description.lower())

    results: list[tuple[int, dict]] = []
    for listing in listings:
        # Filter by price ceiling (inclusive).
        if max_price is not None and listing["price"] > max_price:
            continue

        # Filter by size — case-insensitive substring match (e.g. "M" in "S/M").
        if size is not None and size.lower() not in listing["size"].lower():
            continue

        # Build the searchable text from the listing's text-bearing fields.
        searchable = " ".join(
            [
                listing["title"],
                listing["description"],
                listing["category"],
                listing.get("brand") or "",
                " ".join(listing["style_tags"]),
                " ".join(listing["colors"]),
            ]
        ).lower()
        haystack = set(re.findall(r"[a-z0-9]+", searchable))

        # Score by how many distinct query keywords appear in the listing.
        score = sum(1 for kw in keywords if kw in haystack)
        if score > 0:
            results.append((score, listing))

    # Sort by score, highest first (stable sort preserves dataset order on ties).
    results.sort(key=lambda pair: pair[0], reverse=True)
    return [listing for _, listing in results]


# ── Tool 2: suggest_outfit ────────────────────────────────────────────────────

def suggest_outfit(new_item: dict, wardrobe: dict) -> str:
    """
    Given a thrifted item and the user's wardrobe, suggest 1–2 complete outfits.

    Args:
        new_item: A listing dict (the item the user is considering buying).
        wardrobe: A wardrobe dict with an 'items' key containing a list of
                  wardrobe item dicts. May be empty — handle this gracefully.

    Returns:
        A non-empty string with outfit suggestions.
        If the wardrobe is empty, offer general styling advice for the item
        rather than raising an exception or returning an empty string.

    TODO:
        1. Check whether wardrobe['items'] is empty.
        2. If empty: call the LLM with a prompt for general styling ideas
           (what kinds of items pair well, what vibe it suits, etc.).
        3. If not empty: format the wardrobe items into a prompt and ask
           the LLM to suggest specific outfit combinations using the new item
           and named pieces from the wardrobe.
        4. Return the LLM's response as a string.

    Before writing code, fill in the Tool 2 section of planning.md.
    """
    client = _get_groq_client()

    # Describe the thrifted item the user is considering.
    item_desc = (
        f"- {new_item.get('title', 'item')} "
        f"({new_item.get('category', 'unknown category')}); "
        f"colors: {', '.join(new_item.get('colors', [])) or 'n/a'}; "
        f"style: {', '.join(new_item.get('style_tags', [])) or 'n/a'}"
    )

    items = wardrobe.get("items", [])

    if not items:
        # Empty wardrobe → general styling advice, no specific pieces to name.
        prompt = (
            "A user is considering buying this thrifted item but hasn't told you "
            "what's already in their wardrobe:\n\n"
            f"{item_desc}\n\n"
            "Suggest 1–2 complete outfit ideas built around this item. Since you "
            "don't know their wardrobe, describe the kinds of pieces that pair "
            "well with it (e.g. 'a pair of high-waisted straight jeans'), the "
            "overall vibe it suits, and a styling tip or two. Keep it friendly "
            "and concise."
        )
    else:
        # Format the wardrobe into a readable list for the prompt.
        wardrobe_lines = []
        for w in items:
            wardrobe_lines.append(
                f"- {w.get('name', 'item')} "
                f"({w.get('category', 'unknown category')}); "
                f"colors: {', '.join(w.get('colors', [])) or 'n/a'}; "
                f"style: {', '.join(w.get('style_tags', [])) or 'n/a'}"
            )
        wardrobe_text = "\n".join(wardrobe_lines)

        prompt = (
            "A user is considering buying this thrifted item:\n\n"
            f"{item_desc}\n\n"
            "Here is what's already in their wardrobe:\n\n"
            f"{wardrobe_text}\n\n"
            "Suggest 1–2 complete outfits that pair the new item with specific "
            "pieces from their wardrobe. Refer to wardrobe pieces by name. "
            "Explain briefly why each outfit works (color, vibe, occasion). "
            "Keep it friendly and concise."
        )

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {
                "role": "system",
                "content": (
                    "You are FitFindr, a friendly thrift-fashion stylist who helps "
                    "people build outfits around secondhand finds."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        temperature=0.7,
    )

    return response.choices[0].message.content


# ── Tool 3: create_fit_card ───────────────────────────────────────────────────

def create_fit_card(outfit: str, new_item: dict) -> str:
    """
    Generate a short, shareable outfit caption for the thrifted find.

    Args:
        outfit:   The outfit suggestion string from suggest_outfit().
        new_item: The listing dict for the thrifted item.

    Returns:
        A 2–4 sentence string usable as an Instagram/TikTok caption.
        If outfit is empty or missing, return a descriptive error message
        string — do NOT raise an exception.

    The caption should:
    - Feel casual and authentic (like a real OOTD post, not a product description)
    - Mention the item name, price, and platform naturally (once each)
    - Capture the outfit vibe in specific terms
    - Sound different each time for different inputs (use higher LLM temperature)

    TODO:
        1. Guard against an empty or whitespace-only outfit string.
        2. Build a prompt that gives the LLM the item details and the outfit,
           and asks for a caption matching the style guidelines above.
        3. Call the LLM and return the response.

    Before writing code, fill in the Tool 3 section of planning.md.
    """
    # Guard: empty / whitespace-only / non-string outfit → error message, no crash.
    if not isinstance(outfit, str) or not outfit.strip():
        return (
            "Can't create a fit card without an outfit suggestion. "
            "Run suggest_outfit() first and pass its result here."
        )

    client = _get_groq_client()

    title = new_item.get("title", "this find")
    price = new_item.get("price")
    price_str = f"${price:.2f}" if isinstance(price, (int, float)) else "a steal"
    platform = new_item.get("platform", "thrift")

    prompt = (
        "Write a short, casual social-media caption (Instagram/TikTok OOTD style) "
        "for a thrifted outfit.\n\n"
        f"The thrifted item: {title}, {price_str}, found on {platform}.\n\n"
        f"The outfit it's styled in:\n{outfit}\n\n"
        "Guidelines:\n"
        f"- 2–4 sentences, casual and authentic — like a real person posting, "
        "not a product description.\n"
        f"- Mention the item name, the price ({price_str}), and the platform "
        f"({platform}) naturally, once each.\n"
        "- Capture the outfit's vibe in specific terms.\n"
        "- Feel free to use a couple of fitting hashtags or emojis."
    )

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {
                "role": "system",
                "content": (
                    "You are FitFindr, writing fun, authentic OOTD captions for "
                    "secondhand fashion finds."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        # Higher temperature so repeated calls on the same input vary.
        temperature=1.0,
    )

    return response.choices[0].message.content