import config
import shared_functions as fn
import json
import time
from datetime import datetime
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

# ---------------------------------------------------
# START OF PROCESSING FILE
# ---------------------------------------------------
print(fn.log_header(f"PROCESSING FILE: {config.INPUT_FILE}"))
print(fn.log_header(f"LANGUAGES: {config.SOURCE_LANGUAGE["name"]} => {config.TARGET_LANGUAGE["name"]}"))

if config.MOCK_MODE:
    print(fn.log_header(f"MOCK MODE IS ON! API Calls to the remote LLM are only simulated.", color=config.YELLOW))

# ---------------------------------------------------
# CONFIGURATION INFO INCL. USER-PROMPTED PARAMETERS
# ---------------------------------------------------
print(fn.log_header("CONFIGURATION"))

# Just as info: print out the resume-relevant params
print(f"{fn.to_multiline_text(fn.get_resume_relevant_config())}")

# If Terminology exists, ask the user what to do with it
fn.prompt_for_terminology_rebuild()

# ---------------------------------------------------
# DETERMINE RUN MODE
# ---------------------------------------------------
try:

    run_mode = fn.determine_run_mode()
    print(fn.log_header(f"Run mode: {run_mode}", color=config.YELLOW))

except ValueError as e:

    print(fn.log(f"{config.RED}❌ {e.args[0]}{config.RESET}"))
    exit()


# ---------------------------------------------------
# INITIALIZE RUN, DEPENDING ON RUN MODE
# ---------------------------------------------------
progress_info = None

if run_mode == config.NEW_RUN:

    # ---------------------------------------------------
    # Case 1: INITIALIZE PROGRESS
    # ---------------------------------------------------
    print(fn.log_header(f"\nINITIALIZE PROGRESS"))
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
            starting_text = fn.load_translatables_for_batch(resume_batch, limit=1)[0]["text"][:100]
            print(fn.log(
                f"Resuming from Batch with id={resume_batch["id"]} [Terminology: {resume_batch[config.TERMINOLOGY_STATUS]} / Translation: {resume_batch[config.TRANSLATION_STATUS]}] - starting with: \"{starting_text} ...\"\n")
            )

    except ValueError as e:

        print(fn.log(f"{config.RED}❌ {e.args[0]}{config.RESET}"))
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
current_time = datetime.now().strftime("%H:%M:%S")
print(fn.log(f"Start global timer (time: {current_time})"))


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
    print(fn.log_header(f"IMPORT INPUT FILE: {config.INPUT_FILE}"))

    input_data = fn.load_json_input(config.INPUT_FILE)

    # ---------------------------------------------------
    # EXTRACT TRANSLATABLES
    # ---------------------------------------------------
    print(fn.log_header(f"EXTRACT TRANSLATABLES"))

    translatables = []

    # Recursively fill translatables with matching nodes in babele_data
    if config.INPUT_TYPE == config.INPUT_TYPE_BABELE:

        fn.extract_translatables_from_babele(
            input=input_data,
            translatables=translatables,
            current_path=[]
        )

    else:

        fn.extract_translatables_from_lang_file(
            input=input_data,
            translatables=translatables,
            current_path=[]
        )

    print(fn.log(f"Extracted translatables: {len(translatables)}\n"))
    # -------
    # Tests:
    # -------
    # unit_tests.test_extract_translatables_from_babele(translatables)

    # ---------------------------------------------------
    # SAVE TRANSLATABLES TO PROGRESS FOLDER
    # ---------------------------------------------------
    print(fn.log_header(f"SAVE TRANSLATABLES TO PROGRESS FOLDER"))

    fn.save_json_output(
        translatables,
        config.TRANSLATABLES_FILE
    )

    loaded_translatables = fn.load_json_input(config.TRANSLATABLES_FILE)

    # -------
    # Tests:
    # -------
    # unit_tests.test_save_to_file(translatables, loaded_translatables)

    # -----------------------------------------------------------------
    # PROTECT TRANSLATABLES WITH PLACEHOLDERS
    # -----------------------------------------------------------------
    print(fn.log_header(f"PROTECT TRANSLATABLES WITH PLACEHOLDERS (MASK FOUNDRY ELEMENTS) ==="))

    translatables_with_placeholders, placeholders = fn.protect_with_placeholders(
        translatables
    )

    # ==================
    # Tests:
    # ==================
    # unit_tests.test_create_translatables_with_placeholders(translatables_with_placeholders)

    # ---------------------------------------------------
    # SAVE TRANSLATABLES WITH PLACEHOLDERS
    # ---------------------------------------------------
    print(fn.log_header(f"SAVE TRANSLATABLES WITH PLACEHOLDERS TO PROGRESS FOLDER ==="))

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
    # loaded_translatables_with_placeholders = fn.load_translatables(with_placeholders=True)
    # unit_tests.test_save_to_file(translatables_with_placeholders, loaded_translatables_with_placeholders)
    # loaded_placeholders = fn.load_placeholders()
    # unit_tests.test_save_to_file(placeholders, loaded_placeholders)

    # ---------------------------------------------------
    # BUILD BATCHES
    # ---------------------------------------------------
    print(fn.log_header(f"BUILD BATCHES"))

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

        print(fn.log(f"{config.RED}❌ {details["error"]}{config.RESET}"))
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
    print(fn.log_header(f"SAVE BATCHES TO PROGRESS FOLDER"))

    fn.save_json_output(
        batches,
        config.BATCHES_FILE
    )

    # -------
    # Tests:
    # -------
    # loaded_batches = fn.load_batches()
    # unit_tests.test_save_to_file(batches, loaded_batches)

    # ---------------------------------------------------
    # PREPARE API REQUEST
    # ---------------------------------------------------
    client = None
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

        print(fn.log_header(f"REUSING EXISTING TERMINOLOGY ({len(master_terminology["terms"])} entries).",
                            color=config.MAGENTA))

    else:

        if (run_mode == config.RESUME
                and config.TERMINOLOGY_FILE.exists()):

            master_terminology_raw = fn.load_json_input(
                config.TERMINOLOGY_FILE
            )

            print(fn.log(f"RESUMING TERMINOLOGY BUILD FROM LAST RUN ({len(master_terminology_raw["terms"])} entries) ...{config.RESET}"))

        else:

            master_terminology_raw = {
                "terms": []
            }

            print(fn.log(f"BUILDING FRESH TERMINOLOGY ..."))

        # ---------------------------------------------------
        # BEGIN TERMINOLOGY BATCH LOOP ...
        # ---------------------------------------------------
        print(fn.log_header(f"BEGIN TERMINOLOGY BATCH LOOP ..."))

        for batch in batches:

            # if batch["id"] > 0:
            #     raise Exception("!!! TEST ABORT !!!")

            if (run_mode == config.RESUME
                    and batch[config.TERMINOLOGY_STATUS] == config.COMPLETED):

                print(fn.log(
                    "Terminology skipped (already completed)",
                    batch_id=batch['id'], batch_cnt=len(batches),
                    color=config.GREEN)
                )

                continue

            batch[config.TERMINOLOGY_STATUS] = config.PROCESSING
            fn.save_batch(batch, batches, progress_info)

            batch_translatables = fn.load_translatables_for_batch(
                batch,
                with_placeholders=False
            )

            batch_payload = "\n\n".join(
                translatable["text"]
                for translatable in batch_translatables
            )

            print(fn.log(
                f"Terminology has {len(batch_payload)} chars",
                batch_id=batch['id'], batch_cnt=len(batches))
            )

            if config.MOCK_MODE:

                print(fn.log_header(f"MOCK MODE IS ON! Terminology will be empty.", color=config.YELLOW))

                batch[config.TERMINOLOGY_STATUS] = config.COMPLETED
                fn.save_batch(batch, batches, progress_info)

            else:

                api_timer_start = time.perf_counter()
                current_time = datetime.now().strftime("%H:%M:%S")
                print(fn.log(f"Start API timer (time: {current_time})"))
                response = None

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

                print(fn.log(
                    f"API duration: {api_timer_end - api_timer_start:.2f} seconds",
                    batch_id=batch['id'], batch_cnt=len(batches),
                    color=config.BLUE)
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

        if duplicate_cnt > 0:
            print(fn.log(
                f"Eliminated {duplicate_cnt} duplicate(s) from Terminology.",
                     color=config.YELLOW)
            )

        fn.save_json_output(
            master_terminology,
            config.TERMINOLOGY_FILE
        )

        print(fn.log(
            f"Saved {len(master_terminology["terms"])} entries in Master Terminology: {config.TERMINOLOGY_FILE}",
            color=config.GREEN)
        )

    # ---------------------------------------------------
    # BEGIN BATCH TRANSLATION LOOP ...
    # ---------------------------------------------------
    print(fn.log_header(f"BEGIN TRANSLATION BATCH LOOP ..."))

    # In Resume mode with all Translation Batches already completed,
    # reconstruct translations_with_placeholders from file and skip
    # directly to post-processing.

    if run_mode == config.RESUME and resume_batch is None:

        print(fn.log(
            f"All Translation processing already completed. Continuing with post-processing only.",
            color=config.GREEN)
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

                    print(fn.log(
                        f"Translation skipped (already completed)",
                        batch_id=batch["id"], batch_cnt=len(batches),
                        color=config.GREEN)
                    )

                    continue

                else:

                    resume_batch = None

            # ---------------------------------------------------
            # ASSEMBLE BATCH PAYLOAD
            # ---------------------------------------------------
            print(fn.log(f"Assemble payload",
                                batch_id=batch["id"], batch_cnt=len(batches)))

            batch_payload = []

            batch_translatables = (
                fn.load_translatables_for_batch(
                    batch,
                    with_placeholders=True
                ))

            print(fn.log(f"{len(batch_translatables)} translatables loaded.", batch_id=batch["id"], batch_cnt=len(batches)))

            # -------
            # Tests:
            # -------
            # unit_tests.test_assemble_batch_payload(batch, batch_translatables)

            # ---------------------------------------------------
            # BEGIN TRANSLATABLES LOOP ...
            # ---------------------------------------------------
            for translatable in batch_translatables:
                batch_payload.append({
                    "id": translatable["id"],
                    "text": translatable["text"]
                })

            # ---------------------------------------------------
            # ... END OF TRANSLATABLES LOOP
            # ---------------------------------------------------
            batch_payload_chars = fn.total_char_count(batch_payload, "text")
            print(fn.log(f"Payload assembled wth {batch_payload_chars} chars", batch_id=batch["id"], batch_cnt=len(batches)))

            # ---------------------------------------------------
            # ENRICH INSTRUCTIONS WITH TERMINOLOGY
            # ---------------------------------------------------
            print(fn.log("Identify terminology ...",
                                batch_id=batch["id"], batch_cnt=len(batches)))

            # Extract batch-specific terminology from Master Terminology
            batch_text = "\n".join(
                translatable["text"]
                for translatable in batch_translatables
            )

            batch_text_lower = batch_text.lower()

            batch_relevant_terms = [
                term
                for term in master_terminology["terms"]
                if term["original"].lower() in batch_text_lower
            ]

            print(fn.log(f"Found {len(batch_relevant_terms)} relevant terms in Master Terminology.",
                         batch_id=batch["id"], batch_cnt=len(batches)))

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

            print(fn.log(f"Translation status: [{batch[config.TRANSLATION_STATUS]}]...", batch_id=batch["id"], batch_cnt=len(batches)))

            if config.MOCK_MODE:

                print(fn.log_header(f"MOCK MODE IS ON! Translations will just be copies of the input text.", color=config.YELLOW))

                for translatable in batch_payload:
                    translations_with_placeholders.append({
                        "id": translatable["id"],
                        "translation": translatable["text"]
                    })

            else:

                api_timer_start = time.perf_counter()
                current_time = datetime.now().strftime("%H:%M:%S")
                print(fn.log(f"Start API timer (time: {current_time})"))

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

                    print(fn.log("Completenes check...", batch_id=batch["id"], batch_cnt=len(batches)))

                    fn.verify_translation_completeness(batch, len(batches), batch_payload, new_translations)

                    print(fn.log(f"... completeness check: {config.GREEN}PASSED{config.RESET}", batch_id=batch["id"], batch_cnt=len(batches)))

                    # ---------------------------------------------------
                    # PRE-CHECK PLACEHOLDERS (AND CONFIRM IF ANY)
                    # ---------------------------------------------------
                    print(fn.log("Pre-check placeholders in translation", batch_id=batch["id"], batch_cnt=len(batches)))

                    expected_placeholder_errors = fn.identify_review_items(
                        batch_payload,
                        new_translations
                    )

                    if len(expected_placeholder_errors) == 0:
                        print(fn.log(f"No Placeholder translation issue(s) identified in Batch",
                                     batch_id=batch["id"], batch_cnt=len(batches),
                                     color=config.GREEN))

                        translations_with_placeholders.extend(new_translations)

                    else:

                        # In case of errors, ask the user what to do with this Batch
                        list_errors_text = ""
                        for error in expected_placeholder_errors:
                            list_errors_text += fn.to_multiline_text(error["details"]) + "\n"

                        print(fn.log(f"{list_errors_text}", color=config.YELLOW))
                        print(fn.log(f"WARNING - Confirmation required: Batch contains {len(expected_placeholder_errors)} placeholder translation error(s) - see above.",
                                     batch_id=batch["id"], batch_cnt=len(batches),
                                     color=config.YELLOW))

                        if not fn.confirm_batch_nonfatal_errors():

                            raise Exception(config.ABORTED_BY_USER_ERROR)

                        else:

                            translations_with_placeholders.extend(new_translations)

                except Exception as e:

                    batch[config.TRANSLATION_STATUS] = config.FAILED
                    fn.save_batch(batch, batches, progress_info)

                    print(fn.log(f"{e.args[0]}", color=config.RED))

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

                print(fn.log(f"API duration: {api_timer_end - api_timer_start:.2f} seconds",
                             batch_id=batch["id"], batch_cnt=len(batches),
                             color=config.BLUE)
                )

            # ---------------------------------------------------
            # SAVE TRANSLATIONS (STILL WITH PLACEHOLDERS)
            # ---------------------------------------------------
            fn.save_json_output(translations_with_placeholders, config.TRANSLATIONS_WITH_PLACEHOLDERS_FILE)

            print(fn.log(f"Saved {len(translations_with_placeholders)} translations (with placeholders)",
                         batch_id=batch["id"], batch_cnt=len(batches),
                         color=config.GREEN))

            # -------
            # Tests:
            # -------
            # loaded_translations_with_placeholders = fn.load_json_input(config.TRANSLATIONS_WITH_PLACEHOLDERS_FILE)
            # unit_tests.test_save_to_file(translations_with_placeholders, loaded_translations_with_placeholders)

            # ---------------------------------------------------
            # SET BATCH & PROGRESS INFO TO COMPLETED
            # ---------------------------------------------------
            batch[config.TRANSLATION_STATUS] = config.COMPLETED
            fn.save_batch(batch, batches, progress_info)
            print(fn.log_header(f"Translation status: [{batch[config.TRANSLATION_STATUS]}]...",
                                batch_id=batch["id"], batch_cnt=len(batches),
                                color=config.GREEN))

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
    print(fn.log(f"Picked up {len(translations_final)} translations from previous run:"))
    # print(f"{
    # to_multiline_text(
    #     input=translations_final,
    #     value_char_limit=50
    # )}")


# ---------------------------------------------------
# VALIDATE PLACEHOLDERS => REVIEW ITEMS
# ---------------------------------------------------
print(fn.log_header(f"VALIDATE PLACEHOLDERS"))

review_items = fn.identify_review_items(
    translatables_with_placeholders,
    translations_with_placeholders
)

print(fn.log(f"{len(review_items)} Placeholder translation issue(s) identified",
             color=config.GREEN if len(review_items) == 0 else config.YELLOW))


# ---------------------------------------------------
# SAVE REVIEW ITEMS
# ---------------------------------------------------
if len(review_items) > 0:
    fn.save_json_output(
        review_items,
        config.REVIEW_ITEMS_FILE
    )
else:
    fn.delete_file(config.REVIEW_ITEMS_FILE)

if len(review_items) > 0:
    print(fn.log(f"{len(review_items)} Post-review item(s) written to {config.REVIEW_ITEMS_FILE}",
                 color=config.GREEN if len(review_items) == 0 else config.YELLOW))
    # print(fn.log(f"DEBUG - \n{fn.to_prettified_json(review_items)}"))


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
print(fn.log_header(f"APPLY TRANSLATIONS TO Babele"))

fn.apply_translations(
    input_data,
    translatables,
    translations_final
)
print(fn.log(f"{len(translations_final)} translations applied to original Babele data."))

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
print(fn.log_header(f"SAVE FINAL Babele FIILE"))
fn.save_json_output(input_data, config.OUTPUT_FILE)


# ------------------------------------------------------------
# Stop global timer
# ------------------------------------------------------------
global_timer_end = time.perf_counter()
print(fn.log(f"TOTAL processing duration: {config.BLUE}{global_timer_end - global_timer_start:.2f} seconds{config.RESET}"))
print(fn.log(f"Find the translated file here: {config.BLUE}{config.OUTPUT_FILE}{config.RESET}"))

if config.MOCK_MODE:

    print(fn.log_header(f"MOCK MODE IS ON! THIS WAS ONLY A SIMULATION!", color=config.YELLOW))

else:

    current_time = datetime.now().strftime("%H:%M:%S")
    print(fn.log_header(f"PROCESS COMPLETED SUCCESSFULLY (time: {current_time})", color=config.GREEN))

