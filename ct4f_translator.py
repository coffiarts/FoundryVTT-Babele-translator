import ct4f_config as config
import ct4f_translator_dialogs as translator_dialogs
import ct4f_core_functions as fn
import ct4f_exceptions as exceptions
import json
import time
import traceback
from datetime import datetime
from collections.abc import Callable


# ------------------------------------------------------------
# Function: Report Outcome
# Runs the given work and reports exactly ONE outcome to on_ended.
# The outcome is a dict: {"outcome", "result", "message", "details"}
# ------------------------------------------------------------
def report_outcome(work, on_ended):

    outcome = {
        "outcome": config.OUTCOME_SUCCESS,
        "result": None,
        "message": None,
        "details": None
    }

    try:
        outcome["result"] = work()

    except exceptions.CancelledException:
        outcome["outcome"] = config.OUTCOME_CANCELLED

    except exceptions.DeclinedException:
        outcome["outcome"] = config.OUTCOME_DECLINED

    except exceptions.ExpectedException as e:
        outcome["outcome"] = config.OUTCOME_EXPECTED_ERROR
        outcome["message"] = str(e)

    except Exception as e:
        outcome["outcome"] = config.OUTCOME_UNEXPECTED_ERROR
        outcome["message"] = f"{type(e).__name__}: {e}"
        outcome["details"] = traceback.format_exc()

    on_ended(outcome)


def prepare(logger: Callable[str], on_ended):
    report_outcome(lambda: _prepare(logger), on_ended)


def run(logger: Callable[str], on_ended, cancel_event):
    report_outcome(lambda: _run(logger, cancel_event), on_ended)


# ------------------------------------------------------------
# Function: Prepare Translation
# Offline part: validation, run mode, extraction, placeholders and batch building.
# Returns the info needed by run_translation(), or None if the user aborted.
# ------------------------------------------------------------
def _prepare(logger: Callable[str]):

    translator_dialogs.set_logger(logger)

    resume_batch = None  # only set in RESUME mode

    # ---------------------------------------------------
    # CHECK IF INPUT_FILE HAS BEEN SET
    # ---------------------------------------------------
    if config.INPUT_FILE is None:
        raise ValueError("❌ Input File is not defined.")

    # ---------------------------------------------------
    # START OF PROCESSING FILE
    # ---------------------------------------------------
    fn.LOGGER(fn.log_header(f"PROCESSING FILE: {config.INPUT_FILE}"))
    fn.LOGGER(fn.log_header(f"LANGUAGES: {config.SOURCE_LANGUAGE["name"]} => {config.TARGET_LANGUAGE["name"]}"))

    # ---------------------------------------------------
    # CONFIGURATION INFO INCL. USER-PROMPTED PARAMETERS
    # ---------------------------------------------------
    fn.LOGGER(fn.log_header("CONFIGURATION"))

    # Just as info: print out the resume-relevant params
    fn.LOGGER(f"{fn.to_multiline_text(fn.get_resume_relevant_config())}")

    # ---------------------------------------------------
    # VALIDATE INPUT FILE
    # Before anything is asked or any progress file is touched
    # ---------------------------------------------------
    if config.INPUT_TYPE == config.INPUT_TYPE_LOCALIZATION:

        fn.validate_lang_file_content(fn.load_json_input(config.INPUT_FILE))

        # Unusual file name: not a hard block, the user decides
        if not fn.is_lang_file_name(config.INPUT_FILE_NAME):

            if not translator_dialogs.confirm_unusual_lang_file_name():
                raise exceptions.DeclinedException()

    # ---------------------------------------------------
    # DETERMINE RUN MODE
    # ---------------------------------------------------
    try:

        run_mode = fn.determine_run_mode()
        fn.LOGGER(fn.log_header(f"Run mode: {run_mode}", color=config.CONSOLE_YELLOW))

    except ValueError as e:

        fn.LOGGER(fn.batch_log_msg(f"❌ {e.args[0]}"), config.TAG_ERROR)
        raise RuntimeError(str(e))

    # ---------------------------------------------------
    # CHECK RESUME-RELEVANT CONFIG
    # If settings have changed since the last run, the user decides whether to discard the progress
    # ---------------------------------------------------
    if run_mode == config.RESUME:

        differences = fn.get_resume_config_differences(
            fn.load_json_input(config.PROGRESS_INFO_FILE)
        )

        if differences:

            if not translator_dialogs.confirm_discard_progress(differences):
                raise exceptions.DeclinedException()

            # Start fresh: the NEW_RUN branch below initializes the progress
            fn.cleanup_progress_files()
            run_mode = config.NEW_RUN
            fn.LOGGER(fn.log_header(f"Run mode: {run_mode}", color=config.CONSOLE_YELLOW))

    # ---------------------------------------------------
    # INITIALIZE RUN, DEPENDING ON RUN MODE
    # ---------------------------------------------------
    progress_info = None

    if run_mode == config.NEW_RUN:

        # ---------------------------------------------------
        # Case 1: INITIALIZE PROGRESS
        # ---------------------------------------------------
        fn.LOGGER(fn.log_header(f"\nINITIALIZE PROGRESS"))
        if not config.MOCK_MODE:
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

            if resume_batch is not None:
                starting_text = fn.load_translatables_for_batch(resume_batch, limit=1)[0]["text"][:100]
                fn.LOGGER(fn.batch_log_msg(
                    f"Resuming from Batch with id={resume_batch["id"]} [Terminology: {resume_batch[config.TERMINOLOGY_STATUS]} / Translation: {resume_batch[config.TRANSLATION_STATUS]}] - starting with: \"{starting_text} ...\"\n")
                    , config.TAG_INFO)

        except ValueError as e:

            fn.LOGGER(fn.batch_log_msg(f"❌ {e.args[0]}"), config.TAG_ERROR)
            raise RuntimeError(str(e))

    elif run_mode == config.POSTPROCESSING_ONLY:

        # Nothing to do here.
        pass

    if run_mode != config.POSTPROCESSING_ONLY:

        # ---------------------------------------------------
        # IMPORT INPUT FILE
        # ---------------------------------------------------
        fn.LOGGER(fn.log_header(f"IMPORT INPUT FILE: {config.INPUT_FILE}"))

        input_data = fn.load_json_input(config.INPUT_FILE)

        # ---------------------------------------------------
        # EXTRACT TRANSLATABLES
        # ---------------------------------------------------
        fn.LOGGER(fn.log_header(f"EXTRACT TRANSLATABLES"))

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

        fn.LOGGER(fn.batch_log_msg(f"Extracted translatables: {len(translatables)}\n"))
        # -------
        # Tests:
        # -------
        # unit_tests.test_extract_translatables_from_babele(translatables)

        # ---------------------------------------------------
        # VALIDATE EXTRACTION RESULT
        # ---------------------------------------------------
        fn.validate_translatables_found(translatables)

        # ---------------------------------------------------
        # SAVE TRANSLATABLES TO PROGRESS FOLDER
        # ---------------------------------------------------
        fn.LOGGER(fn.log_header(f"SAVE TRANSLATABLES TO PROGRESS FOLDER"))

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
        fn.LOGGER(fn.log_header(f"PROTECT TRANSLATABLES WITH PLACEHOLDERS (MASK FOUNDRY ELEMENTS) ==="))

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
        fn.LOGGER(fn.log_header(f"SAVE TRANSLATABLES WITH PLACEHOLDERS TO PROGRESS FOLDER ==="))

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
        fn.LOGGER(fn.log_header(f"BUILD BATCHES"))

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

            # A failed preparation must leave nothing behind, so that the next attempt starts fresh
            fn.cleanup_progress_files()

            raise exceptions.ExpectedException(e.args[0]["error"])

        # -------
        # Tests:
        # -------

        # fn.LOGGER(
        #     f"DEBUG - First 10 batches: "
        #     f"{stringify_json(batches[:10])}"
        # )

        # ---------------------------------------------------
        # SAVE BATCHES TO PROGRESS FOLDER
        # ---------------------------------------------------
        fn.LOGGER(fn.log_header(f"SAVE BATCHES TO PROGRESS FOLDER"))

        fn.save_json_output(
            batches,
            config.BATCHES_FILE
        )

        # -------
        # Tests:
        # -------
        # loaded_batches = fn.load_batches()
        # unit_tests.test_save_to_file(batches, loaded_batches)

    return {
        "run_mode": run_mode,
        "analysis": fn.analyze_progress_info()
    }


# -------------------------------------------------------------------------------------------------------
# This controls the main process of translating a Babele input file:
# - extract master terminology from the input (using the online LLM)
# - translate (using the external LLM)
# - validate
# - Post-Processing: Restore Foundry specific syntax from placeholders, reassemble, export to a new Babele file
# -------------------------------------------------------------------------------------------------------
def _run(logger: Callable[str], cancel_event):

    translator_dialogs.set_logger(logger)

    # ---------------------------------------------------
    # WARN IF MOCK MODE IS ON
    # ---------------------------------------------------
    fn.check_and_warn_if_mock_mode("API Calls to the remote LLM will only be simulated.")

    # ---------------------------------------------------
    # RETRIEVE PREPARATION DATA
    # ---------------------------------------------------
    run_mode = fn.determine_run_mode()
    progress_info = None
    resume_batch = None

    if run_mode != config.POSTPROCESSING_ONLY:

        progress_info = fn.load_json_input(config.PROGRESS_INFO_FILE)

        if run_mode == config.RESUME:
            resume_batch = fn.find_resume_batch(progress_info)

    # ------------------------------------------------------------
    # Start global timer
    # ------------------------------------------------------------
    global_timer_start = time.perf_counter()
    current_time = datetime.now().strftime("%H:%M:%S")
    fn.LOGGER(fn.batch_log_msg(f"Start global timer (time: {current_time})"), config.TAG_INFO)

    if run_mode != config.POSTPROCESSING_ONLY:
        batches = progress_info["batches"]

        # ---------------------------------------------------
        # PREPARE API REQUEST
        # ---------------------------------------------------
        client = None
        if not config.MOCK_MODE:
            client = fn.init_api_client()

        # ---------------------------------------------------
        # REUSE, CONTINUE OR BUILD MASTER TERMINOLOGY
        # ---------------------------------------------------
        if run_mode != config.RESUME and config.TERMINOLOGY_FILE.exists():

            master_terminology = fn.load_json_input(
                config.TERMINOLOGY_FILE
            )

            # As we're skipping terminology completely, tell process control (progress-info) that everything's completed here.
            # Otherwise, there would be an abort due to "missing terminology" later
            for batch in batches:
                batch[config.TERMINOLOGY_STATUS] = config.COMPLETED

            fn.save_batches(
                batches,
                progress_info
            )

            fn.LOGGER(fn.log_header(f"REUSING EXISTING TERMINOLOGY ({len(master_terminology["terms"])} entries)."), config.TAG_INFO)

        else:

            if (run_mode == config.RESUME
                    and config.TERMINOLOGY_FILE.exists()):

                master_terminology_raw = fn.load_json_input(
                    config.TERMINOLOGY_FILE
                )

                fn.LOGGER(fn.batch_log_msg(
                    f"RESUMING TERMINOLOGY BUILD FROM LAST RUN ({len(master_terminology_raw["terms"])} entries) ..."), config.TAG_INFO)

            else:

                master_terminology_raw = {
                    "terms": []
                }

                fn.LOGGER(fn.batch_log_msg(f"BUILDING FRESH TERMINOLOGY ..."))


            # ---------------------------------------------------
            # BEGIN TERMINOLOGY BATCH LOOP ...
            # ---------------------------------------------------
            fn.LOGGER(fn.log_header(f"BEGIN TERMINOLOGY BATCH LOOP ..."))

            mock_delay_per_batch = calc_mock_delay_per_batch(batches, config.TERMINOLOGY_STATUS, logger)

            for batch in batches:

                # if batch["id"] > 0:
                #     raise Exception("!!! TEST ABORT !!!")

                if (run_mode == config.RESUME
                        and batch[config.TERMINOLOGY_STATUS] in (config.COMPLETED, config.REVIEW_REQUIRED)):
                    fn.LOGGER(
                        fn.batch_log_msg(
                            "Terminology skipped (already completed)",
                            batch_id=batch['id'], batch_cnt=len(batches)
                        ), config.TAG_SUCCESS
                    )

                    continue

                batch[config.TERMINOLOGY_STATUS] = config.PROCESSING
                fn.save_batch(batch, batches, progress_info)

                if config.MOCK_MODE:
                    time.sleep(mock_delay_per_batch)

                batch_translatables = fn.load_translatables_for_batch(
                    batch,
                    with_placeholders=False
                )

                batch_payload = "\n\n".join(
                    translatable["text"]
                    for translatable in batch_translatables
                )

                fn.LOGGER(fn.batch_log_msg(
                    f"Terminology has {len(batch_payload)} chars",
                    batch_id=batch['id'], batch_cnt=len(batches))
                )

                if fn.check_and_warn_if_mock_mode("Terminology will be empty."):

                    batch[config.TERMINOLOGY_STATUS] = config.COMPLETED
                    fn.save_batch(batch, batches, progress_info)

                else:

                    api_timer_start = time.perf_counter()
                    current_time = datetime.now().strftime("%H:%M:%S")
                    fn.LOGGER(fn.batch_log_msg(f"Start API timer (time: {current_time})"))
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
                        # fn.LOGGER(f"DEBUG - terminology response: {to_prettified_json(terminology_response)}")
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

                    fn.LOGGER(
                        fn.batch_log_msg(
                            f"API duration: {api_timer_end - api_timer_start:.2f} seconds",
                            batch_id=batch['id'], batch_cnt=len(batches)
                        ), config.TAG_INFO
                    )

                fn.save_json_output(
                    master_terminology_raw,
                    config.TERMINOLOGY_FILE
                )

                batch[config.TERMINOLOGY_STATUS] = config.COMPLETED
                fn.save_batch(batch, batches, progress_info)

                abort_if_cancelled(cancel_event)

                if config.MOCK_MODE:
                    time.sleep(mock_delay_per_batch)

            # ---------------------------------------------------
            # ... END OF TERMINOLOGY BATCH LOOP
            # ---------------------------------------------------
            master_terminology = fn.deduplicate_terminology(
                master_terminology_raw
            )

            duplicate_cnt = len(master_terminology_raw["terms"]) - len(master_terminology["terms"])

            if duplicate_cnt > 0:
                fn.LOGGER(fn.batch_log_msg(
                    f"Eliminated {duplicate_cnt} duplicate(s) from Terminology."),
                    config.TAG_INFO
                )

            fn.save_json_output(
                master_terminology,
                config.TERMINOLOGY_FILE
            )

            fn.LOGGER(fn.batch_log_msg(
                f"Saved {len(master_terminology["terms"])} entries in Master Terminology: {config.TERMINOLOGY_FILE}"),
                config.TAG_SUCCESS
            )

        # ---------------------------------------------------
        # BEGIN TRANSLATION ...
        # ---------------------------------------------------
        fn.LOGGER(fn.log_header(f"BEGIN TRANSLATION BATCH LOOP ..."))

        # In Resume mode with all Translation Batches already completed,
        # reconstruct translations_with_placeholders from file and skip
        # directly to post-processing.

        if run_mode == config.RESUME and resume_batch is None:

            fn.LOGGER(fn.batch_log_msg(
                f"All Translation processing already completed. Continuing with post-processing only."),
                config.TAG_SUCCESS
            )

            translations_with_placeholders = fn.load_json_input(
                config.TRANSLATIONS_WITH_PLACEHOLDERS_FILE
            )

        else:

            # ---------------------------------------------------
            # BEGIN BATCH TRANSLATION LOOP
            # ---------------------------------------------------

            translations_with_placeholders = []

            mock_delay_per_batch = calc_mock_delay_per_batch(batches, config.TRANSLATION_STATUS, logger)

            for batch in batches:

                # ---------------------------------------------------
                # ABORT IF TERMINOLOGY IS MISSING
                # ---------------------------------------------------
                if batch[config.TERMINOLOGY_STATUS] != config.COMPLETED:
                    raise ValueError(
                        "❌ Master terminology has not been completed yet. "
                        "Translation cannot start."
                    )

                # In RUN_MODE = RESUME, skip all Batches whose translation is already completed.
                # This is decided per Batch, because Terminology and Translation progress are independent
                if (run_mode == config.RESUME
                        and batch[config.TRANSLATION_STATUS] in (config.COMPLETED, config.REVIEW_REQUIRED)):

                    already_translated = fn.load_translations_for_batch(batch)
                    translations_with_placeholders.extend(already_translated)

                    fn.LOGGER(fn.batch_log_msg(
                        f"Translation skipped (already completed)",
                        batch_id=batch["id"], batch_cnt=len(batches)
                        ), config.TAG_SUCCESS
                    )

                    continue

                # ---------------------------------------------------
                # ASSEMBLE BATCH PAYLOAD
                # ---------------------------------------------------
                fn.LOGGER(fn.batch_log_msg(f"Assemble payload",
                                           batch_id=batch["id"], batch_cnt=len(batches)))

                batch_payload = []

                batch_translatables = (
                    fn.load_translatables_for_batch(
                        batch,
                        with_placeholders=True
                    ))

                fn.LOGGER(fn.batch_log_msg(f"{len(batch_translatables)} translatables loaded.", batch_id=batch["id"],
                                           batch_cnt=len(batches)))

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
                fn.LOGGER(fn.batch_log_msg(f"Payload assembled wth {batch_payload_chars} chars", batch_id=batch["id"],
                                           batch_cnt=len(batches)))

                # ---------------------------------------------------
                # ENRICH INSTRUCTIONS WITH TERMINOLOGY
                # ---------------------------------------------------
                fn.LOGGER(fn.batch_log_msg("Identify terminology ...",
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

                fn.LOGGER(fn.batch_log_msg(f"Found {len(batch_relevant_terms)} relevant terms in Master Terminology.",
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

                if config.MOCK_MODE:
                    time.sleep(mock_delay_per_batch)

                fn.LOGGER(fn.batch_log_msg(f"Translation status: [{batch[config.TRANSLATION_STATUS]}]...", batch_id=batch["id"],
                                           batch_cnt=len(batches)))

                if fn.check_and_warn_if_mock_mode("Translations will just be copies of the input text."):

                    for translatable in batch_payload:
                        translations_with_placeholders.append({
                            "id": translatable["id"],
                            "translation": translatable["text"]
                        })

                else:

                    api_timer_start = time.perf_counter()
                    current_time = datetime.now().strftime("%H:%M:%S")
                    fn.LOGGER(fn.batch_log_msg(f"Start API timer (time: {current_time})"), config.TAG_INFO)

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

                        fn.LOGGER(fn.batch_log_msg("Completeness check...", batch_id=batch["id"], batch_cnt=len(batches)))

                        fn.verify_translation_completeness(batch, len(batches), batch_payload, new_translations)

                        fn.LOGGER(
                            fn.batch_log_msg(f"... completeness check: PASSED",
                                             batch_id=batch["id"],
                                             batch_cnt=len(batches),
                                             color=config.CONSOLE_GREEN)
                        )

                        # ---------------------------------------------------
                        # PRE-CHECK PLACEHOLDERS (AND CONFIRM IF ANY)
                        # ---------------------------------------------------
                        fn.LOGGER(fn.batch_log_msg("Pre-check placeholders in translation", batch_id=batch["id"],
                                                   batch_cnt=len(batches)))

                        expected_placeholder_errors = fn.identify_review_items(
                            batch_payload,
                            new_translations
                        )

                        if len(expected_placeholder_errors) == 0:
                            fn.LOGGER(fn.batch_log_msg(f"No Placeholder translation issue(s) identified in Batch",
                                                       batch_id=batch["id"], batch_cnt=len(batches)),
                                   config.TAG_SUCCESS
                            )

                            translations_with_placeholders.extend(new_translations)

                        else:

                            # In case of errors, ask the user what to do with this Batch
                            list_errors_text = ""
                            for error in expected_placeholder_errors:
                                list_errors_text += fn.to_multiline_text(error["details"]) + "\n"

                            fn.LOGGER(fn.batch_log_msg(f"{list_errors_text}"), config.TAG_WARNING)
                            fn.LOGGER(
                                fn.batch_log_msg(
                                f"WARNING - Confirmation required: Batch contains {len(expected_placeholder_errors)} placeholder translation error(s) - see above.",
                                    batch_id=batch["id"], batch_cnt=len(batches)),
                                config.TAG_WARNING
                            )

                            if not translator_dialogs.confirm_batch_nonfatal_errors():

                                raise exceptions.DeclinedException()

                            else:

                                translations_with_placeholders.extend(new_translations)

                                existing_review_items = []

                                if config.PROGRESS_REVIEW_ITEMS_FILE.exists():
                                    existing_review_items = fn.load_json_input(
                                        config.PROGRESS_REVIEW_ITEMS_FILE
                                    )

                                existing_review_items.extend(
                                    expected_placeholder_errors
                                )

                                fn.save_json_output(
                                    existing_review_items,
                                    config.PROGRESS_REVIEW_ITEMS_FILE
                                )

                                batch[config.TRANSLATION_STATUS] = config.REVIEW_REQUIRED

                    except exceptions.DeclinedException:

                        # The user declined to keep this Batch: mark it, but this is no fatal error
                        batch[config.TRANSLATION_STATUS] = config.FAILED
                        fn.save_batch(batch, batches, progress_info)
                        raise

                    except exceptions.CancelledException:

                        # The user cancelled while a prompt was pending: the Batch has to be redone later
                        batch[config.TRANSLATION_STATUS] = config.UNPROCESSED
                        fn.save_batch(batch, batches, progress_info)
                        raise

                    except Exception as e:

                        # A final catcher for any "Tales of the Unexpected" - a case for a post-mortem dump
                        batch[config.TRANSLATION_STATUS] = config.FAILED
                        fn.save_batch(batch, batches, progress_info)

                        fn.LOGGER(fn.batch_log_msg(f"{e.args[0]}"), config.TAG_ERROR)

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

                    fn.LOGGER(
                        fn.batch_log_msg(f"API duration: {api_timer_end - api_timer_start:.2f} seconds",
                                         batch_id=batch["id"], batch_cnt=len(batches)
                                         ), config.TAG_INFO
                    )


                # ---------------------------------------------------
                # SAVE TRANSLATIONS (STILL WITH PLACEHOLDERS)
                # ---------------------------------------------------
                fn.save_json_output(translations_with_placeholders, config.TRANSLATIONS_WITH_PLACEHOLDERS_FILE)

                fn.LOGGER(fn.batch_log_msg(f"Saved {len(translations_with_placeholders)} translations (with placeholders)",
                                           batch_id=batch["id"], batch_cnt=len(batches)),
                       config.TAG_SUCCESS
                )

                abort_if_cancelled(cancel_event)

                # -------
                # Tests:
                # -------
                # loaded_translations_with_placeholders = fn.load_json_input(config.TRANSLATIONS_WITH_PLACEHOLDERS_FILE)
                # unit_tests.test_save_to_file(translations_with_placeholders, loaded_translations_with_placeholders)

                # ---------------------------------------------------
                # SET BATCH & PROGRESS INFO TO COMPLETED
                # ---------------------------------------------------
                if batch[config.TRANSLATION_STATUS] != config.REVIEW_REQUIRED:
                    batch[config.TRANSLATION_STATUS] = config.COMPLETED

                fn.save_batch(batch, batches, progress_info)
                fn.LOGGER(fn.log_header(f"Translation status: [{batch[config.TRANSLATION_STATUS]}]...",
                                    batch_id=batch["id"], batch_cnt=len(batches)),
                       config.TAG_SUCCESS
                )

                if config.MOCK_MODE:
                    time.sleep(mock_delay_per_batch)

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

    translations_final = {}  # must be a dict, because it is used like a key-based lookup later

    # Pick up any existing translations from previous run.
    # Important for RESUME and MOCK MODE, otherwise previous results would get lost!
    if config.TRANSLATIONS_FINAL_FILE.exists():
        translations_final = fn.load_translations_final()
        fn.LOGGER(fn.batch_log_msg(f"Picked up {len(translations_final)} translations from previous run:"))
        # fn.LOGGER(f"{
        # to_multiline_text(
        #     input=translations_final,
        #     value_char_limit=50
        # )}")

    # ---------------------------------------------------
    # SAVE COLLECTED REVIEW ITEMS TO OUTPUT FOLDER
    # ---------------------------------------------------
    fn.LOGGER(fn.log_header(f"SAVE COLLECTED REVIEW ITEMS TO OUTPUT FOLDER"))

    review_items = []

    if config.PROGRESS_REVIEW_ITEMS_FILE.exists():
        review_items = fn.load_json_input(
            config.PROGRESS_REVIEW_ITEMS_FILE
        )

    if len(review_items) > 0:
        fn.save_json_output(
            review_items,
            config.REVIEW_ITEMS_FILE
        )
        fn.LOGGER(
            fn.batch_log_msg(f"{len(review_items)} Post-review item(s) written to {config.REVIEW_ITEMS_FILE}"),
            config.TAG_SUCCESS if len(review_items) == 0 else config.TAG_WARNING
        )
        # fn.LOGGER(fn.log(f"DEBUG - \n{fn.to_prettified_json(review_items)}"))
    else:
        fn.delete_file(config.REVIEW_ITEMS_FILE)


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
    fn.LOGGER(fn.log_header(f"APPLY TRANSLATIONS TO Babele"))

    fn.apply_translations(
        input_data,
        translatables,
        translations_final
    )
    fn.LOGGER(fn.batch_log_msg(f"{len(translations_final)} translations applied to original Babele data."))

    # -------
    # Tests:
    # -------
    # fn.LOGGER(
    #     f"DEBUG - Result of FIRST translation at Babele path: {loaded_translatables[0]["path"]}"
    #     f"\n=> {get_json_element(babele_json, loaded_translatables[0]["path"])}"
    #     f"\nDEBUG - Result of LAST translation at Babele path: {loaded_translatables[1]["path"]}"
    #     f"\n=> {get_json_element(babele_json, loaded_translatables[1]["path"])}"
    # )
    # fn.LOGGER(f"DEBUG - Final translation:"
    #     f"\n{stringify_json(babele_data)}"
    # )

    # ---------------------------------------------------
    # SAVE FINAL Babele FIILE
    # ---------------------------------------------------
    fn.LOGGER(fn.log_header(f"SAVE FINAL Babele FIILE"))
    fn.save_json_output(input_data, config.OUTPUT_FILE)

    # ------------------------------------------------------------
    # Stop global timer
    # ------------------------------------------------------------
    global_timer_end = time.perf_counter()
    fn.LOGGER(fn.batch_log_msg(
        f"TOTAL processing duration: {global_timer_end - global_timer_start:.2f} seconds"), config.TAG_INFO)
    fn.LOGGER(fn.batch_log_msg(f"Find the translated file here: {config.OUTPUT_FILE}"), config.TAG_INFO)

    if not fn.check_and_warn_if_mock_mode("THIS WAS ONLY A SIMULATION!"):

        current_time = datetime.now().strftime("%H:%M:%S")
        fn.LOGGER(fn.log_header(f"PROCESS COMPLETED SUCCESSFULLY (time: {current_time})"), config.TAG_SUCCESS)


def calc_mock_delay_per_batch(batches:list, status_key:str, logger) -> int | float:
    if not config.MOCK_MODE or batches is None or len(batches) == 0:
        return 0

    else:
        completed_statuses = ([config.COMPLETED]
                              if status_key == config.TERMINOLOGY_STATUS
                              else [config.COMPLETED, config.REVIEW_REQUIRED])

        cnt_batches = sum(1 for batch in batches if
                  batch[status_key] not in completed_statuses)

        if (cnt_batches == 0):
            return 0

        else:

            delay = fn.clamp(
                    config.MOCK_PROGRESSBAR_DURATION_SEC / cnt_batches,
                    0.25,
                    1)
            logger(f"Mock delay per batch: {delay} sec.")
            return delay


def abort_if_cancelled(cancel_event):
    if cancel_event is not None and cancel_event.is_set():
        raise exceptions.CancelledException()



