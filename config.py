import os
from pathlib import Path

INPUT_FILE_NAME = "test-input.json"

# ------------------------------------------------------------
# Core Configuration
# The following params are Resume-relevant:
# They must not change in between incremental runs for the same
# input file, because they control how text is being preprocessed.
# See also: get_resume_relevant_config()
# ------------------------------------------------------------

MAX_BATCH_SIZE = 50000

TRANSLATABLE_FIELDS = {
    "text",
    "name",
    "caption",
    "description"
}

FOUNDRY_SYNTAX_PATTERNS = {
    r'@(UUID|Embed|Compendium)\[[^\]]*\]',
    r'\[\[[^\]]*\]\]'
}


# ------------------------------------------------------------
# Translation Instructions
# ------------------------------------------------------------

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
# Folders and file names
# ------------------------------------------------------------

INPUT_FOLDER_NAME = "input"
PROGRESS_INFO_FOLDER_NAME = "progress-info"
SECRETS_FOLDER_NAME = "local_secret_do_not_commit"
ERRORS_FOLDER_NAME = "errors"
OUTPUT_FOLDER_NAME = "output"

PROGRESS_INFO_FILE_NAME = "00-progress-info.json"
TRANSLATABLES_FILE_NAME = "01-translatables.json"
TRANSLATABLES_WITH_PLACEHOLDERS_FILE_NAME = "02-translatables-with-placeholders.json"
PLACEHOLDERS_FILE_NAME = "03-placeholders.json"
BATCHES_FILE_NAME = "04-batches.json"
TRANSLATIONS_WITH_PLACEHOLDERS_FILE_NAME = "05-translations-with-placeholders.json"
TRANSLATIONS_FINAL_FILE_NAME = "06-translations-final.json"
POST_REVIEW_ITEMS_FILE_NAME = "07-post-review-items.json"

ERRORS_FILE_NAME = "errors.json"
APIKEY_FILE_NAME = "openai_api_key.txt"


# ------------------------------------------------------------
# String Constants (do not edit!)
# ------------------------------------------------------------

# Run Mode
NEW_RUN = "NEW_RUN"
RESUME = "RESUME"

# Batch Status
UNPROCESSED = "UNPROCESSED"
PROCESSING = "PROCESSING"
FAILED = "FAILED"
COMPLETED = "COMPLETED"

# Test Result
PASSED = "PASSED" # FAILED can be reused from above

# Colors
RED    = "\033[31m"
GREEN  = "\033[32m"
YELLOW = "\033[33m"
BLUE   = "\033[34m"
RESET  = "\033[0m"


# ------------------------------------------------------------
# Preprocess configuration (do not edit!)
# ------------------------------------------------------------
INPUT_FILE = Path(INPUT_FOLDER_NAME) / INPUT_FILE_NAME
OUTPUT_FILE = Path(OUTPUT_FOLDER_NAME) / INPUT_FILE_NAME

# create specific progress-info subfolder for current input (if necessary)
PROGRESS_INFO_SUBFOLDER_NAME = Path(PROGRESS_INFO_FOLDER_NAME) / INPUT_FILE_NAME.removesuffix(".json")
if not os.path.exists(PROGRESS_INFO_SUBFOLDER_NAME):
    os.makedirs(PROGRESS_INFO_SUBFOLDER_NAME)

PROGRESS_INFO_FILE = Path(PROGRESS_INFO_SUBFOLDER_NAME) / PROGRESS_INFO_FILE_NAME
TRANSLATABLES_FILE = Path(PROGRESS_INFO_SUBFOLDER_NAME) / TRANSLATABLES_FILE_NAME
TRANSLATABLES_WITH_PLACEHOLDERS_FILE = Path(PROGRESS_INFO_SUBFOLDER_NAME) / TRANSLATABLES_WITH_PLACEHOLDERS_FILE_NAME
PLACEHOLDERS_FILE = Path(PROGRESS_INFO_SUBFOLDER_NAME) / PLACEHOLDERS_FILE_NAME
BATCHES_FILE = Path(PROGRESS_INFO_SUBFOLDER_NAME) / BATCHES_FILE_NAME
TRANSLATIONS_WITH_PLACEHOLDERS_FILE = Path(PROGRESS_INFO_SUBFOLDER_NAME) / TRANSLATIONS_WITH_PLACEHOLDERS_FILE_NAME
TRANSLATIONS_FINAL_FILE = Path(PROGRESS_INFO_SUBFOLDER_NAME) / TRANSLATIONS_FINAL_FILE_NAME
POST_REVIEW_ITEMS_FILE = Path(PROGRESS_INFO_SUBFOLDER_NAME) / POST_REVIEW_ITEMS_FILE_NAME

ERRORS_FILE = Path(ERRORS_FOLDER_NAME) / ERRORS_FILE_NAME
APIKEY_FILE = Path(SECRETS_FOLDER_NAME) / APIKEY_FILE_NAME

