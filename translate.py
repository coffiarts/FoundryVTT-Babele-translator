import os
import json
import time
from pathlib import Path
from openai import OpenAI

# ------------------------------------------------------------
# Configuration
# ------------------------------------------------------------

INPUT_FILE_NAME = "test-input.json"
MAX_BATCH_SIZE = 50000 # It may (unproven) help to scale this with the overall input size (larger input => larger batch size)
TRANSLATABLE_FIELDS = {
    "text",
    "name",
    "caption",
    "description"
}

INPUT_FOLDER_NAME = "input"
PROCESS_FOLDER_NAME = "progress"
SECRETS_FOLDER_NAME = "local_secret_do_not_commit"
ERRORS_FOLDER_NAME = "errors"
OUTPUT_FOLDER_NAME = "output"

PROGRESS_FILE_NAME = "00-progress.json"
TRANSLATABLES_FILE_NAME = "01-translatables.json"
BATCHES_FILE_NAME = "02-batches.json"
PROTECTED_ELEMENTS_FILE_NAME = "03-protected_elements.json"
TRANSLATIONS_WITH_PLACEHOLDERS_FILE_NAME = "04-translations_with-placeholders.json"
TRANSLATIONS_FINAL_FILE_NAME = "05-translations-final.json"
POST_REVIEW_ITEMS_FILE_NAME = "06-post-review-items.json"

ERRORS_FILE_NAME = "errors.json"
APIKEY_FILE_NAME = "openai_api_key.txt"


# ------------------------------------------------------------
# Preprocess configuration (do not edit anything from here on)!
# ------------------------------------------------------------
INPUT_FILE = Path(INPUT_FOLDER_NAME) / INPUT_FILE_NAME
OUTPUT_FILE = Path(OUTPUT_FOLDER_NAME) / INPUT_FILE_NAME

# create specific progress subfolder for current input (if necessary)
PROCESS_SUBFOLDER_NAME = Path(PROCESS_FOLDER_NAME) / INPUT_FILE_NAME.removesuffix(".json")
if not os.path.exists(PROCESS_SUBFOLDER_NAME):
    os.makedirs(PROCESS_SUBFOLDER_NAME)

PROGRESS_FILE = Path(PROCESS_SUBFOLDER_NAME) / PROGRESS_FILE_NAME
TRANSLATABLES_FILE = Path(PROCESS_SUBFOLDER_NAME) / TRANSLATABLES_FILE_NAME
BATCHES_FILE = Path(PROCESS_SUBFOLDER_NAME) / BATCHES_FILE_NAME
PROTECTED_ELEMENTS_FILE = Path(PROCESS_SUBFOLDER_NAME) / PROTECTED_ELEMENTS_FILE_NAME
TRANSLATIONS_WITH_PLACEHOLDERS_FILE = Path(PROCESS_SUBFOLDER_NAME) / TRANSLATIONS_WITH_PLACEHOLDERS_FILE_NAME
TRANSLATIONS_FINAL_FILE = Path(PROCESS_SUBFOLDER_NAME) / TRANSLATIONS_FINAL_FILE_NAME
POST_REVIEW_ITEMS_FILE = Path(PROCESS_SUBFOLDER_NAME) / POST_REVIEW_ITEMS_FILE_NAME

ERRORS_FILE = Path(ERRORS_FOLDER_NAME) / ERRORS_FILE_NAME
APIKEY_FILE = Path(SECRETS_FOLDER_NAME) / APIKEY_FILE_NAME


# ------------------------------------------------------------
# Function: Load Babele input file
# ------------------------------------------------------------
def load_babele_input():
    with INPUT_FILE.open(
            "r",
            encoding="utf-8"
    ) as file:

        babele_json = json.load(file)

    return babele_json

# ------------------------------------------------------------
# Function: Import translatables
# ------------------------------------------------------------
def import_translatables(input, translatables, current_path):

    if isinstance(input, dict):

        for key, item in input.items():

            if (
                    key in TRANSLATABLE_FIELDS
                    and isinstance(item, str)
            ):

                translatables.append({
                    "id": len(translatables),
                    "path": current_path + [key],
                    "original": item
                })

            elif isinstance(item, (dict, list)):

                import_translatables(
                    item,
                    translatables,
                    current_path+ [key]
                )

    elif isinstance(input, list):

        for index, item in enumerate(input):

            import_translatables(
                item,
                translatables,
                current_path + [index]
            )

# ------------------------------------------------------------
# Function: Save Translatables
# ------------------------------------------------------------
def save_translatables(translatables):

    with open(
            TRANSLATABLES_FILE,
            "w",
            encoding="utf-8"
    ) as file:

        json.dump(
            translatables,
            file,
            ensure_ascii=False,
            indent=2
        )


# ------------------------------------------------------------
# Function: Load translatables
# ------------------------------------------------------------
def load_translatables():

    with open(
            TRANSLATABLES_FILE,
            "r",
            encoding="utf-8"
    ) as file:

        return json.load(file)


# ------------------------------------------------------------
# Function: Initialize API client
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
# Function: Get JSON element
# ------------------------------------------------------------
def get_json_element(
        json_object,
        path):

    current = json_object

    for element in path:
        current = current[element]

    return current


# ------------------------------------------------------------
# Function: Set JSON Element
# ------------------------------------------------------------

def set_json_element(
        target_json_object,
        path,
        new_value):

    current = target_json_object

    for element in path[:-1]:
        current = current[element]

    current[path[-1]] = new_value


# ------------------------------------------------------------
# Function: Apply translations (all at once)
# ------------------------------------------------------------
def apply_translations(
        babele_json,
        translatables,
        translations):

    for id, translation in translations.items():
        set_json_element(babele_json, translatables[id]["path"], translation)

    # TODO - apply any "on-top"" translations (like translator's watermark etc.)


# ----------------------------------------------------------------------------------
# Save Babele output
# This is the final export step that produces a ready-to-use Babele translation file
# ----------------------------------------------------------------------------------
def save_babele_output(babele_json):

    json_string = json.dumps(
        babele_json,
        ensure_ascii=False,
        indent=2
    )

    with open(
            OUTPUT_FILE,
            "w",
            encoding="utf-8"
    ) as file:

        file.write(json_string)

    print(f"Translated file written to: {OUTPUT_FILE} with {len(json_string)} chars")


# ------------------------------------------------------------
# MAIN ;-)
# ------------------------------------------------------------

print(
    f"\n=== PROCESSING FILE: {INPUT_FILE} ===\n"
    f"Batch Size: max. {MAX_BATCH_SIZE} chars (excluding instructions & terminology)"
)

global_timer_start = time.perf_counter()

print(f"\n=== LOAD INPUT FILE (Babele translation JSON exported from FoundryVTT) ===")

babele_json = load_babele_input()
babele_chars_cnt = json.dumps(
    babele_json,
    ensure_ascii=False,
    indent=2
)

print(f"loaded: {len(babele_chars_cnt)} chars from {INPUT_FILE} ===")

print(f"\n=== IMPORT TRANSLATABLES ===")

translatables = []
import_translatables(
    input=babele_json,
    translatables=translatables,
    current_path=[]
)
translatables_imported_cnt = len(translatables)

print(f"imported: {translatables_imported_cnt} translatables")
# print(f"DEBUG - Content of first 10 translatables:"
#     f"\n{json.dumps(
#         translatables[:10],
#         ensure_ascii=False,
#         indent=2)}"
# )

print(f"\n=== SAVE TRANSLATABLES TO PROGRESS FOLDER ===")

save_translatables(translatables)
loaded_translatables = load_translatables()

print(f"loaded {len(loaded_translatables)} translatables. Expected: {translatables_imported_cnt}")
print(
    f"DEBUG - first translatable identical: "
    f"{translatables[0] == loaded_translatables[0]}"
)
print(
    f"DEBUG - last translatable identical: "
    f"{translatables[-1] == loaded_translatables[-1]}"
)

print(f"\n=== APPLY TRANSLATIONS ===")

apply_translations(
    babele_json,
    loaded_translatables,
    {
        0: "[FIRST TRANSLATED]",
        1: "[LAST TRANSLATED]"
    } # just a mock-up for now
)
# print(
#     f"DEBUG - Result of FIRST translation at Babele path: {loaded_translatables[0]["path"]}"
#     f"\n=> {get_json_element(babele_json, loaded_translatables[0]["path"])}"
#     f"\nDEBUG - Result of LAST translation at Babele path: {loaded_translatables[1]["path"]}"
#     f"\n=> {get_json_element(babele_json, loaded_translatables[1]["path"])}"
# )
# print(f"DEBUG - Final translation:"
#     f"\n{json.dumps(
#         babele_json,
#         ensure_ascii=False,
#         indent=2)}"
# )

print(f"\n=== SAVE FINAL Babele FIILE ===")
save_babele_output(babele_json)


# ------------------------------------------------------------
# Stop global timer
# ------------------------------------------------------------

global_timer_end = time.perf_counter()
print(f"\n=== TOTAL processing duration: {global_timer_end - global_timer_start:.2f} seconds ===")
