BLENDER_PATH = "C:\Program Files\Blender Foundation\Blender 5.0\blender.exe"

dev-win-env:
	python -m venv venv
	venv\Scripts\python -m pip install --upgrade pip
	venv\Scripts\pip install -r requirements.txt

open-win-test-blend:
	$(BLENDER_PATH) "$(USERPROFILE)\Desktop\Untitled.blend"