import json
import re
import time
from pathlib import Path
from openai import OpenAI


# ------------------------------------------------------------
# Configuration
# ------------------------------------------------------------

FILENAME = "dnd-phandelver-below.pbso-items.json"


# ------------------------------------------------------------
# Translation instructions
# ------------------------------------------------------------

TRANSLATION_INSTRUCTIONS = """
You are a translator for a D&D 5e fantasy role-playing adventure.

Translate the supplied JSON content into German.

IMPORTANT:
- The supplied input is a complete JSON document.
- Preserve the complete JSON structure exactly.
- Return a complete, valid JSON document.
- Do not add or remove JSON objects, arrays, properties, or values.
- Do not change property names.
- Only translate translatable string values.
- Preserve numbers, booleans, null values, and all non-translatable
  structural elements exactly.
- Preserve all JSON syntax and structure.

Translate string values belonging to these properties:
- "text"
- "name"
- "caption"
- "description"

Do not translate other string values unless they are clearly
translatable content.

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
itself is NOT part of that content and MUST remain unchanged.

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

Proper names must remain untranslated unless the terminology
explicitly specifies otherwise.

Return only the translated JSON document.
"""


# ------------------------------------------------------------
# Protect Foundry syntax
# ------------------------------------------------------------

def protect_foundry_syntax(
        text,
        start_index=0
):
    protected = {}

    def replace(match):

        placeholder = (
            f"<<<FOUNDRY_"
            f"{start_index + len(protected):03d}>>>"
        )

        protected[placeholder] = match.group(0)

        return placeholder

    # Protect Foundry @UUID[...] and @Embed[...] syntax.
    text = re.sub(
        r'@(UUID|Embed)\[[^\]]*\]',
        replace,
        text
    )

    # Protect Foundry inline rolls, checks, and saves.
    text = re.sub(
        r'\[\[[^\]]*\]\]',
        replace,
        text
    )

    return text, protected


# ------------------------------------------------------------
# Restore Foundry syntax
# ------------------------------------------------------------

def restore_foundry_syntax(
        text,
        protected
):
    for placeholder, original in protected.items():
        text = text.replace(
            placeholder,
            original
        )

    return text


# ------------------------------------------------------------
# Verify protected elements
# ------------------------------------------------------------

def verify_protected_integrity(
        translated_text,
        protected
):
    print("\n=== PROTECTED ELEMENT INTEGRITY ===")

    all_ok = True

    for placeholder, original in protected.items():

        count = translated_text.count(
            original
        )

        if count == 1:
            print(
                f"{placeholder}: OK"
            )

        elif count == 0:
            print(
                f"{placeholder}: MISSING"
            )
            all_ok = False

        else:
            print(
                f"{placeholder}: "
                f"FOUND {count} TIMES"
            )
            all_ok = False

    return all_ok


# ------------------------------------------------------------
# Translate complete JSON
# ------------------------------------------------------------

def translate_json(
        client,
        protected_json,
        terminology,
        protected
):
    print("\n=== PROTECTED ELEMENTS ===")

    for placeholder, original in protected.items():
        print(
            f"{placeholder} -> {original}"
        )

    print(
        "\n=== COMPLETE PROTECTED JSON "
        "SENT TO LLM ==="
    )

    print(
        f"{len(protected_json):,} characters"
    )

    # Convert terminology database to JSON text.
    terminology_json = json.dumps(
        terminology,
        ensure_ascii=False,
        indent=2
    )

    # Add terminology as additional instructions.
    instructions = (
            TRANSLATION_INSTRUCTIONS
            + "\n\n"
            + "=== TERMINOLOGY DATABASE ===\n"
            + terminology_json
            + "\n\n"
            + "=== END TERMINOLOGY DATABASE ===\n"
    )

    start = time.perf_counter()

    response = client.responses.create(
        model="gpt-5.4-mini",
        instructions=instructions,
        input=protected_json
    )

    end = time.perf_counter()

    print(
        f"\n=== API Call Duration "
        f"(Translation): "
        f"{end - start:.2f} Seconds ==="
    )

    translated_json = response.output_text

    # Restore original Foundry syntax.
    restored_json = restore_foundry_syntax(
        translated_json,
        protected
    )

    # Verify protected elements.
    integrity_ok = verify_protected_integrity(
        restored_json,
        protected
    )

    if not integrity_ok:
        raise ValueError(
            "Protected Foundry elements were "
            "missing or modified during translation."
        )

    # Verify that the model returned valid JSON.
    try:
        translated_data = json.loads(
            restored_json
        )
    except json.JSONDecodeError as error:
        print(
            "\n=== INVALID TRANSLATED JSON ==="
        )
        print(
            restored_json
        )

        raise ValueError(
            "The translated output is not valid JSON."
        ) from error

    return translated_data


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
# Serialize complete JSON
# ------------------------------------------------------------

original_json = json.dumps(
    data,
    ensure_ascii=False,
    indent=2
)

print(
    f"\n=== ORIGINAL JSON ==="
)
print(
    f"{len(original_json):,} characters"
)


# ------------------------------------------------------------
# Protect Foundry syntax
# ------------------------------------------------------------

protected_json, protected = (
    protect_foundry_syntax(
        original_json
    )
)

print(
    f"\n=== PROTECTED JSON ==="
)
print(
    f"{len(protected_json):,} characters"
)
print(
    f"{len(protected)} protected elements"
)


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
# Translate complete JSON in ONE API call
# ------------------------------------------------------------

translated_data = translate_json(
    client,
    protected_json,
    terminology,
    protected
)


# ------------------------------------------------------------
# Serialize translated JSON
# ------------------------------------------------------------

translated_json = json.dumps(
    translated_data,
    ensure_ascii=False,
    indent=2
)


# ------------------------------------------------------------
# Output
# ------------------------------------------------------------

print(
    "\n=== TRANSLATED JSON ==="
)

print(
    f"{len(translated_json):,} characters"
)

print(
    translated_json
)