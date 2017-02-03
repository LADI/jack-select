PACKAGE = jackselect
PROJECT = jack-select
PREFIX ?= /usr/local
PYTHON ?= python3
INSTALL ?= install

GENERATED_FILES = README.rst $(PROJECT).1

.PHONY: all install install-user

all:
	@echo 'make install: install jack-select to $(PREFIX)'
	@echo 'make install-user: install jack-select as current user'

README.rst: README.md
	pandoc -f markdown -t rst $< > $@

$(PROJECT).1: $(PROJECT).1.rst
	rst2man $< > $@

flake8:
	flake8 $(PACKAGE)

install: $(PROJECT).1
	$(PYTHON) setup.py install --prefix=$(PREFIX)
	$(INSTALL) -Dm644 $(PROJECT).png $(PREFIX)/share/icons/hicolor/48x48/apps
	$(INSTALL) -Dm644 $(PROJECT).desktop $(PREFIX)/share/applications/
	$(INSTALL) -Dm644 $(PROJECT).1 $(PREFIX)/share/man/man1/$(PROJECT).1
	update-desktop-database -q
	gtk-update-icon-cache $(PREFIX)/share/icons/hicolor

install-user:
	$(PYTHON) setup.py install --user
	$(INSTALL) -Dm644 $(PROJECT).png $(HOME)/.local/share/icons/hicolor/48x48/apps
	$(INSTALL) -Dm644 $(PROJECT).desktop $(HOME)/.local/share/applications/

sdist: $(GENERATED_FILES)
	$(PYTHON) setup.py sdist --formats=bztar,zip

pypi-upload: $(GENERATED_FILES)
	$(PYTHON) setup.py sdist --formats=bztar,zip bdist_wheel upload
