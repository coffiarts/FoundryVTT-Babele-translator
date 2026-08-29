import os
import json
import time
from pathlib import Path
from openai import OpenAI

# ------------------------------------------------------------
# Configuration
# ------------------------------------------------------------

INPUT_FILE_NAME = "test-input.json"
MAX_CHARS_PER_CHUNK = 50000 # It may (unproven) help to scale this with the overall input size (larger input => larger batch size)
TRANSLATABLE_FIELDS = {
    "text",
    "name",
    "caption",
    "description"
}

INPUT_FOLDER_NAME = "input"
PROCESS_FOLDER_NAME = "process"
SECRETS_FOLDER_NAME = "local_secret_do_not_commit"
ERRORS_FOLDER_NAME = "errors"

NODES_FILE_NAME = "01-nodes.json"
CHUNKS_FILE_NAME = "02-chunks.json"
PROTECTED_ELEMENTS_FILE_NAME = "03-protected_elements.json"
TRANSLATIONS_RAW_FILE_NAME = "04-translations_raw.json"
TRANSLATIONS_REINJECTED_FILE_NAME = "05-translations-reinjected.json"
POST_REVIEW_ITEMS_FILE_NAME = "06-post-review-items.json"
ERRORS_FILE_NAME = "errors.json"
APIKEY_FILE_NAME = "openai_api_key.txt"


# ------------------------------------------------------------
# Preprocess configuration (do not edit anything from here on)!
# ------------------------------------------------------------
INPUT_FILE = Path(INPUT_FOLDER_NAME) / INPUT_FILE_NAME

# create specific progress subfolder for current input (if necessary)
PROCESS_SUBFOLDER_NAME = Path(PROCESS_FOLDER_NAME) / INPUT_FILE_NAME.removesuffix(".json")
if not os.path.exists(PROCESS_SUBFOLDER_NAME):
    os.makedirs(PROCESS_SUBFOLDER_NAME)

NODES_FILE = Path(PROCESS_SUBFOLDER_NAME) / NODES_FILE_NAME
CHUNKS_FILE = Path(PROCESS_SUBFOLDER_NAME) / CHUNKS_FILE_NAME
PROTECTED_ELEMENTS_FILE = Path(PROCESS_SUBFOLDER_NAME) / PROTECTED_ELEMENTS_FILE_NAME
TRANSLATIONS_RAW_FILE = Path(PROCESS_SUBFOLDER_NAME) / TRANSLATIONS_RAW_FILE_NAME
TRANSLATIONS_REINJECTED_FILE = Path(PROCESS_SUBFOLDER_NAME) / TRANSLATIONS_REINJECTED_FILE_NAME
POST_REVIEW_ITEMS_FILE = Path(PROCESS_SUBFOLDER_NAME) / POST_REVIEW_ITEMS_FILE_NAME

ERRORS_FILE = Path(ERRORS_FOLDER_NAME) / ERRORS_FILE_NAME
APIKEY_FILE = Path(SECRETS_FOLDER_NAME) / APIKEY_FILE_NAME


# ------------------------------------------------------------
# Function: Load input file
# ------------------------------------------------------------
def load_input():
    with INPUT_FILE.open(
            "r",
            encoding="utf-8"
    ) as file:

        original_data = json.load(file)

    # Deep copy for testing
    working_data = json.loads(
        json.dumps(
            original_data,
            ensure_ascii=False
        )
    )
    return original_data, working_data

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
# Function: Save nodes
# ------------------------------------------------------------
def save_nodes(nodes):

    with open(
            NODES_FILE,
            "w",
            encoding="utf-8"
    ) as file:

        json.dump(
            nodes,
            file,
            ensure_ascii=False,
            indent=2
        )


# ------------------------------------------------------------
# Function: Load nodes
# ------------------------------------------------------------
def load_nodes():

    with open(
            NODES_FILE,
            "r",
            encoding="utf-8"
    ) as file:

        return json.load(file)


# ------------------------------------------------------------
# Function: Initialize LLM API client
# ------------------------------------------------------------
def init_api_client():

    api_key = APIKEY_FILE.read_text(
        encoding="utf-8"
    ).strip()
    client = OpenAI(
        api_key=api_key
    )
    return client

# ------------------------------------------------------------
# MAIN ;-)
# ------------------------------------------------------------

print(
    f"\n=== PROCESSING FILE: {INPUT_FILE} ===\n"
    f"Batch Size: max. {MAX_CHARS_PER_CHUNK} chars (excluding instructions & terminology)"
)

global_timer_start = time.perf_counter()

print(f"\n=== LOAD INPUT FILE ===")

original_data, working_data = load_input()
original_chars_cnt = json.dumps(
    original_data,
    ensure_ascii=False,
    indent=2
)

print(f"loaded: {len(original_chars_cnt)} chars from {INPUT_FILE} ===\n")

print(f"\n=== IMPORT NODES ===")

nodes = []
import_nodes(
    input=working_data,
    nodes=nodes,
    current_path=[]
)
nodes_imported_cnt = len(nodes)

print(f"imported: {nodes_imported_cnt} nodes\n")
print(f"DEBUG - Content of first 10 nodes:"
    f"\n{json.dumps(
        nodes[:10],
        ensure_ascii=False,
        indent=2)}"
)

print(f"\n=== SAVE NODES TO PROGRESS FOLDER ===")

save_nodes(nodes)
loaded_nodes = load_nodes()
loaded_nodes_cnt = len(loaded_nodes)

print(f"DEBUG - loaded {loaded_nodes_cnt} nodes. Expected: {nodes_imported_cnt}")
print(
    f"DEBUG - first node identical: "
    f"{nodes[0] == loaded_nodes[0]}"
)
print(
    f"DEBUG - last node identical: "
    f"{nodes[-1] == loaded_nodes[-1]}"
)


# ------------------------------------------------------------
# Stop global timer
# ------------------------------------------------------------

global_timer_end = time.perf_counter()

print(f"\n=== TOTAL processing duration: {global_timer_end - global_timer_start:.2f} seconds ==="
)
