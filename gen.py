# TODO: generate this file

from enum import Enum, IntEnum


__all__ = (
    "ItemId",
    "LocationId",
    "WorkingDataKey",
    "character_class_keys",
    "character_exists_keys",
    "character_in_logic_keys",
    "character_items",
    "character_starter_weapon_keys",
    "progression_event_rewards",
    "progression_items",
    "spell_progression",
    "useful_items",
)


class WorkingDataKey(Enum):
    BOY_CLASS = "boyClass"
    GIRL_CLASS = "girlClass"
    SPRITE_CLASS = "spriteClass"
    BOY_EXISTS = "boyExists"  # exists + !in_logic = start_with
    GIRL_EXISTS = "girlExists"
    SPRITE_EXISTS = "spriteExists"
    BOY_IN_LOGIC = "findBoy"
    GIRL_IN_LOGIC = "findGirl"
    SPRITE_IN_LOGIC = "findSprite"
    BOY_START_WEAPON_INDEX = "boyStartWeapon"
    GIRL_START_WEAPON_INDEX = "girlStartWeapon"
    SPRITE_START_WEAPON_INDEX = "spriteStartWeapon"


class ItemId(IntEnum):
    nothing = 0
    glove_orb = 4
    boy = 12
    girl = 13
    sprite = 14
    sea_hare_tail = 15
    gold_tower_key = 16
    glove = 37
    sword = 38
    axe = 39
    spear = 40
    whip = 41
    bow = 42
    boomerang = 43
    javelin = 44


class LocationId(IntEnum):
    mech_rider3 = 4
    dread_slime = 6


character_exists_keys = {
    "boy": WorkingDataKey.BOY_EXISTS,
    "girl": WorkingDataKey.GIRL_EXISTS,
    "sprite": WorkingDataKey.SPRITE_EXISTS,
}


character_in_logic_keys = {
    "boy": WorkingDataKey.BOY_IN_LOGIC,
    "girl": WorkingDataKey.GIRL_IN_LOGIC,
    "sprite": WorkingDataKey.SPRITE_IN_LOGIC,
}


character_class_keys = {
    "boy": WorkingDataKey.BOY_CLASS,
    "girl": WorkingDataKey.GIRL_CLASS,
    "sprite": WorkingDataKey.SPRITE_CLASS,
}

character_starter_weapon_keys = {
    "boy": WorkingDataKey.BOY_START_WEAPON_INDEX,
    "girl": WorkingDataKey.GIRL_START_WEAPON_INDEX,
    "sprite": WorkingDataKey.SPRITE_START_WEAPON_INDEX,
}


spell_progression = {
    "OGboy": "noCaster",
    "OGgirl": "girlCaster",
    "OGsprite": "spriteCaster",
}


progression_items = frozenset(
    (
        # TODO: load this from said JSON; can be created by looking at requirements for all locations
        # TODO: use IDs instead of names
        "axe",
        "sword",
        "whip",
        # NOTE: boy, girl and sprite are only prog items if they lock a spell
        # TODO: seeds should only be progression in VLong/VShort for restrictive
        "water seed",
        "earth seed",
        "wind seed",
        "fire seed",
        "light seed",
        "dark seed",
        "moon seed",
        "dryad seed",
        "undine spells",  # NOTE: they don't exist if we don't have a caster, so always prog
        "gnome spells",
        "sylphid spells",
        "salamando spells",
        "lumina spells",
        "shade spells",
        "luna spells",
        "dryad spells",
        "gold tower key",
        "sea hare tail",
        "flammie drum",
    )
)


useful_items = frozenset(
    (
        "midge mallet",
        "moogle belt",
    )
)

progression_event_rewards = frozenset(
    (
        "anyCaster",
        "girlCaster",
        "spriteCaster",
        "Did the thing",
    )
)


character_items = frozenset(
    (
        ItemId.boy,
        ItemId.girl,
        ItemId.sprite,
    )
)
