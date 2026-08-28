import json
import re
import time
from pathlib import Path
from collections import Counter
from openai import OpenAI

# ------------------------------------------------------------
# Configuration
# ------------------------------------------------------------

FILENAME = "adventures-test.json"
MAX_CHARS_PER_CHUNK = 50000 # It may (unproven) help to scale this with the overall input size (larger input => larger batch size)

ERROR_FILENAME = (
    f"errors/"
    f"{FILENAME}-errors.txt"
)

TRANSLATABLE_FIELDS = {
    "text",
    "name",
    "caption",
    "description"
}

TRANSLATION_INSTRUCTIONS = """
Translate every text to German.

Return ONLY valid JSON.

Input format:

[
  {
    "id": 123,
    "text": "some text"
  }
]

Output format:

[
  {
    "id": 123,
    "translation": "übersetzter Text"
  }
]

Rules:
- Preserve every id unchanged.
- Translate only the text.
- Do not omit entries.
- Do not add entries.
- Return only JSON.

A placeholder always belongs to the label that follows it.

When translating, the label may be translated and moved
to a different position in the sentence if German grammar
requires it.

However, the placeholder must move together with the label.

Input:
They are loyal to <<<FOUNDRY_000001>>>{King Grol}.

Correct output:
Sie sind <<<FOUNDRY_000001>>>{König Grol} gegenüber loyal.

Incorrect output:
Sie sind König Grol gegenüber loyal.
"""

# ------------------------------------------------------------
# Function: Global placeholder registry
# ------------------------------------------------------------

protected_elements = {}

# ------------------------------------------------------------
# Function: Collect translatable nodes
# ------------------------------------------------------------

def collect_translatable_nodes(value, nodes):

    if isinstance(value, dict):

        for key, item in value.items():

            if (
                    key in TRANSLATABLE_FIELDS
                    and isinstance(item, str)
            ):

                nodes.append({
                    "id": len(nodes),
                    "container": value,
                    "key": key,
                    "original": item
                })

            elif isinstance(item, (dict, list)):

                collect_translatable_nodes(
                    item,
                    nodes
                )

    elif isinstance(value, list):

        for item in value:

            collect_translatable_nodes(
                item,
                nodes
            )


# ------------------------------------------------------------------
# Function: Protect & Restore Foundry Syntax (aka "Protection by Placeholder")
# ------------------------------------------------------------------

def protect_foundry_syntax(text):

    def replace(match):

        placeholder = (
            f"<<<FOUNDRY_{len(protected_elements):06d}>>>"
        )

        protected_elements[
            placeholder
        ] = match.group(0)

        return placeholder

    # Protect Foundry @UUID[...] and @Embed[...] syntax
    text = re.sub(
        r'@(UUID|Embed|Compendium)\[[^\]]*\]',
        replace,
        text
    )

    # Protect inline rolls, checks, saves, etc.
    text = re.sub(
        r'\[\[[^\]]*\]\]',
        replace,
        text
    )

    return text


def restore_foundry_syntax(
        text,
        protected
):
    for placeholder, original in protected.items():

        text = text.replace(
            placeholder,
            original
        )

    return text


# ------------------------------------------------------------
# Function: Extract Response Metadata
# ------------------------------------------------------------

def extract_response_metadata(
        response
):
    # Debugging only
    # print(type(response))
    # print(dir(response))

    return {
        "status": response.status,
        "incomplete_details": response.incomplete_details,
        "truncation": response.truncation
    }

# ------------------------------------------------------------
# Function: Verify placeholder integrity
# ------------------------------------------------------------

def verify_protected_integrity(
        original_protected_text,
        translated_text):

    placeholders = set(
        re.findall(
            r'<<<FOUNDRY_\d{6}>>>',
            original_protected_text
        )
    )

    for placeholder in placeholders:

        count = translated_text.count(
            placeholder
        )

        if count != 1:

            print(
                f"\n❌ PLACEHOLDER ERROR: "
                f"{placeholder}"
            )

            print(
                f"Occurrences in translation: "
                f"{count}"
            )

            print(
                f"\nTranslated text (missing {placeholder}): "
                f"{translated_text}"
            )

            print(
                f"\nOriginal text (should contain {placeholder}): "
                f"{original_protected_text}"
            )

            print(
                f"\n=== PROTECTED ELEMENT ===\n"
                f"{placeholder} -> {protected_elements[placeholder]}"
            )

            position = original_protected_text.find(
                placeholder
            )

            start = max(
                0,
                position - 200
            )

            end = min(
                len(original_protected_text),
                position + len(placeholder) + 200
            )

            return {
                "placeholder": placeholder,
                "count": count,
                "translated_context": translated_text[
                    max(0, position - 300):
                    min(len(translated_text), position + 300)
                ],
                "original_context": original_protected_text[
                    start:end
                ]
            }

            # raise ValueError(
            #     f"Placeholder integrity failure: "
            #     f"{placeholder}"
            # )

    return None

# ----------------------------------------------------------------------------
# Function: Post Mortem Dump
# (used by all FATAL error cases to rescue as much processed data as possible)
# ----------------------------------------------------------------------------

def post_mortem_dump(
        title,
        details,
        raw_response=None,
        response_metadata=None,
        translations=None,
        protected_elements=None,
        integrity_errors=None
):

    with open(
            ERROR_FILENAME,
            "w",
            encoding="utf-8"
    ) as file:

        file.write(
            "====================================================\n"
        )

        file.write(
            f"{title}\n"
        )

        file.write(
            "====================================================\n\n"
        )

        file.write(
            f"{details}\n\n"
        )

        if response_metadata is not None:

            file.write(
                "====================================================\n"
                "RESPONSE METADATA\n"
                "====================================================\n\n"
            )

            file.write(
                json.dumps(
                    response_metadata,
                    indent=2,
                    ensure_ascii=False
                )
            )

            file.write("\n\n")

        if raw_response is not None:

            file.write(
                "====================================================\n"
                "RAW RESPONSE OUTPUT\n"
                "====================================================\n\n"
            )

            file.write(
                f"{raw_response}\n\n"
            )

        if integrity_errors is not None:

            file.write(
                "====================================================\n"
                "COLLECTED INTEGRITY ERRORS\n"
                "====================================================\n\n"
            )

            file.write(
                json.dumps(
                    integrity_errors,
                    indent=2,
                    ensure_ascii=False
                )
            )

            file.write("\n\n")

        if translations is not None:

            file.write(
                "====================================================\n"
                "COMPLETED TRANSLATIONS\n"
                "====================================================\n\n"
            )

            file.write(
                json.dumps(
                    translations,
                    indent=2,
                    ensure_ascii=False
                )
            )

            file.write("\n\n")

        if protected_elements is not None:

            file.write(
                "====================================================\n"
                "PROTECTED ELEMENTS\n"
                "====================================================\n\n"
            )

            file.write(
                json.dumps(
                    protected_elements,
                    indent=2,
                    ensure_ascii=False
                )
            )

            file.write("\n\n")

    print(
        f"\n❌ POST-MORTEM DUMP WRITTEN"
    )

    print(
        f"{ERROR_FILENAME}"
    )


# ------------------------------------------------------------
# Function: Reinsert translations
# ------------------------------------------------------------

def reinsert_translations(
        nodes,
        translations
):

    for node in nodes:

        node["container"][node["key"]] = (
            translations[node["id"]]
        )

# ------------------------------------------------------------
# Load JSON: Input file and (master) terminology file
# ------------------------------------------------------------

global_timer_start = time.perf_counter()

input_path = (
        Path("input")
        / FILENAME
)

with input_path.open(
        "r",
        encoding="utf-8"
) as file:

    original_data = json.load(file)

print(
    f"\n=== PROCESSING FILE: {input_path} ===\n"
    f"Batch Size: max. {MAX_CHARS_PER_CHUNK} chars (excluding instructions & terminology)"
)

master_terminology_filename = f"terminology/terminology-{FILENAME}"

with open(
        master_terminology_filename,
        "r",
        encoding="utf-8"
) as file:

    master_terminology = json.load(file)

master_terminology_json = json.dumps(
    master_terminology,
    ensure_ascii=False,
    indent=2
)


print(
    f"\n=== MASTER TERMINOLOGY (derived from complete input file) ===\n"
    f"source: {master_terminology_filename}\n"
    f"term count: {len(master_terminology["terms"])}\n"
    f"json chars: {len(master_terminology_json):,}"
)

# ------------------------------------------------------------
# Initialize LLM API client
# ------------------------------------------------------------

api_key = Path(
    "local_secret_do_not_commit/openai_api_key.txt"
).read_text(
    encoding="utf-8"
).strip()

client = OpenAI(
    api_key=api_key
)

# ------------------------------------------------------------
# Deep copy for testing
# ------------------------------------------------------------

working_data = json.loads(
    json.dumps(
        original_data,
        ensure_ascii=False
    )
)


# ------------------------------------------------------------
# Collect nodes
# ------------------------------------------------------------

nodes = []

collect_translatable_nodes(
    working_data,
    nodes
)

# ------------------------------------------------------------
# Build chunks
# ------------------------------------------------------------

chunks = []
current_chunk = []
current_size = 0

for node in nodes:

    text_size = len(node["original"])

    if (
            current_chunk
            and current_size + text_size > MAX_CHARS_PER_CHUNK
    ):
        chunks.append(current_chunk)
        current_chunk = []
        current_size = 0

    current_chunk.append(node)
    current_size += text_size

if current_chunk:
    chunks.append(current_chunk)

print(
    f"\n=== CHUNKS SPLIT: {len(chunks)} ==="
)

for i, chunk in enumerate(chunks):

    chars = sum(
        len(node["original"])
        for node in chunk
    )

    print(
        f"Chunk {i}: "
        f"{len(chunk)} nodes, "
        f"{chars:,} chars"
    )


# ------------------------------------------------------------
# Optional inspection
# ------------------------------------------------------------

# Summary of payload contents
print(
    f"\n=== TRANSLATABLE NODES ===: {len(nodes)}\n"
)

complete_payload = []

for node in nodes:

    complete_payload.append({
        "id": node["id"],
        "field": node["key"],
        "text": node["original"]
    })

with open(
        "analyze/translation_payload.json",
        "w",
        encoding="utf-8"
) as file:

    json.dump(
        complete_payload,
        file,
        ensure_ascii=False,
        indent=2
    )

chunk_payload_json = json.dumps(
    complete_payload,
    ensure_ascii=False
)

print(
    f"\n=== PAYLOAD STATS ==="
)

print(
    f"Total Payload char count: "
    f"{len(chunk_payload_json):,}"
)

counter = Counter(
    node["key"]
    for node in nodes
)

print(counter)

chars_per_field = {}

for field in ["name", "description", "text", "caption"]:

    chars_per_field[field] = sum(
        len(node["original"])
        for node in nodes
        if node["key"] == field
    )

print(f"chars_per_field: {chars_per_field}")

# print(
#     f"\n=== FIRST 10 NODES DETAILS ==="
# )
#
# for node in nodes[:10]:
#
#     print(
#         f"\nID: {node['id']}"
#     )
#
#     print(
#         f"CONTAINER length: {len(node['container'])}"
#     )
#
#     print(
#         f"FIELD: {node['key']}"
#     )
#
#     print(
#         f"ORIGINAL [first <=100 of {len(node["original"])} chars]: {node["original"][:100]}"
#     )


# ------------------------------------------------------------
# Translate the compendium (chunk-wise)
# ------------------------------------------------------------

translations = {}

integrity_errors = []

print(
    f"\n=== PROCESSING {len(chunks)} CHUNKS ==="
)

for chunk_index, chunk in enumerate(chunks):

    # Only for debugging (stop-after-n-chunks switch)
    # if (chunk_index > 2):
    #     exit()

    chunk_text = "\n".join(
        node["original"]
        for node in chunk
    )

    print(
        f"\n"
        f"Processing chunk {chunk_index + 1}/{len(chunks)} [{len(chunk_text)} chars]\n"
        f"---------------------------------\n"
    )

    # ----------------------------------------------------------
    # Build chunk-specific sub-terminology from master terminology
    # ----------------------------------------------------------

    chunk_text = "\n".join(
        node["original"]
        for node in chunk
    )

    chunk_text_lower = chunk_text.lower()

    chunk_relevant_terms = [
        term
        for term in master_terminology["terms"]
        if term["original"].lower() in chunk_text_lower
    ]

    chunk_relevant_terminology = {
        "terms": chunk_relevant_terms
    }

    chunk_relevant_terminology_json = json.dumps(
        chunk_relevant_terminology,
        ensure_ascii=False,
        indent=2
    )

    chunk_instructions_with_terminology = (
            TRANSLATION_INSTRUCTIONS
            + "\n\n"
            + "=== TERMINOLOGY DATABASE ===\n"
            + chunk_relevant_terminology_json
            + "\n\n"
            + "=== END TERMINOLOGY DATABASE ===\n"
    )

    # ----------------------------------------
    # Build payload for this chunk
    # ----------------------------------------

    chunk_payload = []

    protected_texts = {}

    protected_texts.update("")

    for node in chunk:

        protected_text = protect_foundry_syntax(
            node["original"]
        )

        protected_texts[
            node["id"]
        ] = protected_text

        chunk_payload.append({
            "id": node["id"],
            "text": protected_text
        })

    chunk_payload_json = json.dumps(
        chunk_payload,
        ensure_ascii=False
    )

    print(
        f"Terminology: {len(chunk_relevant_terminology["terms"]):,} terms, {len(chunk_relevant_terminology_json):,} json chars\n"
        f"Content: {len(chunk_payload):,} entries, {len(chunk_payload_json):,} chars\n",
        # f"Full instructions text (incl. terminology):\n{chunk_instructions_with_terminology}" # this may be LARGE - activate only for debugging!
    )


    # ----------------------------------------
    # Translate the current chunk
    # ----------------------------------------

    chunk_timer_start = time.perf_counter()

    response = client.responses.create(
        model="gpt-5.4-mini",
        instructions=chunk_instructions_with_terminology,
        input=json.dumps(
            chunk_payload,
            ensure_ascii=False
        )
    )

    chunk_timer_end = time.perf_counter()

    # Store response info for potential later debugging or dumping
    # (for tracing API response issues)
    response_metadata = (
        extract_response_metadata(
            response
        )
    )

    print(
        f"Chunk {chunk_index + 1}/{len(chunks)} API duration: "
        f"{chunk_timer_end - chunk_timer_start:.2f} seconds"
    )

    print(
        f"Response length: "
        f"{len(response.output_text):,}"
    )

    # Large! Activate for debugging only
    # print(
    #     f"Response content: "
    #     f"{response.output_text}"
    # )

    try:
        translated_payload = json.loads(
            response.output_text
        )

    except Exception as e:

        post_mortem_dump(
            title="FATAL ERROR",
            details=(
                f"{type(e).__name__}\n"
                f"{str(e)}"
            ),
            raw_response=response.output_text,
            translations=translations,
            protected_elements=protected_elements,
            integrity_errors=integrity_errors
        )

        raise

    expected_entries = len(
        chunk_payload
    )

    returned_entries = len(
        translated_payload
    )

    print(
        f"Expected entries: "
        f"{expected_entries}"
    )

    print(
        f"Returned entries: "
        f"{returned_entries}"
    )

    if returned_entries != expected_entries:

        # FATAL ERROR: Returned entries do not match expected entries- Immediate dump and abort.

        with open(
                ERROR_FILENAME,
                "w",
                encoding="utf-8"
        ) as file:

            file.write(
                "====================================================\n"
                "FATAL ERROR\n"
                "====================================================\n\n"
            )

            file.write(
                f"Chunk: "
                f"{chunk_index + 1}\n"
            )

            file.write(
                f"Expected entries: "
                f"{expected_entries}\n"
            )

            file.write(
                f"Returned entries: "
                f"{returned_entries}\n\n"
            )

            file.write(
                "====================================================\n"
                "RAW RESPONSE OUTPUT\n"
                "====================================================\n\n"
            )

            file.write(
                response.output_text
            )

            post_mortem_dump(
                title="FATAL ERROR",
                details=(
                    f"Chunk: {chunk_index + 1}\n"
                    f"Expected entries: {expected_entries}\n"
                    f"Returned entries: {returned_entries}"
                ),
                raw_response=response.output_text,
                response_metadata=response_metadata,
                translations=translations,
                protected_elements=protected_elements,
                integrity_errors=integrity_errors
            )

            raise RuntimeError(
                f"❌ FATAL: Chunk "
                f"{chunk_index + 1} "
                f"returned "
                f"{returned_entries} "
                f"entries instead of "
                f"{expected_entries}"
            )

    chunk_translations = {}

    for entry in translated_payload:

        error = verify_protected_integrity(
            protected_texts[
                entry["id"]
            ],
            entry["translation"]
        )

        if error:
            integrity_errors.append(
                error
            )

        restored_text = restore_foundry_syntax(
            entry["translation"],
            protected_elements
        )

        chunk_translations[
            entry["id"]
        ] = restored_text

    translations.update(
        chunk_translations
    )


    # ----------------------------------------
    # Merge into global translations
    # ----------------------------------------

    translations.update(
        chunk_translations
    )

print(
    f"\n=== PROTECTED ELEMENTS "
    f"({len(protected_elements)}) ==="
)

for placeholder, original in protected_elements.items():

    print(
        f"{placeholder} -> {original}"
    )

# ------------------------------------------------------------
# Reinsert
# ------------------------------------------------------------

reinsert_translations(
    nodes,
    translations
)


# ------------------------------------------------------------
# Final stats
# ------------------------------------------------------------

print(
    f"\n=== FINAL STATS ==="
)

total_chars = sum(
    len(node["original"])
    for node in nodes
)

print(
    f"Total translatable chars: "
    f"{total_chars:,}"
)

original_json = json.dumps(
    original_data,
    ensure_ascii=False,
    indent=2
)

total_translatable_chars = sum(
    len(node["original"])
    for node in nodes
)

print(
    f"Original JSON chars: {len(original_json):,}"
)

print(
    f"Translatable chars: {total_translatable_chars:,}"
)

print(
    f"Reduction: "
    f"{100 * (1 - total_translatable_chars / len(original_json)):.1f}%"
)

print(
    f"Total nodes to translate: "
    f"{len(nodes):,}"
)

print(
    f"Average chars per node: "
    f"{total_translatable_chars / len(nodes):.1f}"
)
print("\n✅ REINJECTION COMPLETED")

# ------------------------------------------------------------
# Save the results to output
# ------------------------------------------------------------

with open(
        f"output/{FILENAME}",
        "w",
        encoding="utf-8"
) as file:

    json.dump(
        working_data,
        file,
        ensure_ascii=False,
        indent=2
    )

print(f"\n✅ Translated file written to: output/{FILENAME}")

# ------------------------------------------------------------
# Deal with collected INTEGRITY ERRORS
# ------------------------------------------------------------
if len(integrity_errors) > 0:

    with open(
            ERROR_FILENAME,
            "w",
            encoding="utf-8"
    ) as file:

        file.write(
            f"=== INTEGRITY ERRORS ===\n"
            f"{len(integrity_errors)}\n\n"
        )

        for index, error in enumerate(
                integrity_errors,
                start=1
        ):

            file.write(
                "====================================================\n"
            )

            file.write(
                f"ERROR {index} OF "
                f"{len(integrity_errors)}\n"
            )

            file.write(
                "====================================================\n\n"
            )

            file.write(
                f"Placeholder:\n"
                f"{error['placeholder']}\n\n"
            )

            file.write(
                f"Original value:\n"
                f"{protected_elements[error['placeholder']]}\n\n"
            )

            file.write(
                f"Original context:\n"
                f"{error['original_context']}\n\n"
            )

            file.write(
                f"Translated context:\n"
                f"{error['translated_context']}\n\n"
            )

    print(
        f"\n❌ INTEGRITY ERRORS: {len(integrity_errors)}\n"
        f"Integrity report written to: {ERROR_FILENAME}"
    )

    # for error in integrity_errors:
    #
    #     print("\n------------------")
    #
    #     print(
    #         f"Placeholder: "
    #         f"{error['placeholder']}"
    #     )
    #
    #     print(
    #         f"Original value: "
    #         f"{protected_elements[error['placeholder']]}"
    #     )
    #
    #     print(
    #         f"Original context:\n"
    #         f"{error['original_context']}"
    #     )
    #
    #     print(
    #         f"Translated context:\n"
    #         f"{error['translated_context']}"
    #     )

else:
    print(
        f"\n✅ NO INTEGRITY ERRORS\n"
    )

global_timer_end = time.perf_counter()

print(
    f"\nTOTAL processing duration: "
    f"{global_timer_end - global_timer_start:.2f} seconds"
)