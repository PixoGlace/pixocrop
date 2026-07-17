PYTHON ?= python3
VENV := .venv
APP := pixoCrop
APP_ID := pixocrop
APP_VERSION := $(shell PYTHONPATH="$(CURDIR)/src" $(PYTHON) -c "from pixocrop.config import VERSION; print(VERSION)")
PYINSTALLER_CONFIG_DIR := $(CURDIR)/.pyinstaller-cache
BUILD_DIR := build
DIST_DIR := dist
RELEASE_DIR := release
PACKAGING_BUILD_DIR := $(BUILD_DIR)/packaging
DMG_STAGE := $(BUILD_DIR)/dmg-stage
DMG_BACKGROUND := assets/dmg/pixocrop-dmg-background.png
DMG_VOLUME_NAME := PixoCrop
DMG_VOLUME_ICON = $(ICON_FILE)
WINDOWS_WIZARD_IMAGE := $(PACKAGING_BUILD_DIR)/windows-wizard.bmp
WINDOWS_SMALL_IMAGE := $(PACKAGING_BUILD_DIR)/windows-small.bmp
LINUX_BANNER := $(PACKAGING_BUILD_DIR)/linux-banner.png
DMG_FILE = $(RELEASE_DIR)/$(APP)-macos-$(ARCH).dmg
WINDOWS_INSTALLER := $(RELEASE_DIR)/$(APP)-windows-x64-setup.exe

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
	PYINSTALLER_PLATFORM_OPTIONS := --osx-bundle-identifier "io.github.pixoglace.pixocrop"
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

DEB_ARCH := $(ARCH)
ifeq ($(ARCH),x86_64)
	DEB_ARCH := amd64
else ifeq ($(ARCH),aarch64)
	DEB_ARCH := arm64
endif
DEB_FILE := $(RELEASE_DIR)/$(APP_ID)_$(APP_VERSION)_$(DEB_ARCH).deb

RELEASE_NAME := $(APP)-$(PLATFORM)-$(ARCH)
RELEASE_STAGE := $(RELEASE_DIR)/$(RELEASE_NAME)
RELEASE_FILE := $(RELEASE_DIR)/$(RELEASE_NAME).$(RELEASE_EXT)
PYINSTALLER := $(PYTHON_BIN) -m PyInstaller
PYINSTALLER_ASSETS := --add-data "assets$(ADD_DATA_SEP)assets"
PYINSTALLER_ICON := --icon "$(ICON_FILE)"
PYINSTALLER_COMMON := --noconfirm --clean --name "$(APP)" --hidden-import fitz $(PYINSTALLER_ASSETS) $(PYINSTALLER_ICON) $(PYINSTALLER_PLATFORM_OPTIONS)

.PHONY: venv install dev check-venv run run-info test compile build packaging-assets package package-macos package-windows package-linux package-linux-deb release release-current release-info release-macos release-linux release-windows release-all clean

venv:
	$(PYTHON) -m venv $(VENV)

install: venv
	$(PYTHON_BIN) -m pip install --upgrade pip
	$(PYTHON_BIN) -m pip install -e .

dev: venv
	$(PYTHON_BIN) -m pip install --upgrade pip
	$(PYTHON_BIN) -m pip install -e ".[dev,build]"

check-venv:
	@test -x "$(PYTHON_BIN)" || (echo "Environnement virtuel introuvable. Lancez d'abord: make dev" && exit 1)

run: check-venv
	PYTHONPATH="$(CURDIR)/src" $(PYTHON_BIN) -m pixocrop.app

run-info: check-venv
	PYTHONPATH="$(CURDIR)/src" $(PYTHON_BIN) -c "import pixocrop.app as app; print(app.__file__)"

test:
	$(PYTHON_BIN) -m pytest

compile:
	$(PYTHON_BIN) -m compileall src tests

build:
	PYINSTALLER_CONFIG_DIR="$(PYINSTALLER_CONFIG_DIR)" $(PYINSTALLER) $(PYINSTALLER_COMMON) $(PYINSTALLER_MODE) src/pixocrop/app.py
ifeq ($(PLATFORM),macos)
	plutil -replace CFBundleDisplayName -string "$(APP)" "$(DIST_ARTIFACT)/Contents/Info.plist"
	plutil -replace CFBundleShortVersionString -string "$(APP_VERSION)" "$(DIST_ARTIFACT)/Contents/Info.plist"
	plutil -replace CFBundleVersion -string "$(APP_VERSION)" "$(DIST_ARTIFACT)/Contents/Info.plist"
endif

packaging-assets:
	$(PYTHON_BIN) packaging/create_packaging_art.py

package:
	mkdir -p "$(RELEASE_DIR)"
ifeq ($(PLATFORM),macos)
	$(MAKE) package-macos
else ifeq ($(PLATFORM),windows)
	$(MAKE) package-windows
else
	$(MAKE) package-linux
endif
	@echo "Release creee: $(RELEASE_FILE)"

package-macos: packaging-assets
	@test -d "$(DIST_ARTIFACT)" || (echo "Application macOS manquante: $(DIST_ARTIFACT)" && exit 1)
	@test -s "$(ICON_FILE)" || (echo "Icone macOS manquante: $(ICON_FILE)" && exit 1)
	@test -s "$(DMG_VOLUME_ICON)" || (echo "Icone du volume DMG manquante: $(DMG_VOLUME_ICON)" && exit 1)
	@test -s "$(DMG_BACKGROUND)" || (echo "Arriere-plan DMG manquant: $(DMG_BACKGROUND)" && exit 1)
	@test -s "$(DIST_ARTIFACT)/Contents/Resources/$(APP).icns" || (echo "Icone absente du bundle: $(DIST_ARTIFACT)/Contents/Resources/$(APP).icns" && exit 1)
	rm -rf "$(DMG_STAGE)"
	mkdir -p "$(DMG_STAGE)" "$(RELEASE_DIR)"
	cp -R "$(DIST_ARTIFACT)" "$(DMG_STAGE)/$(APP).app"
	rm -f "$(RELEASE_FILE)"
	ditto -c -k --sequesterRsrc --keepParent "$(DIST_ARTIFACT)" "$(RELEASE_FILE)"
	rm -f "$(DMG_FILE)"
	@if command -v create-dmg >/dev/null 2>&1; then \
		create-dmg \
			--volname "$(DMG_VOLUME_NAME)" \
			--volicon "$(DMG_VOLUME_ICON)" \
			--background "$(DMG_BACKGROUND)" \
			--window-pos 200 120 \
			--window-size 660 420 \
			--text-size 13 \
			--icon-size 112 \
			--icon "$(APP).app" 128 255 \
			--hide-extension "$(APP).app" \
			--app-drop-link 515 255 \
			--hdiutil-quiet \
			--no-internet-enable \
			"$(DMG_FILE)" \
			"$(DMG_STAGE)"; \
	else \
		echo "create-dmg absent, creation d'un DMG standard."; \
		ln -sfn /Applications "$(DMG_STAGE)/Applications"; \
		hdiutil create -volname "$(DMG_VOLUME_NAME)" -srcfolder "$(DMG_STAGE)" -ov -format UDZO "$(DMG_FILE)"; \
	fi
	@echo "DMG cree: $(DMG_FILE)"

package-windows: packaging-assets
	$(PYTHON_BIN) -m zipfile -c "$(RELEASE_FILE)" "$(DIST_ARTIFACT)"
	PIXO_APP_NAME="$(APP)" PIXO_APP_VERSION="$(APP_VERSION)" PIXO_SOURCE_DIR="$(CURDIR)/$(DIST_ARTIFACT)" PIXO_OUTPUT_DIR="$(CURDIR)/$(RELEASE_DIR)" PIXO_ROOT_DIR="$(CURDIR)" PIXO_WIZARD_IMAGE="$(CURDIR)/$(WINDOWS_WIZARD_IMAGE)" PIXO_WIZARD_SMALL_IMAGE="$(CURDIR)/$(WINDOWS_SMALL_IMAGE)" iscc packaging/windows/pixoCrop.iss
	@echo "Installateur Windows cree: $(WINDOWS_INSTALLER)"

package-linux: packaging-assets
	rm -rf "$(RELEASE_STAGE)"
	mkdir -p "$(RELEASE_STAGE)/bin" "$(RELEASE_STAGE)/share/applications" "$(RELEASE_STAGE)/share/icons/hicolor/256x256/apps" "$(RELEASE_STAGE)/share/metainfo" "$(RELEASE_STAGE)/share/pixocrop"
	cp "$(DIST_ARTIFACT)" "$(RELEASE_STAGE)/$(APP)"
	chmod +x "$(RELEASE_STAGE)/$(APP)"
	ln -sf "../$(APP)" "$(RELEASE_STAGE)/bin/$(APP)"
	cp "$(ICON_FILE)" "$(RELEASE_STAGE)/share/icons/hicolor/256x256/apps/$(APP_ID).png"
	cp "packaging/linux/io.github.pixoglace.pixocrop.metainfo.xml" "$(RELEASE_STAGE)/share/metainfo/io.github.pixoglace.pixocrop.metainfo.xml"
	cp "$(LINUX_BANNER)" "$(RELEASE_STAGE)/share/pixocrop/banner.png"
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
	$(MAKE) package-linux-deb

package-linux-deb:
	rm -rf "$(RELEASE_DIR)/deb-root"
	mkdir -p "$(RELEASE_DIR)/deb-root/DEBIAN" "$(RELEASE_DIR)/deb-root/opt/$(APP)" "$(RELEASE_DIR)/deb-root/usr/bin" "$(RELEASE_DIR)/deb-root/usr/share/applications" "$(RELEASE_DIR)/deb-root/usr/share/icons/hicolor/256x256/apps" "$(RELEASE_DIR)/deb-root/usr/share/metainfo" "$(RELEASE_DIR)/deb-root/usr/share/pixocrop"
	cp "$(DIST_ARTIFACT)" "$(RELEASE_DIR)/deb-root/opt/$(APP)/$(APP)"
	chmod 755 "$(RELEASE_DIR)/deb-root/opt/$(APP)/$(APP)"
	ln -sf "/opt/$(APP)/$(APP)" "$(RELEASE_DIR)/deb-root/usr/bin/$(APP)"
	cp "$(ICON_FILE)" "$(RELEASE_DIR)/deb-root/usr/share/icons/hicolor/256x256/apps/$(APP_ID).png"
	cp "packaging/linux/io.github.pixoglace.pixocrop.metainfo.xml" "$(RELEASE_DIR)/deb-root/usr/share/metainfo/io.github.pixoglace.pixocrop.metainfo.xml"
	cp "$(LINUX_BANNER)" "$(RELEASE_DIR)/deb-root/usr/share/pixocrop/banner.png"
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
		> "$(RELEASE_DIR)/deb-root/usr/share/applications/$(APP_ID).desktop"
	printf '%s\n' \
		'Package: $(APP_ID)' \
		'Version: $(APP_VERSION)' \
		'Section: utils' \
		'Priority: optional' \
		'Architecture: $(DEB_ARCH)' \
		'Maintainer: PixoGlace' \
		'Description: Detecter, recadrer et imprimer des bordereaux PDF' \
		> "$(RELEASE_DIR)/deb-root/DEBIAN/control"
	dpkg-deb --build "$(RELEASE_DIR)/deb-root" "$(DEB_FILE)"
	@echo "Paquet DEB cree: $(DEB_FILE)"

release: clean dev compile test build package

release-current: release

release-info:
	@echo "Plateforme courante : $(PLATFORM)"
	@echo "Architecture        : $(ARCH)"
	@echo "Mode PyInstaller    : $(PYINSTALLER_MODE)"
	@echo "Artefact PyInstaller: $(DIST_ARTIFACT)"
	@echo "Archive release     : $(RELEASE_FILE)"
	@echo "Version application : $(APP_VERSION)"

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
