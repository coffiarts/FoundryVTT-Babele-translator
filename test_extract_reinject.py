import json
from pathlib import Path
from collections import Counter

# ------------------------------------------------------------
# Configuration
# ------------------------------------------------------------

FILENAME = "dnd-phandelver-below.pbso-adventures.json"

TRANSLATABLE_FIELDS = {
    "text",
    "name",
    "caption",
    "description"
}

MAX_CHARS_PER_CHUNK = 100_000


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

# chunks = []
# current_chunk = []
# current_size = 0
#
# for node in nodes:
#
#     text_size = len(node["original"])
#
#     if (
#             current_chunk
#             and current_size + text_size > MAX_CHARS_PER_CHUNK
#     ):
#         chunks.append(current_chunk)
#         current_chunk = []
#         current_size = 0
#
#     current_chunk.append(node)
#     current_size += text_size
#
# if current_chunk:
#     chunks.append(current_chunk)
#
# print(
#     f"\n=== CHUNKS ===\n"
#     f"{len(chunks)}"
# )
#
# for i, chunk in enumerate(chunks):
#
#     chars = sum(
#         len(node["original"])
#         for node in chunk
#     )
#
#     print(
#         f"Chunk {i}: "
#         f"{len(chunk)} nodes, "
#         f"{chars:,} chars"
#     )
#

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
    f"Payload chars: "
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

translations = simulate_translation(
    nodes
)


# ------------------------------------------------------------
# Reinsert
# ------------------------------------------------------------

reinsert_translations(
    nodes,
    translations
)


# ------------------------------------------------------------
# Verify integrity
# ------------------------------------------------------------

if working_data == original_data:

    print(
        "\n✅ SUCCESS"
    )

    print(
        "Reinjected JSON is identical "
        "to original JSON."
    )

else:

    print(
        "\n❌ FAILURE"
    )

    raise ValueError(
        "Reinjected JSON differs "
        "from original JSON."
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
