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

if MOCK_API_CALL:
    print(f"\n{YELLOW}=== MOCK MODE IS ON ===")
    print(f"API Calls to the remote LLM are only simulated!")
    print(f"For real processing change parameter MOCK_API_CALL to False in config.py{RESET}")

print(f"\n=== CONFIGURATION ===")
print(f"{to_multiline_text(get_resume_relevant_config())}")


try:

    run_mode = determine_run_mode()
    print(f"{YELLOW}Run mode: {run_mode}{RESET}")

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
test_save_to_file(translatables, loaded_translatables)

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
loaded_translatables_with_placeholders = load_translatables(with_placeholders=True)
test_save_to_file(translatables_with_placeholders, loaded_translatables_with_placeholders)
loaded_placeholders = load_placeholders()
test_save_to_file(placeholders, loaded_placeholders)

# ---------------------------------------------------
# BUILD BATCHES
# ---------------------------------------------------

print(f"\n=== BUILD BATCHES ===")

try:

    batches = build_batches(translatables_with_placeholders)

    # IMPORTANT: In Resume mode, we need to preserve any batch status from the preceeding run
    if run_mode == RESUME:
        for batch in batches:
            batch["status"] = progress_info["batches"][batch["id"]]["status"]

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
loaded_batches = load_batches()
test_save_to_file(batches, loaded_batches)

# ---------------------------------------------------
# BEGIN BATCH PROCESSING LOOP ...
# ---------------------------------------------------

print(f"\n=== BEGIN BATCH PROCESSING LOOP ... ===")

translations_with_placeholders = []
placeholder_translation_errors = []
translations_final = {} #must be a dict, because it is used like a key-based lookup later

# Pick up any existing translations from previous run (important for RESUME and MOCK MODE)
if TRANSLATIONS_FINAL_FILE.exists():

    translations_final = load_translations_final()
    print(f"Picked up {len(translations_final)} translations from previous run:")
    print(f"{
        to_multiline_text(
            input=translations_final,
            value_char_limit=50
        )}")


for batch in batches:

    # In RUN_MODE = RESUME, skip all Batches until current batch is the resume_batch
    if run_mode == RESUME:

        if resume_batch is not None and batch != resume_batch:

            print(f"\n{GREEN}=== BATCH {batch['id'] + 1}/{len(batches)} SKIPPED (already completed) ==={RESET}")
            continue

        else:

            resume_batch = None

    # ---------------------------------------------------
    # ENRICH INSTRUCTIONS WITH TERMINOLOGY
    # ---------------------------------------------------

    batch_specific_terminology = "" # postponed, just a placeholder for now

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

    if not MOCK_API_CALL:

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

    batch["status"] = PROCESSING
    save_batch(batch, batches, progress_info)

    print(f"\n=== TRANSLATION OF BATCH {batch['id'] + 1}/{len(batches)}: [{batch["status"]}]... ===")

    if MOCK_API_CALL:

        print(f"\n{YELLOW}=== MOCK MODE IS ON ===")
        print(f"Translations are just copies of the input text.{RESET}\n")

        for translatable in batch_payload:
            translations_with_placeholders.append({
                "id": translatable["id"],
                "translation": translatable["text"]
            })

    else:

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

            new_translations = json.loads(response.output_text)

            for new_translation in new_translations:
                translations_with_placeholders.append(new_translation)

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
                integrity_errors = placeholder_translation_errors
            )

            raise


        api_timer_end = time.perf_counter()

        print(
            f"Batch {batch["id"] + 1}/{len(batches)} API duration: "
            f"{api_timer_end - api_timer_start:.2f} seconds"
        )

    # ---------------------------------------------------
    # SAVE TRANSLATIONS (STILL WITH PLACEHOLDERS)
    # ---------------------------------------------------

    save_json_output(translations_with_placeholders, TRANSLATIONS_WITH_PLACEHOLDERS_FILE)

    # -------
    # Tests:
    # -------
    loaded_translations_with_placeholders = load_json_input(TRANSLATIONS_WITH_PLACEHOLDERS_FILE)
    test_save_to_file(translations_with_placeholders, loaded_translations_with_placeholders)


    # ---------------------------------------------------
    # SET BATCH & PROGRESS INFO TO COMPLETED
    # ---------------------------------------------------

    batch["status"] = COMPLETED
    save_batch(batch, batches, progress_info)
    print(f"\n{GREEN}=== ... TRANSLATION OF BATCH {batch["id"] + 1}/{len(batches)}: [{batch["status"]}] ==={RESET}")

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
    for translation_with_placeholders in translations_with_placeholders:
        translations_final[translation_with_placeholders["id"]] = translation_with_placeholders["translation"]

    if (len(translations_final) > 0):
        translations_final[0] = "FIRST TRANSLATION"

    if (len(translations_final) > 1):
        translations_final[1] = "SECOND TRANSLATION"

    # ---------------------------------------------------
    # SAVE FINAL TRANSLATIONS TO PROGRESS FOLDER
    # just a placeholder for now
    # ---------------------------------------------------

    save_json_output(translations_final, TRANSLATIONS_FINAL_FILE)


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

if MOCK_API_CALL:

    print(f"\n{YELLOW}=== MOCK MODE IS ON! THIS WAS ONLY A SIMULATION! ==={RESET}")

else:

    print(f"\n{GREEN}=== PROCESS COMPLETED SUCCESSFULLY ==={RESET}")

