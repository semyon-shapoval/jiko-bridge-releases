BLENDER_PATH = "C:\Program Files\Blender Foundation\Blender 5.0\blender.exe"
C4D_PATH = "C:\Program Files\Maxon Cinema 4D 2023\Cinema 4D.exe"

dev-win-env:
	python -m venv venv
	venv\Scripts\python -m pip install --upgrade pip
	venv\Scripts\pip install -r requirements.txt

blend:
	$(BLENDER_PATH) "$(USERPROFILE)\Desktop\Untitled.blend"

c4d:
	$(C4D_PATH) g_console=true "$(USERPROFILE)\Desktop\Untitled.c4d"