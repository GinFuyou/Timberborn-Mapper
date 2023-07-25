import argparse
import sys
from enum import Enum
from pathlib import Path
import logging

import colorama

R = colorama.Style.RESET_ALL
H1 = colorama.Fore.RED
BOLD = colorama.Style.BRIGHT


CONFIG_FILE = "mapperconf.toml"

# This is a config template, not source of config defaults. Use MapperConfig __init__ instead
DEFAULT_TOML = """[main]
config_version = 1
non_interactive = false
keep_json = false
maps_dir = ""

[map]
max_map_size_defualt = -1
max_map_size_limit = 512
max_elevation_default = -1
max_elevation_limit = 64
game_version = ""
"""

CONTACTS = {
    "Gin Fuyou": {
        "updated": "Feb. 2023",
        "Timberborn official Discord": "https://discord.gg/csbUhFuw",
        "Github": "https://github.com/GinFuyou/Timberborn-Mapper",
    }
}


class MapperConfig(argparse.Namespace):
    _os_dict = {
        "windows": "w",
        "unknown": "w",  # not like we have many valid options
        "macos": "m",
        "linux": "w"     # change if game supports Linux _natively_
    }
    _base_game_version = "0.4.9.3-6c7fb02"
    _mapper_version = ""

    def __init__(self, mapper_version, skip_values=["", "DEFAULT"], **kwargs):
        self._skip_values = skip_values

        self.maps_dir = ""
        self.max_map_size_defualt = 256
        self.max_map_size_limit = 512
        self.max_elevation_default = 16
        self.max_elevation_limit = 64
        self.nocolor = False
        self.non_interactive = False
        self.keep_json = False

        self._mapper_version = mapper_version
        self._os_key = self.get_os()
        self._os_letter = self._os_dict[self._os_key]
        self.game_version = f"{self._base_game_version}-s{self._os_letter}"

        self._safe_extend(skip_values, **kwargs)

    def get_os(self):
        key = "unknown"
        if sys.platform.startswith("linux"):
            key = "linux"
        elif sys.platform.startswith("win") or sys.platform.startswith("cygwin"):
            key = "windows"
        elif sys.platform.startswith("darwin"):
            key = "macos"
        return key

    def guess_game_dir(self, user=""):
        path = None
        if self._os_key in ("windows", "macos", "linux"):
            path = Path(f"~{user}/Documents/Timberborn/")
        if path:
            path = path.expanduser()
            logging.debug(f"Game Dir: '{path}'")
            if path.is_dir():
                return path
        return None

    def _safe_extend(self, skip_values, **kwargs):
        for key, val in kwargs.items():
            if (val not in skip_values) and (key[0] != "_"):
                setattr(self, key, val)

    """
    def load_defaults(self, **kwargs):
         for key, val in kwargs.items():
            if (key[0] != "_") and not hasattr(self, key):
                setattr(self, key, val)
    """

    def update_extend(self, **kwargs):
        """extend self attributes overriding existing if value is not in skip_values"""
        if "_skip_values" in kwargs:
            skip_values = kwargs.pop("_skip_values")
        else:
            skip_values = self._skip_values

        self._safe_extend(skip_values, **kwargs)


class GameDefs(Enum):
    """ Game default values and properties """
    MAP_SUFFIX = ".timber"
    MAX_ELEVATION = 16
    MAX_MAP_SIZE = 256


class GameVer:
    def __init__(self, version_str: str):
        splits = version_str.split('-')
        self.string = version_str
        self.numeric = splits[0]
        if len(splits) > 1:
            self.hash = splits[1]
        else:
            self.hash = None
        if len(splits) > 2:
            self.specific = splits[2]
        else:
            self.specific = None

        self.tuple = tuple(self.numeric.split('.'))

    def __lt__(self, other):
        return self.tuple.__lt__(other.tuple)

    def __le__(self, other):
        return self.tuple.__le__(other.tuple)

    def __eq__(self, other):
        return self.tuple.__eq__(other.tuple)

    def __ne__(self, other):
        return self.tuple.__ne__(other.tuple)

    def __gt__(self, other):
        return self.tuple.__gt__(other.tuple)

    def __ge__(self, other):
        return self.tuple.__ge__(other.tuple)

    def is_older_than_base(self):
        return self < GameVer(MapperConfig._base_game_version)

    def diff_strings(self, other=MapperConfig._base_game_version):
        if isinstance(other, str):
            other = GameVer(other)

        is_different = False
        highlighted = []
        for i, char in enumerate(self.string):
            if not is_different:
                try:
                    other_char = other.string[i]
                    is_different = is_different or (other_char != char)
                except IndexError:
                    is_different = True
            if is_different:
                highlighted.append(f"{BOLD}{H1}{char}{R}")
            else:
                highlighted.append(char)

        return (other.string, "".join(highlighted))


class Action:
    def __init__(self, code, description, function, args=[], kwargs={}):
        self.code = code
        self.description = description
        self.function = function
        self.args = args
        self.kwargs = kwargs


class ActionHandler:
    action_dict = {'quit': Action("quit", "Abort and exit", sys.exit, ["User abort"])}

    def __init__(self, actions=[]):
        self.actions = [self.action_dict['quit']] + actions

    def add_action(self, code, description, function, args=[], kwargs={}):
        self.actions.append(Action(code, description, function, args, kwargs))

    def render_choices(self):
        print(" ~ Select available action. (type number and press Enter) [q/0] to exit: ~")
        for index, action in enumerate(self.actions):
            if index == 0:
                continue
            print(f"{BOLD}{index: >2}{R}. {action.description}")
        print(f" {BOLD}0{R}. {self.actions[0].description}")

    def run_action(self, index):
        action = self.get_action(index)
        return action.function(*action.args, **action.kwargs)

    def get_action(self, index):
        if index <= len(self.actions)-1:
            return self.actions[index]
        else:
            return self.actions[0]

    def run_by_input(self):
        answer = ""
        choices = [str(i) for i in range(len(self.actions)+1)] + ['q']
        while answer not in choices:
            answer = input("> ").strip().lower()

        if answer == 'q':
            return self.run_action(0)
        else:
            return self.run_action(int(answer))
