import logging
from datetime import datetime
from enum import Enum

from image_utils import build_image

from .format import (TimberbornEntity, TimberbornMap, TimberbornMapSize, TimberbornPlantComponents, TimberbornRuinComponents,
                     TimberbornSingletons, TimberbornSoilMoistureSimulator, TimberbornTerrainMap, TimberbornTreeComponents,
                     TimberbornWaterMap, TimberbornWaterSourceComponents)
# TimberbornSimpleComponents
from .treemap import PlantSpecies, TreeSpecies  # Goods
from .validation import BlockValidator, OrientableValidator, PlantValidator, RuinValidator, TreeValidator, WaterSourceValidator

MAP_FORMAT_ELEMENTS = {"GameVersion": (str, int), "Singletons": dict, "Entities": list}
SAVE_FORMAT_ELEMENTS = {"WeatherDurationService": dict, "WeatherService": dict, "FactionService": dict}
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
    features = 'features'
    ruins = 'ruins'


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
    "Oak": {"validator": TreeValidator(species=TreeSpecies.oak),
            "category": Categories.tree,
            "params": TreeSpecies.oak.value[1]},
    "WaterSource": {"validator": WaterSourceValidator(), "category": Categories.landscape},
    "Barrier": {"validator": BlockValidator(), "category": Categories.landscape},
    "Slope":  {"validator": OrientableValidator(), "category": Categories.landscape},
    "UndergroundRuins": {"validator": OrientableValidator(), "category": Categories.features},  # TODO
    "StartingLocation": {"validator": OrientableValidator(), "category": Categories.features},  # TODO
}

ENTITY_REPLACE = {"ChestnutTree": "Pine",
                  "Maple": "Oak"}

ENTITY_TEMPLATES.update(
    {f"RuinColumnH{i}": {"validator": RuinValidator(), "category": Categories.ruins} for i in range(1, 9)}
)


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


def is_game_save(data):
    flags = [key in data.keys() for key in SAVE_FORMAT_ELEMENTS.keys()]
    return any(flags) and is_game_map(data)


def inc_dict_counter(dict_var, key, val=1):
    if key in dict_var.keys():
        dict_var[key] += val
    else:
        dict_var[key] = val


def load_singletons(singletons_data) -> TimberbornSingletons:
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

    return TimberbornSingletons(**loaded_singletons)


def read_terrain(data, config, output_path=None):
    loaded_singletons = load_singletons(data["Singletons"])
    terrain_map = loaded_singletons['TerrainMap']
    map_size = loaded_singletons['MapSize']['Size'].value
    heights_array = terrain_map['Heights'].array_list
    logging.debug(f"Map size: {map_size}")

    image = build_image(heights_array, map_size)

    if output_path:
        output_path = output_path.with_suffix('.png')
        image.save(output_path, "PNG")
        logging.info(f"Exported terrain map as '{output_path}'")
    else:
        image.show()


def read_game_map(data, config, output_path=None):

    loaded_singletons = load_singletons(data["Singletons"])

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
    replaced_entity_counts = {}
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
            # logging.debug(f" *** Entity #{counter} '{entity.template}' is known")
        else:
            template = None
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
            # check if replace required
            logging.debug(f"load template: '{entity.template}'")
            if entity.template in ENTITY_REPLACE.keys():
                replace_template_name = ENTITY_REPLACE[entity.template]
                if config.no_entity_replace:
                    logging.debug(f"Template '{entity.template}' should be replaced with "
                                  f"{replace_template_name} but it was disabled.")
                else:
                    logging.debug(f"Replace {entity.template} with {replace_template_name}")
                    inc_dict_counter(replaced_entity_counts, entity.template)
                    template = ENTITY_TEMPLATES[replace_template_name]

            category = template['category']

            try:
                if category == Categories.tree:
                    entity['Components'] = TimberbornTreeComponents.load(
                        entity_dict['Components'], _validator=template['validator']
                    )
                elif category == Categories.plant:
                    entity['Components'] = TimberbornPlantComponents.load(
                        entity_dict['Components'], _validator=template['validator']
                    )
                elif category == Categories.ruins:
                    entity['Components'] = TimberbornRuinComponents.load(
                        entity_dict['Components'], _validator=template['validator']
                    )
                elif entity.template == "WaterSource":
                    entity['Components'] = TimberbornWaterSourceComponents.load(
                        entity_dict['Components'], _validator=template['validator']
                    )
                else:
                    logging.warning(f"Template '{entity.template}' is not handled by validation")

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

    if replaced_entity_counts:
        logging.info("Replaced entities")
        for key, val in replaced_entity_counts.items():
            logging.info(f"{key: >18}: {val: >6}")

    if remove_templates:
        logging.info(f"Removed entities with templates: {', '.join(remove_templates)}")

    timber_map = TimberbornMap(
        updated_game_version,
        loaded_singletons,
        loaded_entities,
        updated_timestamp,
        MapperVersion=config._mapper_version,
    )
    if output_path:
        timber_path = timber_map.write(output_path, config)
        print(f"\nSaved to '{timber_path}'\nIt's HIGHLY recommended you open map in in-game editor and re-save it.")
