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

    # Protect Foundry @UUID[...] and @Embed[...] syntax.
    text = re.sub(r'@(UUID|Embed)\[[^\]]*\]', replace, text)

    # Protect Foundry inline rolls, checks, and saves.
    text = re.sub(r'\[\[[^\]]*\]\]', replace, text)

    return text, protected


def restore_foundry_syntax(text, protected):
    for placeholder, original in protected.items():
        text = text.replace(placeholder, original)
    return text


def translate_text(client, text, terminology):
    # Protect Foundry syntax before sending the text to the LLM.
    protected_text, protected = protect_foundry_syntax(text)

    print("=== PROTECTED TEXT ===")
    print(protected_text)

    print("\n=== PROTECTED ELEMENTS ===")
    for placeholder, original in protected.items():
        print(f"{placeholder} -> {original}")

    # Translate using the existing terminology database.
    start = time.perf_counter()

    response = client.responses.create(
        model="gpt-5.4-mini",
        instructions=f"""
You are a translator for a D&D 5e fantasy role-playing adventure.

Translate the supplied text into German.

Use the following terminology as authoritative:
{json.dumps(terminology, ensure_ascii=False, indent=2)}

Follow the specified translations, grammatical information,
and notes in the terminology exactly.

Every <<<FOUNDRY_###>>> marker is an opaque protected placeholder,
not translatable content.

NEVER interpret, translate, reconstruct, replace, or omit a protected
marker.

If the source contains <<<FOUNDRY_004>>>, the translated output MUST
contain the literal string <<<FOUNDRY_004>>>.

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
""",
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

original_text = data["Hooked Stones"]["text"]


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
# Translate text
# ------------------------------------------------------------

translated_text = translate_text(
    client,
    original_text,
    terminology
)

print("\n=== TRANSLATION ===")
print(translated_text)