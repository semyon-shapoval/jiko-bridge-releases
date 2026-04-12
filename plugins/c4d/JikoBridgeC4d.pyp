import os
import sys
import c4d
import importlib
from c4d import plugins

JIKO_BRIDGE_ID = 1096086

plugin_dir = os.path.abspath(os.path.dirname(__file__))


def load_arnold_module():
    try:
        arnold_folder = os.path.join(
            c4d.storage.GeGetC4DPath(c4d.C4D_PATH_LIBRARY), "scripts"
        )
        if os.path.exists(arnold_folder) and arnold_folder not in sys.path:
            sys.path.append(arnold_folder)
    except Exception as e:
        print(f"Failed to load Arnold module: {e}")

def load_plugin_modules():
    if plugin_dir not in sys.path:
        sys.path.insert(0, plugin_dir)

    modules = ["jb_commands", "jb_api"]
    for module_name in modules:
        if module_name in sys.modules:
            importlib.reload(sys.modules[module_name])
        else:
            importlib.import_module(module_name)


class JIKO_Bridge(plugins.CommandData):
    @staticmethod
    def run(doc):
        from jb_commands import JB_Commands

        return JB_Commands(doc)

    def Execute(self, doc):
        from jb_commands import JB_CommandsPopup

        JB_CommandsPopup().show_popup_menu()
        return True


def main():
    load_arnold_module()
    load_plugin_modules()

    if not plugins.FindPlugin(JIKO_BRIDGE_ID, c4d.PLUGINTYPE_COMMAND):
        try:
            plugins.RegisterCommandPlugin(
                id=JIKO_BRIDGE_ID,
                str="Jiko Bridge",
                info=0,
                help="Jiko Bridge help to improve your workflow",
                dat=JIKO_Bridge(),
                icon=None,
            )
        except Exception as e:
            print(f"Failed to register Jiko Bridge plugin: {e}")

if __name__ == "__main__":
    main()
