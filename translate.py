import json
from pathlib import Path
from collections import Counter
from openai import OpenAI

# ------------------------------------------------------------
# Configuration
# ------------------------------------------------------------

FILENAME = "dnd-phandelver-below.pbso-player-tables.json"

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
"""

MAX_CHARS_PER_CHUNK = 10000


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


# ------------------------------------------------------------
# Simulated translation
# ------------------------------------------------------------

def simulate_translation(nodes):

    translations = {}

    for node in nodes:

        translations[node["id"]] = (
            node["original"]
        )

    return translations


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
# Load JSON
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

translation_payload = []

for node in nodes:

    translation_payload.append({
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
        translation_payload,
        file,
        ensure_ascii=False,
        indent=2
    )

payload_json = json.dumps(
    translation_payload,
    ensure_ascii=False
)

print(
    f"\n=== PAYLOAD STATS ==="
)

print(
    f"Total Payload char count: "
    f"{len(payload_json):,}"
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

print(
    f"\n=== FIRST 10 NODES DETAILS ==="
)

for node in nodes[:10]:

    print(
        f"\nID: {node['id']}"
    )

    print(
        f"CONTAINER length: {len(node['container'])}"
    )

    print(
        f"FIELD: {node['key']}"
    )

    print(
        f"ORIGINAL [first <=100 of {len(node["original"])} chars]: {node["original"][:100]}"
    )


# ------------------------------------------------------------
# Simulate translation
# ------------------------------------------------------------

translations = {}

print(
    f"\n=== PROCESSING {len(chunks)} CHUNKS (MAX SIZE: {MAX_CHARS_PER_CHUNK}) ==="
)

for chunk_index, chunk in enumerate(chunks):

    print(
        f"Processing chunk "
        f"{chunk_index + 1}/{len(chunks)}"
    )

    # ----------------------------------------
    # Build payload for this chunk
    # ----------------------------------------

    payload = []

    for node in chunk:

        payload.append({
            "id": node["id"],
            "text": node["original"]
        })

    payload_json = json.dumps(
        payload,
        ensure_ascii=False
    )

    print(
        f"Chunk {chunk_index + 1}: "
        f"{len(payload):,} entries, "
        f"{len(payload_json):,} chars"
    )

    # ----------------------------------------
    # Real translation test
    # ----------------------------------------

    response = client.responses.create(
        model="gpt-5.4-mini",
        instructions=TRANSLATION_INSTRUCTIONS,
        input=json.dumps(
            payload,
            ensure_ascii=False
        )
    )

    print(
        f"Response length: "
        f"{len(response.output_text):,}"
    )

    translated_payload = json.loads(
        response.output_text
    )

    print(
        f"Expected entries: {len(payload)}"
    )

    print(
        f"Returned entries: {len(translated_payload)}"
    )

    chunk_translations = {}

    for entry in translated_payload:

        chunk_translations[
            entry["id"]
        ] = entry["translation"]

    translations.update(
        chunk_translations
    )


    # ----------------------------------------
    # Merge into global translations
    # ----------------------------------------

    translations.update(
        chunk_translations
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


