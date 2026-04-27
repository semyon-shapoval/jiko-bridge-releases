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

blend-test:
	@echo "Running Blender tests..."
	set BLENDER_USER_SCRIPTS="$(ADDONS_PATH)" && \
	"$(BLENDER_PATH)" --addons JikoBridgeBlend --python "$(CURDIR)/tests/integration/blender/test_blend_flows.py"

c4d-test:
	@echo "Running C4D tests..."
	set "g_additionalModulePath=$(C4D_PLUGIN_PATH)" && \
	"$(C4D_PYTHON)" "$(CURDIR)/tests/integration/c4d/test_c4d_flows.py"

c4d-lint:
	$(PYTHON) -m mypy --config-file pyproject.toml plugins/cinema4d/src