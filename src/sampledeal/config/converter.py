"""Convert between GUI profiles and configuration files."""

from collections.abc import Sequence
from typing import Any

from ..utils import ByteUnit, TimeUnit, TransferMode, load_json, save_json
from .schemas import ConfigModel


def _combo_value(data: dict[str, Any], key: str, default: str = "") -> str:
    val = data.get(key)
    if isinstance(val, str):
        return val

    items = data.get(f"{key}_items")
    if isinstance(val, int) and isinstance(items, Sequence) and 0 <= val < len(items):
        return str(items[val])

    return default


def _set_combo_value(profile: dict[str, Any], key: str, value: str, items: Sequence[str]) -> None:
    items_list = [str(i) for i in items]
    if value and value not in items_list:
        items_list.append(value)

    profile[f"{key}_items"] = items_list
    profile[key] = items_list.index(value) if value in items_list else 0


def convert_profile_to_config(profile_data: dict[str, Any]) -> dict[str, Any]:
    """Convert GUI profile data to configuration data."""
    root = _combo_value(profile_data, "root_combo")
    dest = _combo_value(profile_data, "dest_combo")

    should_create = bool(profile_data.get("folder", False))
    folder_count = int(profile_data.get("folder_count", 1)) if should_create else 1

    data = {
        "root": root,
        "dest": dest,
        "filecount": {
            "count": int(profile_data.get("filecount_fixed_val", 0)),
            "is_rand_enabled": bool(profile_data.get("filecount_rand_chk", False)),
            "rand_min": int(profile_data.get("filecount_rand_min", 0)),
            "rand_max": int(profile_data.get("filecount_rand_max", 0)),
        },
        "folder": {
            "should_create": should_create,
            "is_unique": bool(profile_data.get("folder_unique", True)),
            "name": str(profile_data.get("folder_name", "")),
            "count": folder_count,
        },
        "filename": {
            "template": str(profile_data.get("filename_template", "{original}")) or "{original}",
        },
        "transfermode": {
            "transfer_mode": _combo_value(profile_data, "transfermode_mode", TransferMode.SYMLINK),
        },
        "keyword": {
            "is_enabled": bool(profile_data.get("keyword", False)),
            "should_include": bool(profile_data.get("keyword_include", True)),
            "text": str(profile_data.get("keyword_text", "")),
        },
        "extension": {
            "is_enabled": bool(profile_data.get("extension", False)),
            "should_include": bool(profile_data.get("extension_include", True)),
            "text": str(profile_data.get("extension_text", "")),
        },
        "filesize": {
            "is_enabled": bool(profile_data.get("filesize", False)),
            "minimum": float(profile_data.get("filesize_minimum", 0.0)),
            "maximum": float(profile_data.get("filesize_maximum", 0.0)),
            "unit": _combo_value(profile_data, "filesize_unit"),
        },
        "duration": {
            "is_enabled": bool(profile_data.get("duration", False)),
            "minimum": float(profile_data.get("duration_minimum", 0.0)),
            "maximum": float(profile_data.get("duration_maximum", 0.0)),
            "unit": _combo_value(profile_data, "duration_unit"),
        },
        "folder_size_limit": {
            "is_enabled": bool(profile_data.get("folder_size_limit", False)),
            "size_limit": float(profile_data.get("folder_size_limit_size", 0.0)),
            "unit": _combo_value(profile_data, "folder_size_limit_unit"),
        },
        "total_size_limit": {
            "is_enabled": bool(profile_data.get("total_size_limit", False)),
            "size_limit": float(profile_data.get("total_size_limit_size", 0.0)),
            "unit": _combo_value(profile_data, "total_size_limit_unit"),
        },
        "options": {
            "max_per_folder": int(profile_data.get("options_max_per_folder", 0)),
            "should_follow_symlink": bool(profile_data.get("options_should_follow_symlink", False)),
            "is_dry_run": bool(profile_data.get("options_dry_run", False)),
        },
    }

    config = ConfigModel.model_validate(data)
    return config.model_dump()


def convert_config_to_profile(config_data: dict[str, Any]) -> dict[str, Any]:
    """Convert configuration data to GUI profile data."""
    config = ConfigModel.model_validate(config_data)
    data = config.model_dump()

    profile: dict[str, Any] = {
        "folder": data["folder"]["should_create"],
        "filecount_fixed_val": data["filecount"]["count"],
        "filecount_rand_chk": data["filecount"]["is_rand_enabled"],
        "filecount_rand_min": data["filecount"]["rand_min"],
        "filecount_rand_max": data["filecount"]["rand_max"],
        "folder_count": data["folder"]["count"],
        "folder_name": data["folder"]["name"],
        "folder_unique": data["folder"]["is_unique"],
        "filename_template": data["filename"]["template"],
        "keyword": data["keyword"]["is_enabled"],
        "keyword_include": data["keyword"]["should_include"],
        "keyword_text": data["keyword"]["text"],
        "extension": data["extension"]["is_enabled"],
        "extension_include": data["extension"]["should_include"],
        "extension_text": data["extension"]["text"],
        "filesize": data["filesize"]["is_enabled"],
        "filesize_minimum": data["filesize"]["minimum"],
        "filesize_maximum": data["filesize"]["maximum"],
        "duration": data["duration"]["is_enabled"],
        "duration_minimum": data["duration"]["minimum"],
        "duration_maximum": data["duration"]["maximum"],
        "folder_size_limit": data["folder_size_limit"]["is_enabled"],
        "folder_size_limit_size": data["folder_size_limit"]["size_limit"],
        "total_size_limit": data["total_size_limit"]["is_enabled"],
        "total_size_limit_size": data["total_size_limit"]["size_limit"],
        "options_max_per_folder": data["options"]["max_per_folder"],
        "options_should_follow_symlink": data["options"]["should_follow_symlink"],
        "options_dry_run": data["options"]["is_dry_run"],
    }

    _set_combo_value(profile, "root_combo", data["root"], [data["root"]])
    _set_combo_value(profile, "dest_combo", data["dest"], [data["dest"]])
    _set_combo_value(profile, "filesize_unit", data["filesize"]["unit"], list(ByteUnit))
    _set_combo_value(profile, "duration_unit", data["duration"]["unit"], list(TimeUnit))
    _set_combo_value(profile, "folder_size_limit_unit", data["folder_size_limit"]["unit"], list(ByteUnit))
    _set_combo_value(profile, "total_size_limit_unit", data["total_size_limit"]["unit"], list(ByteUnit))

    transfer_modes = list(TransferMode)
    _set_combo_value(profile, "transfermode_mode", data["transfermode"]["transfer_mode"], transfer_modes)

    return profile


def profile_to_config_file(profile_path: str, config_path: str) -> None:
    """Convert GUI profile JSON to configuration JSON."""
    profile_data = load_json(profile_path)
    config_data = convert_profile_to_config(profile_data)
    save_json(config_path, config_data)


def config_to_profile_file(config_path: str, profile_path: str) -> None:
    """Convert configuration JSON to GUI profile JSON."""
    config_data = load_json(config_path)
    profile_data = convert_config_to_profile(config_data)
    save_json(profile_path, profile_data)
