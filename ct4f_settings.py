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
