import json
import re
import time
from pathlib import Path
from openai import OpenAI


def protect_foundry_syntax(text):
    protected = {}

    def replace(match):
        placeholder = f"<<<FOUNDRY_{len(protected):03d}>>>"
        protected[placeholder] = match.group(0)
        return placeholder

    # Foundry @UUID[...] und @Embed[...] schützen
    text = re.sub(r'@(UUID|Embed)\[[^\]]*\]', replace, text)

    # Foundry Inline-Rolls / Checks / Saves schützen
    text = re.sub(r'\[\[[^\]]*\]\]', replace, text)

    return text, protected


def restore_foundry_syntax(text, protected):
    for placeholder, original in protected.items():
        text = text.replace(placeholder, original)
    return text


# ------------------------------------------------------------
# JSON einlesen
# ------------------------------------------------------------

with open("input/test-entry.json", "r", encoding="utf-8") as file:
    data = json.load(file)

original_text = data["Hooked Stones"]["text"]

# ------------------------------------------------------------
# Initialize OpenAI API client
# ------------------------------------------------------------

api_key = Path(
    "local_secret_do_not_commit/openai_api_key.txt"
).read_text(encoding="utf-8").strip()

client = OpenAI(api_key=api_key)

# ------------------------------------------------------------
# Terminologie-Kandidaten extrahieren (OpenAI API call)
# ------------------------------------------------------------

start = time.perf_counter()

terminology_response = client.responses.create(
    model="gpt-5.4-mini",
    instructions="""
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

Return only valid JSON. Do not wrap the JSON in Markdown code fences.
""",
    input=original_text
)

end = time.perf_counter()
print(f"\n=== API Call Duration (Terminology): {end - start:.2f} Seconds ===")


terminology = json.loads(terminology_response.output_text)

start = time.perf_counter()

with open(
        "terminology/terminology.json",
        "w",
        encoding="utf-8"
) as file:
    json.dump(terminology, file, ensure_ascii=False, indent=2)

print("\n=== TERMINOLOGIE ===")
print(json.dumps(terminology, ensure_ascii=False, indent=2))

# ------------------------------------------------------------
# Foundry-Syntax schützen
# ------------------------------------------------------------

protected_text, protected = protect_foundry_syntax(original_text)

print("=== GESCHÜTZTER TEXT ===")
print(protected_text)

print("\n=== GESCHÜTZTE ELEMENTE ===")
for placeholder, original in protected.items():
    print(f"{placeholder} -> {original}")

# ------------------------------------------------------------
# Translate (OpenAI API call), using terminology file from above
# ------------------------------------------------------------

start = time.perf_counter()

with open("terminology/terminology.json", "r", encoding="utf-8") as file:
    terminology = json.load(file)

response = client.responses.create(
    model="gpt-5.4-mini",
    instructions=f"""
You are a translator for a D&D 5e fantasy role-playing adventure.

Translate the supplied text into German.

Use the following terminology as authoritative:
{json.dumps(terminology, ensure_ascii=False, indent=2)}

Follow the specified translations, grammatical information,
and notes in the terminology exactly.

Every <<<FOUNDRY_###>>> marker is a protected Foundry VTT element.
You MUST reproduce every marker exactly once, unchanged,
and in the same position relative to the surrounding text.
Never translate, remove, reorder, or otherwise modify these markers.

Proper names must remain untranslated unless the terminology
explicitly specifies otherwise.

Return only the translated text.
""",
    input=protected_text
)

end = time.perf_counter()
print(f"\n=== API Call Duration (Translation): {end - start:.2f} Seconds ===")

translated_text = response.output_text

# ------------------------------------------------------------
# Foundry-Syntax wiederherstellen
# ------------------------------------------------------------

restored_text = restore_foundry_syntax(
    translated_text,
    protected
)

print("\n=== ÜBERSETZUNG ===")
print(restored_text)

print("\n=== GESCHÜTZTE ELEMENTE INTEGRITÄT ===")
for placeholder, original in protected.items():
    if original in restored_text:
        print(f"{placeholder}: OK")
    else:
        print(f"{placeholder}: FEHLT ODER VERÄNDERT")