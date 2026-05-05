"""
Commands for JB Asset Importer/Exporter plugin in Cinema 4D.
Code by Semyon Shapoval, 2026
"""

import c4d
from src.jb_types import JbSource
from src.jb_asset_importer import JbAssetImporter
from src.jb_asset_exporter import JbAssetExporter
from src.jb_utils import reload_plugin_modules

IDC_POPUP_ACTION_IMPORT = 2001
IDC_POPUP_ACTION_EXPORT = 2002
IDC_POPUP_ACTION_RELOAD = 2003


class JbCommandsPopup:
    """icon reference:
    https://developers.maxon.net/docs/py/2024_3_0/modules/c4d.bitmaps/RESOURCEIMAGE.html
    """

    def __init__(self, source: JbSource):
        self.doc = source
        self.asset_import = JbAssetImporter(source)
        self.asset_export = JbAssetExporter(source)

    def export_asset(self):
        """Export asset to Jiko Bridge."""
        self.doc.StartUndo()
        try:
            msg = self.asset_export.export_message()
            if c4d.gui.QuestionDialog(msg):
                self.asset_export.export_asset()
        finally:
            self.doc.EndUndo()
            c4d.EventAdd()

    def import_asset(self):
        """Import asset from Jiko Bridge."""
        self.doc.StartUndo()
        try:
            msg = self.asset_import.import_message()
            if c4d.gui.QuestionDialog(msg):
                self.asset_import.import_assets()
        finally:
            self.doc.EndUndo()
            c4d.EventAdd()

    def reload_modules(self):
        """Reload plugin modules."""
        reload_plugin_modules()
        c4d.EventAdd()

    def show_popup_menu(self):
        """Show the popup menu."""
        bc = c4d.BaseContainer()
        bc.InsData(IDC_POPUP_ACTION_IMPORT, f"Import&i{c4d.ID_MODELING_FLATTEN_TOOL}&")
        bc.InsData(IDC_POPUP_ACTION_EXPORT, f"Export&i{c4d.RESOURCEIMAGE_EYEACTIVE}&")
        bc.InsData(IDC_POPUP_ACTION_RELOAD, f"Reload&i{c4d.ID_MODELING_ROTATE}&")

        res = c4d.gui.ShowPopupDialog(cd=None, bc=bc, x=c4d.MOUSEPOS, y=c4d.MOUSEPOS)

        if res == IDC_POPUP_ACTION_IMPORT:
            self.import_asset()
        elif res == IDC_POPUP_ACTION_EXPORT:
            self.export_asset()
        elif res == IDC_POPUP_ACTION_RELOAD:
            self.reload_modules()


class JbCommands:
    """Main command for headless execution."""

    def __init__(self, source: JbSource):
        self.asset_import = JbAssetImporter(source)
        self.asset_export = JbAssetExporter(source)

    def export_asset(self) -> None:
        """Export asset to Jiko Bridge."""
        return self.asset_export.export_asset()

    def import_asset(self) -> None:
        """Import asset from Jiko Bridge."""
        return self.asset_import.import_assets()
