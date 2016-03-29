#!/usr/bin/env python

import os
import sys

os.environ['NO_AT_BRIDGE'] = "1"  # noqa
import gi
gi.require_version('GLib', '2.0')  # noqa
from gi.repository import GLib

import dbus
import dbus.mainloop.glib

def catchall(*args, **kw):
    print("Caught signal (in catchall handler) %(interface)s.%(member)s:" % kw)
    arg = object
    for arg in args:
        print("         %s" % (arg,))
    if arg is object:
        print("No arguments")

if __name__ == '__main__':
    dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)

    bus = dbus.SessionBus()
    bus.add_signal_receiver(
        catchall,
        signal_name=None,
        bus_name="org.jackaudio.service",
        dbus_interface="org.jackaudio.JackControl",
        interface_keyword='interface',
        member_keyword='member')

    loop = GLib.MainLoop()
    loop.run()
