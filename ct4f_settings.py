import ct4f_config as config
import ct4f_core_functions as fn


# ------------------------------------------------------------
# Function: Load Settings
# Returns the persisted settings as a dict (empty if there is no settings file yet).
# Raises OSError/ValueError if the file exists but cannot be read or parsed,
# so that the caller can decide how to report it.
# ------------------------------------------------------------
def load_settings() -> dict:

    if not config.SETTINGS_FILE.exists():
        return {}

    settings = fn.load_json_input(config.SETTINGS_FILE)

    return settings if isinstance(settings, dict) else {}


# ------------------------------------------------------------
# Function: Save Settings
# Persists the given settings dict to the settings file
# ------------------------------------------------------------
def save_settings(settings: dict) -> None:

    fn.save_json_output(settings, config.SETTINGS_FILE)


# ------------------------------------------------------------
# Function: Update Settings
# Merges <changes> into the persisted settings, keeping all other entries
# ------------------------------------------------------------
def update_settings(changes: dict) -> None:

    settings = load_settings()
    settings.update(changes)
    save_settings(settings)


# ------------------------------------------------------------
# Function: Load UI Language
# The language code of the UI, needed before the window is built.
# Falls back to the default if there is no (readable) setting
# ------------------------------------------------------------
def load_ui_language() -> str:

    try:
        return load_settings().get("ui_language") or config.UI_LANGUAGE

    except (OSError, ValueError):
        return config.UI_LANGUAGE


# ------------------------------------------------------------
# Function: Load UI Theme
# The theme's name ("fantasy" or "neutral"), needed before the theme is loaded.
# Falls back to the default if there is no (readable) setting
# ------------------------------------------------------------
def load_ui_theme() -> str:

    try:
        style:str = str(load_settings().get("ui_theme"))
        return style if style in fn.available_themes() else config.UI_THEME

    except (OSError, ValueError):
        return config.UI_THEME
