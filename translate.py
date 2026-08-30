import time
from shared_functions import *

# -------------------------------------------------------------------------------------------------------
# This controls the main process of translating a Babele input file:
# - import from Babele file
# - extract translatables
# - build batches for processing
# - translate (using an external LLM)
# - validate
# - export to a new Babele file
#
# The input file to process, plus any other relevant parameters can be configured in config.py
# -------------------------------------------------------------------------------------------------------

print(
    f"\n=== PROCESSING FILE: {INPUT_FILE} ===\n"
    f"Batch Size: max. {MAX_BATCH_SIZE} chars (excluding instructions & terminology)"
)

global_timer_start = time.perf_counter()


# ---------------------------------------------------
# IMPORT INPUT FILE
# ---------------------------------------------------

print(f"\n=== IMPORT INPUT FILE (JSON exported from FoundryVTT) ===")

babele_data = load_json_input(INPUT_FILE)


# ---------------------------------------------------
# EXTRACT TRANSLATABLES
# ---------------------------------------------------

print(f"\n=== EXTRACT TRANSLATABLES ===")

translatables = []
# Recursively fill translatables with matching nodes in babele_data
extract_translatables_from_babele(
    input=babele_data,
    translatables=translatables,
    current_path=[]
)
print(f"Extracted translatables: {len(translatables)}")
# print(f"DEBUG - Content of first 10 translatables:"
#     f"\n{json.dumps(
#         translatables[:10],
#         ensure_ascii=False,
#         indent=2)}"
# )


# ---------------------------------------------------
# SAVE TRANSLATABLES TO PROGRESS FOLDER
# ---------------------------------------------------

print(f"\n=== SAVE TRANSLATABLES TO PROGRESS FOLDER ===")

save_json_output(
    translatables,
    TRANSLATABLES_FILE
)
loaded_translatables = load_json_input(TRANSLATABLES_FILE)

print(f"Expected: {len(translatables)}")
# print(
#     f"DEBUG - first translatable identical: "
#     f"{translatables[0] == loaded_translatables[0]}"
# )
# print(
#     f"DEBUG - last translatable identical: "
#     f"{translatables[-1] == loaded_translatables[-1]}"
# )


# ---------------------------------------------------
# BUILD BATCHES
# ---------------------------------------------------

print(f"\n=== BUILD BATCHES ===")

batches = build_batches(translatables)

# print(
#     f"DEBUG - First 10 batches: "
#     f"{json.dumps(
#     batches[:10],
#     indent=2,
#     ensure_ascii=False)}"
# )


# ---------------------------------------------------
# SAVE BATCHES TO PROGRESS FOLDER
# ---------------------------------------------------

print(f"\n=== SAVE BATCHES TO PROGRESS FOLDER ===")

save_json_output(
    batches,
    BATCHES_FILE
)

loaded_batches = load_batches()
print(f"Expected: {len(batches)}")
print(
    f"DEBUG - first batch identical: "
    f"{batches[0] == loaded_batches[0]}"
)

print(
    f"DEBUG - last batch identical: "
    f"{batches[-1] == loaded_batches[-1]}"
)

# ---------------------------------------------------
# TRANSLATE
# just a mock-up for now
# ---------------------------------------------------

translations = {
    0: "[FIRST TRANSLATED]",
    1: "[LAST TRANSLATED]"
}


# ---------------------------------------------------
# APPLY TRANSLATIONS TO Babele
# ---------------------------------------------------

print(f"\n=== APPLY TRANSLATIONS TO Babele ===")

apply_translations(
    babele_data,
    loaded_translatables,
    translations
)
print(f"{len(translations)} translations applied to original Babele data.")

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


# ---------------------------------------------------
# SAVE FINAL Babele FIILE
# ---------------------------------------------------

print(f"\n=== SAVE FINAL Babele FIILE ===")
save_json_output(babele_data, OUTPUT_FILE)


# ------------------------------------------------------------
# Stop global timer
# ------------------------------------------------------------

global_timer_end = time.perf_counter()
print(f"\n=== TOTAL processing duration: {global_timer_end - global_timer_start:.2f} seconds ===")
