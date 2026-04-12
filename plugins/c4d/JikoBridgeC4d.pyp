import os
import sys
import c4d
import importlib
from c4d import plugins

JIKO_BRIDGE_ID = 1096086

plugin_dir = os.path.abspath(os.path.dirname(__file__))


def load_arnold_module():
    arnold_folder = os.path.join(
        c4d.storage.GeGetC4DPath(c4d.C4D_PATH_LIBRARY), "scripts"
    )
    if os.path.exists(arnold_folder) and arnold_folder not in sys.path:
        sys.path.append(arnold_folder)


def load_plugin_modules():
    if plugin_dir not in sys.path:
        sys.path.insert(0, plugin_dir)

    modules = ["jb_commands", "jb_api"]
    for module_name in modules:
        if module_name in sys.modules:
            importlib.reload(sys.modules[module_name])
        else:
            importlib.import_module(module_name)


def reload_plugin_modules():
    importlib.invalidate_caches()
    
    plugin_modules = {
        name: mod for name, mod in list(sys.modules.items())
        if getattr(mod, "__file__", None) 
        and os.path.abspath(mod.__file__).startswith(plugin_dir)
    }
    
    for name in plugin_modules:
        del sys.modules[name]
    

load_arnold_module()
load_plugin_modules()

class JIKO_Bridge(plugins.CommandData):
    @staticmethod
    def run(doc):
        from jb_commands import JB_Commands

        return JB_Commands(doc)

    def Execute(self, doc):
        reload_plugin_modules()
        from jb_commands import JB_CommandsPopup

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
            icon=None,
        )


if __name__ == "__main__":
    main()
