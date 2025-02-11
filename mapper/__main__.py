#!/usr/bin/env python3
import argparse
import json
import logging
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from platform import python_version
# from subprocess import run
from time import time
from typing import Any, Optional, Union
from zipfile import ZipFile

import colorama
from appdirs import AppDirs
from base import CONFIG_FILE, CONTACTS, DEFAULT_TOML, ActionHandler, GameDefs, GameVer, MapperConfig
from maps.format import INTERNAL_ARC_NAME, TimberbornMap, TimberbornSingletons
from maps.gamemap import is_game_map, is_game_save, read_game_map, read_terrain, ascii_preview
from maps.heightmap import ImageToTimberbornHeightmapLinearConversionSpec, ImageToTimberbornHeightmapSpec, read_heightmap
from maps.treemap import ImageToTimberbornTreemapSpec, read_tree_map
from maps.watermap import read_water_map

try:
    import tomllib
except ModuleNotFoundError:
    TOML_AVAILABLE = False
else:
    TOML_AVAILABLE = True

#  __  __      _
# |  \/  |__ _(_)_ _
# | |\/| / _` | | ' \
# |_|  |_\__,_|_|_||_|
# Main

__version__ = "0.4.10a3"

APPNAME = "TimberbornMapper"
# Original script creator
APP_AUTHOR = "MattMcMullan"


R = colorama.Style.RESET_ALL
H1 = colorama.Fore.BLUE
W1 = colorama.Fore.RED
# H2 = colorama.Fore.GREEN
BOLD = colorama.Style.BRIGHT
CODE = colorama.Back.WHITE + colorama.Fore.BLACK


@dataclass
class ImageToTimberbornWatermapSpec:
    filename: str


class ImageToTimberbornSpec:
    def __init__(
        self,
        heightmap: Union[ImageToTimberbornHeightmapSpec, dict],
        width: int = -1,  # XXX should use optional instead of sentinel value
        height: int = -1,
        treemap: Union[Optional[ImageToTimberbornTreemapSpec], dict] = None,
        watermap: Union[Optional[ImageToTimberbornWatermapSpec], dict] = None,
    ):
        self.width = width
        self.height = height

        if isinstance(heightmap, dict):
            heightmap = ImageToTimberbornHeightmapSpec(**heightmap)
        self.heightmap = heightmap

        if isinstance(treemap, dict):
            treemap = ImageToTimberbornTreemapSpec(**treemap)
        self.treemap = treemap

        if isinstance(watermap, dict):
            watermap = ImageToTimberbornWatermapSpec(**watermap)
        self.watermap = watermap

    width: int
    height: int
    heightmap: ImageToTimberbornHeightmapSpec
    treemap: Optional[ImageToTimberbornTreemapSpec]
    watermap: Optional[ImageToTimberbornWatermapSpec]


def image_to_timberborn(spec: ImageToTimberbornSpec, path: Path, output_path: Path, args: Any) -> Path:
    config = args

    logging.info(f"Output dir: `{output_path.parent}`")

    t = -time()
    heightmap = read_heightmap(width=spec.width, height=spec.height, spec=spec.heightmap, path=path, args=config)
    logging.info(f"Finished in {t + time():.2f} sec.")

    t = -time()
    if spec.watermap is None:
        water_map = read_water_map(heightmap, None, None)
    else:
        water_map = read_water_map(heightmap, filename=spec.watermap.filename, path=path)
    logging.info(f"Finished water map in {t + time():.2f} sec.")

    t = -time()
    tree_map = read_tree_map(heightmap, water_map, spec=spec.treemap, path=path)
    logging.info(f"Finished tree map in {t + time():.2f} sec.")

    singletons = TimberbornSingletons(
        MapSize=heightmap.map_size,
        SoilMoistureSimulator=water_map.soil_moisture_simulator,
        TerrainMap=heightmap.terrain_map,
        WaterMap=water_map.water_map,
    )
    timber_map = TimberbornMap(config.game_version, singletons, tree_map.entities, MapperVersion=__version__)
    timber_path = timber_map.write(output_path, config)
    print(f"\nSaved to '{timber_path}'\nYou can now open it in Timberborn map editor to add finishing touches.")
    return timber_path


def make_output_path(args: Any, suffix=GameDefs.MAP_SUFFIX.value) -> Path:
    output_path = args.output
    if output_path:
        if output_path.suffix != suffix:
            logging.warning(f"Output extension ('{output_path.suffix}') is not '{suffix}'"
                            f" it will be changed automatically.")
    elif args.maps_dir:
        output_path = Path(args.maps_dir) / args.input.with_suffix('.tmp').name
    else:
        output_path = args.input.with_suffix(".tmp")
    if not output_path.is_absolute():
        output_path = Path.cwd() / output_path
    return output_path


def manual_image_to_timberborn(args: Any) -> None:
    treemap = None
    if args.treemap is not None:
        treemap = ImageToTimberbornTreemapSpec(
            filename=args.treemap,
            treeline_cutoff=args.treeline_cutoff,
            birch_cutoff=args.birch_cutoff,
            pine_cutoff=args.pine_cutoff,
        )

    watermap = None
    if args.water_map is not None:
        watermap = ImageToTimberbornWatermapSpec(
            filename=args.water_map,
        )

    output_path = make_output_path(args)

    image_to_timberborn(
        ImageToTimberbornSpec(
            width=args.width,
            height=args.height,
            heightmap=ImageToTimberbornHeightmapSpec(
                filename=args.input,
                linear_conversion=ImageToTimberbornHeightmapLinearConversionSpec(
                    min_height=args.min_elevation, max_height=args.max_elevation
                ),  # if not args.bucketize_heightmap else None,
                # ImageToTimberbornHeightmapBucketizedConversionSpec() if args.bucketize_heightmap else None,
                bucketized_conversion=None,
            ),
            treemap=treemap,
            watermap=watermap,
        ),
        args.input.parent,
        output_path,
        args,
    )


def read_json_input(config: Any) -> None:
    if config.input.suffix.lower() == GameDefs.MAP_SUFFIX.value:
        with ZipFile(config.input) as timber_zip:
            namelist = timber_zip.namelist()
            if INTERNAL_ARC_NAME in namelist:
                world_file_name = INTERNAL_ARC_NAME
            else:
                world_file_name = ""
                logging.warning(
                    f'"{config.input.basename}" doesn\'t include "{INTERNAL_ARC_NAME}"! Will use first ".json" file'
                )
                for name in namelist:
                    if name.endswith(".json"):
                        world_file_name = name
                if not world_file_name:
                    logging.error("No suitable file found!")
                    raise RuntimeError("Input file doesn't contain expected data")

            with timber_zip.open(world_file_name, "r") as world_file:
                data = json.loads(world_file.read())
    else:
        with open(config.input, "r") as f:
            data = json.load(f)

    action_handler = ActionHandler()

    if "heightmap" in data.keys():
        logging.info("Found key 'heightmap' in json data, processing as spec file")
        specfile_to_timberborn(data, config)
    elif is_game_map(data):
        action_handler.add_action(
            code="export-terrain",
            description=f'{BOLD}[BETA]{R} Export height map as PNG',
            function=read_terrain,
            args=(data, config),
            kwargs={'output_path': make_output_path(config, suffix='.png')}
        )
        action_handler.add_action(
            code="map-ascii",
            description=f'{BOLD}[BETA]{R} shom map preview as ASCII',
            function=ascii_preview,
            args=(data, config),
            kwargs={}
        )

        file_game_ver = data.get("GameVersion", None)
        if is_game_save(data):
            logging.info(f"File looks like game save format, game version stated: {file_game_ver}")
        else:
            logging.info(f"File looks like game map format, game version stated: {file_game_ver}")
            if file_game_ver is None:
                file_game_ver = "0"
            file_game_ver = GameVer(file_game_ver)
            base_str, diff_str = file_game_ver.diff_strings()
            logging.info(f"Base ver: {base_str}")
            logging.info(f"File ver: {diff_str}")
            if file_game_ver.is_older_than_base():
                logging.debug("Upgrade action is reasonable")
            action_handler.add_action(
                code="upgrade-map",
                description=(
                    f"{BOLD}[BETA]{R} upgrade map to version ~ '{config.game_version} and pack as "
                    f"'{GameDefs.MAP_SUFFIX.value}'\n"
                    f"\t{BOLD}{W1}warning{R}: this is an experimental feature, there is no gurantee it will work,\n"
                    "\tit also might remove objects from the map.\n"
                    f"\t{BOLD}note{R}: this may output a huge wall of text depending on log level"
                ),
                function=read_game_map,
                args=(data, config),
                kwargs={'output_path': make_output_path(config)}
            )

        if config.select_action:
            action_index = int(config.select_action)
            logging.info(f"Auto-selected '{action_handler.get_action(action_index).code}'")
            action_handler.run_action(action_index)

        elif config.non_interactive:
            # TODO guess action by GameVersion, force action by config args
            action_index = 1
            logging.info(f"Non-interactive mode: assuming '{action_handler.get_action(action_index).code}'")
            action_handler.run_action(action_index)

        else:
            action_handler.render_choices()
            action_handler.run_by_input()
    else:
        logging.error("Can't identify file by content!")


def specfile_to_timberborn(specdict: dict, config: Any) -> None:
    output_path = make_output_path(config)
    image_to_timberborn(ImageToTimberbornSpec(**specdict), config.input.parent, output_path, config)


def build_parser() -> argparse.ArgumentParser:
    # try to guess script name ('python mapper' vs 'TimberbornMapper.exe')
    script = "mapper"
    for arg in sys.argv:
        if arg.lower().endswith('.exe'):
            script = Path(arg).name
            break

    description = (
        f"Tool for importing heightmap images as Timberborn custom maps.\n"
        f"\n  {BOLD}HOW TO USE:{R}\n\n"
        f" Script has 2 modes: {BOLD}manual{R} and {BOLD}specfile{R}\n"
        f" - {BOLD}Manual{R} mode takes as input a path to an heightmap (image) file and a number of options\n"
        f" - {BOLD}Specfile{R} mode pulls all map option from a json-formatted file, commandline map options are\n"
        f" ignored.\n"
        f" Mode is set by checking input file extension.\n\n"
        f" If you are using a binary version you can just {BOLD}drag-n-drop{R} image or spec file on executable or it's link.\n"
        f" (but then you can't set options directly)\n\n"
        f' Run "{BOLD}{script} --help{R}" to see manual mode and generic options. \n'
        f" like desired map height and width or base elevation. It can also take separate tree and water maps.\n\n"
        f" Try example command:\n"
        f" {CODE}{script} m examples/alpine_lakes/height.png --min-height 4 --width 128 --height 128{R}\n"
        f" Output will be zipped JSON file with {H1}{BOLD}{GameDefs.MAP_SUFFIX.value}{R} extension that should be ready to be"
        f"  opened with {BOLD}{H1}map editor{R}."
    )

    parser = argparse.ArgumentParser(
        description=description,
        formatter_class=argparse.RawTextHelpFormatter,
    )

    parser.add_argument("input", type=Path, help="Path to a heightmap image or json spec file")
    parser.add_argument(
        "--output", type=Path, help="Path to output the resulting map to. Defaults to input file name, with timber ext."
    )

    parser.add_argument(
        "--min-elevation", "--min-height", "--low", type=int,
        help="Soil elevation at the lowest point in the heightmap. Defaults to 3.", default=3,
    )
    parser.add_argument(
        "--max-elevation", "--max-height", "--high", type=int,
        help=f"Soil elevation at the highest point in the heightmap. Defaults to {GameDefs.MAX_ELEVATION.value}.",
        default=GameDefs.MAX_ELEVATION.value
    )
    # parser.add_argument(
    #     "--bucketize-heightmap",
    #     action="store_true",
    #     help=("Use a specific proportion of height values rather than linearly interpolating the image value"
    #           " between the min and max height. Use a spec file to specify non-default bucket weights."),
    # )
    parser.add_argument("--width", type=int, help="Width of the resulting map. Defaults to image width.", default=-1)
    parser.add_argument("--height", type=int, help="Height of the resulting map. Defaults to image height.", default=-1)

    parser.add_argument("--treemap", type=str, help="Path to a grayscale treemap image.", default=None)
    parser.add_argument(
        "--treeline-cutoff",
        type=float,
        help="Relative pixel intensity under which trees will not spawn. Defaults to 0.1.",
        default=0.1,
    )
    parser.add_argument(
        "--birch-cutoff",
        type=float,
        help="Relative pixel intensity under which trees will spwan as birch trees. Defaults to 0.4.",
        default=0.4,
    )
    parser.add_argument(
        "--pine-cutoff",
        type=float,
        help="Relative pixel intensity under which trees will spwan as pine trees. Defaults to 0.7.",
        default=0.7,
    )

    parser.add_argument("--water-map", type=str, help="Path to a grayscale water map image. None by default.", default=None)

    parser.add_argument('-c', '--confpath', type=str, default='',
                        help="Path to config file. Will use default location if empty. '0' to disable.")
    """
    parser.add_argument('--open-config', action='store', dest='open_config',
                        nargs='?', const='vi', default=False,
                        help="Open config file with editor, editor command as argument or vi as default")
    """
    parser.add_argument('--keep-json', action='store_true', default='DEFAULT', help="Do not remove map .json after packing")
    parser.add_argument('--replace-entities', action='store', default='DEFAULT',
                        help="DEFAULT, 0, or JSON dictionary of original:target mapping of Entity Template IDs")
    # parser.add_argument('--write-config', action="store_true", help='Write (overwrite) config file at defualt location.')
    parser.add_argument('-l', '--loglevel', choices=('debug', 'info', 'warning', 'error', 'critical'), default='info',
                               help='Control additional output verbosity')
    # parser.add_argument('-C', '--nocolor', action="store_true", default='DEFAULT', help='Disable usage of colors in console')

    parser.add_argument('-I', '--non-interactive', action='store_true', default='DEFAULT', help="Disable interactions"),

    parser.add_argument('--no-entity-replace', action="store_true",
                        help="Disable replacing outdated objects according to specification")

    parser.add_argument('--select-action', action='store', default='',
                        help="(ALPHA) automatically select interaction by number")

    return parser


def main() -> None:
    t = -time()
    colorama.init()

    args = build_parser().parse_args()
    config = MapperConfig(mapper_version=__version__, skip_values=["", "DEFAULT", -1])

    # configure logging
    loglevel = getattr(args, "loglevel", "INFO").upper()
    logging.basicConfig(
        level=getattr(logging, loglevel),
        format=f'{H1}%(levelname)s{R}: %(message)s'
    )
    print(f"{BOLD}Timberborn Mapper{R} ver. {H1}{BOLD}{__version__}{R} running on python {H1}{python_version()}{R}")

    """
    if TOML_AVAILABLE:
        if args.open_config:
            run([args.open_config, str(config_path)])
            sys.exit(0)

    """

    if args.confpath == "0":
        logging.debug("config reading is disabled by options")
        # config.read_dict(DEFUALT_CONF)
    elif TOML_AVAILABLE:
        if args.confpath:
            config_path = Path(args.confpath)
        else:
            app_dirs = AppDirs(APPNAME, APP_AUTHOR)
            config_path = Path(app_dirs.user_config_dir) / CONFIG_FILE

        if config_path.is_file():
            logging.debug(f"reading config file from '{config_path}'")
            with open(config_path, "rb") as f:
                toml_config = tomllib.load(f)
                for title, section in toml_config.items():
                    config.update_extend(**section)
        else:
            if args.confpath:
                logging.critical(f"Can't read config file - it doesn't exist or not a file: '{config_path}'")
                sys.exit("Couldn't read configuration")
            else:
                try:
                    toml_config = tomllib.loads(DEFAULT_TOML)
                    for title, section in toml_config.items():
                        config.update_extend(**section)
                    config_path.parent.mkdir(parents=True, exist_ok=True)

                    toml_str = DEFAULT_TOML

                    if not config.non_interactive:
                        guessed_game_dir = config.guess_game_dir()
                        if guessed_game_dir:
                            answer = None
                            print(f"Found game directory at '{guessed_game_dir}'")
                            while answer not in ('y', 'n', '0', '1'):
                                answer = input("Add it's 'Maps/' into config file? (Y/n or 0/1) > ")
                                if answer:
                                    answer = str(answer).strip().lower()[0]
                            if answer in ('1', 'y'):
                                maps_dir = str(guessed_game_dir / "Maps/").replace("\\", "\\\\")
                                toml_str = re.sub(
                                    '^maps_dir = [\"\']{2}',
                                    f'maps_dir = "{maps_dir}"',
                                    toml_str,
                                    flags=re.M
                                )

                    with open(config_path, "w") as f:
                        f.write(toml_str)
                except tomllib.TOMLDecodeError as exc:
                    logging.error(f"Error in default TOML configuration, please contact authors: {exc}")
                except (OSError, PermissionError) as exc:
                    logging.error(f"Couln't write config file to '{config_path}', probably permissions or path issue: {exc}")
                else:
                    logging.info(f"Created defualt config file: '{config_path}'")
    else:
        logging.warning("tomllib is not available (it's included in python 3.11+) reading configuration files is disabled")

    config.update_extend(_skip_values=["DEFAULT"], **vars(args))

    if config.width > config.max_map_size_limit or config.height > config.max_map_size_limit:
        logging.warning(f"map size {config.width} x {config.height} exceeds 'max_map_size_limit' = {config.max_map_size_limit}")
        max_of_size = max(config.width, config.height)
        ratio = config.max_map_size_limit / max_of_size
        if config.width > 0:
            config.width = int(config.width * ratio)
        if config.height > 0:
            config.height = int(config.height * ratio)
        logging.warning(f"adjusted to {config.width} x {config.height}. Change options or config to override.")
    # config building is done

    logging.debug(f"OS detected as {config._os_key.title()} mapper will set GameVersion as {config.game_version}")

    # from pprint import pprint
    # pprint(vars(config))
    # print("-- dir --")
    # pprint(dir(config))

    if not config.input.is_absolute():
        config.input = Path.cwd() / config.input

    logging.info(f"Input path: `{config.input}`")

    if not config.input.is_file():
        sys.exit(f"Path `{config.input}` is not a file or not accessible. Please check it and try again.")

    # wrapping execution in exception catcher to halt window form closing in interactive mode
    try:
        suffix = config.input.suffix.lower()
        if suffix in (".json", GameDefs.MAP_SUFFIX.value):
            logging.debug(f' "{suffix}" file will be read and handled based on contents')
            read_json_input(config)
        else:
            logging.info("File will be verified and processed like an image")
            manual_image_to_timberborn(config)
    except Exception as exc:
        logging.critical(f"{W1}{BOLD}Exception happened!{R}")
        contact_msg = "If you can't figure it out, please contact developers about the problem and include traceback:\n"
        for dev, contacts in CONTACTS.items():
            contact_msg += f"{BOLD}{dev}{R}:\n"
            for title, value in contacts.items():
                if title.lower() == 'updated':
                    contact_msg += f"\t(updated on {value})\n"
                else:
                    contact_msg += f"\t{BOLD}{title}{R}: {value}\n"

        if not config.non_interactive:
            logging.critical("Following error happened during execution:")
            logging.critical(exc)
            print(contact_msg)
            input('(Press enter to throw traceback and exit. Run from console to see details if window closes)')
        else:
            print(contact_msg)
        raise exc

    t += time()
    if not config.non_interactive:
        input('(Press enter to exit)')
    logging.info(f"Total execution time: {t:.2f} sec.")


if __name__ == "__main__":
    main()
