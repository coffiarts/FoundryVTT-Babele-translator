import json
import time
from pathlib import Path
from openai import OpenAI

# ------------------------------------------------------------
# Configuration
# ------------------------------------------------------------

FILENAME = "test-input.json"

MAX_CHARS_PER_CHUNK = 50000 # It may (unproven) help to scale this with the overall input size (larger input => larger batch size)

TRANSLATABLE_FIELDS = {
    "text",
    "name",
    "caption",
    "description"
}


# ------------------------------------------------------------
# Function: Collect translatable nodes
# ------------------------------------------------------------

def import_nodes(input, nodes, current_path):

    if isinstance(input, dict):

        for key, item in input.items():

            if (
                    key in TRANSLATABLE_FIELDS
                    and isinstance(item, str)
            ):

                nodes.append({
                    "id": len(nodes),
                    "path": current_path + [key],
                    "original": item
                })

            elif isinstance(item, (dict, list)):

                import_nodes(
                    item,
                    nodes,
                    current_path+ [key]
                )

    elif isinstance(input, list):

        for index, item in enumerate(input):

            import_nodes(
                item,
                nodes,
                current_path + [index]
            )

# ------------------------------------------------------------
# Start global timer
# ------------------------------------------------------------

global_timer_start = time.perf_counter()


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
# Load JSON: Input file
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

print(
    f"\n=== PROCESSING FILE: {input_path} ===\n"
    f"Batch Size: max. {MAX_CHARS_PER_CHUNK} chars (excluding instructions & terminology)"
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
# Unit Testing
# ------------------------------------------------------------

nodes = []

import_nodes(
    input=working_data,
    nodes=nodes,
    current_path=[]
)

print(json.dumps(
    nodes[:10],
    ensure_ascii=False,
    indent=2
))

# ------------------------------------------------------------
# Stop global timer
# ------------------------------------------------------------

global_timer_end = time.perf_counter()

print(
    f"\nTOTAL processing duration: "
    f"{global_timer_end - global_timer_start:.2f} seconds"
)