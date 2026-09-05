import config
import shared_functions as fn
import unit_tests
import json
import time
from pathlib import Path
from openai import OpenAI

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

# ---------------------------------------------------
# ASK FOR WHICH FILE TO TRANSLATE
# ---------------------------------------------------
fn.prompt_for_input_file()

print("\n")
print(f"===========================================================")
print(f"=== PROCESSING FILE: {config.INPUT_FILE}")
print(f"===========================================================")

if config.MOCK_MODE:
    print(f"\n{config.YELLOW}=== MOCK MODE IS ON ===")
    print(f"API Calls to the remote LLM are only simulated!")
    print(f"For real processing change parameter MOCK_API_CALL to False in config.py{config.COLOR_RESET}")

# ---------------------------------------------------
# CONFIGURATION INFO INCL. USER-PROMPTED PARAMETERS
# ---------------------------------------------------
print(f"\n=== CONFIGURATION ===")

# Just as info: print out the resume-relevant params
print(f"{fn.to_multiline_text(fn.get_resume_relevant_config())}")

# If Terminology exists, ask the user what to do with it
fn.prompt_for_terminology_rebuild()


# ---------------------------------------------------
# DETERMINE RUN MODE
# ---------------------------------------------------
try:

    run_mode = fn.determine_run_mode()
    print(f"\n{config.YELLOW}Run mode: {run_mode}{config.COLOR_RESET}\n")

except ValueError as e:

    print(f"{config.RED}❌ {e.args[0]}{config.COLOR_RESET}")
    exit()


# ---------------------------------------------------
# INITIALIZE RUN, DEPENDING ON RUN MODE
# ---------------------------------------------------
if run_mode == config.NEW_RUN:

    # ---------------------------------------------------
    # Case 1: INITIALIZE PROGRESS
    # ---------------------------------------------------
    print(f"\n=== INITIALIZE PROGRESS ===")
    fn.cleanup_progress_files()
    progress_info = fn.init_progress_info()

elif run_mode == config.RESUME:

    # ---------------------------------------------------
    # Case 2: RESUME PROGRESS
    # ---------------------------------------------------
    try:

        progress_info, resume_batch = (
            fn.validate_progress_info()
        )

        fn.validate_resume_relevant_config(progress_info)

        if resume_batch is not None:
            starting_text = fn.load_translatables_for_batch(resume_batch, limit=1)[0]["original"][:100]
            print(f"Resuming from Batch with id={resume_batch["id"]} [Terminology: {resume_batch[config.TERMINOLOGY_STATUS]} / Translation: {resume_batch[config.TRANSLATION_STATUS]}] - starting with: \"{starting_text} ...\"")

    except ValueError as e:

        print(f"{config.RED}❌ {e.args[0]}{config.COLOR_RESET}")
        exit()

elif run_mode == config.POSTPROCESSING_ONLY:

    # Nothing to do here. This mode skips the whole first section
    # (INPUT PROCESSING & TRANSLATION) and joins in later in the
    # POST-PROCESSING section, where everything relevant will be initialized properly
    pass


# ------------------------------------------------------------
# Start global timer
# ------------------------------------------------------------
global_timer_start = time.perf_counter()


if run_mode != config.POSTPROCESSING_ONLY:

# ---------------------------------------------------
# START OF INPUT PROCESSING AND TRANSLATION
# ---------------------------------------------------
# Everything from here on is either the preparation of
# or the execution of batch-based processing of the
# translatable texts from the input file through an
# online translation service (LLM like OpenAI). It ends
# at the point where all raw translations have been
# received from the remote LLM and safely stored locally.
# It includes recoverability logic for handling
# unexpected errors, thus avoiding unnecessary remote calls.
# ---------------------------------------------------

    # ---------------------------------------------------
    # IMPORT INPUT FILE
    # ---------------------------------------------------
    print(f"\n=== IMPORT INPUT FILE: {config.INPUT_FILE} ===")
    input_data = fn.load_json_input(config.INPUT_FILE)

    # ---------------------------------------------------
    # EXTRACT TRANSLATABLES
    # ---------------------------------------------------
    print(f"\n=== EXTRACT TRANSLATABLES ===")

    translatables = []

    # Recursively fill translatables with matching nodes in babele_data
    fn.extract_translatables_from_input(
        input=input_data,
        translatables=translatables,
        current_path=[]
    )
    print(f"Extracted translatables: {len(translatables)}")

    # -------
    # Tests:
    # -------
    unit_tests.test_extract_translatables_from_babele(translatables)

    # ---------------------------------------------------
    # SAVE TRANSLATABLES TO PROGRESS FOLDER
    # ---------------------------------------------------
    print(f"\n=== SAVE TRANSLATABLES TO PROGRESS FOLDER ===")

    fn.save_json_output(
        translatables,
        config.TRANSLATABLES_FILE
    )

    loaded_translatables = fn.load_json_input(config.TRANSLATABLES_FILE)

    # -------
    # Tests:
    # -------
    unit_tests.test_save_to_file(translatables, loaded_translatables)

    # -----------------------------------------------------------------
    # PROTECT TRANSLATABLES WITH PLACEHOLDERS
    # -----------------------------------------------------------------
    print(f"\n=== PROTECT TRANSLATABLES WITH PLACEHOLDERS (MASK FOUNDRY ELEMENTS) ===")

    translatables_with_placeholders, placeholders = fn.protect_with_placeholders(
        translatables
    )

    # ==================
    # Tests:
    # ==================
    unit_tests.test_create_translatables_with_placeholders(translatables_with_placeholders)

    # ---------------------------------------------------
    # SAVE TRANSLATABLES WITH PLACEHOLDERS
    # ---------------------------------------------------
    print(f"\n=== SAVE TRANSLATABLES WITH PLACEHOLDERS TO PROGRESS FOLDER ===")

    fn.save_json_output(
        translatables_with_placeholders,
        config.TRANSLATABLES_WITH_PLACEHOLDERS_FILE
    )

    fn.save_json_output(
        placeholders,
        config.PLACEHOLDERS_FILE
    )

    # -------
    # Tests:
    # -------
    loaded_translatables_with_placeholders = fn.load_translatables(with_placeholders=True)
    unit_tests.test_save_to_file(translatables_with_placeholders, loaded_translatables_with_placeholders)
    loaded_placeholders = fn.load_placeholders()
    unit_tests.test_save_to_file(placeholders, loaded_placeholders)

    # ---------------------------------------------------
    # BUILD BATCHES
    # ---------------------------------------------------
    print(f"\n=== BUILD BATCHES ===")

    try:

        batches = fn.build_batches(translatables_with_placeholders)

        # IMPORTANT: In Resume mode, we need to preserve any batch status from the preceding run
        if run_mode == config.RESUME:
            for batch in batches:
                batch[config.TERMINOLOGY_STATUS] = progress_info["batches"][batch["id"]][config.TERMINOLOGY_STATUS]
                batch[config.TRANSLATION_STATUS] = progress_info["batches"][batch["id"]][config.TRANSLATION_STATUS]

        # Update ProgressInfo (batches will be saved later)
        progress_info["batches"] = batches
        fn.save_json_output(data=progress_info, output_file=config.PROGRESS_INFO_FILE)

    except ValueError as e:

        details = e.args[0]

        # Update ProgressInfo to register error
        progress_info["batches"] = details["batches"]
        fn.save_json_output(data=progress_info, output_file=config.PROGRESS_INFO_FILE)

        # Also persist all hitherto known
        # Batches in BATCHES_FILE right away (before aborting)
        # But we do not want to store the last failed batch here, so we pop it off first
        details["batches"].pop()
        fn.save_json_output(data=details["batches"], output_file=config.BATCHES_FILE)

        print(f"{config.RED}❌ {details["error"]}{config.COLOR_RESET}")
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

    fn.save_json_output(
        batches,
        config.BATCHES_FILE
    )

    # -------
    # Tests:
    # -------
    loaded_batches = fn.load_batches()
    unit_tests.test_save_to_file(batches, loaded_batches)

    # ---------------------------------------------------
    # PREPARE API REQUEST
    # ---------------------------------------------------
    if not config.MOCK_MODE:
        api_key = Path(
            "local_secret_do_not_commit/openai_api_key.txt"
        ).read_text(
            encoding="utf-8"
        ).strip()

        client = OpenAI(
            api_key=api_key
        )

    # ---------------------------------------------------
    # REUSE, CONTINUE OR BUILD MASTER TERMINOLOGY
    # ---------------------------------------------------

    if run_mode != config.RESUME and config.TERMINOLOGY_FILE.exists() and not config.REBUILD_TERMINOLOGY_IF_EXISTS:

        master_terminology = fn.load_json_input(
            config.TERMINOLOGY_FILE
        )

        # We're skipping terminology completely, so we need to tell process control (progress-info) that everything's completed here.
        # Otherwise, there would be an abort due to "missing terminology" later
        for batch in batches:
            batch[config.TERMINOLOGY_STATUS] = config.COMPLETED

        fn.save_batches(
            batches,
            progress_info
        )

        print(
            f"\n{config.MAGENTA}=== REUSING EXISTING TERMINOLOGY ({len(master_terminology["terms"])} entries) ==={config.COLOR_RESET}")

    else:

        if (run_mode == config.RESUME
                and config.TERMINOLOGY_FILE.exists()):

            master_terminology_raw = fn.load_json_input(
                config.TERMINOLOGY_FILE
            )

            print(f"\n=== CONTINUING TERMINOLOGY FROM LAST RUN ({len(master_terminology_raw["terms"])} entries) ... ==={config.COLOR_RESET}")

        else:

            master_terminology_raw = {
                "terms": []
            }

            print(f"\n=== BUILDING FRESH TERMINOLOGY ... ===")

        # ---------------------------------------------------
        # START TERMINOLOGY BATCH LOOP ...
        # ---------------------------------------------------
        for batch in batches:

            # if batch["id"] > 0:
            #     raise Exception("!!! TEST ABORT !!!")

            if (run_mode == config.RESUME
                    and batch[config.TERMINOLOGY_STATUS] == config.COMPLETED):

                print(
                    f"\n{config.GREEN}"
                    f"=== TERMINOLOGY BATCH "
                    f"{batch['id'] + 1}/{len(batches)} "
                    f"SKIPPED (already completed) ==="
                    f"{config.COLOR_RESET}"
                )

                continue

            batch[config.TERMINOLOGY_STATUS] = config.PROCESSING
            fn.save_batch(batch, batches, progress_info)

            batch_translatables = fn.load_translatables_for_batch(
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

            if config.MOCK_MODE:

                print(f"\n{config.YELLOW}=== MOCK MODE IS ON ===")
                print(f"Terminology will be empty.{config.COLOR_RESET}\n")

                batch[config.TERMINOLOGY_STATUS] = config.COMPLETED
                fn.save_batch(batch, batches, progress_info)

            else:

                api_timer_start = time.perf_counter()

                try:

                    response = client.responses.create(
                        model=config.LLM_MODEL,
                        instructions=config.TERMINOLOGY_INSTRUCTIONS,
                        input=json.dumps(
                            batch_payload,
                            ensure_ascii=False
                        ),
                        text=config.TERMINOLOGY_OUTPUT_STRUCTURE
                    )

                    terminology_response = json.loads(response.output_text)
                    # print(f"DEBUG - terminology response: {to_prettified_json(terminology_response)}")
                    master_terminology_raw["terms"].extend(terminology_response["terms"])

                except Exception as e:

                    batch[config.TERMINOLOGY_STATUS] = config.FAILED
                    fn.save_batch(batch, batches, progress_info)

                    fn.post_mortem_dump(
                        title="FATAL ERROR",
                        details=(
                            f"{type(e).__name__}\n"
                            f"{str(e)}"
                        ),
                        response_metadata=None,
                        raw_response=response.output_text,
                        batch_payload=batch_payload,
                        master_terminology=master_terminology_raw
                    )

                    raise

                api_timer_end = time.perf_counter()

                print(
                    f"Batch {batch["id"] + 1}/{len(batches)} - API duration: "
                    f"{config.BLUE}{api_timer_end - api_timer_start:.2f} seconds{config.COLOR_RESET}"
                )

            fn.save_json_output(
                master_terminology_raw,
                config.TERMINOLOGY_FILE
            )

            batch[config.TERMINOLOGY_STATUS] = config.COMPLETED
            fn.save_batch(batch, batches, progress_info)

        # ---------------------------------------------------
        # ... END OF TERMINOLOGY BATCH LOOP
        # ---------------------------------------------------
        master_terminology = fn.deduplicate_terminology(
            master_terminology_raw
        )

        duplicate_cnt = len(master_terminology_raw["terms"]) - len(master_terminology["terms"])

        if (duplicate_cnt > 0):
            print(f"{config.YELLOW}Eliminated {duplicate_cnt} duplicate(s){config.COLOR_RESET} from Terminology.")

        fn.save_json_output(
            master_terminology,
            config.TERMINOLOGY_FILE
        )

        print(
            f"{config.GREEN}Saved {len(master_terminology["terms"])} entries in Master Terminology: {config.TERMINOLOGY_FILE}{config.COLOR_RESET}")

    # ---------------------------------------------------
    # BEGIN BATCH TRANSLATION LOOP ...
    # ---------------------------------------------------
    print(f"\n=== BEGIN BATCH PROCESSING LOOP ... ===")

    # In Resume mode with all Translation Batches already completed,
    # reconstruct translations_with_placeholders from file and skip
    # directly to post-processing.

    if run_mode == config.RESUME and resume_batch is None:

        print(
            f"{config.GREEN}All Translation processing already completed."
            f" Continuing with post-processing only.{config.COLOR_RESET}"
        )

        translations_with_placeholders = fn.load_json_input(
            config.TRANSLATIONS_WITH_PLACEHOLDERS_FILE
        )

    else:

        # ---------------------------------------------------
        # BEGIN BATCH TRANSLATION LOOP
        # ---------------------------------------------------

        translations_with_placeholders = []

        for batch in batches:

            # if batch["id"] > 0:
            #     raise Exception("!!! TEST ABORT !!!")

            # ---------------------------------------------------
            # ABORT IF TERMINOLOGY IS MISSING
            # ---------------------------------------------------
            if batch[config.TERMINOLOGY_STATUS] != config.COMPLETED:
                raise ValueError(
                    "❌ Master terminology has not been completed yet. "
                    "Translation cannot start."
                )

            # In RUN_MODE = RESUME, skip all Batches until current batch is the resume_batch
            if run_mode == config.RESUME:

                if resume_batch is not None and batch["id"] != resume_batch["id"]:

                    already_translated = fn.load_translations_for_batch(batch)
                    translations_with_placeholders.extend(already_translated)

                    print(
                        f"\n{config.GREEN}=== BATCH {batch['id'] + 1}/{len(batches)} SKIPPED (already completed) ==={config.COLOR_RESET}")
                    print(f"Reusing {len(already_translated)} already translated texts.")
                    continue

                else:

                    resume_batch = None

            # ---------------------------------------------------
            # ASSEMBLE BATCH PAYLOAD
            # ---------------------------------------------------
            print(f"\n=== ASSEMBLE BATCH PAYLOAD ===")

            batch_payload = []

            batch_translatables = (
                fn.load_translatables_for_batch(
                    batch,
                    with_placeholders=True
                ))

            print(f"Batch {batch['id'] + 1}/{len(batches)}: {len(batch_translatables)} translatables loaded.")

            # -------
            # Tests:
            # -------
            unit_tests.test_assemble_batch_payload(batch, batch_translatables)

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
            batch_payload_chars = fn.total_char_count(batch_payload, "text")
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

            batch_specific_terminology_json = fn.to_prettified_json(
                batch_specific_terminology
            )

            instructions = (
                    config.TRANSLATION_INSTRUCTIONS
                    + "\n\n"
                    + "=== TERMINOLOGY DATABASE ===\n"
                    + batch_specific_terminology_json
                    + "\n\n"
                    + "=== END TERMINOLOGY DATABASE ===\n"
            )

            # ---------------------------------------------------
            # TRANSLATE BATCH
            # ---------------------------------------------------
            batch[config.TRANSLATION_STATUS] = config.PROCESSING
            fn.save_batch(batch, batches, progress_info)

            print(
                f"\n=== TRANSLATION OF BATCH {batch['id'] + 1}/{len(batches)}: [{batch[config.TRANSLATION_STATUS]}]... ===")

            if config.MOCK_MODE:

                print(f"\n{config.YELLOW}=== MOCK MODE IS ON ===")
                print(f"Translations are just copies of the input text.{config.COLOR_RESET}\n")

                for translatable in batch_payload:
                    translations_with_placeholders.append({
                        "id": translatable["id"],
                        "translation": translatable["text"]
                    })

            else:

                api_timer_start = time.perf_counter()

                response = client.responses.create(
                    model=config.LLM_MODEL,
                    instructions=instructions,
                    input=json.dumps(
                        batch_payload,
                        ensure_ascii=False
                    )
                )

                try:

                    new_translations = json.loads(response.output_text)

                    print(f"\n=== COMPLETENESS CHECK FOR BATCH {batch['id'] + 1}/{len(batches)}... ===")
                    fn.verify_translation_completeness(batch, len(batches), batch_payload, new_translations)
                    print(f"... completeness check: {config.GREEN}PASSED{config.COLOR_RESET}\n")

                    translations_with_placeholders.extend(new_translations)

                except Exception as e:

                    batch[config.TRANSLATION_STATUS] = config.FAILED
                    fn.save_batch(batch, batches, progress_info)

                    print(f"{config.RED}{e.args[0]}{config.COLOR_RESET}")

                    fn.post_mortem_dump(
                        title="FATAL ERROR",
                        details=(
                            f"{type(e).__name__}\n"
                            f"{str(e)}"
                        ),
                        response_metadata=None,
                        raw_response=response.output_text,
                        batch_payload=batch_payload,
                        translations_with_placeholders=translations_with_placeholders
                    )

                    raise

                api_timer_end = time.perf_counter()

                print(
                    f"Batch {batch["id"] + 1}/{len(batches)} API duration: "
                    f"{config.BLUE}{api_timer_end - api_timer_start:.2f} seconds{config.COLOR_RESET}"
                )

            # ---------------------------------------------------
            # SAVE TRANSLATIONS (STILL WITH PLACEHOLDERS)
            # ---------------------------------------------------
            print(f"\n=== SAVING {len(translations_with_placeholders)} TRANSLATIONS (STILL WITH PLACEHOLDERS) ===")
            fn.save_json_output(translations_with_placeholders, config.TRANSLATIONS_WITH_PLACEHOLDERS_FILE)

            # -------
            # Tests:
            # -------
            loaded_translations_with_placeholders = fn.load_json_input(config.TRANSLATIONS_WITH_PLACEHOLDERS_FILE)
            unit_tests.test_save_to_file(translations_with_placeholders, loaded_translations_with_placeholders)

            # ---------------------------------------------------
            # SET BATCH & PROGRESS INFO TO COMPLETED
            # ---------------------------------------------------
            batch[config.TRANSLATION_STATUS] = config.COMPLETED
            fn.save_batch(batch, batches, progress_info)
            print(
                f"\n{config.GREEN}=== ... TRANSLATION OF BATCH {batch["id"] + 1}/{len(batches)}: [{batch[config.TRANSLATION_STATUS]}] ==={config.COLOR_RESET}")

        # ---------------------------------------------------
        # ... END OF BATCH PROCESSING LOOP
        # ---------------------------------------------------

# ---------------------------------------------------
# START OF POST-PROCESSING
# ---------------------------------------------------
# Everything from here on is just post-processing of
# local files: No more Batch-preparation or remote
# API Calls involved. All the different scenarios come
# together at this junction point. So first of all,
# we want to reload everything processed so far once
# more from the files. This makes clear that every
# scenario now continues with the same persisted data from here.
# ---------------------------------------------------

input_data = fn.load_json_input(config.INPUT_FILE)

translatables = fn.load_json_input(config.TRANSLATABLES_FILE)

translatables_with_placeholders = fn.load_json_input(
    config.TRANSLATABLES_WITH_PLACEHOLDERS_FILE
)

translations_with_placeholders = fn.load_json_input(
    config.TRANSLATIONS_WITH_PLACEHOLDERS_FILE
)

placeholders = fn.load_placeholders()

translations_final = {} #must be a dict, because it is used like a key-based lookup later

# Pick up any existing translations from previous run.
# Important for RESUME and MOCK MODE, otherwise previous results would get lost!
if config.TRANSLATIONS_FINAL_FILE.exists():

    translations_final = fn.load_translations_final()
    print(f"Picked up {len(translations_final)} translations from previous run:")
    # print(f"{
    # to_multiline_text(
    #     input=translations_final,
    #     value_char_limit=50
    # )}")


# ---------------------------------------------------
# VALIDATE PLACEHOLDERS => REVIEW ITEMS
# ---------------------------------------------------
review_items = fn.identify_review_items(
    translatables_with_placeholders,
    translations_with_placeholders
)
print(f"\n=== VALIDATE PLACEHOLDERS ===")

print(
    f"{config.GREEN if len(review_items) == 0 else config.YELLOW}"
    f"{len(review_items)} Placeholder translation issue(s) identified{config.COLOR_RESET}"
)


# ---------------------------------------------------
# SAVE REVIEW ITEMS
# ---------------------------------------------------
if (len(review_items) > 0):
    fn.save_json_output(
        review_items,
        config.REVIEW_ITEMS_FILE
    )
else:
    fn.delete_file(config.REVIEW_ITEMS_FILE)

if (len(review_items) > 0):
    print(
        f"{config.GREEN if len(review_items) == 0 else config.YELLOW}"
        f"Post-review item(s) written to {config.REVIEW_ITEMS_FILE}:\n"
        f"{fn.to_prettified_json(review_items)}"
        f"{config.COLOR_RESET}"
    )


# ---------------------------------------------------
# REPLACE PLACEHOLDERS (Restore Foundry Syntax)
# ---------------------------------------------------
for translation_with_placeholders in translations_with_placeholders:

    restored_translation = fn.restore_foundry_syntax(
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
fn.save_json_output(translations_final, config.TRANSLATIONS_FINAL_FILE)


# ---------------------------------------------------
# COMBINE AND APPLY TRANSLATIONS TO Babele FILE
# ---------------------------------------------------
print(f"\n=== APPLY TRANSLATIONS TO Babele ===")

fn.apply_translations(
    input_data,
    translatables,
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
fn.save_json_output(input_data, config.OUTPUT_FILE)


# ------------------------------------------------------------
# Stop global timer
# ------------------------------------------------------------
global_timer_end = time.perf_counter()
print(f"\n=== TOTAL processing duration: {config.BLUE}{global_timer_end - global_timer_start:.2f} seconds{config.COLOR_RESET} ===")
print(f"\nFind the translated file here: {config.BLUE}{config.OUTPUT_FILE}{config.COLOR_RESET}")

if config.MOCK_MODE:

    print(f"\n{config.YELLOW}=== MOCK MODE IS ON! THIS WAS ONLY A SIMULATION! ==={config.COLOR_RESET}")

else:

    print(f"\n{config.GREEN}=== PROCESS COMPLETED SUCCESSFULLY ==={config.COLOR_RESET}")

