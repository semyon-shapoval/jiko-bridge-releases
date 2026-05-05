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

diff:
	code --diff "$(C4D_PLUGIN_PATH)/src/jb_protocols.py" "$(BLENDER_PLUGIN_PATH)/src/jb_protocols.py"

check-diff:
	@$(PYTHON) scripts/check_diff.py "$(C4D_PLUGIN_PATH)" "$(BLENDER_PLUGIN_PATH)"

c4d:
	make c4d-lint
	make c4d-typecheck
	make c4d-test

c4d-lint:
	$(PYTHON) -m pylint --rcfile=pyproject.toml plugins/cinema4d tests/integration

c4d-typecheck:
	$(PYTHON) -m mypy --config-file pyproject.toml plugins/cinema4d tests/integration

c4d-test:
	clear
	@echo "Running C4D tests..."
	set "JB_ENV=test" && \
	set "g_additionalModulePath=$(C4D_PLUGIN_PATH)" && \
	"$(C4D_PYTHON)" "$(CURDIR)/tests/integration/test_flows.py"

blend:
	make blend-lint
	make blend-typecheck
	make blend-test

blend-run:
	@echo "Running Blender..."
	set "BLENDER_USER_SCRIPTS=$(ROOT_ADDONS_PATH)" && \
	"$(BLENDER_PATH)" --addons $(ADDON_NAME)

blend-lint:
	$(PYTHON) -m pylint --rcfile=pyproject.toml plugins/blender/addons/$(ADDON_NAME) tests/integration

blend-typecheck:
	$(PYTHON) -m mypy --config-file pyproject.toml plugins/blender/addons/$(ADDON_NAME) tests/integration


blend-test:
	clear
	@echo "Running Blender tests..."
	set "JB_ENV=test" && \
	set "BLENDER_USER_SCRIPTS=$(ROOT_ADDONS_PATH)" && \
	"$(BLENDER_PATH)" --addons $(ADDON_NAME) --python "$(CURDIR)/tests/integration/test_flows.py"
