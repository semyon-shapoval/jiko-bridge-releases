# Пути к софту
BLENDER_PATH ?= C:\Program Files\Blender Foundation\Blender 5.0\blender.exe
C4D_PATH     ?= C:\Program Files\Maxon Cinema 4D 2023\Cinema 4D.exe

# Специфика окружения
VENV_BIN     := venv\Scripts
PYTHON       := $(VENV_BIN)\python.exe
PIP          := $(VENV_BIN)\pip.exe

# Системные пути
DESKTOP      := $(USERPROFILE)\Desktop

# Путь к папке с аддонами проекта
ADDONS_PATH  := $(CURDIR)/plugins/blender