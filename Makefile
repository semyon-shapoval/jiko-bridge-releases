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

.PHONY: help dev-env blend-test c4d

help:
	@echo "Detected System: $(SYSTEM)"
	@echo "Available targets:"
	@echo "  dev-env      - Create venv and install dependencies"
	@echo "  blend-test   - Run Blender integration tests"
	@echo "  c4d          - Open Cinema 4D with sample file"

dev-env:
	python -m venv venv
	$(PYTHON) -m pip install --upgrade pip
	$(PIP) install -r requirements.txt

blend-help:
	"$(BLENDER_PATH)" --help

blend-test:
	@echo "Running Blender tests..."
	set BLENDER_USER_SCRIPTS="$(ADDONS_PATH)" && \
	"$(BLENDER_PATH)" --addons JikoBridgeBlend --python "$(CURDIR)/tests/integration/blender/test_blend_flows.py"

c4d:
	@echo "Opening C4D..."
	"$(C4D_PATH)" "$(DESKTOP)/Untitled.c4d"