import os
from pathlib import Path

# ------------------------------------------------------------
# Configuration
# ------------------------------------------------------------

INPUT_FILE_NAME = "test-input.json"
MAX_BATCH_SIZE = 50000 # It may (unproven) help to scale this with the overall input size (larger input => larger batch size)
TRANSLATABLE_FIELDS = {
    "text",
    "name",
    "caption",
    "description"
}

INPUT_FOLDER_NAME = "input"
PROCESS_FOLDER_NAME = "progress"
SECRETS_FOLDER_NAME = "local_secret_do_not_commit"
ERRORS_FOLDER_NAME = "errors"
OUTPUT_FOLDER_NAME = "output"

PROGRESS_FILE_NAME = "00-progress.json"
TRANSLATABLES_FILE_NAME = "01-translatables.json"
BATCHES_FILE_NAME = "02-batches.json"
PROTECTED_ELEMENTS_FILE_NAME = "03-protected_elements.json"
TRANSLATIONS_WITH_PLACEHOLDERS_FILE_NAME = "04-translations_with-placeholders.json"
TRANSLATIONS_FINAL_FILE_NAME = "05-translations-final.json"
POST_REVIEW_ITEMS_FILE_NAME = "06-post-review-items.json"

ERRORS_FILE_NAME = "errors.json"
APIKEY_FILE_NAME = "openai_api_key.txt"


# ------------------------------------------------------------
# Preprocess configuration (do not edit anything from here on)!
# ------------------------------------------------------------
INPUT_FILE = Path(INPUT_FOLDER_NAME) / INPUT_FILE_NAME
OUTPUT_FILE = Path(OUTPUT_FOLDER_NAME) / INPUT_FILE_NAME

# create specific progress subfolder for current input (if necessary)
PROCESS_SUBFOLDER_NAME = Path(PROCESS_FOLDER_NAME) / INPUT_FILE_NAME.removesuffix(".json")
if not os.path.exists(PROCESS_SUBFOLDER_NAME):
    os.makedirs(PROCESS_SUBFOLDER_NAME)

PROGRESS_FILE = Path(PROCESS_SUBFOLDER_NAME) / PROGRESS_FILE_NAME
TRANSLATABLES_FILE = Path(PROCESS_SUBFOLDER_NAME) / TRANSLATABLES_FILE_NAME
BATCHES_FILE = Path(PROCESS_SUBFOLDER_NAME) / BATCHES_FILE_NAME
PROTECTED_ELEMENTS_FILE = Path(PROCESS_SUBFOLDER_NAME) / PROTECTED_ELEMENTS_FILE_NAME
TRANSLATIONS_WITH_PLACEHOLDERS_FILE = Path(PROCESS_SUBFOLDER_NAME) / TRANSLATIONS_WITH_PLACEHOLDERS_FILE_NAME
TRANSLATIONS_FINAL_FILE = Path(PROCESS_SUBFOLDER_NAME) / TRANSLATIONS_FINAL_FILE_NAME
POST_REVIEW_ITEMS_FILE = Path(PROCESS_SUBFOLDER_NAME) / POST_REVIEW_ITEMS_FILE_NAME

ERRORS_FILE = Path(ERRORS_FOLDER_NAME) / ERRORS_FILE_NAME
APIKEY_FILE = Path(SECRETS_FOLDER_NAME) / APIKEY_FILE_NAME


