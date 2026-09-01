import time
from shared_functions import *
from unit_tests import *

# -------------------------------------------------------------------------------------------------------
# This controls the main process of translating a Babele input file:
# - import from Babele file
# - extract translatables
# - protect translatables by replacing Foundry specific syntax with placeholders
# - build batches for processing
# - translate (using an external LLM)
# - validate
# - restore Foundry specific syntax from placeholders
# - reassemble
# - export to a new Babele file
#
# The input file to process, plus any other relevant parameters are configured in config.py
#
# Processing is automatically be resumed after aborts, given that some crucial config params haven't been changed
# -------------------------------------------------------------------------------------------------------

print(f"\n=== PROCESSING FILE: {INPUT_FILE} ===")

print(f"\n=== CONFIGURATION ===")
print(f"{to_multiline_text(get_resume_relevant_config())}")


try:

    run_mode = determine_run_mode()
    print(f"Run mode: {run_mode}")

except ValueError as e:

    print(f"{RED}{e.args[0]}{RESET}")
    exit()

global_timer_start = time.perf_counter()

if run_mode == NEW_RUN:

    # ---------------------------------------------------
    # Case 1: INITIALIZE PROGRESS
    # ---------------------------------------------------
    print(f"\n=== INITIALIZE PROGRESS ===")
    cleanup_progress_files()
    progress_info = init_progress_info()

else:

    # ---------------------------------------------------
    # Case 2: RESUME PROGRESS
    # ---------------------------------------------------
    try:

        progress_info, pickup_batch = validate_progress_info()
        starting_text = load_translatables_for_batch(pickup_batch, limit=1)[0]["original"][:100]
        print(f"Resuming from Batch with id={pickup_batch["id"]} [{pickup_batch["status"]}] - starting with: \"{starting_text} ...\"")

    except ValueError as e:

        print(f"{RED}{e.args[0]}{RESET}")
        exit()



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
test_extract_translatables_from_babele(translatables)

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
test_save_translatables(translatables, loaded_translatables)

# -----------------------------------------------------------------
# PROTECT TRANSLATABLES WITH PLACEHOLDERS
# -----------------------------------------------------------------

print(f"\n=== PROTECT TRANSLATABLES WITH PLACEHOLDERS (MASK FOUNDRY ELEMENTS) ===")

translatables_with_placeholders, placeholders = protect_with_placeholders(
    translatables
)

# ==================
# Tests:
# ==================
test_create_translatables_with_placeholders(translatables_with_placeholders)

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
test_save_translatables_with_placeholders(translatables, placeholders)

# ---------------------------------------------------
# BUILD BATCHES
# ---------------------------------------------------

print(f"\n=== BUILD BATCHES ===")

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

    # Also persist all hitherto known
    # Batches in BATCHES_FILE right away (before aborting)
    # But we do not want to store the last failed batch here, so we pop it off first
    details["batches"].pop()
    save_json_output(data=details["batches"], output_file=BATCHES_FILE)

    # TODO: (optional): post-mortem dump

    print(f"{RED}{details["error"]}{RESET}")
    exit()

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


# -------
# Tests:
# -------
test_save_batches(batches)

# ---------------------------------------------------
# BEGIN BATCH PROCESSING LOOP ...
# ---------------------------------------------------
for batch in batches:

    batch["status"] = PROCESSING

    # ---------------------------------------------------
    # IDENTIFY BATCH-RELATED TERMINOLOGY
    # just a placeholder for now
    # ---------------------------------------------------

    # postponed

    # ---------------------------------------------------
    # ASSEMBLE BATCH PAYLOAD
    # ---------------------------------------------------

    batch_payload = []

    batch_translatables = load_translatables_for_batch(
        batch,
        with_placeholders=True
    )

    # ---------------------------------------------------
    # BEGIN TRANSLATABLES LOOP ...
    # ---------------------------------------------------
    for translatable in batch_translatables:

        batch_payload.append({
            "id": translatable["id"],
            "text": translatable["original"]
        })


    # ---------------------------------------------------
    # ... END OF TRANSLATABLES LOOP
    # ---------------------------------------------------


    # ---------------------------------------------------
    # PREPARE TRANSLATION REQUEST
    # just a placeholder for now
    # ---------------------------------------------------

    # ---------------------------------------------------
    # TRANSLATE BATCH
    # just a mock-up for now
    # ---------------------------------------------------

    translations = {
        0: "[FIRST TRANSLATED]",
        1: "[LAST TRANSLATED]"
    }

    # ---------------------------------------------------
    # SAVE TRANSLATIONS (STILL WITH PLACEHOLDERS)
    # just a placeholder for now
    # ---------------------------------------------------

    # ---------------------------------------------------
    # PLACEHOLDER INTEGRITY CHECK => IDENTIFY POST-REVIEW ITEMS
    # just a placeholder for now
    # ---------------------------------------------------

    # ---------------------------------------------------
    # SAVE POST-REVIEW ITEMS
    # just a placeholder for now
    # ---------------------------------------------------

    # ---------------------------------------------------
    # REPLACE PLACEHOLDERS
    # just a placeholder for now
    # ---------------------------------------------------

    # ---------------------------------------------------
    # SAVE FINAL TRANSLATIONS TO PROGRESS FOLDER
    # just a placeholder for now
    # ---------------------------------------------------

    # ---------------------------------------------------
    # SET BATCH STATUS TO COMPLETED
    # just a placeholder for now
    # ---------------------------------------------------

# ---------------------------------------------------
# ... END OF BATCH PROCESSING LOOP
# ---------------------------------------------------

# ---------------------------------------------------
# COMBINE AND APPLY TRANSLATIONS TO Babele FILE
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

print(f"\n{GREEN}=== PROCESS COMPLETED SUCCESSFULLY ==={RESET}")

