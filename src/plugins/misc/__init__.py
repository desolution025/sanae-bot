from pathlib import Path
from nonebot import load_plugins


# store all subplugins
manager_plugins = set()
# load sub plugins
manager_plugins |= load_plugins(
    str((Path(__file__).parent).resolve()))