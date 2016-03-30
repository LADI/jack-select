PREFIX ?= /usr/local
PYTHON ?= python
INSTALL ?= install

GENERATED_FILES = README.rst jack-select.1

.PHONY: install install-user

README.rst: README.md
	pandoc -f markdown -t rst $< > $@

jack-select.1: jack-select.1.rst
	rst2man $< > $@

install: $(GENERATED_FILES)
	$(PYTHON) setup.py install --prefix=$(PREFIX)
	$(INSTALL) -Dm644 jack-select.png $(PREFIX)/share/icons/hicolor/48x48/apps
	$(INSTALL) -Dm644 jack-select.desktop $(PREFIX)/share/applications/
	$(INSTALL) -Dm644 jack-select.1 $(PREFIX)/share/man/man1/jack-select.1
	update-desktop-database -q
	gtk-update-icon-cache $(PREFIX)/share/icons/hicolor

install-user:
	$(PYTHON) setup.py install --user
	$(INSTALL) -Dm644 jack-select.png $(HOME)/.local/share/icons/hicolor/48x48/apps
	$(INSTALL) -Dm644 jack-select.desktop $(HOME)/.local/share/applications/

sdist: $(GENERATED_FILES)
	$(PYTHON) setup.py sdist --formats=bztar,zip

pypi-upload: $(GENERATED_FILES)
	$(PYTHON) setup.py sdist --formats=bztar,zip bdist_wheel upload
