"""
Jiko Bridge for Cinema 4D
Code by Semyon Shapoval, 2026
"""

import importlib
import os
import sys
import c4d

plugin_dir = os.path.abspath(os.path.dirname(__file__))
if plugin_dir not in sys.path:
    sys.path.insert(0, plugin_dir)

JIKO_BRIDGE_ID = 1096086


class JikoBridge(c4d.plugins.CommandData):
    """Main command plugin class for Jiko Bridge."""

    def GetScriptName(self):  # pylint: disable=invalid-name
        """Return a stable script name."""
        return "Jiko Bridge"

    def Execute(self, doc):  # pylint: disable=invalid-name
        """Show the Jiko Bridge commands popup menu."""
        mod = importlib.import_module("src.jb_commands")
        mod.JbCommandsPopup(doc).show_popup_menu()
        return True


def main():
    """Main entry point for the plugin."""
    mod = importlib.import_module("src.jb_utils")
    mod.reload_plugin_modules()

    if not c4d.plugins.FindPlugin(JIKO_BRIDGE_ID, c4d.PLUGINTYPE_COMMAND):
        try:
            c4d.plugins.RegisterCommandPlugin(
                id=JIKO_BRIDGE_ID,
                str="Jiko Bridge",
                info=0,
                help="Jiko Bridge help to improve your workflow",
                dat=JikoBridge(),
                icon=None,
            )
        except (TypeError, RuntimeError, ValueError) as e:
            print(f"Failed to register Jiko Bridge plugin: {e}")


if __name__ == "__main__":
    main()
