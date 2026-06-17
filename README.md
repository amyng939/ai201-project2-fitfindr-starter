## Tool Inventory

### Tool 1: search_listings

**Purpose:**
It takes what the user is looking for such as the description of the clothing, the size, and max price, and returns a list of matching listing dicts from listings.json sorted by relevance.

**Input parameters:**
- `description` (str): the details of the clothing the user is looking for
- `size` (str): the clothing size the user is looking for
- `max_price` (float): the highest price the clothing found for what the user is looking for should be

**What it returns:**
A list of the most relevant sorted listing dicts from listings.json. If none are found, should return an empty list. The dicts contain id, title, description, category, style_tags, size, condition, price, colors, brand, platform

**What happens if it fails or returns nothing:**
Tell the user a listing can't be found for what the user asked and maybe to try describing differently. Nothing else should be called.

---

### Tool 2: suggest_outfit

**Purpose:**
Takes in an item found from search_listings and the user's wardrobe and pairs the item with relevant pieces from the wardrobe to complete an outfit and return the suggestion to the user.

**Input parameters:**
- `new_item` (dict): the listing dict that search_listing found for the user to buy
- `wardrobe` (dict): the user's wardrobe of pieces whose dict key is items and values a list of dicts of each piece with keys id, name, category, colors, style_tags, notes

**What it returns:**
A string with outfit suggestions including the user's wardrobe pieces.

**What happens if it fails or returns nothing:**
If the wardrobe is empty, the string is populated with general styling advice for the new_item as an outfit suggestion.

---

### Tool 3: create_fit_card

**What it does:**
Generates a caption of the outfit given from suggest_outfit for social media.

**Input parameters:**
- `outfit` (str):  the outfit clothings from suggest_outfit
- `new_item` (dict): The listing dict for the thrifted item

**What it returns:**
A string of 2-4 sentences to show off the outfit found in a social media caption. It should be casual and authentic and not read off a a product description.

**What happens if it fails or returns nothing:**
If outfit is empty or missing, return a descriptive error message string — do NOT raise an exception.

---

## Planning Loop
The loop runs a sequence of steps, reading from and writing to the session dict at each step (see State Management below). The session is what each step looks at to decide whether it can continue: if a step can't produce usable output, it sets `session["error"]` and returns early, and the loop is done. Otherwise it runs to completion and returns the session. This means the agent does not call all tools in a fixed sequence regardless of context — it responds to what it receives.

1. **Initialize the session.** Call `_new_session(query, wardrobe)` to create the session dict that every later step reads from and writes to.

2. **Parse the query.** Ask the LLM to extract `description`, `size`, and `max_price` from the free-text query, then store the result in `session["parsed"]`.

3. **Search listings.** Call `search_listings()` with the parsed `description`, `size`, and `max_price`. Store the results in `session["search_results"]`. If no results: set `session["error"]` to a helpful message and return the session early. Do NOT proceed to `suggest_outfit` with empty input.

4. **Select the item.** Take the top (most relevant) result and store it in `session["selected_item"]`.

5. **Suggest an outfit.** Call `suggest_outfit()` with the selected item and the wardrobe. Store the result in `session["outfit_suggestion"]`.

6. **Create the fit card.** Call `create_fit_card()` with the outfit suggestion and the selected item. Store the result in `session["fit_card"]`.

7. **Return the session.**

---

## State Management Approach
There is a session dict created by _new_session at the start of each run that is read from in each step of the planning loop and written to by the agent so that the next tools can access previous data. It stores the original query string, parsed description, size, and max price from the query, search_results of the matching listing dicts, selected_item for top result, wardrobe for the user's wardrobe dict, the outfit_suggestion string, fit_card string, and error in case interaction ended early. At the start of a new session, the session dict only has the query and wardrobe and everything else is set to none or empty. error is set by the agent if a step can't continue such as if search_results is empty and error is read first by caller to ensure a step can be done. The session will then be returned at the end of the run.

---

## Error Handling
| Tool | Failure mode | Agent response |
|------|-------------|----------------|
| search_listings | No results match the query | tool returns empty list. Agent sets session["error"] to a helpful message like "No results match the query. Try a different description or a higher max price." and returns the session early. Nothing else gets called. |
| suggest_outfit | Wardrobe is empty | Agent notices wardrobe["items"] is empty and asks LLM for general styling advice for the item and returns a non-empty string. Call create_fit_card next. |
| create_fit_card | Outfit input is missing or incomplete | Guards against empty outfit input and returns an error that "A fit card can't be made: No outfit suggestion was provided." The agent tells the user such. |

**Example from testing:** Triggering `create_fit_card` with an empty outfit string: 
```
python -c "
from tools import search_listings, create_fit_card
results = search_listings('vintage graphic tee', size=None, max_price=50)
print(create_fit_card('', results[0]))
"
```

**Outputs**: "We couldn't put together a caption for this look right now. Try a different item or search again." As expected, it returns a descriptive error message string — not a Python exception.

---

## Spec Reflection
**One way the spec helped me:** The architecture was useful to capture the entirety of what errors and outcomes I should expect from each step in order to understand the flow before I got started on coding.

**One way implementation diverged from it and why:** The spec didn't take into account how the LLM would treat the parsed query and returned `size` as a JSON number rather than the string which crashed `search_listings` when it called `.lower()` on the size. I had to add a normalization step inside the query parsing to coerce `size` to a string and `max_price` to a float (with a fallback to a keyword-only search if parsing fails entirely) — before any of those values reach the tools. The divergence was necessary because the spec assumed the model's output was trustworthy, and the implementation had to defend against the fact that it isn't.

---

## AI Usage

**Instance 1:**
For the third tool create_fit_card, I gave Claude my Tool specs for that tool and the provided tool stub. It implemented the tool fully and looking through it, I noticed the error message given from an incomplete outfit was worded more for a developer than a user, which would be confusing if a user happen to come by the message. Instead, I had it change the tone to be more suitable for a user to read.

**Instance 2:**
I had Claude help create some test cases for the tools providing the error handling sections of the spec. I realized that the tests weren't the most helpful as I couldn't see what the return values were and instead just if it passed or not, so I added print statements to each one to better verify everything works.

---