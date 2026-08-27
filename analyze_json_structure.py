import json


# ------------------------------------------------------------
# Configuration
# ------------------------------------------------------------

MAX_CHARS_PER_CHUNK = 50000

FILENAME = "dnd-phandelver-below.pbso-adventures.json"

CHUNK_LEVELS = {
    "dnd-phandelver-below.pbso-adventures.json": "journals",
    "dnd-phandelver-below.pbso-bestiary.json": "entries",
    "dnd-phandelver-below.pbso-items.json": "entries",
    "dnd-phandelver-below.pbso-player-options.json": "entries",
    "dnd-phandelver-below.pbso-player-tables.json": "entries",
}


# ------------------------------------------------------------
# Find cut nodes
# ------------------------------------------------------------

def find_cut_nodes(value, target_key, path=""):
    nodes = []

    if isinstance(value, dict):

        for key, item in value.items():

            child_path = f"{path}/{key}" if path else key

            if key == target_key and isinstance(item, dict):

                for child_key, child_value in item.items():
                    nodes.append({
                        "path": f"{child_path}/{child_key}",
                        "data": child_value
                    })

            else:
                nodes.extend(
                    find_cut_nodes(
                        item,
                        target_key,
                        child_path
                    )
                )

    elif isinstance(value, list):

        for index, item in enumerate(value):

            child_path = f"{path}/{index}"

            nodes.extend(
                find_cut_nodes(
                    item,
                    target_key,
                    child_path
                )
            )

    return nodes


# ------------------------------------------------------------
# Create chunks
# ------------------------------------------------------------

def create_chunks(cut_nodes):
    chunks = []
    current_nodes = []
    current_length = 0

    for node in cut_nodes:

        node_text = json.dumps(
            node["data"],
            ensure_ascii=False
        )

        node_length = len(node_text)

        if (
                current_nodes
                and current_length + node_length
                > MAX_CHARS_PER_CHUNK
        ):
            chunks.append(current_nodes)

            current_nodes = []
            current_length = 0

        current_nodes.append(node)
        current_length += node_length

    if current_nodes:
        chunks.append(current_nodes)

    return chunks


# ------------------------------------------------------------
# Load input file
# ------------------------------------------------------------

target_key = CHUNK_LEVELS[FILENAME]

with open(
        f"input/{FILENAME}",
        "r",
        encoding="utf-8"
) as file:
    data = json.load(file)


# ------------------------------------------------------------
# Find cut nodes
# ------------------------------------------------------------

cut_nodes = find_cut_nodes(
    data,
    target_key
)

print(f"=== CUT NODES: {len(cut_nodes)} ===")


# ------------------------------------------------------------
# Create chunks
# ------------------------------------------------------------

chunks = create_chunks(cut_nodes)

print(f"=== CHUNKS: {len(chunks)} ===")


# ------------------------------------------------------------
# Inspect chunks
# ------------------------------------------------------------

for index, chunk in enumerate(chunks, start=1):

    chunk_text = "\n\n".join(
        json.dumps(
            node["data"],
            ensure_ascii=False
        )
        for node in chunk
    )

    print(
        f"\n=== CHUNK {index} "
        f"({len(chunk_text)} characters) ==="
    )

    # print(chunk_text)