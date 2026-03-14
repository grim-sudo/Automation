"""Built-in distro build profiles."""

from pathlib import Path

PROFILES_DIR = Path(__file__).parent


def list_profiles() -> list[str]:
    """
    Return the names of all available .toml profile files.

    Returns:
        List of profile name strings (file stems, without the .toml extension),
        sorted alphabetically.
    """
    return sorted(p.stem for p in PROFILES_DIR.glob("*.toml"))


def get_profile_path(name: str) -> Path:
    """
    Return the absolute path to a named profile .toml file.

    Args:
        name: Profile name (without the .toml extension), e.g. "debian_base".

    Returns:
        Absolute Path to the .toml file.

    Raises:
        FileNotFoundError: If no profile with the given name exists.
    """
    path = PROFILES_DIR / f"{name}.toml"
    if not path.exists():
        available = list_profiles()
        raise FileNotFoundError(
            f"Profile '{name}' not found in {PROFILES_DIR}. Available profiles: {available}"
        )
    return path


__all__ = ["PROFILES_DIR", "list_profiles", "get_profile_path"]
