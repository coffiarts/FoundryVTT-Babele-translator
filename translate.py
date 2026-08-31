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
# INITIALIZE PROGRESS
# ---------------------------------------------------

print(f"\n=== INITIALIZE PROGRESS ===")

init_progress()
progress = load_json_input(PROGRESS_INFO_FILE)

print(f"Run config parameters: {progress["config"]}")


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

# -------
# Tests:
# -------
# print(f"DEBUG - Content of first 10 translatables:"
#     f"\n{stringify_json(translatables[:10])}"
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

# -------
# Tests:
# -------
print(f"UNIT TEST - Expected: {len(translatables)}")
color = test_result_color(len(translatables) == len(loaded_translatables))
print(
    f"UNIT TEST - Translatables count identical: "
    f"{color}{len(translatables) == len(loaded_translatables)}{RESET}"
)
# print(
#     f"DEBUG - first translatable identical: "
#     f"{translatables[0] == loaded_translatables[0]}"
# )
# print(
#     f"DEBUG - last translatable identical: "
#     f"{translatables[-1] == loaded_translatables[-1]}"
# )


# -----------------------------------------------------------------
# CREATE TRANSLATABLES WITH PLACEHOLDERS
# -----------------------------------------------------------------

print(f"\n=== CREATE TRANSLATABLES WITH PLACEHOLDERS (PROTECT FOUNDRY ELEMENTS) ===")

translatables_with_placeholders, placeholders = protect_with_placeholders(
    translatables
)

# ==================
# Tests:
# ==================
# all_text = "\n".join(
#     translatable["original"]
#     for translatable in translatables_with_placeholders
# )

# print(
#     f"DEBUG - All Placeholders:\n"
#     f"{to_prettified_json(placeholders)}"
# )
# print(
#     f"DEBUG - All Translatables with PLaceholders:\n"
#     f"{to_prettified_json([
#         translatable
#         for translatable in translatables_with_placeholders
#         if any(
#             placeholder in translatable["original"]
#             for placeholder in placeholders
#         )
#     ])}"
# )


# ---------------------------------------------------
# SAVE TRANSLATABLES WITH PLACEHOLDERS
# ---------------------------------------------------

print(f"\n=== SAVE TRANSLATABLES WITH PLACEHOLDERS TO PROGRESS FOLDER ===")

save_json_output(
    translatables_with_placeholders,
    TRANSLATABLES_WITH_PLACEHOLDERS_FILE
)

save_json_output(
    placeholders,
    PLACEHOLDERS_FILE
)

# -------
# Tests:
# -------
loaded_translatables_with_placeholders = load_translatables(with_placeholders=True)
print(f"UNIT TEST - Expected: {len(translatables)}")
color = test_result_color(len(translatables) == len(loaded_translatables_with_placeholders))
print(
    f"UNIT TEST - Translatables with Placeholders count identical: "
    f"{color}{len(translatables) == len(loaded_translatables_with_placeholders)}{RESET}"
)
loaded_placeholders = load_placeholders()
print(f"UNIT TEST - Expected: {len(placeholders)}")
color = test_result_color(len(placeholders) == len(loaded_placeholders))
print(
    f"UNIT TEST - Placeholder count identical: "
    f"{color}{len(placeholders) == len(loaded_placeholders)}{RESET}"
)


# ---------------------------------------------------
# BUILD BATCHES
# ---------------------------------------------------

print(f"\n=== BUILD BATCHES ===")

progress_info = load_json_input(PROGRESS_INFO_FILE)

try:

    batches = build_batches(translatables_with_placeholders)

    # Update ProgressInfo (batches will be saved later)
    progress_info["batches"] = batches
    save_json_output(data=progress_info, output_file=PROGRESS_INFO_FILE)

except ValueError as e:

    details = e.args[0]

    # Update ProgressInfo to register error
    progress_info["batches"] = details["batches"]
    save_json_output(data=progress_info, output_file=PROGRESS_INFO_FILE)

    # Also persist all hitherto known Batches in BATCHES_FILE right away (before aborting)
    # But we do not want to store the last failed batch here, so we pop it off first
    details["batches"].pop()
    save_json_output(data=details["batches"], output_file=BATCHES_FILE)

    # TODO: (optional): post-mortem dump

    raise

# -------
# Tests:
# -------
# print(
#     f"DEBUG - First 10 batches: "
#     f"{stringify_json(batches[:10])}"
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

# -------
# Tests:
# -------
print(f"UNIT TEST - Expected: {len(batches)}")
color = test_result_color(len(batches) == len(loaded_batches))
print(
    f"UNIT TEST - Batches count identical: "
    f"{color}{len(batches) == len(loaded_batches)}{RESET}"
)
# print(
#     f"DEBUG - first batch identical: "
#     f"{batches[0] == loaded_batches[0]}"
# )
#
# print(
#     f"DEBUG - last batch identical: "
#     f"{batches[-1] == loaded_batches[-1]}"
# )


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

# -------
# Tests:
# -------
# print(
#     f"DEBUG - Result of FIRST translation at Babele path: {loaded_translatables[0]["path"]}"
#     f"\n=> {get_json_element(babele_json, loaded_translatables[0]["path"])}"
#     f"\nDEBUG - Result of LAST translation at Babele path: {loaded_translatables[1]["path"]}"
#     f"\n=> {get_json_element(babele_json, loaded_translatables[1]["path"])}"
# )
# print(f"DEBUG - Final translation:"
#     f"\n{stringify_json(babele_data)}"
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
