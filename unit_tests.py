from config import *
from shared_functions import *

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
            "status": PASSED,
            "color": GREEN
        }
    else:
        return {
            "status": FAILED,
            "color": RED
        }


def test_extract_translatables_from_babele(translatables):

    pass
    # print(f"DEBUG - Content of first 10 translatables:"
    #     f"\n{stringify_json(translatables[:10])}"
    # )


def test_save_translatables(translatables, loaded_translatables):

    print(f"UNIT TEST - Expected: {len(translatables)}")
    result = check_result(len(translatables) == len(loaded_translatables))
    print(
        f"UNIT TEST - Translatables count identical ({len(translatables)} == {len(loaded_translatables)}): "
        f"{result["color"]}{result["status"]}{RESET}"
    )
    if result["status"] == FAILED:
        exit("Terminated with Unit Test Failure!")

    # print(
    #     f"DEBUG - first translatable identical: "
    #     f"{translatables[0] == loaded_translatables[0]}"
    # )
    # print(
    #     f"DEBUG - last translatable identical: "
    #     f"{translatables[-1] == loaded_translatables[-1]}"
    # )


def test_create_translatables_with_placeholders(translatables_with_placeholders):

    all_text = "\n".join(
        translatable["original"]
        for translatable in translatables_with_placeholders
    )
    remainders = find_patterns(all_text, FOUNDRY_SYNTAX_PATTERNS, leading_trailing_chars=100)
    result = check_result(len(remainders) == 0)
    print(
        f"UNIT TEST - No of remaining foundry syntax matches == 0 ({len(remainders)}): "
        f"{result["color"]}{(result["status"])}{RESET}"
    )
    if result["status"] == FAILED:
        print(
            f"{result["color"]}{to_prettified_json(remainders)}{RESET}"
        )
        exit("Terminated with Unit Test Failure!")

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


def test_save_translatables_with_placeholders(translatables, placeholders):

    loaded_translatables_with_placeholders = load_translatables(with_placeholders=True)
    print(f"UNIT TEST - Expected: {len(translatables)}")
    result = check_result(len(translatables) == len(loaded_translatables_with_placeholders))
    print(
        f"UNIT TEST - Translatables with Placeholders count identical ({len(translatables)} == {len(loaded_translatables_with_placeholders)}): "
        f"{result["color"]}{result["status"]}{RESET}"
    )
    if result["status"] == FAILED:
        exit("Terminated with Unit Test Failure!")

    loaded_placeholders = load_placeholders()
    print(f"UNIT TEST - Expected: {len(placeholders)}")
    result = check_result(len(placeholders) == len(loaded_placeholders))
    print(
        f"UNIT TEST - Placeholder count identical ({len(placeholders)} == {len(loaded_placeholders)}): "
        f"{result["color"]}{result["status"]}{RESET}"
    )
    if result["status"] == FAILED:
        exit("Terminated with Unit Test Failure!")


def test_save_batches(batches):

    print(f"UNIT TEST - Expected: {len(batches)}")
    loaded_batches = load_batches()

    result = check_result(len(batches) == len(loaded_batches))
    print(
        f"UNIT TEST - Batches count identical ({len(batches)} == {len(loaded_batches)}): "
        f"{result["color"]}{result["status"]}{RESET}"
    )
    if result["status"] == FAILED:
        exit("Terminated with Unit Test Failure!")

    # print(
    #     f"DEBUG - first batch identical: "
    #     f"{batches[0] == loaded_batches[0]}"
    # )
    #
    # print(
    #     f"DEBUG - last batch identical: "
    #     f"{batches[-1] == loaded_batches[-1]}"
    # )


def test_assemble_batch_payload(batch, batch_translatables):

    result = check_result(len(batch_translatables) == len(batch["translatable_ids"]))
    print(
        f"UNIT TEST - Translatables count in Batch identical to Loaded ({len(batch["translatable_ids"])} == {len(batch_translatables)}): "
        f"{result["color"]}{result["status"]}{RESET}"
    )
    if result["status"] == FAILED:
        exit("Terminated with Unit Test Failure!")







