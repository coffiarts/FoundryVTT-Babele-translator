import time
from unit_tests import *

# -------------------------------------------------------------------------------------------------------
# This controls the main process of translating a Babele input file:
# - import from Babele file
# - extract translatables
# - protect translatables by replacing Foundry specific syntax with placeholders
# - build batches for processing
# - extract master terminology from the input (or reuse an existing one)
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
    print(f"For real processing change parameter MOCK_API_CALL to False in config.py{COLOR_RESET}")

# ---------------------------------------------------
# CONFIGURATION INFO AND PROMPTS
# ---------------------------------------------------
print(f"\n=== CONFIGURATION ===")

print(f"{to_multiline_text(get_resume_relevant_config())}")

REBUILD_TERMINOLOGY_IF_EXISTS = prompt_for_terminology_rebuild()

try:

    run_mode = determine_run_mode()
    print(f"\n{YELLOW}Run mode: {run_mode}{COLOR_RESET}\n")

except ValueError as e:

    print(f"{RED}❌ {e.args[0]}{COLOR_RESET}")
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

        if resume_batch is not None:
            starting_text = load_translatables_for_batch(resume_batch, limit=1)[0]["original"][:100]
            print(f"Resuming from Batch with id={resume_batch["id"]} [Terminology: {resume_batch[TERMINOLOGY_STATUS]} / Translation: {resume_batch[TRANSLATION_STATUS]}] - starting with: \"{starting_text} ...\"")

    except ValueError as e:

        print(f"{RED}❌ {e.args[0]}{COLOR_RESET}")
        exit()


# ---------------------------------------------------
# IMPORT INPUT FILE
# ---------------------------------------------------
print(f"\n=== IMPORT INPUT FILE: {INPUT_FILE} ===")
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

    # IMPORTANT: In Resume mode, we need to preserve any batch status from the preceding run
    if run_mode == RESUME:
        for batch in batches:
            batch[TERMINOLOGY_STATUS] = progress_info["batches"][batch["id"]][TERMINOLOGY_STATUS]
            batch[TRANSLATION_STATUS] = progress_info["batches"][batch["id"]][TRANSLATION_STATUS]

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

    print(f"{RED}❌ {details["error"]}{COLOR_RESET}")
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
# BUILD OR REUSE MASTER TERMINOLOGY
# ---------------------------------------------------
master_terminology_raw = {
    "terms": []
}

if TERMINOLOGY_FILE.exists() and not REBUILD_TERMINOLOGY_IF_EXISTS:

    master_terminology = load_json_input(
        TERMINOLOGY_FILE
    )

    # We're skipping terminology completely, so we need to tell process control (progress-info) that everything's completed here.
    # Otherwise, there would be an abort due to "missing terminology" later
    for batch in batches:
        batch[TERMINOLOGY_STATUS] = COMPLETED

    save_batches(
        batches,
        progress_info
    )

    print(f"\n{MAGENTA}=== REUSING EXISTING MASTER TERMINOLOGY ({len(master_terminology["terms"])} entries) ==={COLOR_RESET}")

else:

    print(f"\n=== BUILDING FRESH MASTER TERMINOLOGY ... ===")


    # ---------------------------------------------------
    # START TERMINOLOGY BATCH LOOP ...
    # ---------------------------------------------------
    for batch in batches:

        batch[TERMINOLOGY_STATUS] = PROCESSING
        save_batch(batch, batches, progress_info)

        batch_translatables = load_translatables_for_batch(
            batch,
            with_placeholders=False
        )

        batch_payload = "\n\n".join(
            translatable["original"]
            for translatable in batch_translatables
        )

        print(
            f"Terminology Batch {batch['id'] + 1}/{len(batches)} "
            f"[{len(batch_payload)} chars]"
        )

        if MOCK_API_CALL:

            print(f"\n{YELLOW}=== MOCK MODE IS ON ===")
            print(f"Terminology will be empty.{COLOR_RESET}\n")

            batch[TERMINOLOGY_STATUS] = COMPLETED
            save_batch(batch, batches, progress_info)

        else:

            api_timer_start = time.perf_counter()

            try:

                response = client.responses.create(
                    model = LLM_MODEL,
                    instructions = TERMINOLOGY_INSTRUCTIONS,
                    input = json.dumps(
                        batch_payload,
                        ensure_ascii=False
                    ),
                    text=TERMINOLOGY_OUTPUT_STRUCTURE
                )

                terminology_response = json.loads(response.output_text)
                # print(f"DEBUG - terminology response: {to_prettified_json(terminology_response)}")
                master_terminology_raw["terms"].extend(terminology_response["terms"])

            except Exception as e:

                batch[TERMINOLOGY_STATUS] = FAILED
                save_batch(batch, batches, progress_info)

                post_mortem_dump(
                    title = "FATAL ERROR",
                    details = (
                        f"{type(e).__name__}\n"
                        f"{str(e)}"
                    ),
                    response_metadata = None,
                    raw_response = response.output_text,
                    batch_payload = batch_payload,
                    master_terminology = master_terminology_raw
                )

                raise


            api_timer_end = time.perf_counter()

            print(
                f"Batch {batch["id"] + 1}/{len(batches)} - API duration: "
                f"{BLUE}{api_timer_end - api_timer_start:.2f} seconds{COLOR_RESET}"
            )

        save_json_output(
            master_terminology_raw,
            TERMINOLOGY_FILE
        )

        batch[TERMINOLOGY_STATUS] = COMPLETED
        save_batch(batch, batches, progress_info)


    # ---------------------------------------------------
    # ... END OF TERMINOLOGY BATCH LOOP
    # ---------------------------------------------------
    master_terminology = deduplicate_terminology(
        master_terminology_raw
    )

    duplicate_cnt = len(master_terminology_raw["terms"]) - len(master_terminology["terms"])

    if (duplicate_cnt > 0):
        print(f"{YELLOW}Eliminated {duplicate_cnt} duplicate(s){COLOR_RESET} from Terminology.")

    save_json_output(
        master_terminology,
        TERMINOLOGY_FILE
    )

    print(f"{GREEN}Saved {len(master_terminology["terms"])} entries in Master Terminology: {TERMINOLOGY_FILE}{COLOR_RESET}")


# ---------------------------------------------------
# BEGIN BATCH TRANSLATION LOOP ...
# ---------------------------------------------------
print(f"\n=== BEGIN BATCH PROCESSING LOOP ... ===")

# In Resume mode with all Translation Batches already completed,
# reconstruct translations_with_placeholders from file and skip
# directly to post-processing.

if run_mode == RESUME and resume_batch is None:

    print(
        f"{GREEN}All Translation processing already completed."
        f" Continuing with post-processing only.{COLOR_RESET}"
    )

    translations_with_placeholders = load_json_input(
        TRANSLATIONS_WITH_PLACEHOLDERS_FILE
    )

else:

    # ---------------------------------------------------
    # BEGIN BATCH TRANSLATION LOOP
    # ---------------------------------------------------

    translations_with_placeholders = []

    for batch in batches:

        # ---------------------------------------------------
        # ABORT IF TERMINOLOGY IS MISSING
        # ---------------------------------------------------
        if batch[TERMINOLOGY_STATUS] != COMPLETED:

            raise ValueError(
                "❌ Master terminology has not been completed yet. "
                "Translation cannot start."
            )

        # In RUN_MODE = RESUME, skip all Batches until current batch is the resume_batch
        if run_mode == RESUME:

            if resume_batch is not None and batch["id"] != resume_batch["id"]:

                already_translated = load_translations_for_batch(batch)
                translations_with_placeholders.extend(already_translated)

                print(f"\n{GREEN}=== BATCH {batch['id'] + 1}/{len(batches)} SKIPPED (already completed) ==={COLOR_RESET}")
                print(f"Resusint {len(already_translated)} already translated texts.")
                continue

            else:

                resume_batch = None


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


        # ---------------------------------------------------
        # ... END OF TRANSLATABLES LOOP
        # ---------------------------------------------------
        batch_payload_chars = total_char_count(batch_payload, "text")
        print(f"Batch {batch["id"] + 1}/{len(batches)}: Payload assembled wth {batch_payload_chars} chars")


        # ---------------------------------------------------
        # ENRICH INSTRUCTIONS WITH TERMINOLOGY
        # ---------------------------------------------------
        print(f"\n=== ENRICH INSTRUCTIONS WITH TERMINOLOGY ... ===")

        # Extract batch-specific terminology from Master Terminology
        batch_text = "\n".join(
            translatable["original"]
            for translatable in batch_translatables
        )

        batch_text_lower = batch_text.lower()

        batch_relevant_terms = [
            term
            for term in master_terminology["terms"]
            if term["original"].lower() in batch_text_lower
        ]

        print(f"Found {len(batch_relevant_terms)} relevant terms in Master Terminology.")

        batch_specific_terminology = {
            "terms": batch_relevant_terms
        }

        batch_specific_terminology_json = to_prettified_json(
            batch_specific_terminology
        )

        instructions = (
                TRANSLATION_INSTRUCTIONS
                + "\n\n"
                + "=== TERMINOLOGY DATABASE ===\n"
                + batch_specific_terminology_json
                + "\n\n"
                + "=== END TERMINOLOGY DATABASE ===\n"
        )


        # ---------------------------------------------------
        # TRANSLATE BATCH
        # ---------------------------------------------------
        batch[TRANSLATION_STATUS] = PROCESSING
        save_batch(batch, batches, progress_info)

        print(f"\n=== TRANSLATION OF BATCH {batch['id'] + 1}/{len(batches)}: [{batch[TRANSLATION_STATUS]}]... ===")

        if MOCK_API_CALL:

            print(f"\n{YELLOW}=== MOCK MODE IS ON ===")
            print(f"Translations are just copies of the input text.{COLOR_RESET}\n")

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

                print(f"\n=== COMPLETENESS CHECK FOR BATCH {batch['id'] + 1}/{len(batches)}... ===")
                verify_translation_completeness(batch, len(batches), batch_payload, new_translations)
                print(f"... completeness check: {GREEN}PASSED{COLOR_RESET}\n")

                translations_with_placeholders.extend(new_translations)

            except Exception as e:

                batch[TRANSLATION_STATUS] = FAILED
                save_batch(batch, batches, progress_info)

                print(f"{RED}{e.args[0]}{COLOR_RESET}")

                post_mortem_dump(
                    title = "FATAL ERROR",
                    details = (
                        f"{type(e).__name__}\n"
                        f"{str(e)}"
                    ),
                    response_metadata = None,
                    raw_response = response.output_text,
                    batch_payload = batch_payload,
                    translations_with_placeholders = translations_with_placeholders
                )

                raise


            api_timer_end = time.perf_counter()

            print(
                f"Batch {batch["id"] + 1}/{len(batches)} API duration: "
                f"{BLUE}{api_timer_end - api_timer_start:.2f} seconds{COLOR_RESET}"
            )


        # ---------------------------------------------------
        # SAVE TRANSLATIONS (STILL WITH PLACEHOLDERS)
        # ---------------------------------------------------
        print(f"\n=== SAVING {len(translations_with_placeholders)} TRANSLATIONS (STILL WITH PLACEHOLDERS) ===")
        save_json_output(translations_with_placeholders, TRANSLATIONS_WITH_PLACEHOLDERS_FILE)

        # -------
        # Tests:
        # -------
        loaded_translations_with_placeholders = load_json_input(TRANSLATIONS_WITH_PLACEHOLDERS_FILE)
        test_save_to_file(translations_with_placeholders, loaded_translations_with_placeholders)


        # ---------------------------------------------------
        # SET BATCH & PROGRESS INFO TO COMPLETED
        # ---------------------------------------------------
        batch[TRANSLATION_STATUS] = COMPLETED
        save_batch(batch, batches, progress_info)
        print(f"\n{GREEN}=== ... TRANSLATION OF BATCH {batch["id"] + 1}/{len(batches)}: [{batch[TRANSLATION_STATUS]}] ==={COLOR_RESET}")


# ---------------------------------------------------
# ... END OF BATCH PROCESSING LOOP
# ---------------------------------------------------


# ---------------------------------------------------
# VALIDATE PLACEHOLDERS => REVIEW ITEMS
# ---------------------------------------------------
review_items = identify_review_items(
    translatables_with_placeholders,
    translations_with_placeholders
)
print(f"\n=== VALIDATE PLACEHOLDERS ===")

print(
    f"{GREEN if len(review_items) == 0 else YELLOW}"
    f"{len(review_items)} Placeholder translation issue(s) identified{COLOR_RESET}"
)


# ---------------------------------------------------
# SAVE REVIEW ITEMS
# ---------------------------------------------------
if (len(review_items) > 0):
    save_json_output(
        review_items,
        REVIEW_ITEMS_FILE
    )
else:
    delete_file(REVIEW_ITEMS_FILE)

if (len(review_items) > 0):
    print(
        f"{GREEN if len(review_items) == 0 else YELLOW}"
        f"Post-review item(s) written to {REVIEW_ITEMS_FILE}:\n"
        f"{to_prettified_json(review_items)}"
        f"{COLOR_RESET}"
    )


# ---------------------------------------------------
# REPLACE PLACEHOLDERS (Restore Foundry Syntax)
# ---------------------------------------------------
translations_final = {} #must be a dict, because it is used like a key-based lookup later

# Pick up any existing translations from previous run (important for RESUME and MOCK MODE)
if TRANSLATIONS_FINAL_FILE.exists():

    translations_final = load_translations_final()
    print(f"Picked up {len(translations_final)} translations from previous run:")
    # print(f"{
    # to_multiline_text(
    #     input=translations_final,
    #     value_char_limit=50
    # )}")


for translation_with_placeholders in translations_with_placeholders:

    restored_translation = restore_foundry_syntax(
        translation_with_placeholders["translation"],
        placeholders
    )

    translations_final[
        translation_with_placeholders["id"]
    ] = restored_translation


# ---------------------------------------------------
# SAVE FINAL TRANSLATIONS TO PROGRESS FOLDER
# just a placeholder for now
# ---------------------------------------------------
save_json_output(translations_final, TRANSLATIONS_FINAL_FILE)


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
print(f"\n=== TOTAL processing duration: {BLUE}{global_timer_end - global_timer_start:.2f} seconds{COLOR_RESET} ===")
print(f"\nFind the translated file here: {BLUE}{OUTPUT_FILE}{COLOR_RESET}")

if MOCK_API_CALL:

    print(f"\n{YELLOW}=== MOCK MODE IS ON! THIS WAS ONLY A SIMULATION! ==={COLOR_RESET}")

else:

    print(f"\n{GREEN}=== PROCESS COMPLETED SUCCESSFULLY ==={COLOR_RESET}")

