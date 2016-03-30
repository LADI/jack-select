=============
 jack-select
=============

-----------------------------------------------------------------------------
show a systray icon with a pop-up menu to set JACK configuration from presets
-----------------------------------------------------------------------------

:Author: Christopher Arndt <chris@chrisarndt.de>
:Date: 2016-03-30
:Copyright: The MIT License (MIT)
:Version: 1.0
:Manual section: 1
:Manual group: audio


SYNOPSIS
========

jack-select [preset name]


DESCRIPTION
===========

jack-select displays an icon in the system tray (also known as notification
area) of your desktop, which shows the status of the JACK audio server and when
clicked, presents a pop-up menu, where the user can select from a list of JACK
configuration presets created with QjackCtl.

When a preset is selected, the JACK configuration is changed according to the
settings of the preset via DBus and then the JACK server is restarted. This
allows the user to switch between different JACK audio setups with just two
mouse clicks.

When the mouse pointer hovers over the systray icon and JACK is running, a
tooltip will show the name of the active preset (if known), the most important
parameters of the current configuration and some JACK server statistics.


STARTUP
=======

jack-select may be started from the command-line, from the desktop start menu
or along with the user's desktop session, by putting the
``jack-select.desktop`` file into the user's autostart folder
(``<XDG_CONFIG_HOME>/autostart``).

When jack-select starts up, it first checks whether there is already a running
instance of jack-select. If so, when called with no command argument arguments,
it tells the existing jack-select instance to open its menu.

If a preset name is passed as the first positional command-line argument and
another instance of jack-select is already running, jack-select will tell the
existing instance to activate the preset. An invalid preset name is silently
ignored.


OPTIONS
=======

-v      Set logging level to DEBUG


FILES
=====

``<XDG_CONFIG_HOME>/rncbc.org/QjackCtl.conf``
    This file contains QjackCtl's configuration settings and the JACK
    configuration presets jack-select uses.

    jack-select does not create or change this file. It parses the file on
    startup and then checks it at a regular interval. If the file is created,
    changed or deleted, jack-select will update its menu accordingly.


ENVIRONMENT
===========

``XDG_CONFIG_HOME``
    Specifies the root of the user's configuration directory tree, under which
    jack-select will look for QjackCtl's configuration file (see FILES
    section).


SEE ALSO
========

* JACK (http://jackaudio.org/)
* QjackCtl (http://qjackctl.sourceforge.net/)
