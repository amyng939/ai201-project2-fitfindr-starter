from tools import search_listings, suggest_outfit, create_fit_card
from utils.data_loader import get_example_wardrobe, get_empty_wardrobe

# ── search_listings ─────────────────────────────────────────────────────────────

def test_search_returns_results():
    results = search_listings("vintage graphic tee", size=None, max_price=50)
    assert isinstance(results, list)
    assert len(results) > 0

def test_search_empty_results():
    results = search_listings("designer ballgown", size="XXS", max_price=5)
    assert results == []   # empty list, no exception

def test_search_price_filter():
    results = search_listings("jacket", size=None, max_price=10)
    assert all(item["price"] <= 10 for item in results)


# ── suggest_outfit ─────────────────────────────────────────────────────────────
# These hit the Groq API, so they need GROQ_API_KEY in .env to run.

def _sample_item():
    return search_listings("vintage graphic tee")[0]

def test_suggest_outfit_with_wardrobe():
    result = suggest_outfit(_sample_item(), get_example_wardrobe())
    print("\n[with wardrobe]\n" + result)
    assert isinstance(result, str)
    assert result.strip() != ""   # non-empty suggestion

def test_suggest_outfit_empty_wardrobe():
    # Should give general advice, not crash, when the wardrobe is empty.
    result = suggest_outfit(_sample_item(), get_empty_wardrobe())
    print("\n[empty wardrobe]\n" + result)
    assert isinstance(result, str)
    assert result.strip() != ""


# ── create_fit_card ─────────────────────────────────────────────────────────────
# These hit the Groq API, so they need GROQ_API_KEY in .env to run.

_SAMPLE_OUTFIT = (
    "Pair the tee with baggy straight-leg jeans and chunky white sneakers "
    "for an easy everyday streetwear look."
)

def test_fit_card_returns_caption():
    result = create_fit_card(_SAMPLE_OUTFIT, _sample_item())
    print("\n[fit card]\n" + result)
    assert isinstance(result, str)
    assert result.strip() != ""

def test_fit_card_empty_outfit_returns_error_string():
    # Empty / whitespace outfit → descriptive error string, NOT an exception.
    for bad_outfit in ["", "   "]:
        result = create_fit_card(bad_outfit, _sample_item())
        print(result)
        assert isinstance(result, str)
        assert result.strip() != ""

def test_fit_card_outputs_vary():
    # Same input run multiple times should not all be identical (high temperature).
    item = _sample_item()
    runs = [create_fit_card(_SAMPLE_OUTFIT, item) for _ in range(3)]
    for i, r in enumerate(runs, 1):
        print(f"\n[fit card run {i}]\n" + r)
    assert len(set(runs)) > 1, "captions were identical — raise the temperature"

