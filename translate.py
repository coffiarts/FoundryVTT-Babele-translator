import time
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

print("\n")
print(f"===========================================================")
print(f"=== PROCESSING FILE: {INPUT_FILE}")
print(f"===========================================================")

print(f"\n=== CONFIGURATION ===")
print(f"{to_multiline_text(get_resume_relevant_config())}")


try:

    run_mode = determine_run_mode()
    print(f"Run mode: {run_mode}")

except ValueError as e:

    print(f"{RED}❌ {e.args[0]}{RESET}")
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

        progress_info, resume_batch = validate_progress_info()
        starting_text = load_translatables_for_batch(resume_batch, limit=1)[0]["original"][:100]
        print(f"Resuming from Batch with id={resume_batch["id"]} [{resume_batch["status"]}] - starting with: \"{starting_text} ...\"")

    except ValueError as e:

        print(f"{RED}❌ {e.args[0]}{RESET}")
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

    print(f"{RED}❌ {details["error"]}{RESET}")
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

print(f"\n=== BEGIN BATCH PROCESSING LOOP ... ===")

translations_with_placeholders = {}

integrity_errors = []

translations_final = {}

for batch in batches:

    # In RUN_MODE = RESUME, skip all Batches until current batch is the resume_batch
    if run_mode == RESUME:

        if batch != resume_batch:
            continue

        else:
            resume_batch = None


    batch["status"] = PROCESSING

    # ---------------------------------------------------
    # IDENTIFY BATCH-RELATED TERMINOLOGY
    # just a placeholder for now
    # ---------------------------------------------------

    batch_specific_terminology = "" # postponed, still empty

    instructions = (
            TRANSLATION_INSTRUCTIONS
            + "\n\n"
            + "=== TERMINOLOGY DATABASE ===\n"
            + batch_specific_terminology
            + "\n\n"
            + "=== END TERMINOLOGY DATABASE ===\n"
    )


    # ---------------------------------------------------
    # ASSEMBLE BATCH PAYLOAD
    # ---------------------------------------------------

    print(f"\n=== ASSEMBLE BATCH PAYLOAD ===")

    batch_payload = []

    batch_translatables = (
        load_translatables_for_batch(
        batch,
        with_placeholders=True
    ))

    print(f"Batch {batch['id'] + 1}/{len(batches)}: {len(batch_translatables)} translatables loaded.")

    # -------
    # Tests:
    # -------
    test_assemble_batch_payload(batch, batch_translatables)


    # ---------------------------------------------------
    # BEGIN TRANSLATABLES LOOP ...
    # ---------------------------------------------------
    for translatable in batch_translatables:

        batch_payload.append({
            "id": translatable["id"],
            "text": translatable["original"]
        })

    batch_payload_chars = total_char_count(batch_payload, "text")
    print(f"Batch {batch["id"] + 1}/{len(batches)}: Payload assembled wth {batch_payload_chars} chars")

    # ---------------------------------------------------
    # ... END OF TRANSLATABLES LOOP
    # ---------------------------------------------------

    # ---------------------------------------------------
    # PREPARE API REQUEST
    # ---------------------------------------------------

    api_key = Path(
        "local_secret_do_not_commit/openai_api_key.txt"
    ).read_text(
        encoding="utf-8"
    ).strip()

    client = OpenAI(
        api_key=api_key
    )


    # ---------------------------------------------------
    # TRANSLATE BATCH
    # ---------------------------------------------------

    print(f"\n=== TRANSLATE BATCH {batch['id'] + 1}/{len(batches)} ===")

    api_timer_start = time.perf_counter()

    response = client.responses.create(
        model = LLM_MODEL,
        instructions = instructions,
        input = json.dumps(
            batch_payload,
            ensure_ascii=False
        )
    )

    try:

        translated_payload = json.loads(
            response.output_text
        )

    except Exception as e:

        post_mortem_dump(
            title = "FATAL ERROR",
            details = (
                f"{type(e).__name__}\n"
                f"{str(e)}"
            ),
            response_metadata = None,
            raw_response = response.output_text,
            batch_payload = batch_payload,
            translations_with_placeholders = translations_with_placeholders,
            integrity_errors = integrity_errors
        )

        raise


    api_timer_end = time.perf_counter()

    print(
        f"Batch {batch["id"] + 1}/{len(batches)} API duration: "
        f"{api_timer_end - api_timer_start:.2f} seconds"
    )

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

    # mockup!
    translations_final = {
        0: "[FIRST TRANSLATED]",
        1: "[LAST TRANSLATED]"
    }


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
    translations_final
)
print(f"{len(translations_final)} translations applied to original Babele data.")

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

