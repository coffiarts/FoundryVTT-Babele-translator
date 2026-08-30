import time
from shared_functions import *

# -------------------------------------------------------------------------------------------------------
# This controls the main process of translating a Babele input file:
# - import from Babele file
# - extract translatables
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

print(f"\n=== LOAD INPUT FILE (Babele translation JSON exported from FoundryVTT) ===")

babele_json = load_json_input(INPUT_FILE)
babele_chars_cnt = json.dumps(
    babele_json,
    ensure_ascii=False,
    indent=2
)

print(f"loaded: {len(babele_chars_cnt)} chars from {INPUT_FILE} ===")

print(f"\n=== IMPORT TRANSLATABLES ===")

translatables = []
extract_translatables_from_babele(
    input=babele_json,
    translatables=translatables,
    current_path=[]
)
translatables_imported_cnt = len(translatables)

print(f"extracted: {translatables_imported_cnt} translatables")
# print(f"DEBUG - Content of first 10 translatables:"
#     f"\n{json.dumps(
#         translatables[:10],
#         ensure_ascii=False,
#         indent=2)}"
# )

print(f"\n=== SAVE TRANSLATABLES TO PROGRESS FOLDER ===")

save_json_output(translatables, TRANSLATABLES_FILE)
loaded_translatables = load_json_input(TRANSLATABLES_FILE)

print(f"loaded {len(loaded_translatables)} translatables. Expected: {translatables_imported_cnt}")
print(
    f"DEBUG - first translatable identical: "
    f"{translatables[0] == loaded_translatables[0]}"
)
print(
    f"DEBUG - last translatable identical: "
    f"{translatables[-1] == loaded_translatables[-1]}"
)

print(f"\n=== APPLY TRANSLATIONS ===")

apply_translations(
    babele_json,
    loaded_translatables,
    {
        0: "[FIRST TRANSLATED]",
        1: "[LAST TRANSLATED]"
    } # just a mock-up for now
)
# print(
#     f"DEBUG - Result of FIRST translation at Babele path: {loaded_translatables[0]["path"]}"
#     f"\n=> {get_json_element(babele_json, loaded_translatables[0]["path"])}"
#     f"\nDEBUG - Result of LAST translation at Babele path: {loaded_translatables[1]["path"]}"
#     f"\n=> {get_json_element(babele_json, loaded_translatables[1]["path"])}"
# )
# print(f"DEBUG - Final translation:"
#     f"\n{json.dumps(
#         babele_json,
#         ensure_ascii=False,
#         indent=2)}"
# )

print(f"\n=== SAVE FINAL Babele FIILE ===")
save_json_output(babele_json, OUTPUT_FILE)


# ------------------------------------------------------------
# Stop global timer
# ------------------------------------------------------------

global_timer_end = time.perf_counter()
print(f"\n=== TOTAL processing duration: {global_timer_end - global_timer_start:.2f} seconds ===")
