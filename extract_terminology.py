import json
import time
from pathlib import Path
from openai import OpenAI


# ------------------------------------------------------------
# Configuration
# ------------------------------------------------------------
LLM_MODEL = "gpt-5.4-mini" #"gpt-5.6-luna"

FILENAME = "dnd-phandelver-below.pbso-adventures.json"


# ------------------------------------------------------------
# Terminology instructions
# ------------------------------------------------------------

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

# ------------------------------------------------------------
# Collect translatable texts
# ------------------------------------------------------------

def collect_translatable_texts(value):
    texts = []

    if isinstance(value, dict):

        for key, item in value.items():

            if key in {
                "text",
                "name",
                "caption",
                "description"
            }:

                if isinstance(item, str):
                    texts.append(item)

            elif isinstance(item, (dict, list)):
                texts.extend(
                    collect_translatable_texts(item)
                )

    elif isinstance(value, list):

        for item in value:
            texts.extend(
                collect_translatable_texts(item)
            )

    return texts


# ------------------------------------------------------------
# Load input JSON
# ------------------------------------------------------------

input_path = Path(
    "input"
) / FILENAME

with input_path.open(
        "r",
        encoding="utf-8"
) as file:
    data = json.load(file)


# ------------------------------------------------------------
# Collect translatable texts
# ------------------------------------------------------------

texts = collect_translatable_texts(data)

print(
    f"\n=== TRANSLATABLE TEXTS: "
    f"{len(texts)} ==="
)


# ------------------------------------------------------------
# Build complete input text
# ------------------------------------------------------------

input_text = "\n\n".join(texts)

print(
    f"=== COMPLETE TEXT FOR TERMINOLOGY "
    f"ANALYSIS: {len(input_text):,} characters ==="
)


# ------------------------------------------------------------
# Initialize OpenAI API client
# ------------------------------------------------------------

api_key = Path(
    "local_secret_do_not_commit/openai_api_key.txt"
).read_text(
    encoding="utf-8"
).strip()

client = OpenAI(
    api_key=api_key
)


# ------------------------------------------------------------
# Extract terminology
# ------------------------------------------------------------

print(
    f"\n=== EXTRACTING TERMINOLOGY (using LLM MODEL {LLM_MODEL}) ==="
)

start = time.perf_counter()

terminology_response = client.responses.create(
    model=LLM_MODEL,
    instructions=TERMINOLOGY_INSTRUCTIONS,
    input=input_text,
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
                "required": [
                    "terms"
                ],
                "additionalProperties": False
            }
        }
    }
)

end = time.perf_counter()

print(
    f"API duration: "
    f"{end - start:.2f} seconds"
)


# ------------------------------------------------------------
# Parse terminology response
# ------------------------------------------------------------

terminology = json.loads(
    terminology_response.output_text
)

all_terms = terminology["terms"]


# ------------------------------------------------------------
# Eliminate duplicates
# ------------------------------------------------------------

unique_terms = {}

for term in all_terms:

    if "original" not in term:

        print(
            "\n=== INVALID TERMINOLOGY ENTRY ==="
        )

        print(
            json.dumps(
                term,
                ensure_ascii=False,
                indent=2
            )
        )

        continue

    original = term["original"]

    if original not in unique_terms:
        unique_terms[original] = term


terminology = {
    "terms": list(
        unique_terms.values()
    )
}


# ------------------------------------------------------------
# Report result
# ------------------------------------------------------------

print(
    f"\n=== TERMINOLOGY ENTRIES: "
    f"{len(terminology['terms'])} ==="
)


# ------------------------------------------------------------
# Save terminology
# ------------------------------------------------------------

output_path = Path(
    "terminology/terminology.json"
)

with output_path.open(
        "w",
        encoding="utf-8"
) as file:

    json.dump(
        terminology,
        file,
        ensure_ascii=False,
        indent=2
    )


print(
    f"Saved terminology to: {output_path}"
)


# ------------------------------------------------------------
# Optional detailed output
# ------------------------------------------------------------

# print("\n=== TERMINOLOGY ===")
# print(
#     json.dumps(
#         terminology,
#         ensure_ascii=False,
#         indent=2
#     )
# )