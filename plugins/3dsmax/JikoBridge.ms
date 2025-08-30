fn showJikoBridgePopup = (
    rcmenu JikoBridgePopup
    (
        menuItem Import "Import"

        on Import picked do
        (
            python.executeFile (getFilenamePath (getThisScriptFilename()) + "JikoBridge3ds.py")
            python.execute "bridge.import_asset()"
        )
    )

    popupMenu JikoBridgePopup pos:mouse.screenpos
)

macroScript JikoBridgeShow
category:"JikoBridge"
tooltip:"show JikoBridge"
buttonText:"JikoBridge"
(
    showJikoBridgePopup()
)