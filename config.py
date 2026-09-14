from pathlib import Path

# ------------------------------------------------------------
# Language to translate from/to
# ------------------------------------------------------------

SOURCE_LANGUAGE = {
    "code": "en",
    "name": "English"
}

# Some other supported languages (quickly tested): fr/French, it/Italian, es/Spanish, ja/Japanese
TARGET_LANGUAGE = {
    "code": "de",
    "name": "German" # Always use the english name here
}

# --------------------------------------------------------------------
# --------------------------------------------------------------------
# --- RESUME-RELEVANT CORE CONFIGURATION
# --- The following params must not changed in between incremental
# --- runs for the same input file, because they control how text
# -- is being preprocessed and Batches are built
# --- See also: get_resume_relevant_config()
# --------------------------------------------------------------------
# --------------------------------------------------------------------

MOCK_MODE = True # Default: False: If set to True, remote LLM requests/responses are only mocked (for testing surrounding logic without causing costs)

GAME_SYSTEM_CONTEXT = "D&D 5e" # Used in translation instructions. Free prompt-style. Always use the english name here, optionally enrich it by a translation, like: "The Dark Eye (aka 'Das Schwarze Auge')

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
    "results",
    "drawings"
}

# Regular Expressions for identifying anything technical inside the translatable text that should not be touched
# by the translation and must therefor be masked temporarily by placeholders
PROTECTED_SYNTAX_PATTERNS = {
    r'@(UUID|Embed|Compendium)\[[^\]]*\]',
    r'\[\[[^\]]*\]\]'
}

# The fixed pattern used for the numbered placeholders that temporarily replace text chunks identified
# by FOUNDRY_SYNTAX_PATTERNS
PLACEHOLDER_PATTERN = r'<<<PLACEHOLDER_\d{6}>>>' # MUST contain \d{<number>} to represent the increment number of n digits length

# --------------------------------------------------------------------
# --------------------------------------------------------------------
# --- END OF RESUME-RELEVANT CORE CONFIGURATION
# --------------------------------------------------------------------
# --------------------------------------------------------------------


# ------------------------------------------------------------
# LLM Parameters (change these only for translation fine-tuning)
# ------------------------------------------------------------

# LLM_MODEL = "gpt-5.4-mini"
LLM_MODEL = "gpt-5.6-luna"

TRANSLATION_INSTRUCTIONS = f"""
Translate every text to {TARGET_LANGUAGE["name"]}.

Return ONLY valid JSON.

Input format:

[
  {{
    "id": 123,
    "text": "some text"
  }}
]

Output format:

[
  {{
    "id": 123,
    "translation": "übersetzter Text"
  }}
]

Rules:
- Preserve every id unchanged.
- Translate only the text.
- Do not omit entries.
- Do not add entries.
- Return only JSON.

A placeholder always belongs to the label that follows it.

When translating, the label may be translated and moved
to a different position in the sentence if {TARGET_LANGUAGE["name"]} grammar
requires it.

However, the placeholder must move together with the label.

Input:
They are loyal to <<<FOUNDRY_000001>>>{{King Grol}}.

German example ...

Correct output:
Sie sind <<<FOUNDRY_000001>>>{{König Grol}} gegenüber loyal.

Incorrect output:
Sie sind König Grol gegenüber loyal.
"""

TERMINOLOGY_INSTRUCTIONS = f"""
You are a terminology analyst for a {TARGET_LANGUAGE["name"]} translation of a
{GAME_SYSTEM_CONTEXT} fantasy role-playing adventure.

Analyze the supplied {SOURCE_LANGUAGE["name"]} text and identify only terms that
are likely to require consistent translation across the adventure.

Prioritize:
- {GAME_SYSTEM_CONTEXT} rules terminology
- creature and monster names or types
- established fantasy and setting terminology
- names of places, people, factions, organizations, etc.
- terms whose {TARGET_LANGUAGE["name"]} grammatical gender, number, or inflection
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
- the original {SOURCE_LANGUAGE["name"]} term
- your proposed {TARGET_LANGUAGE["name"]} translation
- grammatical gender and number
- whether it is a proper name
- a short note explaining an important translation decision,
  ambiguity, or grammatical consideration

The proposed translations are suggestions only. Do not assume
that they are official {GAME_SYSTEM_CONTEXT} terminology.

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
                            "proposedTranslation": {
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
                            "proposedTranslation",
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


# ------------------------------------------------------------
# String Constants (better not edit at all!)
# ------------------------------------------------------------

# Run Modes
NEW_RUN = "NEW_RUN"
RESUME = "RESUME"
POSTPROCESSING_ONLY = "POSTPROCESSING_ONLY"

# Input Types
INPUT_TYPE_BABELE = "Babele JSON export"
INPUT_TYPE_LOCALIZATION = "Localization file (lang/*.json)"

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

# Console Colors &  Formatting
RED    = "\033[31m"
GREEN  = "\033[32m"
YELLOW = "\033[33m"
BLUE   = "\033[34m"
MAGENTA = "\033[35m"
CYAN = "\033[36m"
WHITE = "\033[37m"
HEADER = "\033[95m"
BOLD = "\033[1m"
UNDERLINE = "\033[4m"
RESET  = "\033[0m" # Used to end any coloring or formatting

# Error Types
PLACEHOLDER_TRANSLATION_ERROR = "PLACEHOLDER_TRANSLATION_ERROR"
ABORTED_BY_USER_ERROR = "Aborted by user."

# Other
YES = "Y"
NO = "N"
UNKNOWN_MODULE_NAME = "unknown-module"

# ---------------------------------------------------------------
# Folders and file names (usually no reason to change any of these)
# If you adjust this, never add language suffixes here (like input/en),
# because these will be added dynamically by the application.
# ---------------------------------------------------------------
INPUT_FOLDER_NAME = "input"
OUTPUT_FOLDER_NAME = "output"
PROGRESS_FOLDER_NAME = "progress"
TERMINOLOGY_FOLDER_NAME = "terminology"
SECRETS_FOLDER_NAME = "local_secret_do_not_commit"

PROGRESS_INFO_FILE_NAME = "00-progress-info.json"
TRANSLATABLES_FILE_NAME = "01-translatables.json"
TRANSLATABLES_WITH_PLACEHOLDERS_FILE_NAME = "02-translatables-with-placeholders.json"
PLACEHOLDERS_FILE_NAME = "03-placeholders.json"
BATCHES_FILE_NAME = "04-batches.json"
TRANSLATIONS_WITH_PLACEHOLDERS_FILE_NAME = "05-translations-with-placeholders.json"
TRANSLATIONS_FINAL_FILE_NAME = "06-translations-final.json"
POST_MORTEM_DUMP_FILE_NAME = "99-post-mortem-dump.json"

APIKEY_FILE_NAME = "openai_api_key.txt"

# ---------------------------------------------------------------
# Preprocess configuration (do not edit under ANY circumstance!)
# ---------------------------------------------------------------
INPUT_TYPE = None  # Just for initializing. Parameter is handled by user prompt

INPUT_FILE_NAME = None  # Just for initializing. Parameter is handled by user prompt
MODULE_NAME = None  # Just for initializing. Parameter is handled by user prompt

REVIEW_ITEMS_FILE_NAME = None  # Just for initializing. Parameter is handled by user prompt
TERMINOLOGY_FILE_NAME = None  # Just for initializing. Parameter is handled by user prompt

INPUT_FILE = None  # Just for initializing. Parameter is handled by user prompt
OUTPUT_FILE = None  # Just for initializing. Parameter is handled by user prompt
PROGRESS_INFO_FILE = None  # Just for initializing. Parameter is handled by user prompt
TRANSLATABLES_FILE = None  # Just for initializing. Parameter is handled by user prompt
TRANSLATABLES_WITH_PLACEHOLDERS_FILE = None  # Just for initializing. Parameter is handled by user prompt
PLACEHOLDERS_FILE = None  # Just for initializing. Parameter is handled by user prompt
BATCHES_FILE = None  # Just for initializing. Parameter is handled by user prompt
TERMINOLOGY_FILE = None  # Just for initializing. Parameter is handled by user prompt
TRANSLATIONS_WITH_PLACEHOLDERS_FILE = None  # Just for initializing. Parameter is handled by user prompt
TRANSLATIONS_FINAL_FILE = None  # Just for initializing. Parameter is handled by user prompt
POST_MORTEM_DUMP_FILE = None  # Just for initializing. Parameter is handled by user prompt
REVIEW_ITEMS_FILE = None  # Just for initializing. Parameter is handled by user prompt

APIKEY_FILE = Path(SECRETS_FOLDER_NAME) / APIKEY_FILE_NAME
REBUILD_TERMINOLOGY_IF_EXISTS = False  # Just for initializing. Parameter is handled by user prompt




