import c4d
from c4d import plugins
import sys
import os
import importlib

JIKO_BRIDGE_ID = 1096086

def load_arnold_module():
    arnold_folder = os.path.join(c4d.storage.GeGetC4DPath(c4d.C4D_PATH_LIBRARY), "scripts")
    if os.path.exists(arnold_folder) and arnold_folder not in sys.path:
        sys.path.append(arnold_folder)

def load_plugin_modules():
    plugin_dir = os.path.abspath(os.path.dirname(__file__))
    if plugin_dir not in sys.path:
        sys.path.insert(0, plugin_dir)

load_arnold_module()
load_plugin_modules()

def reload_plugin_modules():
    plugin_dir = os.path.abspath(os.path.dirname(__file__))
    importlib.invalidate_caches()
    for name, mod in list(sys.modules.items()):
        f = getattr(mod, "__file__", None)
        if f and os.path.abspath(f).startswith(plugin_dir):
            try:
                importlib.reload(mod)
            except Exception as e:
                print("reload error:", name, e)

class JIKO_Bridge(plugins.CommandData):
    def Execute(self, doc):
        reload_plugin_modules()
        from jb_commands_popup import JB_CommandsPopup
        JB_CommandsPopup().show_popup_menu()
        return True


def main():
    if not plugins.FindPlugin(JIKO_BRIDGE_ID, c4d.PLUGINTYPE_COMMAND):
        plugins.RegisterCommandPlugin(
            id=JIKO_BRIDGE_ID,
            str="Jiko Bridge",
            info=0,
            help="Jiko Bridge help to improve your workflow",
            dat=JIKO_Bridge(),
            icon=None
        )

if __name__ == "__main__":
    main()