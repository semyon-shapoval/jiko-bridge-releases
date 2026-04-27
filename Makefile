# Определение ОС
SYSTEM := $(if $(filter Windows_NT,$(OS)),Windows,$(shell uname -s))

# Подключаем нужный конфиг в зависимости от системы
ifeq ($(SYSTEM),Windows)
    include MakeWin.mk
else ifeq ($(SYSTEM),Darwin)
    -include MakeMac.mk
else
    -include MakeLinux.mk
endif

.PHONY: help venv blend-test c4d-test

help:
	@echo "Detected System: $(SYSTEM)"
	@echo "Available targets:"
	@echo "  venv           - Create venv and install dependencies"
	@echo "  blend-test     - Run Blender integration tests"
	@echo "  c4d-test       - Run Cinema 4D integration tests via c4dpy"

venv:
	python -m venv venv
	$(PYTHON) -m pip install --upgrade pip
	$(PIP) install -r requirements.txt

c4d:
	-make c4d-lint
	make c4d-typecheck

c4d-lint:
	$(PYTHON) -m pylint --rcfile=pyproject.toml plugins/cinema4d

c4d-typecheck:
	$(PYTHON) -m mypy --config-file pyproject.toml plugins/cinema4d

c4d-test:
	@echo "Running C4D tests..."
	set "g_additionalModulePath=$(C4D_PLUGIN_PATH)" && \
	"$(C4D_PYTHON)" "$(CURDIR)/tests/integration/c4d/test_c4d_flows.py"

blend:
	-make blend-lint
	make blend-typecheck

blend-lint:
	$(PYTHON) -m pylint --rcfile=pyproject.toml plugins/blender/addons/JikoBridgeBlend

blend-typecheck:
	$(PYTHON) -m mypy --config-file pyproject.toml plugins/blender/addons/JikoBridgeBlend


blend-test:
	@echo "Running Blender tests..."
	set BLENDER_USER_SCRIPTS="$(ADDONS_PATH)" && \
	"$(BLENDER_PATH)" --addons JikoBridgeBlend --python "$(CURDIR)/tests/integration/blender/test_blend_flows.py"
