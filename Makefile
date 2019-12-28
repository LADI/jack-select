DESTDIR ?= /
INSTALL ?= install
PACKAGE = jackselect
PROJECT = jack-select
PACKAGE_US = jack_select
PREFIX ?= /usr/local
PYTHON ?= python3
TWINE ?= twine
PYVER = $(shell $(PYTHON) -c 'import sys;print("%s.%s" % sys.version_info[:2])')

GENERATED_FILES = README.rst $(PROJECT).1

.PHONY: all build flake8 install install-user uninstall

all:
	@echo 'make install: install jack-select to $(PREFIX) (needs root)'
	@echo 'make install-user: install jack-select as current user to $(HOME)/.local'

README.rst: README.md
	pandoc -f markdown -t rst $< > $@

$(PROJECT).1: $(PROJECT).1.rst
	rst2man $< > $@

flake8:
	flake8 $(PACKAGE)

build:
	$(PYTHON) setup.py build

install: $(PROJECT).1 build
	$(PYTHON) setup.py install --skip-build --root=$(DESTDIR) --prefix=$(PREFIX) --optimize=1
	$(INSTALL) -Dm644 $(PROJECT).png -t $(DESTDIR:/=)$(PREFIX)/share/icons/hicolor/48x48/apps
	$(INSTALL) -Dm644 $(PROJECT).desktop -t $(DESTDIR:/=)$(PREFIX)/share/applications
	$(INSTALL) -Dm644 $(PROJECT).1 -t $(DESTDIR:/=)$(PREFIX)/share/man/man1
	-update-desktop-database -q
	-gtk-update-icon-cache -q $(DESTDIR:/=)$(PREFIX)/share/icons/hicolor

install-user: build
	$(PYTHON) setup.py install --skip-build --optimize=1 --user
	$(INSTALL) -Dm644 $(PROJECT).png -t $(HOME)/.local/share/icons/hicolor/48x48/apps
	$(INSTALL) -Dm644 $(PROJECT).desktop -t $(HOME)/.local/share/applications/

uninstall:
	rm -rf $(DESTDIR:/=)$(PREFIX)/lib/python$(PYVER)/site-packages/$(PACKAGE)
	rm -rf $(DESTDIR:/=)$(PREFIX)/lib/python$(PYVER)/site-packages/$(PACKAGE_US)-*.egg-info
	rm -f $(DESTDIR:/=)$(PREFIX)/bin/$(PROJECT)
	rm -f $(DESTDIR:/=)$(PREFIX)/share/icons/hicolor/48x48/apps/$(PROJECT).png
	rm -f $(DESTDIR:/=)$(PREFIX)/share/applications/$(PROJECT).desktop
	rm -f $(DESTDIR:/=)$(PREFIX)/share/man/man1/$(PROJECT).1*
	-update-desktop-database -q
	-gtk-update-icon-cache -q $(DESTDIR:/=)$(PREFIX)/share/icons/hicolor

sdist: $(GENERATED_FILES)
	$(PYTHON) setup.py sdist --formats=gztar,zip

wheel: $(GENERATED_FILES)
	$(PYTHON) setup.py bdist_wheel

pypi-upload: sdist wheel
	$(TWINE) upload --skip-existing dist/*.tar.gz dist/*.whl
