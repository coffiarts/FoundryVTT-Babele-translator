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
PROGRESS_INFO_FOLDER_NAME = "progress-info"
SECRETS_FOLDER_NAME = "local_secret_do_not_commit"
ERRORS_FOLDER_NAME = "errors"
OUTPUT_FOLDER_NAME = "output"

PROGRESS_INFO_FILE_NAME = "00-progress-info.json"
TRANSLATABLES_FILE_NAME = "01-translatables.json"
BATCHES_FILE_NAME = "02-batches.json"
PLACEHOLDERS_FILE_NAME = "03-placeholders.json"
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

# create specific progress-info subfolder for current input (if necessary)
PROGRESS_INFO_SUBFOLDER_NAME = Path(PROGRESS_INFO_FOLDER_NAME) / INPUT_FILE_NAME.removesuffix(".json")
if not os.path.exists(PROGRESS_INFO_SUBFOLDER_NAME):
    os.makedirs(PROGRESS_INFO_SUBFOLDER_NAME)

PROGRESS_INFO_FILE = Path(PROGRESS_INFO_SUBFOLDER_NAME) / PROGRESS_INFO_FILE_NAME
TRANSLATABLES_FILE = Path(PROGRESS_INFO_SUBFOLDER_NAME) / TRANSLATABLES_FILE_NAME
BATCHES_FILE = Path(PROGRESS_INFO_SUBFOLDER_NAME) / BATCHES_FILE_NAME
PLACEHOLDERS_FILE = Path(PROGRESS_INFO_SUBFOLDER_NAME) / PLACEHOLDERS_FILE_NAME
TRANSLATIONS_WITH_PLACEHOLDERS_FILE = Path(PROGRESS_INFO_SUBFOLDER_NAME) / TRANSLATIONS_WITH_PLACEHOLDERS_FILE_NAME
TRANSLATIONS_FINAL_FILE = Path(PROGRESS_INFO_SUBFOLDER_NAME) / TRANSLATIONS_FINAL_FILE_NAME
POST_REVIEW_ITEMS_FILE = Path(PROGRESS_INFO_SUBFOLDER_NAME) / POST_REVIEW_ITEMS_FILE_NAME

ERRORS_FILE = Path(ERRORS_FOLDER_NAME) / ERRORS_FILE_NAME
APIKEY_FILE = Path(SECRETS_FOLDER_NAME) / APIKEY_FILE_NAME


