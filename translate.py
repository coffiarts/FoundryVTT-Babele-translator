import json
import re
import time
from pathlib import Path
from collections import Counter
from openai import OpenAI

# ------------------------------------------------------------
# Configuration
# ------------------------------------------------------------

FILENAME = "dnd-phandelver-below.pbso-items.json"

TRANSLATABLE_FIELDS = {
    "text",
    "name",
    "caption",
    "description"
}

TRANSLATION_INSTRUCTIONS = """
Translate every text to German.

Return ONLY valid JSON.

Input format:

[
  {
    "id": 123,
    "text": "some text"
  }
]

Output format:

[
  {
    "id": 123,
    "translation": "übersetzter Text"
  }
]

Rules:
- Preserve every id unchanged.
- Translate only the text.
- Do not omit entries.
- Do not add entries.
- Return only JSON.

A placeholder always belongs to the label that follows it.

When translating, the label may be translated and moved
to a different position in the sentence if German grammar
requires it.

However, the placeholder must move together with the label.

Input:
They are loyal to <<<FOUNDRY_000001>>>{King Grol}.

Correct output:
Sie sind <<<FOUNDRY_000001>>>{König Grol} gegenüber loyal.

Incorrect output:
Sie sind König Grol gegenüber loyal.
"""

MAX_CHARS_PER_CHUNK = 30000

# ------------------------------------------------------------
# Global placeholder registry
# ------------------------------------------------------------

protected_elements = {}

# ------------------------------------------------------------
# Collect translatable nodes
# ------------------------------------------------------------

def collect_translatable_nodes(value, nodes):

    if isinstance(value, dict):

        for key, item in value.items():

            if (
                    key in TRANSLATABLE_FIELDS
                    and isinstance(item, str)
            ):

                nodes.append({
                    "id": len(nodes),
                    "container": value,
                    "key": key,
                    "original": item
                })

            elif isinstance(item, (dict, list)):

                collect_translatable_nodes(
                    item,
                    nodes
                )

    elif isinstance(value, list):

        for item in value:

            collect_translatable_nodes(
                item,
                nodes
            )


# ------------------------------------------------------------------
# Protect & Restore Foundry Syntax (aka "Protection by Placeholder")
# ------------------------------------------------------------------

def protect_foundry_syntax(text):

    def replace(match):

        placeholder = (
            f"<<<FOUNDRY_{len(protected_elements):06d}>>>"
        )

        protected_elements[
            placeholder
        ] = match.group(0)

        return placeholder

    # Protect Foundry @UUID[...] and @Embed[...] syntax
    text = re.sub(
        r'@(UUID|Embed|Compendium)\[[^\]]*\]',
        replace,
        text
    )

    # Protect inline rolls, checks, saves, etc.
    text = re.sub(
        r'\[\[[^\]]*\]\]',
        replace,
        text
    )

    return text


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
# Verify placeholder integrity
# ------------------------------------------------------------

def verify_protected_integrity(
        original_protected_text,
        translated_text):

    placeholders = set(
        re.findall(
            r'<<<FOUNDRY_\d{6}>>>',
            original_protected_text
        )
    )

    for placeholder in placeholders:

        count = translated_text.count(
            placeholder
        )

        if count != 1:

            print(
                f"\n❌ PLACEHOLDER ERROR: "
                f"{placeholder}"
            )

            print(
                f"Occurrences in translation: "
                f"{count}"
            )

            print(
                f"\nTranslated text (missing {placeholder}): "
                f"{translated_text}"
            )

            print(
                f"\nOriginal text (should contain {placeholder}): "
                f"{original_protected_text}"
            )

            print(
                f"\n=== PROTECTED ELEMENT ===\n"
                f"{placeholder} -> {protected_elements[placeholder]}"
            )

            raise ValueError(
                f"Placeholder integrity failure: "
                f"{placeholder}"
            )


# ------------------------------------------------------------
# Reinsert translations
# ------------------------------------------------------------

def reinsert_translations(
        nodes,
        translations
):

    for node in nodes:

        node["container"][node["key"]] = (
            translations[node["id"]]
        )

# ------------------------------------------------------------
# Load JSON: Input file and (master) terminology file
# ------------------------------------------------------------

input_path = (
        Path("input")
        / FILENAME
)

with input_path.open(
        "r",
        encoding="utf-8"
) as file:

    original_data = json.load(file)

master_terminology_filename = f"terminology/terminology-{FILENAME}"

with open(
        master_terminology_filename,
        "r",
        encoding="utf-8"
) as file:

    master_terminology = json.load(file)

master_terminology_json = json.dumps(
    master_terminology,
    ensure_ascii=False,
    indent=2
)


print(
    f"\n=== MASTER TERMINOLOGY (derived from complete input file) ===\n"
    f"source: {master_terminology_filename}\n"
    f"term count: {len(master_terminology["terms"])}\n"
    f"json chars: {len(master_terminology_json):,}"
)

# ------------------------------------------------------------
# Initialize LLM API client
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
# Deep copy for testing
# ------------------------------------------------------------

working_data = json.loads(
    json.dumps(
        original_data,
        ensure_ascii=False
    )
)


# ------------------------------------------------------------
# Collect nodes
# ------------------------------------------------------------

nodes = []

collect_translatable_nodes(
    working_data,
    nodes
)

# ------------------------------------------------------------
# Build chunks
# ------------------------------------------------------------

chunks = []
current_chunk = []
current_size = 0

for node in nodes:

    text_size = len(node["original"])

    if (
            current_chunk
            and current_size + text_size > MAX_CHARS_PER_CHUNK
    ):
        chunks.append(current_chunk)
        current_chunk = []
        current_size = 0

    current_chunk.append(node)
    current_size += text_size

if current_chunk:
    chunks.append(current_chunk)

print(
    f"\n=== CHUNKS ===\n"
    f"{len(chunks)}"
)

for i, chunk in enumerate(chunks):

    chars = sum(
        len(node["original"])
        for node in chunk
    )

    print(
        f"Chunk {i}: "
        f"{len(chunk)} nodes, "
        f"{chars:,} chars"
    )


# ------------------------------------------------------------
# Optional inspection
# ------------------------------------------------------------

# Summary of payload contents
print(
    f"\n=== TRANSLATABLE NODES ===\n"
    f"{len(nodes)}"
)

complete_payload = []

for node in nodes:

    complete_payload.append({
        "id": node["id"],
        "field": node["key"],
        "text": node["original"]
    })

with open(
        "analyze/translation_payload.json",
        "w",
        encoding="utf-8"
) as file:

    json.dump(
        complete_payload,
        file,
        ensure_ascii=False,
        indent=2
    )

chunk_payload_json = json.dumps(
    complete_payload,
    ensure_ascii=False
)

print(
    f"\n=== PAYLOAD STATS ==="
)

print(
    f"Total Payload char count: "
    f"{len(chunk_payload_json):,}"
)

counter = Counter(
    node["key"]
    for node in nodes
)

print(counter)

chars_per_field = {}

for field in ["name", "description", "text", "caption"]:

    chars_per_field[field] = sum(
        len(node["original"])
        for node in nodes
        if node["key"] == field
    )

print(f"chars_per_field: {chars_per_field}")

# print(
#     f"\n=== FIRST 10 NODES DETAILS ==="
# )
#
# for node in nodes[:10]:
#
#     print(
#         f"\nID: {node['id']}"
#     )
#
#     print(
#         f"CONTAINER length: {len(node['container'])}"
#     )
#
#     print(
#         f"FIELD: {node['key']}"
#     )
#
#     print(
#         f"ORIGINAL [first <=100 of {len(node["original"])} chars]: {node["original"][:100]}"
#     )


# ------------------------------------------------------------
# Translate the compendium (chunk-wise)
# ------------------------------------------------------------

translations = {}

print(
    f"\n=== PROCESSING {len(chunks)} CHUNKS (MAX SIZE (excluding JSON overhead): {MAX_CHARS_PER_CHUNK}) ==="
)

for chunk_index, chunk in enumerate(chunks):

    chunk_text = "\n".join(
        node["original"]
        for node in chunk
    )

    print(
        f"\nProcessing chunk {chunk_index + 1}/{len(chunks)} [{len(chunk_text)} chars]"
    )

    # ----------------------------------------------------------
    # Build chunk-specific sub-terminology from master terminology
    # ----------------------------------------------------------

    chunk_text = "\n".join(
        node["original"]
        for node in chunk
    )

    chunk_text_lower = chunk_text.lower()

    chunk_relevant_terms = [
        term
        for term in master_terminology["terms"]
        if term["original"].lower() in chunk_text_lower
    ]

    print(
        f"Chunk {chunk_index + 1}: "
        f"{len(chunk_relevant_terms)} relevant terms"
    )

    chunk_relevant_terminology = {
        "terms": chunk_relevant_terms
    }


    chunk_relevant_terminology_json = json.dumps(
        chunk_relevant_terminology,
        ensure_ascii=False,
        indent=2
    )

    print(
        f"Length of chunk-relevant terminology: "
        f"terms: {len(chunk_relevant_terminology):,}, "
        f"json chars: {len(chunk_relevant_terminology_json):,}"
    )

    chunk_instructions_with_terminology = (
            TRANSLATION_INSTRUCTIONS
            + "\n\n"
            + "=== TERMINOLOGY DATABASE ===\n"
            + chunk_relevant_terminology_json
            + "\n\n"
            + "=== END TERMINOLOGY DATABASE ===\n"
    )

    # print(
    #     f"\n=== Instructions used in this chunk (with chunk-relevant terminology) ===\n"
    #     f"{chunk_instructions_with_terminology}"
    # )

    # ----------------------------------------
    # Build payload for this chunk
    # ----------------------------------------

    chunk_payload = []

    protected_texts = {}

    for node in chunk:

        protected_text = protect_foundry_syntax(
            node["original"]
        )

        protected_texts[
            node["id"]
        ] = protected_text

        chunk_payload.append({
            "id": node["id"],
            "text": protected_text
        })

    chunk_payload_json = json.dumps(
        chunk_payload,
        ensure_ascii=False
    )

    print(
        f"Chunk {chunk_index + 1}: "
        f"{len(chunk_payload):,} entries, "
        f"{len(chunk_payload_json):,} chars"
    )


    # ----------------------------------------
    # Translate the current chunk
    # ----------------------------------------

    start = time.perf_counter()

    response = client.responses.create(
        model="gpt-5.4-mini",
        instructions=chunk_instructions_with_terminology,
        input=json.dumps(
            chunk_payload,
            ensure_ascii=False
        )
    )

    end = time.perf_counter()

    print(
        f"API duration: "
        f"{end - start:.2f} seconds"
    )

    print(
        f"Response length: "
        f"{len(response.output_text):,}"
    )

    # print(
    #     f"Response content: "
    #     f"{response.output_text}"
    # )

    translated_payload = json.loads(
        response.output_text
    )

    print(
        f"Expected entries: {len(chunk_payload)}"
    )

    print(
        f"Returned entries: {len(translated_payload)}"
    )

    chunk_translations = {}

    for entry in translated_payload:

        verify_protected_integrity(
            protected_texts[
                entry["id"]
            ],
            entry["translation"]
        )

        restored_text = restore_foundry_syntax(
            entry["translation"],
            protected_elements
        )

        chunk_translations[
            entry["id"]
        ] = restored_text

    translations.update(
        chunk_translations
    )


    # ----------------------------------------
    # Merge into global translations
    # ----------------------------------------

    translations.update(
        chunk_translations
    )

print(
    f"\n=== PROTECTED ELEMENTS "
    f"({len(protected_elements)}) ==="
)

for placeholder, original in protected_elements.items():

    print(
        f"{placeholder} -> {original}"
    )

# ------------------------------------------------------------
# Reinsert
# ------------------------------------------------------------

reinsert_translations(
    nodes,
    translations
)


# ------------------------------------------------------------
# Final stats
# ------------------------------------------------------------

print(
    f"\n=== FINAL STATS ==="
)

total_chars = sum(
    len(node["original"])
    for node in nodes
)

print(
    f"Total translatable chars: "
    f"{total_chars:,}"
)

original_json = json.dumps(
    original_data,
    ensure_ascii=False,
    indent=2
)

total_translatable_chars = sum(
    len(node["original"])
    for node in nodes
)

print(
    f"Original JSON chars: {len(original_json):,}"
)

print(
    f"Translatable chars: {total_translatable_chars:,}"
)

print(
    f"Reduction: "
    f"{100 * (1 - total_translatable_chars / len(original_json)):.1f}%"
)

print(
    f"Total nodes to translate: "
    f"{len(nodes):,}"
)

print(
    f"Average chars per node: "
    f"{total_translatable_chars / len(nodes):.1f}"
)
print("\n✅ REINJECTION COMPLETED")

# ------------------------------------------------------------
# Save the results to output
# ------------------------------------------------------------

with open(
        f"output/{FILENAME}",
        "w",
        encoding="utf-8"
) as file:

    json.dump(
        working_data,
        file,
        ensure_ascii=False,
        indent=2
    )

print(f"\n✅ File has been written to: output/{FILENAME}")
# print(
#     "\n❌ FAILURE"
# )
#
# raise ValueError(
#     "Reinjected JSON differs "
#     "from original JSON."
# )


