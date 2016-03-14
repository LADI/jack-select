PREFIX ?= /usr/local
PYTHON ?= python
INSTALL ?= install

.PHONY: install

install:
	$(PYTHON) setup.py install --prefix=$(PREFIX)
	$(INSTALL) -Dm644 jack-select.png $(PREFIX)/share/icons/hicolor/48x48/apps
	$(INSTALL) -Dm644 jack-select.desktop $(PREFIX)/share/applications/
	update-desktop-database -q
	gtk-update-icon-cache $(PREFIX)/share/icons/hicolor

install-user:
	$(PYTHON) setup.py install --user
	$(INSTALL) -Dm644 jack-select.png $(HOME)/.local/share/icons/hicolor/48x48/apps
	$(INSTALL) -Dm644 jack-select.desktop $(HOME)/.local/share/applications/
