import logging
from enum import Enum
from typing import Optional, Union  # Any, List, ,


class Validator(dict):
    base_data = {}

    def __init__(self, data: dict = {}, raises: Union[bool, Exception] = False):
        super().__init__(**self.base_data)
        if data:
            self.update(data)

        if raises:
            if isinstance(raises, type) and issubclass(raises, Exception):
                self.exception_class = raises
            else:
                self.exception_class = ValueError
        else:
            self.exception_class = None

    def clean_attr(self, key: str):
        """ return value, was_fixed """
        logging.warning(f"{key} in {self.keys()} ?")
        if key in self.keys():
            logging.info(f"Validator: name='{key}' is required but missing!")
            sub = self.get(key)
            if sub.exception_class:
                raise sub.exception_class(f"Validation failed for `{key}` - required and can't be fixed!")
            else:
                value = dict(self[key])
                logging.debug(f"Will try to fix missing attribute with `{value}`")
                return (value, True)
        else:
            # logging.debug(f" name='{key}' is optional, skip")
            return (None, False)


class PlantValidator(Validator):
    base_data = {
        "Growable": Validator({"GrowthProgress": 1.0}),
        "BlockObject": Validator({"Coordinates": Validator(raises=True)}, raises=True)
    }

    def __init__(self, data: dict = {},  raises: Union[bool, Exception] = False, species: Optional[Enum] = None):
        super().__init__(data=data, raises=raises)
        if species:
            self.add_species_data(species.value[1])

    def add_species_data(self, plant_args):
        if plant_args.get("gth_good"):
            self["Yielder:Gatherable"] = Validator({
                "Yield": {
                    "Good": {"Id": plant_args['gth_good'].value},
                    "Amount": plant_args['gth_amount']
                }
            })
            self['GatherableYieldGrower'] = Validator({"GrowthProgress": 0.5})


class TreeValidator(PlantValidator):
    base_data = PlantValidator.base_data | {
        "Yielder:Cuttable": Validator({
            "Good": {
              "Id": "Log"
            },
            "Amount": 2
        }),
    }

    def add_species_data(self, plant_args):
        super().add_species_data(plant_args)
        self["Yielder:Cuttable"]["Amount"] = plant_args['logs']
