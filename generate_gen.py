import functools
import json
import typing as t


def generate_gen(f: t.TextIO) -> None:
    f.write("# This file is auto-generated! DO NOT MODIFY BY HAND!\n\n")
    f.write("from enum import Enum, IntEnum\n")
    f.write("\n")
    dump_dict(f, "item_name_to_id", get_item_mapping())
    dump_dict(f, "location_name_to_id", get_location_mapping())
    dump_dict(f, "item_name_groups", get_item_grouping(), type_hint="dict[str, set[str]]")
    f.write("\n\n")
    working_data_keys = get_working_data_keys()
    dump_enum(f, "WorkingDataKey", working_data_keys)
    f.write("\n\n")
    dump_enum(f, "ItemId", get_item_ids_enum_data(), "IntEnum")
    f.write("\n\n")
    dump_enum(f, "LocationId", get_location_ids_enum_data(), "IntEnum")
    f.write("\n\n")
    characters = ("boy", "girl", "sprite")
    dump_enum_mapping(f, "character_exists_keys", "WorkingDataKey", characters, "_EXISTS")
    dump_enum_mapping(f, "character_in_logic_keys", "WorkingDataKey", characters, "_IN_LOGIC")
    dump_enum_mapping(f, "character_class_keys", "WorkingDataKey", characters, "_CLASS")
    dump_enum_mapping(f, "character_starter_weapon_keys", "WorkingDataKey", characters, "_START_WEAPON_INDEX")
    dump_dict(f, "spell_progression", get_spell_progression())
    dump_frozen_set(f, "progression_items", get_progression_items(), type_hint="ItemId", raw=True)
    dump_frozen_set(f, "useful_items", get_useful_items(), type_hint="ItemId", raw=True)
    dump_frozen_set(f, "character_items", get_character_items(), type_hint="ItemId", raw=True)
    dump_frozen_set(f, "progression_event_rewards", get_progression_event_rewards(), type_hint="str")


def main() -> None:
    with open("gen.py", "w", encoding="utf-8") as f:
        generate_gen(f)


def dump_dict(f: t.TextIO, obj_name: str, obj: dict[t.Any, t.Any], type_hint: str = "", raw: bool = False) -> None:
    type_hint = f": {type_hint}" if type_hint else ""
    f.write(f"{obj_name}{type_hint} = {{")
    if not obj:
        f.write("}\n")
        return
    f.write("\n")
    for k, v in obj.items():
        k_str = json.dumps(k)
        v_str = v if raw else json.dumps(v)
        f.write(f"    {k_str}: {v_str},\n")
    f.write("}\n")


def dump_enum(f: t.TextIO, enum_name: str, pairs: t.Iterable[tuple[str, t.Any]], enum_type: str = "Enum") -> None:
    f.write(f"class {enum_name}({enum_type}):\n")
    for k, v in pairs:
        v_str = json.dumps(v)
        f.write(f"    {k} = {v_str}\n")


def dump_enum_mapping(f: t.TextIO, map_name: str, enum_name: str, items: t.Iterable[str], suffix: str) -> None:
    dct = {item: f"{enum_name}.{item.upper()}{suffix}" for item in items}
    dump_dict(f, map_name, dct, raw=True)


def dump_frozen_set(
    f: t.TextIO, set_name: str, values: t.Iterable[t.Any], type_hint: str = "", raw: bool = False
) -> None:
    type_hint = f": frozenset[{type_hint}]" if type_hint else ""
    f.write(f"{set_name}{type_hint} = frozenset(\n")
    f.write("    (\n")
    for value in values:
        value_str = value if raw else json.dumps(value)
        f.write(f"        {value_str},\n")
    f.write("    )\n")
    f.write(")\n")


def pythonize(s: str) -> str:
    s = s.lower()
    for c in " -()":
        s = s.replace(c, "_").replace("__", "_")
    for n in range(0, 10):
        s = s.replace(f"_{n}", f"{n}")
    return s


@functools.cache
def get_item_mapping() -> dict[str, int]:
    from pysomr import OW

    return {item.name: item.id for item in OW.get_all_items()}


def get_item_ids_enum_data() -> list[tuple[str, int]]:
    """Returns name-value pairs for an item id enum."""

    return [(pythonize(k), v) for k, v in get_item_mapping().items()]


@functools.cache
def get_location_mapping() -> dict[str, int]:
    from pysomr import OW

    def fixup_location_name(s: str) -> str:
        return s.replace("(sprite)", "item1").replace("(bow)", "item2").split(" (", 1)[0].replace("lighthouse", "solar")

    somr_locations = {fixup_location_name(location.name): location.id for location in OW.get_all_locations()}
    return {
        **somr_locations,
        "boy starter weapon": get_item_mapping()["boy"] + 256,
        "girl starter weapon": get_item_mapping()["girl"] + 256,
        "sprite starter weapon": get_item_mapping()["sprite"] + 256,
    }


def get_location_ids_enum_data() -> list[tuple[str, int]]:
    """Returns name-value pairs for an item id enum."""

    return [(pythonize(k), v) for k, v in get_location_mapping().items()]


def get_item_grouping() -> dict[str, set[str]]:
    return {}  # TODO: implement this


def get_working_data_keys() -> list[tuple[str, str]]:
    # TODO: get from pysomr, or move to and import from pysomr?
    return [
        ("BOY_CLASS", "boyClass"),
        ("GIRL_CLASS", "girlClass"),
        ("SPRITE_CLASS", "spriteClass"),
        ("BOY_EXISTS", "boyExists"),
        ("GIRL_EXISTS", "girlExists"),
        ("SPRITE_EXISTS", "spriteExists"),
        ("BOY_IN_LOGIC", "findBoy"),
        ("GIRL_IN_LOGIC", "findGirl"),
        ("SPRITE_IN_LOGIC", "findSprite"),
        ("BOY_START_WEAPON_INDEX", "boyStartWeapon"),
        ("GIRL_START_WEAPON_INDEX", "girlStartWeapon"),
        ("SPRITE_START_WEAPON_INDEX", "spriteStartWeapon"),
    ]


def get_spell_progression() -> dict[str, str]:
    # TODO: get from pysomr, or move to and import from pysomr?
    return {
        "OGboy": "noCaster",
        "OGgirl": "girlCaster",
        "OGsprite": "spriteCaster",
    }


def get_progression_items() -> t.Iterable[str]:
    # TODO: get from pysomr, or move to and import from pysomr?
    enum_names = (
        "axe",
        "sword",
        "whip",
        # NOTE: boy, girl and sprite depend on gen
        # TODO: seeds should only be progression in VLong/VShort for restrictive
        "water_seed",
        "earth_seed",
        "wind_seed",
        "fire_seed",
        "light_seed",
        "dark_seed",
        "moon_seed",
        "dryad_seed",
        "undine_spells",  # NOTE: they don't exist if we don't have a caster, so always prog
        "gnome_spells",
        "sylphid_spells",
        "salamando_spells",
        "lumina_spells",
        "shade_spells",
        "luna_spells",
        "dryad_spells",
        "gold_tower_key",
        "sea_hare_tail",
        "flammie_drum",
    )
    return [f"ItemId.{name}" for name in enum_names]


def get_useful_items() -> t.Iterable[str]:
    # TODO: get from pysomr, or move to and import from pysomr?
    enum_names = (
        "midge_mallet",
        "moogle_belt",
    )
    return [f"ItemId.{name}" for name in enum_names]


def get_character_items() -> t.Iterable[str]:
    # TODO: get from pysomr, or move to and import from pysomr?
    enum_names = (
        "boy",
        "girl",
        "sprite",
    )
    return [f"ItemId.{name}" for name in enum_names]


def get_progression_event_rewards() -> t.Iterable[str]:
    # TODO: make this more flexible
    return (
        "anyCaster",
        "girlCaster",
        "spriteCaster",
        "Did the thing",
    )


if __name__ == "__main__":
    main()
