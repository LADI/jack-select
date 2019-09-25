=============
 jack-select
=============

-----------------------------------------------------------------------------
show a systray icon with a pop-up menu to set JACK configuration from presets
-----------------------------------------------------------------------------

:Author: Christopher Arndt <chris@chrisarndt.de>
:Date: 2019-04-18
:Copyright: The MIT License (MIT)
:Version: 1.3.0
:Manual section: 1
:Manual group: audio


SYNOPSIS
========

jack-select [-h] [--version] [-a] [-d] [-i] [-v] [preset]


DESCRIPTION
===========

jack-select displays an icon in the system tray (also known as notification
area) of your desktop, which shows the status of the JACK audio server and when
clicked, presents a pop-up menu, where the user can select from a list of JACK
configuration presets created with **QjackCtl**.

When a preset is selected, the JACK configuration is changed according to the
settings of the preset via DBus and then the JACK server is restarted. This
allows the user to switch between different JACK audio setups with just two
mouse clicks.

When the mouse pointer hovers over the systray icon and JACK is running, a
tooltip will show the name of the active preset (if known), the most important
parameters of the current configuration and some JACK server statistics.

Lastly, there are menu entries to stop the JACK server and to quit the
application.


STARTUP
=======

jack-select may be started from the command-line, from the desktop start menu
or along with the user's desktop session, by putting the
``jack-select.desktop`` file into the user's autostart folder
(``<XDG_CONFIG_HOME>/autostart``).

When jack-select starts up, it first checks whether there is already a running
instance of jack-select. If so, when called with no command argument arguments,
it tells the existing jack-select instance to open its menu.

If a preset name is passed as the first positional command-line argument the
preset is activated immediately at application startup. If another instance of
jack-select is already running, jack-select will tell the existing instance to
activate the preset. An invalid preset name is silently ignored.


PRESETS
=======

jack-select reads JACK configuration presets from QjackCtl's configuration file
(see **FILES** section). jack-select does not create or change this file. It
parses the file on startup and then checks it at a regular interval. If the
file is created, changed or deleted, jack-select will update its menu
accordingly.

To create or edit presets, the program **QjackCtl** can be used. Make the
desired changes in its configuration dialog and close it with "Ok" so the
changes are saved. The changes will be reflected in the jack-select menu
immediately.

QjackCtl stores a nameless preset referred to with the label *(default)* in its
interface. Since there is no way to remove this preset from QjackCtl's
interface, jack-select can optionally ignore this preset, unless it is the only
preset found in the configuration (see **OPTIONS** section).


DEVICE DISCOVERY
================

jack-select is able to detect the presence of ALSA devices and when they are
attached or removed. Menu entries for presets, which refer to ALSA devices
currently unavailable, will be deactivated. ALSA device discovery can be
disabled via a command line option (see **OPTIONS** section).


OPTIONS
=======

usage: jack-select [-h] [--version] [-a] [-c PATH] [-d] [-i] [-v] [preset]

positional arguments:
  preset                Configuration preset to activate on startup.

optional arguments:
  -h, --help            show this help message and exit
  --version             Show program version and exit.
  -a, --no-alsa-monitor
                        Disable ALSA device monitoring and filtering.
  -c PATH, --config PATH
                        Path to configuration file (default:
                        <XDG_CONFIG_HOME>/rncbc.org/QjackCtl.conf)
  -d, --default         Activate default preset.
  -i, --ignore-default  Ignore the nameless '(default)' preset if any other
                        presets are stored in the configuration.
  -v, --verbose         Be verbose about what the script does.


FILES
=====

``<XDG_CONFIG_HOME>/rncbc.org/QjackCtl.conf``
    The default path to QjackCtl's configuration file. This file contains the
    JACK settings and configuration presets jack-select uses. The path can be
    changed via a command line option.


ENVIRONMENT
===========

``XDG_CONFIG_HOME``
    Specifies the root of the user's configuration directory tree, under which
    jack-select will look for QjackCtl's configuration file (see FILES
    section).


SEE ALSO
========

* Project homepage (https://github.com/SpotlightKid/jack-select)
* JACK (http://jackaudio.org/)
* QjackCtl (http://qjackctl.sourceforge.net/)
