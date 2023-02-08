import logging
from enum import Enum

from .format import (TimberbornEntity,  # TimberbornMap,TimberbornSingletons, trunc_float
                     TimberbornMapSize, TimberbornSoilMoistureSimulator, TimberbornTerrainMap,
                     TimberbornTreeComponents, TimberbornWaterMap)
from .treemap import TreeSpecies  # Goods
from .validation import TreeValidator  # , Validator

MAP_FORMAT_ELEMENTS = {"GameVersion": (str, int), "Singletons": dict, "Entities": list}
SINGLETONS = {
    "MapSize": {"type": dict, "mandatory": True, "class": TimberbornMapSize},
    "TerrainMap": {"type": dict, "mandatory": True, "class": TimberbornTerrainMap},
    "WaterMap": {"type": dict, "mandatory": True, "class": TimberbornWaterMap},
    "SoilMoistureSimulator": {'type': dict, "mandatory": True, "class": TimberbornSoilMoistureSimulator},
}


class Categories(Enum):
    tree = 'tree'
    landscape = 'landscape'


# All Components attributes are optional unless handler states required


ENTITY_TEMPLATES = {
    "Dandelion": {"handle": None, "category": None},
    "BlueberryBush": {"handle": None, "category": None},
    "Birch": {"handle": None, "category": Categories.tree, "params": TreeSpecies.birch.value[1]},
    "Pine": {"handle": None, "category": Categories.tree, "params": TreeSpecies.pine.value[1]},
    "Maple": {"handle": None, "category": Categories.tree, "params": TreeSpecies.maple.value[1]},
    "ChestnutTree": {"handle": None, "category": Categories.tree, "params": TreeSpecies.chestnut.value[1]},
    "WaterSource": {"handle": None, "category": Categories.landscape},  # TODO user right handler
}


def is_game_map(data):
    flags = []
    for key, type_check in MAP_FORMAT_ELEMENTS.items():
        if key in data.keys():
            pass_flag = isinstance(data[key], type_check)
        else:
            pass_flag = False
            logging.debug(f"Key '{key}' is not present in data")
            continue

        if pass_flag:
            logging.debug(f"Key '{key}' is of type '{type(data[key])}' [Pass]")
        else:
            logging.debug(f"Key '{key}' is of type '{type(data[key])}' [FAIL]")
        flags.append(pass_flag)
    # extra_keys = []  TODO
    return all(flags)


def inc_dict_counter(dict_var, key, val=1):
    if key in dict_var.keys():
        dict_var[key] += val
    else:
        dict_var[key] = val


def read_game_map(data):
    singletons_data = data["Singletons"]

    loaded_singletons = {}
    for key, spec in SINGLETONS.items():
        if key in singletons_data.keys():
            singleton_value = singletons_data[key]
            assert isinstance(singleton_value, spec['type'])
            obj = spec['class'].load(singleton_value)
            loaded_singletons[key] = obj

        elif spec.get("mandatory", False):
            logging.warning(f"Key '{key}' is mandatory but is not present!")
        else:
            pass

    import pprint
    logging.debug("Loaded singletons: ")
    # pprint.pprint(loaded_singletons)

    entity_data = data['Entities']
    loaded_entities = []
    unknown_entity_templates = []
    remove_templates = []
    removed_entity_counts = {}
    entity_counts = {}

    for entity_dict in entity_data:
        entity = TimberbornEntity.load(entity_dict)

        inc_dict_counter(entity_counts, entity.template)

        if entity.template in remove_templates:
            inc_dict_counter(removed_entity_counts, entity.template)
            continue

        if entity.template in ENTITY_TEMPLATES.keys():
            template = ENTITY_TEMPLATES[entity.template]
            logging.debug(f"Entity '{entity.template}' is known")
            # handler = template.get('handle')
        else:
            template = None
            # handler = AttributeHandler()
            unknown_entity_templates.append(entity.template)
            logging.warning(f"Entity '{entity.template}' is unknown!")
            answer = input("Remove entities with this template from the map? (Y/n 1/0)\n").strip().lower()
            if answer in ('y', '1'):
                remove_templates.append(entity.template)
                continue

        # entity['Components'] = entity_dict['Components']
        # logging.debug(f'Handler: {handler}')
        entity['Components'] = {}
        if template and (template['category'] == Categories.tree):
            entity['Components'] = TimberbornTreeComponents.load(entity_dict['Components'], _validator=TreeValidator())
        loaded_entities.append(entity)

    logging.debug("Loaded Entities: ")
    pprint.pprint(loaded_entities)
    if unknown_entity_templates:
        logging.warning(
            f"Found {len(unknown_entity_templates)} unknown entity templates: {', '.join(unknown_entity_templates)}"
        )
    else:
        logging.info("No unknown entities found")
    logging.info("Processed entities")
    pprint.pprint(entity_counts)

    if remove_templates:
        logging.info(f"Removed entities with templates: {', '.join(remove_templates)}")
