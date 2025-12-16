import importlib
import logging
import pkgutil
from pathlib import Path

from ._tool_descriptor import Tool


def _discover_tools() -> dict[str, Tool]:
    tools: dict[str, Tool] = {}

    for importer, modname, ispkg in pkgutil.iter_modules([str(Path(__file__).parent)]):
        if modname.startswith("_"):
            continue  # Skip private modules

        try:
            module = importlib.import_module(f'.{modname}', __name__)

            if hasattr(module, 'tool') and isinstance(module.tool, Tool):
                if module.tool.name in tools:
                    logging.warning(f"Duplicate tool name detected: '{module.tool.name}' - skipping.")
                tools[module.tool.name] = module.tool
        except Exception as e:
            logging.warning(f"Failed to import tool module '{modname}': {e}")

    return tools


tools: dict[str, Tool] = _discover_tools()
__all__ = ["tools"]
