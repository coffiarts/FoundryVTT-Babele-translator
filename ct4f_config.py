# ------------------------------------------------------------
# Language to translate from/to
# ------------------------------------------------------------

SUPPORTED_LANGUAGES = [
    {"code": "en", "name": "English"},
    {"code": "de", "name": "German"},
    {"code": "fr", "name": "French"},
    {"code": "it", "name": "Italian"},
    {"code": "es", "name": "Spanish"},
    {"code": "ja", "name": "Japanese"},
]

SOURCE_LANGUAGE = {
    "code": "en",
    "name": "English"
}

TARGET_LANGUAGE = {
    "code": "de",
    "name": "German" # Always use the english name here
}

GAME_SYSTEM_AGNOSTIC = "Generic (system-agnostic)"
GENRE_AGNOSTIC = "Generic"

# id => English name. The English name is the actual value: it goes into the AI prompts and is saved in
# the settings and the progress info. The id only serves for the dropdown's display text, which is
# looked up in the language files (keys "game_system.<id>" and "genre.<id>")
GAME_SYSTEMS = {
    "dnd5e": "Dungeons & Dragons (DnD5e)",
    "tde5": "The Dark Eye/Das Schwarze Auge (TDE5/DSA5)",
    "pf2e": "Pathfinder (PF2e)",
    "generic": GAME_SYSTEM_AGNOSTIC
}

GENRES = {
    "classical_fantasy": "Classical Fantasy",
    "sci_fi": "Sci-Fi",
    "horror": "Horror",
    "generic": GENRE_AGNOSTIC
}

SUPPORTED_GAME_SYSTEMS = list(GAME_SYSTEMS.values())
SUPPORTED_GENRES = list(GENRES.values())

# --------------------------------------------------------------------
# --------------------------------------------------------------------
# --- RESUME-RELEVANT CORE CONFIGURATION
# --- The following params must not changed in between incremental
# --- runs for the same input file, because they control how text
# -- is being preprocessed and Batches are built
# --- See also: get_resume_relevant_config()
# --------------------------------------------------------------------
# --------------------------------------------------------------------

MOCK_MODE = False # Default: False: If set to True, remote LLM requests/responses are only mocked (for testing surrounding logic without causing costs)

# Translation flavour
GAME_SYSTEM_CONTEXT = "Dungeons & Dragons (DnD5e)"  # pick a value from SUPPORTED_GAME_SYSTEMS
GENRE_CONTEXT = "Classical Fantasy"  # pick a value from SUPPORTED_GENRES

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

PAUSE_AFTER_TERMINOLOGY = True # If True, the run stops once after terminology is complete, so that the user can review it (the option then resets itself and will be set to True again on selecting another input file)


# ------------------------------------------------------------
# LLM Parameters (change these only for translation fine-tuning)
# ------------------------------------------------------------

# LLM_MODEL = "gpt-5.4-mini"
LLM_MODEL = "gpt-5.6-luna"

# Base URL of the API server. Any OpenAI-compatible server can be used
# (e.g. a local Ollama: "http://localhost:11434/v1")
OPENAI_BASE_URL = "https://api.openai.com/v1"
API_BASE_URL = OPENAI_BASE_URL

# False for servers that don't check API keys (e.g. a local Ollama). OpenAI itself always needs one
API_KEY_REQUIRED = True

# If True, no hover info texts (tooltips) are shown
HIDE_TOOLTIPS = False

# Language of the user interface: code of a language file in the lang folder (see ct4f_i18n.py)
UI_LANGUAGE = "en"


def get_translation_instructions():
    return f"""
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
- Address the reader informally. Wherever {TARGET_LANGUAGE["name"]} distinguishes between formal and informal
  address, always use the informal form (for example "du"/"ihr" in German, "tu" in French, "tú" in Spanish,
  "tu" in Italian) and never the formal one (for example "Sie", "vous", "usted", "Lei").

A placeholder always belongs to the label that follows it.

When translating, the label may be translated and moved
to a different position in the sentence if {TARGET_LANGUAGE["name"]} grammar
requires it.

However, the placeholder must move together with the label.

Input:
They are loyal to <<<PLACEHOLDER_000001>>>{{King Grol}}.

German example ...

Correct output:
Sie sind <<<PLACEHOLDER_000001>>>{{König Grol}} gegenüber loyal.

Incorrect output:
Sie sind König Grol gegenüber loyal.
"""

def get_terminology_instructions():

    system_is_specific = GAME_SYSTEM_CONTEXT != GAME_SYSTEM_AGNOSTIC
    genre_is_specific = GENRE_CONTEXT != GENRE_AGNOSTIC

    context_phrase = " ".join(
        part for part in (
            GAME_SYSTEM_CONTEXT if system_is_specific else None,
            GENRE_CONTEXT if genre_is_specific else None
        )
        if part
    )
    context_phrase = f"{context_phrase} " if context_phrase else ""

    rules_bullet = f"- {GAME_SYSTEM_CONTEXT} rules terminology\n" if system_is_specific else ""
    genre_bullet = f"- established {GENRE_CONTEXT} vocabulary\n" if genre_is_specific else ""
    official_terminology_phrase = f"official {GAME_SYSTEM_CONTEXT} terminology" if system_is_specific else "official terminology"

    return f"""
You are a terminology analyst for a {TARGET_LANGUAGE["name"]} translation of a
{context_phrase}role-playing adventure.

Analyze the supplied {SOURCE_LANGUAGE["name"]} text and identify only terms that
are likely to require consistent translation across the adventure.

Prioritize:
{rules_bullet}- creature and monster names or types
{genre_bullet}- setting-specific terminology (invented concepts, phenomena, social or cultural terms, etc.)
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
that they are {official_terminology_phrase}.

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
APP_AUTHOR = "coffiarts"
APP_SHORT_NAME = "CT4F"
APP_FULL_NAME = "coffiarts' Translator for Foundry VTT"

# Run Modes
NEW_RUN = "NEW_RUN"
RESUME = "RESUME"
POSTPROCESSING_ONLY = "POSTPROCESSING_ONLY"

# Input Types
INPUT_TYPE_BABELE = "Babele JSON export"
INPUT_TYPE_LOCALIZATION = "Localization file (lang/*.json)"

# Process Outcomes
OUTCOME_SUCCESS = "SUCCESS"
OUTCOME_CANCELLED = "CANCELLED"
OUTCOME_DECLINED = "DECLINED"
OUTCOME_PAUSED = "PAUSED"
OUTCOME_EXPECTED_ERROR = "EXPECTED_ERROR"
OUTCOME_UNEXPECTED_ERROR = "UNEXPECTED_ERROR"

# Batch Status
TERMINOLOGY_STATUS = "terminology_status"
TRANSLATION_STATUS = "translation_status"
UNPROCESSED = "UNPROCESSED"
PROCESSING = "PROCESSING"
FAILED = "FAILED"
REVIEW_REQUIRED = "REVIEW_REQUIRED"
COMPLETED = "COMPLETED"
ERROR = "ERROR"


# Test Result
PASSED = "PASSED" # FAILED can be reused from above

# Console Colors &  Formatting
CONSOLE_RED    = "\033[31m"
CONSOLE_GREEN  = "\033[32m"
CONSOLE_YELLOW = "\033[33m"
CONSOLE_BLUE   = "\033[34m"
CONSOLE_MAGENTA = "\033[35m"
CONSOLE_CYAN = "\033[36m"
CONSOLE_WHITE = "\033[37m"
CONSOLE_HEADER = "\033[95m"
CONSOLE_BOLD = "\033[1m"
CONSOLE_UNDERLINE = "\033[4m"
CONSOLE_RESET  = "\033[0m" # Used to end any coloring or formatting

# UI Colors (hex values for CustomTkinter widgets, not to be mixed up with the CONSOLE_ colors)
GREY = "#8a8a8a"
YELLOW = "#e0b400"
GREEN = "#3fa34d"
RED = "#d64545"
MAGENTA = "#b04fc0"
BLUE = "#4a90d9"
WHITE = "#ffffff"
BLACK = "#000000"

# Colors and fonts applied by explicit code (not linked to a named CTk element), so they
# aren't part of CTk's own theme format. These are the defaults; a theme's own "extras" section
# (assets/themes/ct4f-theme-*.json) can override any of them, and simply omitting a key here keeps it
theme_extras = {
    "colors": {
        "PARCHMENT_LIGHT": "#e6d9b8",
        "PARCHMENT_LOCKED": "#bdb5a0",
        "INK_LOCKED": "#857d6a",
        "INK_CONTRAST": "#3b2f1e",
        "INK_LIGHT": "#8a7550",
    },
    "fonts": {
        "Heading": {"family": "Metamorphous", "size": 15, "weight": "bold"},
        "Text": {"family": "Metamorphous", "size": 14, "weight": "normal"},
        "Tooltip": {"family": "Metamorphous", "size": 12, "weight": "normal"}
    },
    "images": {
        "banner": "banner-fantasy.png",
        "deco_image": "deco-image-fantasy.png"
    }
}

# Batch status => UI color
STATUS_COLORS = {
    UNPROCESSED: GREY,
    PROCESSING: YELLOW,
    COMPLETED: GREEN,
    FAILED: RED,
    REVIEW_REQUIRED: MAGENTA
}

UI_THEME = "fantasy" # just the default and fallback

# assets/themes/ct4f-theme-<style>.json holds each theme's colors and fonts
THEMES_DIR = "assets/themes"
IMG_DIR = "assets/img"
FONTS_DIR = f"{THEMES_DIR}/fonts"

FONT_HEADING = None   # resolved from the active theme at startup, see ct4f_app.py
FONT_TEXT = None
FONT_TOOLTIP = None

FONT_FAMILY_LOG = "Arial"
FONT_LOG = (FONT_FAMILY_LOG, 13)               # The font is explicit (non-serif)

# Log output (inline log, pop-out log and error views)
LOG_BACKGROUND_COLOR = BLACK
LOG_TEXT_COLOR = WHITE

TAG_ERROR = "error"
TAG_SUCCESS = "success"
TAG_WARNING = "warning"
TAG_INFO = "info"
TAG_QUESTION = "question"

# Log tag => text color
LOG_TAG_COLORS = {
    TAG_ERROR: RED,
    TAG_SUCCESS: GREEN,
    TAG_WARNING: YELLOW,
    TAG_INFO: BLUE,
    TAG_QUESTION: MAGENTA
}

# Error Types
PLACEHOLDER_TRANSLATION_ERROR = "PLACEHOLDER_TRANSLATION_ERROR"

# Prompt Types
PROMPT_TYPE_YESNO = "yes/no"

# Other
YES = "Yes"
NO = "No"
CANCEL = "Cancel"
UNKNOWN_MODULE_NAME = "unknown-module"

# ---------------------------------------------------------------
# Folders and file names (usually no reason to change any of these)
# If you adjust this anyway, do not add module names or language suffixes (like input/my-module/en),
# because all of these will be added dynamically later in ct4f_core_functions.adapt_file_paths()
# ---------------------------------------------------------------
INPUT_FOLDER_NAME = "input"
OUTPUT_FOLDER_NAME = "output"
PROGRESS_FOLDER_NAME = "progress"
TERMINOLOGY_FOLDER_NAME = "terminology"

SETTINGS_FILE_NAME = "settings.json"
PROGRESS_INFO_FILE_NAME = "00-progress-info.json"
TRANSLATABLES_FILE_NAME = "01-translatables.json"
TRANSLATABLES_WITH_PLACEHOLDERS_FILE_NAME = "02-translatables-with-placeholders.json"
PLACEHOLDERS_FILE_NAME = "03-placeholders.json"
BATCHES_FILE_NAME = "04-batches.json"
TRANSLATIONS_WITH_PLACEHOLDERS_FILE_NAME = "05-translations-with-placeholders.json"
TRANSLATIONS_FINAL_FILE_NAME = "06-translations-final.json"
PROGRESS_REVIEW_ITEMS_FILE_NAME = "07-progress-review-items.json"
POST_MORTEM_DUMP_FILE_NAME = "99-post-mortem-dump.json"


# ---------------------------------------------------------------
# Preprocess configuration (do not edit under ANY circumstance!)
# These are just for initializing. Parameter is handled by user prompt
# ---------------------------------------------------------------
APP_DIR = None
USER_CONFIG_DIR = None
USER_DATA_DIR = None
BASE_OUTPUT_DIR = None
PROGRESS_DIR = None
TERMINOLOGY_DIR = None
OUTPUT_DIR = None


INPUT_TYPE = None
MODULE_NAME = None

INPUT_FILE_NAME = None

INPUT_FILE = None
OUTPUT_FILE = None
SETTINGS_FILE = None
PROGRESS_INFO_FILE = None
TRANSLATABLES_FILE = None
TRANSLATABLES_WITH_PLACEHOLDERS_FILE = None
PLACEHOLDERS_FILE = None
BATCHES_FILE = None
TERMINOLOGY_FILE = None
TRANSLATIONS_WITH_PLACEHOLDERS_FILE = None
TRANSLATIONS_FINAL_FILE = None
PROGRESS_REVIEW_ITEMS_FILE = None
POST_MORTEM_DUMP_FILE = None
REVIEW_ITEMS_FILE = None

# And last but not least ...
MOCK_PROGRESSBAR_DURATION_SEC = 5
