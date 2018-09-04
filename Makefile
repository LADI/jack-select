DESTDIR ?= /
INSTALL ?= install
PACKAGE = jackselect
PROJECT = jack-select
PREFIX ?= /usr/local
PYTHON ?= python3
TWINE ?= twine

GENERATED_FILES = README.rst $(PROJECT).1

.PHONY: all install install-user

all:
	@echo 'make install: install jack-select to $(PREFIX) (needs root)'
	@echo 'make install-user: install jack-select as current user to $(HOME)/.local'

README.rst: README.md
	pandoc -f markdown -t rst $< > $@

$(PROJECT).1: $(PROJECT).1.rst
	rst2man $< > $@

flake8:
	flake8 $(PACKAGE)

install: $(PROJECT).1
	$(PYTHON) setup.py install --root=$(DESTDIR) --prefix=$(PREFIX) --optimize=1
	$(INSTALL) -Dm644 $(PROJECT).png -t $(DESTDIR:/=)$(PREFIX)/share/icons/hicolor/48x48/apps
	$(INSTALL) -Dm644 $(PROJECT).desktop -t $(DESTDIR:/=)$(PREFIX)/share/applications
	$(INSTALL) -Dm644 $(PROJECT).1 -t $(DESTDIR:/=)$(PREFIX)/share/man/man1
	-update-desktop-database -q
	-gtk-update-icon-cache -q $(DESTDIR:/=)$(PREFIX)/share/icons/hicolor

install-user:
	$(PYTHON) setup.py install --user
	$(INSTALL) -Dm644 $(PROJECT).png -t $(HOME)/.local/share/icons/hicolor/48x48/apps
	$(INSTALL) -Dm644 $(PROJECT).desktop -t $(HOME)/.local/share/applications/

sdist: $(GENERATED_FILES)
	$(PYTHON) setup.py sdist --formats=gztar,zip

wheel: $(GENERATED_FILES)
	$(PYTHON) setup.py bdist_wheel

pypi-upload: sdist wheel
	$(TWINE) upload --skip-existing dist/*.gz dist/*.whl
