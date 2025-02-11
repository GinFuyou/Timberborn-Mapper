# Timberborn-Mapper
A tool for turning height maps into Timberborn maps.

![](https://raw.githubusercontent.com/GinFuyou/Timberborn-Mapper/main/assets/TimberbornMapper-700.png)
> Screen cap is taken using QuadrupleTerrainHeight mod using 48 layers, vanilla game supports less.

# About

## What it does
1. Converts grayscale images into game map file with terrain.
2. Adds trees and water from *additional* grayscale images.
3. BETA: upgrades old `.json` maps to be loadable.
4. BETA: export game maps into grayscale height maps.

## What it does NOT:
1. Does not create maps fully ready to play: you need to add water sources and starting location in editor.
2. Does not work with save files. *(planned)*

# Setup

## Option 1: (Windows-only) pre-build executable
Windows users can try script packaged as executable `.exe` file from [dist directory](dist/).

__No dependencies or setup required__.

Copy `examples/` dir to try suggested commands.

> Paranoid A/V software can give false positive alert about executable files. Variant packaged as dir might look less suspicious to them, so try it if it's your case or just add exception.

Virustotal gave  [4/70 score](https://www.virustotal.com/gui/file/7fdb18b8097ae138ace2ff792fcb83f6d28271174fe212a6d31ccd9474805d3f/detection), I believe it's safe for you to presume executable is safe.

## Option 2: Cross-platform python script using poetry
Using poetry

1. Install python. You can find it [here](https://www.python.org/downloads/).
2. Clone repository (Click the green "Code" button in github for directions to download this code.)
3. Install [poetry](https://python-poetry.org/docs/)
4. `poetry install` will install all dependencies from `pyproject.toml` and manages virtual environment
5. `poetry shell` activates virtual environment for the project

## Option 3: Cross-platform python script with manual dependencies
1. Install python. You can find it [here](https://www.python.org/downloads/).
2. Install pillow. You can read their instructions [here](https://pillow.readthedocs.io/en/stable/installation.html), or just open your command prompt and run "python -m pip install pillow".
3. Click the green "Code" button in github for directions to download this code.

> Currently project requires python 3.10 or 3.11 but may work on other versions.

# Usage

## Height map import
- script expects a grayscale image as height map (most likely a PNG but some other formats should also work)
- check help for available options, like setting map size, output file name and script behaviour modifiers

### Script version
- Open the command prompt and cd to the directory with the code.
- Run `python mapper --help` to see instructions on how to use it.

### Binary version (Windows)
You can just **drag-n-drop** height map image or `.json` / `.timber` file onto executable's icon or it's links. But can't set options directly this way.
It will output **.timber** file into same place where input file was taken if game dir is not set with config file.

Alternatively:

- Open command promt (or powershell) and `cd` ("change directory" command) to the folder with executable.
- Run `TimberbornMapper.exe --help` to see instructions on how to use it.

## [BETA] Old map format upgrade
If you input (manually or by drag'n'drop) a `.json` file of a old format game map, script will try to detect it's a map and will suggest to upgrade it,
fixing attributes that crash current game version (should apply to maps created in 2021, when chestnuts and maple syrup were not yet added) and then packing it as
`.timber` file.

Feature is not yet extensively tested and still need work, but it should make maps loadable.

## Configuration files

**Note**: Script is using `tomllib` for config format, so it will work only on python **3.11+** (Windows binary uses 3.11).

If configuration is available script will try to write a template config into system-specific config dir.

If file already exists it will try to read it. Command-line arguments should override config values when set.


## Getting height maps

There are likely a number of services where you can get a height map of real or fictional location.

One I've used so far is https://heightmap.skydark.pl/
- It has map size slider limited to 17 km, but you can input it down to 9 km (lesser doesn't work for me for some reason).
- Select desired area and click "Download PNG height map".
- If picture lacks contrast play with "Height scale" input slider.

# TODO

1. ~~Make a Windows binary for players who don't care for python, pip or java alternately.~~
2. More interactivity.
3. More validation and better error handling.
4. Document some example method where and how you can get height map image of real-world location.
5. ~~Try to automatically save to /Documents/Timberborn/Maps/ on Windows.~~
6. Implement configurations (WIP).
7. Disable colors by env vars.
8. ~~Fix plant Yields.~~
9. ~~Add chestnut trees.~~
