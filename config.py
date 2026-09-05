import os
from pathlib import Path

INPUT_FILE_NAME = "dnd-example-file.json"

REBUILD_TERMINOLOGY_IF_EXISTS = False

MOCK_API_CALL = False # Default: False: If set to True, remote LLM requests/responses are only mocked (for testing surrounding logic without causing costs)

# --------------------------------------------------------------------
# --------------------------------------------------------------------
# --- RESUME-RELEVANT CORE CONFIGURATION
# --- The following params must not changed in between incremental
# --- runs for the same input file, because they control how text
# -- is being preprocessed and Batches are built
# --- See also: get_resume_relevant_config()
# --------------------------------------------------------------------
# --------------------------------------------------------------------

MAX_BATCH_SIZE = 50000

# TRANSLATABLE FIELDS
# Identifies translatable texts by their direct attribute names.
# If any plain attributes matching these names are found,
# their related value will get translated.
# Example:
#   "entries": {
#     "Bond": {
#       "name": "Bond",
# Will be translated to:
#   "entries": {
#     "Bond": {
#       "name": "Bindung",
TRANSLATABLE_FIELDS = {
    "text",
    "name",
    "caption",
    "description",
    "label"
}

# TRANSLATABLE CONTAINERS
# Identifies translatable texts by their parent's name.
# If any nodes (with children) matching these names are found,
# any values of their direct children will get translated, no matter how the child attributes are named.
# Example:
# "results": {
#     "1-1": "Result 1",
#     "2-2": "Result 2",
#     "3-3": "Result 3:
# Will be translated to:
# "results": {
#     "1-1": "Ergebnis 1",
#     "2-2": "Ergebnis 2",
#     "3-3": "Ergebnis 3:
TRANSLATABLE_CONTAINERS = {
    "folders",
    "results"
}

# Regular Expressions for identifying anything technical inside the translatable text that should not be touched
# by the translation and must therefor be masked temporarily by placeholders
FOUNDRY_SYNTAX_PATTERNS = {
    r'@(UUID|Embed|Compendium)\[[^\]]*\]',
    r'\[\[[^\]]*\]\]'
}

# The fixed pattern used for the numbered placeholders that temporarily replace text chunks identified
# by FOUNDRY_SYNTAX_PATTERNS
PLACEHOLDER_PATTERN = r'<<<FOUNDRY_\d{6}>>>' # MUST contain \d{<number>} to represent the increment number of n digits length

# --------------------------------------------------------------------
# --------------------------------------------------------------------
# --- END OF RESUME-RELEVANT CORE CONFIGURATION
# --------------------------------------------------------------------
# --------------------------------------------------------------------


# ------------------------------------------------------------
# LLM Parameters (change these only for translation fine-tuning)
# ------------------------------------------------------------

LLM_MODEL = "gpt-5.4-mini"

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

TERMINOLOGY_INSTRUCTIONS = """
You are a terminology analyst for a German translation of a
D&D 5e fantasy role-playing adventure.

Analyze the supplied English text and identify only terms that
are likely to require consistent translation across the adventure.

Prioritize:
- D&D rules terminology
- creature and monster names or types
- established fantasy and setting terminology
- names of places, people, factions, organizations, etc.
- terms whose German grammatical gender, number, or inflection
  could cause recurring translation errors
- terms whose translation is ambiguous or likely to be inconsistent

Do NOT include ordinary vocabulary, generic descriptive words,
or isolated words that do not require terminological consistency.

Proper names must remain untranslated by default.
This includes personal names, place names, organization names,
faction names, and other named entities.
Do not translate or localize a proper name unless the source
text itself clearly indicates that it is a translatable descriptive name.

For each selected term provide:
- the original English term
- your proposed German translation
- grammatical gender and number
- whether it is a proper name
- a short note explaining an important translation decision,
  ambiguity, or grammatical consideration

The proposed translations are suggestions only. Do not assume
that they are official D&D terminology.

Use English for all metadata and notes.

Return only valid JSON.
"""

TERMINOLOGY_OUTPUT_STRUCTURE = {
    "format": {
        "type": "json_schema",
        "name": "terminology",
        "strict": True,
        "schema": {
            "type": "object",
            "properties": {
                "terms": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "original": {
                                "type": "string"
                            },
                            "proposedGerman": {
                                "type": "string"
                            },
                            "gender": {
                                "type": "string"
                            },
                            "number": {
                                "type": "string"
                            },
                            "properName": {
                                "type": "boolean"
                            },
                            "note": {
                                "type": "string"
                            }
                        },
                        "required": [
                            "original",
                            "proposedGerman",
                            "gender",
                            "number",
                            "properName",
                            "note"
                        ],
                        "additionalProperties": False
                    }
                }
            },
            "required": [
                "terms"
            ],
            "additionalProperties": False
        }
    }
}


# ---------------------------------------------------------------------------
# Folders and file names (usually there's no reason to change any of these)
# ---------------------------------------------------------------------------

INPUT_FOLDER_NAME = "input"
PROGRESS_FOLDER_NAME = "progress"
TERMINOLOGY_FOLDER_NAME = "terminology"
SECRETS_FOLDER_NAME = "local_secret_do_not_commit"
OUTPUT_FOLDER_NAME = "output"

PROGRESS_INFO_FILE_NAME = "00-progress-info.json"
TRANSLATABLES_FILE_NAME = "01-translatables.json"
TRANSLATABLES_WITH_PLACEHOLDERS_FILE_NAME = "02-translatables-with-placeholders.json"
PLACEHOLDERS_FILE_NAME = "03-placeholders.json"
BATCHES_FILE_NAME = "04-batches.json"
TERMINOLOGY_FILE_NAME = f"{INPUT_FILE_NAME.removesuffix(".json")}-terminology.json"
TRANSLATIONS_WITH_PLACEHOLDERS_FILE_NAME = "05-translations-with-placeholders.json"
TRANSLATIONS_FINAL_FILE_NAME = "06-translations-final.json"
ERRORS_FILE_NAME = "99-errors.json"
REVIEW_ITEMS_FILE_NAME = f"{INPUT_FILE_NAME.removesuffix(".json")}-review-items.json"
APIKEY_FILE_NAME = "openai_api_key.txt"


# ------------------------------------------------------------
# String Constants (better not edit at all!)
# ------------------------------------------------------------

# Run Mode
NEW_RUN = "NEW_RUN"
RESUME = "RESUME"

# Batch Status
TERMINOLOGY_STATUS = "terminology_status"
TRANSLATION_STATUS = "translation_status"
UNPROCESSED = "UNPROCESSED"
PROCESSING = "PROCESSING"
FAILED = "FAILED"
COMPLETED = "COMPLETED"
ERROR = "ERROR"

# Test Result
PASSED = "PASSED" # FAILED can be reused from above

# Colors
RED    = "\033[31m"
GREEN  = "\033[32m"
YELLOW = "\033[33m"
BLUE   = "\033[34m"
MAGENTA = "\033[35m"
CYAN = "\033[36m"
WHITE = "\033[37m"
COLOR_RESET  = "\033[0m"

# Error Types
PLACEHOLDER_TRANSLATION_ERROR = "PLACEHOLDER_TRANSLATION_ERROR"

# ---------------------------------------------------------------
# Preprocess configuration (do not edit under ANY circumstance!)
# ---------------------------------------------------------------
INPUT_FILE = Path(INPUT_FOLDER_NAME) / INPUT_FILE_NAME
OUTPUT_FILE = Path(OUTPUT_FOLDER_NAME) / INPUT_FILE_NAME

# create subfolders if necessary
PROGRESS_FOLDER_NAME = Path(PROGRESS_FOLDER_NAME) / INPUT_FILE_NAME.removesuffix(".json")
if not os.path.exists(PROGRESS_FOLDER_NAME):
    os.makedirs(PROGRESS_FOLDER_NAME)
if not os.path.exists(OUTPUT_FOLDER_NAME):
    os.makedirs(OUTPUT_FOLDER_NAME)

PROGRESS_INFO_FILE = Path(PROGRESS_FOLDER_NAME) / PROGRESS_INFO_FILE_NAME
TRANSLATABLES_FILE = Path(PROGRESS_FOLDER_NAME) / TRANSLATABLES_FILE_NAME
TRANSLATABLES_WITH_PLACEHOLDERS_FILE = Path(PROGRESS_FOLDER_NAME) / TRANSLATABLES_WITH_PLACEHOLDERS_FILE_NAME
PLACEHOLDERS_FILE = Path(PROGRESS_FOLDER_NAME) / PLACEHOLDERS_FILE_NAME
BATCHES_FILE = Path(PROGRESS_FOLDER_NAME) / BATCHES_FILE_NAME
TERMINOLOGY_FILE = Path(TERMINOLOGY_FOLDER_NAME) / TERMINOLOGY_FILE_NAME
TRANSLATIONS_WITH_PLACEHOLDERS_FILE = Path(PROGRESS_FOLDER_NAME) / TRANSLATIONS_WITH_PLACEHOLDERS_FILE_NAME
TRANSLATIONS_FINAL_FILE = Path(PROGRESS_FOLDER_NAME) / TRANSLATIONS_FINAL_FILE_NAME
REVIEW_ITEMS_FILE = Path(OUTPUT_FOLDER_NAME) / REVIEW_ITEMS_FILE_NAME

ERRORS_FILE = Path(PROGRESS_FOLDER_NAME) / ERRORS_FILE_NAME
APIKEY_FILE = Path(SECRETS_FOLDER_NAME) / APIKEY_FILE_NAME

