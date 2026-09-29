import cfbt_config as config
import keyring

SERVICE_NAME = config.APP_FULL_NAME
KEY_IDENTIFIER = "api_key"


def get_api_key() -> str | None:
    """Retrieve the API key securely from the system keyring."""
    try:
        key = keyring.get_password(SERVICE_NAME, KEY_IDENTIFIER)
        return key.strip() if key else None
    except Exception:
        return None


def set_api_key(api_key: str) -> None:
    """Store the API key in the system keyring, or delete it if empty."""
    if not api_key:
        delete_api_key()
    else:
        keyring.set_password(SERVICE_NAME, KEY_IDENTIFIER, api_key.strip())


def delete_api_key() -> None:
    """Delete the API key from the system keyring."""
    try:
        keyring.delete_password(SERVICE_NAME, KEY_IDENTIFIER)
    except Exception:
        pass


def has_api_key() -> bool:
    """Check whether a valid non-empty API key is stored."""
    key = get_api_key()
    return bool(key and key.strip())