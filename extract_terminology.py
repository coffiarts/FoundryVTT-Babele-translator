import json
import time
from pathlib import Path
from openai import OpenAI
from openai.types.responses import ResponseTextConfigParam

TERMINOLOGY_INSTRUCTIONS = """
You are a terminology analyst for a German translation of a
D&D 5e fantasy role-playing adventure.

Analyze the supplied English text and identify only terms that
are likely to require consistent translation across the adventure.

Prioritize:
- D&D rules terminology
- creature and monster names or types
- established fantasy and setting terminology
- names of places, people, factions, organizations, etc.
- terms whose German grammatical gender, number, or inflection
  could cause recurring translation errors
- terms whose translation is ambiguous or likely to be inconsistent

Do NOT include ordinary vocabulary, generic descriptive words,
or isolated words that do not require terminological consistency.

Proper names must remain untranslated by default.
This includes personal names, place names, organization names,
faction names, and other named entities.
Do not translate or localize a proper name unless the source
text itself clearly indicates that it is a translatable descriptive name.

For each selected term provide:
- the original English term
- your proposed German translation
- grammatical gender and number
- whether it is a proper name
- a short note explaining an important translation decision,
  ambiguity, or grammatical consideration

The proposed translations are suggestions only. Do not assume
that they are official D&D terminology.

Use English for all metadata and notes.

Return only valid JSON.
"""

def collect_translatable_texts(value):
    texts = []

    if isinstance(value, dict):
        for key, item in value.items():
            if key in {"text", "name", "caption", "description"}:
                if isinstance(item, str):
                    texts.append(item)
            elif isinstance(item, (dict, list)):
                texts.extend(collect_translatable_texts(item))

    elif isinstance(value, list):
        for item in value:
            texts.extend(collect_translatable_texts(item))

    return texts


def create_chunks(texts, max_chars=50000):
    chunks = []
    current = []
    current_length = 0

    for text in texts:
        text_length = len(text)

        if current and current_length + text_length > max_chars:
            chunks.append("\n\n".join(current))
            current = []
            current_length = 0

        current.append(text)
        current_length += text_length

    if current:
        chunks.append("\n\n".join(current))

    return chunks


# ------------------------------------------------------------
# Load input JSON
# ------------------------------------------------------------

with open("input/dnd-phandelver-below.pbso-items.json", "r", encoding="utf-8") as file:
    data = json.load(file)

all_texts = collect_translatable_texts(data)

chunks = create_chunks(all_texts)

print(f"\n=== TERMINOLOGY CHUNKS: {len(chunks)} ===")
for index, chunk in enumerate(chunks, start=1):
    print(f"Chunk {index}: {len(chunk):,} characters")


# ------------------------------------------------------------
# Initialize OpenAI API client
# ------------------------------------------------------------

api_key = Path(
    "local_secret_do_not_commit/openai_api_key.txt"
).read_text(encoding="utf-8").strip()

client = OpenAI(api_key=api_key)


# ------------------------------------------------------------
# Extract terminology candidates
# ------------------------------------------------------------

start = time.perf_counter()

all_terms = []

for index, chunk in enumerate(chunks, start=1):

    print(f"\n=== TERMINOLOGY CHUNK {index}/{len(chunks)} ===")

    start = time.perf_counter()

    terminology_response = client.responses.create(
        model="gpt-5.4-mini",
        instructions=TERMINOLOGY_INSTRUCTIONS,
        input=chunk,
        text={
            "format": {
                "type": "json_schema",
                "name": "terminology",
                "strict": True,
                "schema": {
                    "type": "object",
                    "properties": {
                        "terms": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "original": {
                                        "type": "string"
                                    },
                                    "proposedGerman": {
                                        "type": "string"
                                    },
                                    "gender": {
                                        "type": "string"
                                    },
                                    "number": {
                                        "type": "string"
                                    },
                                    "properName": {
                                        "type": "boolean"
                                    },
                                    "note": {
                                        "type": "string"
                                    }
                                },
                                "required": [
                                    "original",
                                    "proposedGerman",
                                    "gender",
                                    "number",
                                    "properName",
                                    "note"
                                ],
                                "additionalProperties": False
                            }
                        }
                    },
                    "required": ["terms"],
                    "additionalProperties": False
                }
            }
        }
    )

    end = time.perf_counter()

    print(
        f"API duration: {end - start:.2f} seconds"
    )

    terminology = json.loads(terminology_response.output_text)

    all_terms.extend(terminology["terms"])

    terminology = {
        "terms": all_terms
    }


# ------------------------------------------------------------
# Eliminate duplicates
# ------------------------------------------------------------

unique_terms = {}

for term in all_terms:
    if "original" not in term:
        print("\n=== INVALID TERMINOLOGY ENTRY ===")
        print(json.dumps(term, ensure_ascii=False, indent=2))
        continue

    original = term["original"]

    if original not in unique_terms:
        unique_terms[original] = term

terminology = {
    "terms": list(unique_terms.values())
}


# ------------------------------------------------------------
# Save terminology
# ------------------------------------------------------------

with open(
        "terminology/terminology.json",
        "w",
        encoding="utf-8"
) as file:
    json.dump(
        terminology,
        file,
        ensure_ascii=False,
        indent=2
    )

print("\n=== TERMINOLOGY ===")
print(json.dumps(
    terminology,
    ensure_ascii=False,
    indent=2
))