from pathlib import Path
from nonebot import load_plugins


# store all subplugins
specific_plugins = set()
# load sub plugins
specific_plugins |= load_plugins(
    str((Path(__file__).parent / "973573381").resolve()))