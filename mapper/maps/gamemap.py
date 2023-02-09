import logging
from datetime import datetime
from enum import Enum

from .format import (TimberbornEntity, TimberbornMap, TimberbornMapSize, TimberbornPlantComponennts, TimberbornSingletons,
                     TimberbornSoilMoistureSimulator, TimberbornTerrainMap, TimberbornTreeComponents, TimberbornWaterMap)
from .treemap import PlantSpecies, TreeSpecies  # Goods
from .validation import PlantValidator, TreeValidator  # , Validator

MAP_FORMAT_ELEMENTS = {"GameVersion": (str, int), "Singletons": dict, "Entities": list}
SINGLETONS = {
    "MapSize": {"type": dict, "mandatory": True, "class": TimberbornMapSize},
    "TerrainMap": {"type": dict, "mandatory": True, "class": TimberbornTerrainMap},
    "WaterMap": {"type": dict, "mandatory": True, "class": TimberbornWaterMap},
    "SoilMoistureSimulator": {'type': dict, "mandatory": True, "class": TimberbornSoilMoistureSimulator},
}


class Categories(Enum):
    tree = 'tree'
    plant = 'plant'
    landscape = 'landscape'


# All Components attributes are optional unless handler states required


ENTITY_TEMPLATES = {
    "Dandelion": {"validator": PlantValidator(species=PlantSpecies.dandelion), "category": Categories.plant},
    "BlueberryBush": {"validator": PlantValidator(species=PlantSpecies.blueberry), "category": Categories.plant},
    "Birch": {"validator": TreeValidator(species=TreeSpecies.birch),
              "category": Categories.tree,
              "params": TreeSpecies.birch.value[1]},
    "Pine": {
                "validator": TreeValidator(species=TreeSpecies.pine),
                "category": Categories.tree, "params": TreeSpecies.pine.value[1]
            },
    "Maple": {"validator": TreeValidator(species=TreeSpecies.maple),
              "category": Categories.tree,
              "params": TreeSpecies.maple.value[1]},
    "ChestnutTree": {"validator": TreeValidator(species=TreeSpecies.chestnut),
                     "category": Categories.tree,
                     "params": TreeSpecies.chestnut.value[1]},
    "WaterSource": {"validator": None, "category": Categories.landscape},  # TODO user right handler
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


def read_game_map(data, config, output_path=None):
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

    loaded_singletons = TimberbornSingletons(**loaded_singletons)

    # import pprint
    # logging.debug("Loaded singletons: ")
    # pprint.pprint(loaded_singletons)

    entity_data = data['Entities']
    loaded_entities = []
    unknown_entity_templates = []
    ignored_entity_templates = set()
    remove_templates = []
    removed_entity_counts = {}
    entity_counts = {}
    initial_entity_count = len(entity_data)
    counter = 0

    for entity_dict in entity_data:
        counter += 1
        if counter % 100 == 0:
            logging.info(f" Processing Entities: {counter: >3}/{initial_entity_count}")

        entity = TimberbornEntity.load(entity_dict)

        inc_dict_counter(entity_counts, entity.template)

        if entity.template in remove_templates:
            inc_dict_counter(removed_entity_counts, entity.template)
            continue

        if entity.template in ignored_entity_templates:
            continue

        if entity.template in ENTITY_TEMPLATES.keys():
            template = ENTITY_TEMPLATES[entity.template]
            logging.debug(f" *** Entity #{counter} '{entity.template}' is known")
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
            else:
                ignored_entity_templates.add(entity.template)

        entity['Components'] = entity_dict['Components']
        if template:
            try:
                if template['category'] == Categories.tree:
                    entity['Components'] = TimberbornTreeComponents.load(
                        entity_dict['Components'], _validator=template['validator']
                    )
                elif template['category'] == Categories.plant:
                    entity['Components'] = TimberbornPlantComponennts.load(
                        entity_dict['Components'], _validator=template['validator']
                    )

            except Exception as ex:
                logging.error(f"Couldn't load Components for template '{entity.template}': {entity_dict['Components']}")
                raise ex

        loaded_entities.append(entity)

    updated_game_version = config.game_version
    updated_timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # logging.debug("Loaded Entities: ")
    # pprint.pprint(loaded_entities)
    if unknown_entity_templates:
        logging.warning(
            f"Found {len(unknown_entity_templates)} unknown entity templates: {', '.join(unknown_entity_templates)}"
        )
    else:
        logging.info("No unknown entities found")

    if entity_counts:
        logging.info("Processed entities")
        for key, val in entity_counts.items():
            logging.info(f"{key: >18}: {val: >6}")
    else:
        logging.info("No entities in the file")

    if remove_templates:
        logging.info(f"Removed entities with templates: {', '.join(remove_templates)}")

    timber_map = TimberbornMap(
        updated_game_version,
        loaded_singletons,
        loaded_entities,
        updated_timestamp
    )
    if output_path:
        timber_map.write(output_path, config)
