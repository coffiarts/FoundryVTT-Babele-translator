from config import *
import json
from openai import OpenAI

# ------------------------------------------------------------
# Function: Load data (as list) from JSON input_file (path)
# Return it as data
# ------------------------------------------------------------
def load_json_input(input_file):

    with input_file.open(
            "r",
            encoding="utf-8"
    ) as file:

        data = json.load(file)


    print(f"Loaded {len(data)} elements from {input_file}")

    return data


# ----------------------------------------------------------------------------------
# Save data (as list) to JSON output_file (path)
# ----------------------------------------------------------------------------------
def save_json_output(data, output_file):

    json_string = json.dumps(
        data,
        ensure_ascii=False,
        indent=2
    )

    with open(
            output_file,
            "w",
            encoding="utf-8"
    ) as file:

        file.write(json_string)

    print(f"File written to: {output_file} with {len(json_string)} chars")


# ------------------------------------------------------------
# Get JSON element
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
# Function: Extract Translatables from Babele input data
# ------------------------------------------------------------
def extract_translatables_from_babele(input, translatables, current_path):

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

                extract_translatables_from_babele(
                    item,
                    translatables,
                    current_path+ [key]
                )

    elif isinstance(input, list):

        for index, item in enumerate(input):

            extract_translatables_from_babele(
                item,
                translatables,
                current_path + [index]
            )


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
# Function: Apply translations (all at once)
# ------------------------------------------------------------
def apply_translations(
        babele_json,
        translatables,
        translations):

    for id, translation in translations.items():
        set_json_element(babele_json, translatables[id]["path"], translation)

    # TODO - apply any "on-top"" translations (like translator's watermark etc.)



