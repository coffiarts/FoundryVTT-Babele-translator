import json
from pathlib import Path


# ------------------------------------------------------------
# UI Localization
# Language files (lang/<code>.json) use the same format as Foundry VTT: nested JSON objects, addressed by dotted keys
# (like "status.running"), with {placeholders} for dynamic parts.
# A missing translation falls back to English, and a missing English text to the key itself.
# This module deliberately doesn't import any other app module, so that it can be used anywhere.
# ------------------------------------------------------------

DEFAULT_LANGUAGE = "en"

_strings = {}   # texts of the selected language
_fallback = {}  # English texts
_lang_dir = None


# ------------------------------------------------------------
# Function: Flatten
# {"a": {"b": "text"}} => {"a.b": "text"}
# ------------------------------------------------------------
def _flatten(node, prefix=""):

    flat = {}

    for key, value in node.items():
        full_key = f"{prefix}{key}"

        if isinstance(value, dict):
            flat.update(_flatten(value, f"{full_key}."))
        else:
            flat[full_key] = value

    return flat


# ------------------------------------------------------------
# Function: Load Language File
# Returns the flattened texts of <lang_dir>/<language>.json (empty if there is no such file)
# ------------------------------------------------------------
def _load_language_file(lang_dir, language):

    path = Path(lang_dir) / f"{language}.json"

    if not path.is_file():
        return {}

    try:
        with open(path, encoding="utf-8") as file:
            return _flatten(json.load(file))

    except (OSError, ValueError, AttributeError):
        return {}


# ------------------------------------------------------------
# Function: Load
# Loads the given language (and English as fallback) from <lang_dir>
# ------------------------------------------------------------
def load(lang_dir, language):

    global _strings, _fallback, _lang_dir

    _lang_dir = lang_dir
    _fallback = _load_language_file(lang_dir, DEFAULT_LANGUAGE)

    _strings = _fallback if language == DEFAULT_LANGUAGE else _load_language_file(lang_dir, language)


# ------------------------------------------------------------
# Function: Translate (t)
# Returns the text for <key>, with {placeholders} filled in from <params>
# ------------------------------------------------------------
def t(key, **params):

    text = _strings.get(key) or _fallback.get(key) or key

    if not params:
        return text

    try:
        return text.format(**params)

    except (KeyError, IndexError, ValueError):
        # A broken translation (unknown or missing placeholder) must never crash the UI
        return text


# ------------------------------------------------------------
# Function: Translate to English (t_en)
# Like t(), but always English. Used for everything that goes to the log,
# so that logs are readable for the developer whatever language the UI is in
# ------------------------------------------------------------
def t_en(key, **params):

    text = _fallback.get(key) or key

    if not params:
        return text

    try:
        return text.format(**params)

    except (KeyError, IndexError, ValueError):
        return text


# ------------------------------------------------------------
# Function: Available Languages
# {code: name} of all language files found in the language folder, sorted by code.
# The name is read from the file itself (key "meta.language_name"), so a language
# can be added by just dropping its file into the folder. Without a name, the code is shown
# ------------------------------------------------------------
def available_languages():

    languages = {}

    if _lang_dir is not None:
        for path in sorted(Path(_lang_dir).glob("*.json")):
            languages[path.stem] = _load_language_file(_lang_dir, path.stem).get("meta.language_name") or path.stem

    return languages or {DEFAULT_LANGUAGE: DEFAULT_LANGUAGE}


# ------------------------------------------------------------
# Function: Translate with default (t_or)
# Like t(), but returns <default> if there is no text for <key> at all
# (used for texts whose translation is optional, like the names of the supported languages)
# ------------------------------------------------------------
def t_or(key, default):

    return _strings.get(key) or _fallback.get(key) or default
