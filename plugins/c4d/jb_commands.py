import c4d
import ctypes
import os
from ctypes import wintypes

from jb_asset_importer import JB_AssetImporter
from jb_asset_exporter import JB_AssetExporter

IDC_POPUP_ACTION_IMPORT = 2001
IDC_POPUP_ACTION_EXPORT = 2002
IDC_POPUP_ACTION_RELOAD = 2003


class JB_CommandsPopup:
    def __init__(self):
        self.asset_import = JB_AssetImporter()
        self.asset_export = JB_AssetExporter()

    def export_asset(self):
        self.asset_export.export_asset()
        c4d.EventAdd()

    def import_asset(self):
        self.asset_import.import_assets()
        c4d.EventAdd()

    def reload_modules(self):
        from jb_utils import reload_plugin_modules

        plugin_dir = os.path.abspath(os.path.dirname(__file__))
        reload_plugin_modules(plugin_dir)
        c4d.EventAdd()

    def show_popup_menu(self):
        bc = c4d.BaseContainer()
        bc.InsData(IDC_POPUP_ACTION_IMPORT, "Import Asset")
        bc.InsData(IDC_POPUP_ACTION_EXPORT, "Export Asset")
        bc.InsData(IDC_POPUP_ACTION_RELOAD, "Reload Modules")

        pt = wintypes.POINT()
        ctypes.windll.user32.GetCursorPos(ctypes.byref(pt))
        mouse_x, mouse_y = int(pt.x), int(pt.y)

        res = c4d.gui.ShowPopupDialog(cd=None, bc=bc, x=mouse_x, y=mouse_y)
        if res == IDC_POPUP_ACTION_IMPORT:
            self.import_asset()
        elif res == IDC_POPUP_ACTION_EXPORT:
            self.export_asset()
        elif res == IDC_POPUP_ACTION_RELOAD:
            self.reload_modules()


class JB_Commands:
    def __init__(self, doc: c4d.documents.BaseDocument):
        self.doc = doc
        self._commands = JB_CommandsPopup()

    def export_asset(self) -> None:
        self._commands.export_asset()

    def import_asset(self) -> None:
        self._commands.import_asset()
