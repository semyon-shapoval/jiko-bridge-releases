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

load_arnold_module()

def load_plugin_modules():
    plugin_dir = os.path.abspath(os.path.dirname(__file__))
    bridge_dir = os.path.abspath(os.path.join(plugin_dir, "..", "bridge"))

    for p in (plugin_dir, bridge_dir):
        if p not in sys.path:
            sys.path.insert(0, p)

    return [plugin_dir, bridge_dir]

python_modules = load_plugin_modules()

def reload_plugin_modules():
    importlib.invalidate_caches()
    for name, mod in list(sys.modules.items()):
        f = getattr(mod, "__file__", None)
        if not f:
            continue
        f = os.path.abspath(f)
        for p in python_modules:
            if str(f).startswith(p):
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