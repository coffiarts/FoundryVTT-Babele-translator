import json
import re
import time
from pathlib import Path
from openai import OpenAI

TRANSLATION_INSTRUCTIONS = """
You are a translator for a D&D 5e fantasy role-playing adventure.

Translate the supplied text into German.

Use the terminology provided with the request as authoritative.
Follow the specified translations, grammatical information,
and notes in the terminology exactly.

Every <<<FOUNDRY_###>>> marker is an opaque protected placeholder.
It is NOT translatable content and MUST be preserved exactly.

Protected markers are mandatory structural elements of the output.

For every protected marker in the input:
- The exact same marker MUST appear in the output.
- It MUST appear exactly once.
- It MUST remain in the same position relative to the surrounding text.
- It MUST be copied character-for-character.
- NEVER omit a marker.
- NEVER translate, rename, reconstruct, or replace a marker.
- NEVER treat a marker as optional.

A protected marker may be immediately followed by visible text such as
a character name, creature name, place name, or other label. The visible
text following the marker is normal translatable content, but the marker
itself is NOT part of that content and MUST remain in the translation.

For example, if the input contains:

<<<FOUNDRY_004>>>{Illithinoch}

the output MUST contain:

<<<FOUNDRY_004>>>{Illithinoch}

If the visible text is translated, only the visible text may change;
the protected marker must remain completely unchanged.

Do not attempt to recreate the original Foundry syntax yourself.
Return every protected marker exactly as it appears in the input.

NEVER interpret, translate, reconstruct, replace, or omit a protected
marker.

Every protected marker MUST be copied character-for-character.
The number, identity, and order of all protected markers MUST remain
unchanged.

Do not attempt to recreate the original Foundry syntax yourself.
Do not replace a marker with the name or meaning of the element it
represents.

Return every protected marker exactly as it appears in the input.

Proper names must remain untranslated unless the terminology
explicitly specifies otherwise.

Return only the translated text.
"""

def create_chunks(items, max_chars=50000):
    chunks = []
    current_texts = []
    current_protected = {}
    current_length = 0

    for item in items:
        text = item["text"]
        protected = item["protected"]
        text_length = len(text)

        if current_texts and current_length + text_length > max_chars:
            chunks.append({
                "text": "\n\n".join(current_texts),
                "protected": current_protected
            })

            current_texts = []
            current_protected = {}
            current_length = 0

        current_texts.append(text)
        current_protected.update(protected)
        current_length += text_length

    if current_texts:
        chunks.append({
            "text": "\n\n".join(current_texts),
            "protected": current_protected
        })

    return chunks


def protect_foundry_syntax(text, start_index=0):
    protected = {}

    def replace(match):
        placeholder = (
            f"<<<FOUNDRY_{start_index + len(protected):03d}>>>"
        )
        protected[placeholder] = match.group(0)
        return placeholder

    # Protect Foundry @UUID[...] and @Embed[...] syntax.
    text = re.sub(r'@(UUID|Embed)\[[^\]]*\]', replace, text)

    # Protect Foundry inline rolls, checks, and saves.
    text = re.sub(r'\[\[[^\]]*\]\]', replace, text)

    return text, protected


def restore_foundry_syntax(text, protected):
    for placeholder, original in protected.items():
        text = text.replace(placeholder, original)
    return text


def translate_text(client, text, terminology, protected):
    # The text has already been protected before chunking.
    protected_text = text

    print("=== PROTECTED TEXT ===")
    print(protected_text)

    print("\n=== PROTECTED ELEMENTS ===")
    for placeholder, original in protected.items():
        print(f"{placeholder} -> {original}")

    # Translate using the existing terminology database.
    start = time.perf_counter()

    print("\n=== CHUNK SENT TO LLM ===")
    print(protected_text)

    response = client.responses.create(
        model="gpt-5.4-mini",
        instructions=TRANSLATION_INSTRUCTIONS,
        input=protected_text
    )

    end = time.perf_counter()
    print(
        f"\n=== API Call Duration (Translation): "
        f"{end - start:.2f} Seconds ==="
    )

    translated_text = response.output_text

    # Restore the original Foundry syntax.
    restored_text = restore_foundry_syntax(
        translated_text,
        protected
    )

    # Verify that all protected elements survived unchanged.
    print("\n=== PROTECTED ELEMENT INTEGRITY ===")
    for placeholder, original in protected.items():
        if original in restored_text:
            print(f"{placeholder}: OK")
        else:
            print(f"{placeholder}: MISSING OR MODIFIED")

    return restored_text


# ------------------------------------------------------------
# Initialize OpenAI API client
# ------------------------------------------------------------

api_key = Path(
    "local_secret_do_not_commit/openai_api_key.txt"
).read_text(encoding="utf-8").strip()

client = OpenAI(api_key=api_key)


# ------------------------------------------------------------
# Load input text
# ------------------------------------------------------------

with open("input/test-entry.json", "r", encoding="utf-8") as file:
    data = json.load(file)

texts = [
    entry["text"]
    for entry in data.values()
    if "text" in entry
]

# ------------------------------------------------------------
# Parse all chunks one by one
# ------------------------------------------------------------

protected_chunks = []

placeholder_index = 0

for text in texts:
    protected_text, text_protected = protect_foundry_syntax(
        text,
        placeholder_index
    )

    protected_chunks.append({
        "text": protected_text,
        "protected": text_protected
    })

    placeholder_index += len(text_protected)

chunks = create_chunks(protected_chunks)

print(f"\n=== CHUNKS: {len(chunks)} ===")
for index, chunk in enumerate(chunks, start=1):
    print(f"Chunk {index}: {len(chunk['text'])} characters")


# ------------------------------------------------------------
# Load terminology database
# ------------------------------------------------------------

with open(
        "terminology/terminology.json",
        "r",
        encoding="utf-8"
) as file:
    terminology = json.load(file)


# ------------------------------------------------------------
# Translate chunks
# ------------------------------------------------------------

translated_chunks = []

for index, chunk in enumerate(chunks, start=1):
    print(f"\n=== TRANSLATING CHUNK {index}/{len(chunks)} ===")

    translated_chunk = translate_text(
        client,
        chunk["text"],
        terminology,
        chunk["protected"]
    )

    translated_chunks.append(translated_chunk)


# ------------------------------------------------------------
# Combine translated chunks
# ------------------------------------------------------------

translated_text = "\n\n".join(translated_chunks)

print("\n=== TRANSLATION ===")
print(translated_text)