# jack-select

A systray application to quickly change the [JACK] configuration from QjackCtl
presets via DBus.

![version](http://badge.kloud51.com/pypi/v/jack-select.svg)
![status](http://badge.kloud51.com/pypi/s/jack-select.svg)
![license](http://badge.kloud51.com/pypi/l/jack-select.svg)
![python versions](http://badge.kloud51.com/pypi/py_versions/jack-select.svg)
![wheel](http://badge.kloud51.com/pypi/w/jack-select.svg)
![downloads](http://badge.kloud51.com/pypi/d/jack-select.svg)

Homepage
--------

**jack-select** is available from the source code repository on Github:

https://github.com/SpotlightKid/jack-select

There you can report issues and suggest new features or contribute via pull
requests. Releases can be downloaded from the Python Package Index ([PyPI]).
**jack-select** is also available as an Arch Linux package from the Arch User
Repository ([AUR]).

[PyPI]: https://pypi.org/project/jack-select
[AUR]: https://aur.archlinux.org/packages/jack-select/


Overview
--------

This application displays an icon in the system tray (also known as
notification area) of your desktop, which shows the status of the JACK audio
server and when you click on it, a menu pops up, which lets you quickly select
from the JACK configuration presets you created with [QjackCtl]. When you
select a preset, its JACK engine and driver configuration settings are loaded
via DBus into JACK and then the server is restarted. This allows you to switch
between different audio setups with just two mouse clicks.

![Screenshot of the pop menu](screenshot.png)

Menu entries for presets, which refer to ALSA devices currently not available
(e.g. those provided by USB interfaces, which are currently un-plugged), will
be deactivated. The application will detect changes in the sound device
configuration via udev and update the menu accordingly (this behaviour can
be disabled via a command line option).

When you hover with the mouse pointer over the systray icon and JACK is
running, a tooltip will show you the name of the active preset (if known), the
most important parameters of the current setup and some server statistics.

![Server status tooltip](tooltip.png)

Lastly, there are menu entries to stop the JACK server and to quit the
application.

To create or edit presets, just use the QjackCtl configuration dialog and make
sure you close it with "Ok" so the changes are saved. **jack-select** will pick
up the changes automatically.


DBus Interface
--------------

**jack-select** also has a DBus interface, which means you can use any generic
DBus client to tell **jack-select** to open its menu, activate a preset by name
or to terminate itself. You can also run the `jack-select` command while
another instance is already running, to access some of the DBus service
methods.

When **jack-select** starts up, it first checks whether there is already an
existing application providing the **jack-select** DBus service. If yes, when
called with no command argument arguments, it tells the running **jack-select**
instance to open its menu. If a preset name is given as the first command line
argument, it tells the running **jack-select** instance to activate this
preset. An invalid preset name is silently ignored.

For details about the DBus interface, please use DBus introspection facilities
to examine the `de.chrisarndt.JackSelectService` service on the session bus.


Installation
------------

To install **jack-select** on your system for everybody, check and install the
requirements below and then get **jack-select** by either downloading a release
archive from the Python Package Index ([PyPI]) and unpack it or clone the
source code repository from Github:

    $ git clone https://github.com/SpotlightKid/jack-select

Then change into the directory created by unpacking the release archive or
cloning the repository and run `make install`:

    $ cd jack-select
    $ [sudo] make PREFIX=/usr install

This will install the `jack-select` executable, the `jackselect` Python
package, the `jack-select.1` man page and the `jack-select.desktop` file and
the `jack-select.png` icon to provide a desktop start menu entry. It will also
install the required Python dependencies if they haven't been installed yet.

If you want to install **jack-select** only for the current user, replace the
last command above with:

    $ make install-user

This will not install the man page.

You can start **jack-select** from your desktop's XDG-compatible start menu or
add or link the `jack-select.desktop` file into your autostart folder (e.g.
`~/.config/autostart`) to have it started along your with your desktop.

**Note:**
If you do not have installed `PyGObject` and/or `dbus-python` via your
distribution's package system yet, running the install command given above will
try to install them via Python setuptools from the Python Package Index (PyPI).
This will most likely require a compiler and some development packages to be
installed, since not all indirect dependencies are available on PyPI as binary
wheels for Linux. If this fails, try installing the packages `build-essential`,
`python-dev` and `libcairo2-dev` (assuming your Linux distribution is a
debian/Ubuntu variant) and try again.

If `dbus-python` is installed via your distribution's package system, you may
get the following error when running **jack-select**:

    pkg_resources.DistributionNotFound: The 'dbus-python' distribution was not found and is required by jack-select

This means that `dbus-python` was not installed in a setuptools-compatible way.
Unfortunately this seems to be the case on most major Linux distributions.
As a workaround, you can install a working version of `dbus-python` from PyPI
only for your current user:

    pip install --user dbus-python


Requirements
------------

This application works with the DBus-version of JACK only. It is written in
Python 3 using the [PyGObject] bindings for GTK 3. Python 2 is not supported.

In addition to PyGObject, the following third-party Python libraries are
required:

* [pyxdg](http://freedesktop.org/Software/pyxdg)
* [dbus-python](https://www.freedesktop.org/wiki/Software/DBusBindings/)
* [pyudev](http://pyudev.readthedocs.org/)

These may be available from the package repository of your distribution as
`python-gobject`, `python-xdg`, `python-dbus` and `python-pyudev` respectively.
They come with their own dependencies, which are not listed here.

If you want to install **jack-select** from a Git repository clone, you'll also
need the Python [docutils](http://docutils.sourceforge.net) to build the man
page from the ReST source.


[JACK]: http://jackaudio.org/
[PyGObject]: https://wiki.gnome.org/Projects/PyGObject
[QjackCtl]: http://qjackctl.sourceforge.net/


License
-------

**jack-select** is licensed under the MIT License.

Please see the file `LICENSE` for more information.


Author
------

**jack-select** was written by Christopher Arndt 2016 - 2019.


Acknowledgements
----------------

**jack-select** incorporates the `pyudev_gobject` library written by Sebastian
Wiesner and released under the LGPL 2.1. See the header of the
`jackselect/pyudev_gobject.py` file for license details.
