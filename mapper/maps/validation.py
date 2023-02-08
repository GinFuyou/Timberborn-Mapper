import logging
from typing import Union  # Any, List, Optional,


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
        if key in self.keys():
            logging.warning(f"Validator: name='{key}' is required but missing!")  # TODO TEST
            sub = self.get(key)
            if sub.exception_class:
                raise sub.exception_class(f"Validation failed for `{key}` - required and can't be fixed!")
            else:
                value = dict(self[key])
                logging.debug(f"Will try to fix missing attribute with `{value}`")
                return (value, True)
        else:
            logging.debug(f" name='{key}' is optional, skip")  # TODO TEST
            return (None, False)


class TreeValidator(Validator):
    base_data = {
        "Growable": Validator({"GrowthProgress": 1.0}),
        "BlockObject": Validator({"Coordinates": Validator(raises=True)}, raises=True),
        "Yielder:Cuttable": Validator({
            "Good": {
              "Id": "Log"
            },
            "Amount": 2
        }),
    }
