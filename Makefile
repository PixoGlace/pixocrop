PYTHON ?= python3
VENV := .venv
APP := pixoCrop
APP_ID := pixocrop
PYINSTALLER_CONFIG_DIR := $(CURDIR)/.pyinstaller-cache
BUILD_DIR := build
DIST_DIR := dist
RELEASE_DIR := release

UNAME_S := $(shell uname -s 2>/dev/null || echo Windows)
UNAME_M := $(shell uname -m 2>/dev/null || echo unknown)

ifeq ($(OS),Windows_NT)
	PLATFORM := windows
	ARCH := $(PROCESSOR_ARCHITECTURE)
	BIN := $(VENV)/Scripts
	PYTHON_BIN := $(BIN)/python.exe
	DIST_ARTIFACT := $(DIST_DIR)/$(APP)
	RELEASE_EXT := zip
	ADD_DATA_SEP := ;
	ICON_FILE := assets/pixoCrop.ico
	PYINSTALLER_MODE := --onedir
else ifeq ($(UNAME_S),Darwin)
	PLATFORM := macos
	ARCH := $(UNAME_M)
	BIN := $(VENV)/bin
	PYTHON_BIN := $(BIN)/python
	DIST_ARTIFACT := $(DIST_DIR)/$(APP).app
	RELEASE_EXT := zip
	ADD_DATA_SEP := :
	ICON_FILE := assets/pixoCrop.icns
	PYINSTALLER_MODE := --windowed
else
	PLATFORM := linux
	ARCH := $(UNAME_M)
	BIN := $(VENV)/bin
	PYTHON_BIN := $(BIN)/python
	DIST_ARTIFACT := $(DIST_DIR)/$(APP)
	RELEASE_EXT := tar.gz
	ADD_DATA_SEP := :
	ICON_FILE := assets/logo_white.png
	PYINSTALLER_MODE := --onefile --windowed
endif

RELEASE_NAME := $(APP)-$(PLATFORM)-$(ARCH)
RELEASE_STAGE := $(RELEASE_DIR)/$(RELEASE_NAME)
RELEASE_FILE := $(RELEASE_DIR)/$(RELEASE_NAME).$(RELEASE_EXT)
PYINSTALLER := $(PYTHON_BIN) -m PyInstaller
PYINSTALLER_ASSETS := --add-data "assets$(ADD_DATA_SEP)assets"
PYINSTALLER_ICON := --icon "$(ICON_FILE)"
PYINSTALLER_COMMON := --noconfirm --clean --name "$(APP)" --hidden-import fitz $(PYINSTALLER_ASSETS) $(PYINSTALLER_ICON)

.PHONY: venv install dev run test compile build package package-linux release release-current release-info release-macos release-linux release-windows release-all clean

venv:
	$(PYTHON) -m venv $(VENV)

install: venv
	$(PYTHON_BIN) -m pip install --upgrade pip
	$(PYTHON_BIN) -m pip install -e .

dev: venv
	$(PYTHON_BIN) -m pip install --upgrade pip
	$(PYTHON_BIN) -m pip install -e ".[dev,build]"

run:
	$(PYTHON_BIN) -m pixocrop.app

test:
	$(PYTHON_BIN) -m pytest

compile:
	$(PYTHON_BIN) -m compileall src tests

build:
	PYINSTALLER_CONFIG_DIR="$(PYINSTALLER_CONFIG_DIR)" $(PYINSTALLER) $(PYINSTALLER_COMMON) $(PYINSTALLER_MODE) src/pixocrop/app.py

package:
	mkdir -p "$(RELEASE_DIR)"
ifeq ($(PLATFORM),macos)
	ditto -c -k --sequesterRsrc --keepParent "$(DIST_ARTIFACT)" "$(RELEASE_FILE)"
else ifeq ($(PLATFORM),windows)
	$(PYTHON_BIN) -m zipfile -c "$(RELEASE_FILE)" "$(DIST_ARTIFACT)"
else
	$(MAKE) package-linux
endif
	@echo "Release creee: $(RELEASE_FILE)"

package-linux:
	rm -rf "$(RELEASE_STAGE)"
	mkdir -p "$(RELEASE_STAGE)/bin" "$(RELEASE_STAGE)/share/applications" "$(RELEASE_STAGE)/share/icons/hicolor/256x256/apps"
	cp "$(DIST_ARTIFACT)" "$(RELEASE_STAGE)/$(APP)"
	chmod +x "$(RELEASE_STAGE)/$(APP)"
	ln -sf "../$(APP)" "$(RELEASE_STAGE)/bin/$(APP)"
	cp "$(ICON_FILE)" "$(RELEASE_STAGE)/share/icons/hicolor/256x256/apps/$(APP_ID).png"
	printf '%s\n' \
		'[Desktop Entry]' \
		'Type=Application' \
		'Name=pixoCrop' \
		'Comment=Detecter, recadrer et imprimer des bordereaux PDF' \
		'Exec=pixoCrop' \
		'Icon=$(APP_ID)' \
		'Terminal=false' \
		'Categories=Utility;Graphics;Office;' \
		'MimeType=application/pdf;' \
		> "$(RELEASE_STAGE)/share/applications/$(APP_ID).desktop"
	printf '%s\n' \
		'pixoCrop Linux release' \
		'======================' \
		'' \
		'Double-cliquez sur ./$(APP) pour lancer l application.' \
		'Executable autonome: ./$(APP)' \
		'Lien compatible installation: bin/$(APP)' \
		'Installation locale optionnelle:' \
		'  install -Dm755 bin/$(APP) "$$HOME/.local/bin/$(APP)"' \
		'  install -Dm644 share/applications/$(APP_ID).desktop "$$HOME/.local/share/applications/$(APP_ID).desktop"' \
		'  install -Dm644 share/icons/hicolor/256x256/apps/$(APP_ID).png "$$HOME/.local/share/icons/hicolor/256x256/apps/$(APP_ID).png"' \
		'' \
		'Puis lancer avec: $(APP)' \
		> "$(RELEASE_STAGE)/README-linux.txt"
	tar -czf "$(RELEASE_FILE)" -C "$(RELEASE_DIR)" "$(RELEASE_NAME)"

release: clean dev compile test build package

release-current: release

release-info:
	@echo "Plateforme courante : $(PLATFORM)"
	@echo "Architecture        : $(ARCH)"
	@echo "Mode PyInstaller    : $(PYINSTALLER_MODE)"
	@echo "Artefact PyInstaller: $(DIST_ARTIFACT)"
	@echo "Archive release     : $(RELEASE_FILE)"

release-macos:
	@test "$(PLATFORM)" = "macos" || (echo "Cette target doit etre lancee sur macOS. Plateforme courante: $(PLATFORM)" && exit 1)
	$(MAKE) release

release-linux:
	@test "$(PLATFORM)" = "linux" || (echo "Cette target doit etre lancee sur Linux. Plateforme courante: $(PLATFORM)" && exit 1)
	$(MAKE) release

release-windows:
	@test "$(PLATFORM)" = "windows" || (echo "Cette target doit etre lancee sur Windows. Plateforme courante: $(PLATFORM)" && exit 1)
	$(MAKE) release

release-all:
	@echo "PyInstaller ne cross-compile pas macOS/Linux/Windows depuis une seule machine."
	@echo "Lancez 'make release-macos' sur macOS, 'make release-linux' sur Linux et 'make release-windows' sur Windows, ou utilisez une CI avec une matrice d'OS."
	@exit 2

clean:
	chmod -R u+w build dist release .pyinstaller-cache 2>/dev/null || true
	rm -rf build dist release *.spec .pytest_cache .pyinstaller-cache || (sleep 1 && rm -rf build dist release *.spec .pytest_cache .pyinstaller-cache)
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
