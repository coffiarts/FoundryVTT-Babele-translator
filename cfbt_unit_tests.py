import cfbt_config as config
import cfbt_core_functions as fn

# ------------------------------------------------------------
# Function: Check Result
# Utility used for running simple True/False checks and producing RED/GREEN colored output.
# Returns a result object containing:
# - PASSED/FAILED status
# - GREEN/RED color
# ------------------------------------------------------------
def check_result(result):

    if result is True:
        return {
            "status": config.PASSED,
            "color": config.CONSOLE_GREEN
        }
    else:
        return {
            "status": config.FAILED,
            "color": config.CONSOLE_RED
        }


def test_extract_translatables_from_babele(translatables):

    pass
    print(f"DEBUG - Content of first 10 translatables:"
        f"\n{fn.to_prettified_json(translatables[:10])}"
    )


def test_save_to_file(saved_data, loaded_data):

    print(f"UNIT TEST - Expected: {len(saved_data)}")
    result = check_result(len(saved_data) == len(loaded_data))
    print(
        f"UNIT TEST - Saved vs. Loaded count identical ({len(saved_data)} == {len(loaded_data)}): "
        f"{result["color"]}{result["status"]}{config.CONSOLE_RESET}"
    )
    if result["status"] == config.FAILED:
        exit("Terminated with Unit Test Failure!")

    # print(
    #     f"DEBUG - first entry identical: "
    #     f"{saved_data[0] == loaded_data[0]}"
    # )
    # print(
    #     f"DEBUG - last entry identical: "
    #     f"{saved_data[-1] == loaded_data[-1]}"
    # )


def test_create_translatables_with_placeholders(translatables_with_placeholders):

    all_text = "\n".join(
        translatable["text"]
        for translatable in translatables_with_placeholders
    )
    remainders = fn.find_patterns(all_text, config.PROTECTED_SYNTAX_PATTERNS, leading_trailing_chars=100)
    result = check_result(len(remainders) == 0)
    print(
        f"UNIT TEST - No of remaining foundry syntax matches == 0 ({len(remainders)}): "
        f"{result["color"]}{(result["status"])}{config.CONSOLE_RESET}"
    )
    if result["status"] == config.FAILED:
        print(
            f"{result["color"]}{fn.to_prettified_json(remainders)}{config.CONSOLE_RESET}"
        )
        exit("Terminated with Unit Test Failure!")

    # print(
    #     f"DEBUG - All Placeholders:\n"
    #     f"{to_prettified_json(placeholders)}"
    # )
    # print(
    #     f"DEBUG - All Translatables with placeholders:\n"
    #     f"{to_prettified_json([
    #         translatable
    #         for translatable in translatables_with_placeholders
    #         if any(
    #             placeholder in translatable["text"]
    #             for placeholder in placeholders
    #         )
    #     ])}"
    # )


def test_assemble_batch_payload(batch, batch_translatables):

    result = check_result(len(batch_translatables) == len(batch["translatable_ids"]))
    print(
        f"UNIT TEST - Translatables count in Batch identical to Loaded ({len(batch["translatable_ids"])} == {len(batch_translatables)}): "
        f"{result["color"]}{result["status"]}{config.CONSOLE_RESET}"
    )
    if result["status"] == config.FAILED:
        exit("Terminated with Unit Test Failure!")


def test_adapt_file_paths_idempotent():

    def snapshot():
        return {
            name: str(value)
            for name, value in vars(config).items()
            if name.endswith(("_DIR", "_FILE"))
        }

    before = snapshot()
    fn.adapt_file_paths()
    after = snapshot()

    result = check_result(before == after)
    print(
        f"UNIT TEST - adapt_file_paths() is idempotent: "
        f"{result["color"]}{result["status"]}{config.CONSOLE_RESET}"
    )
    if result["status"] == config.FAILED:
        changed = {k: {"before": before[k], "after": v} for k, v in after.items() if before[k] != v}
        print(f"{result["color"]}{fn.to_prettified_json(changed)}{config.CONSOLE_RESET}")
        exit("Terminated with Unit Test Failure!")
