#!/usr/bin/env python

import os
import sys

os.environ['NO_AT_BRIDGE'] = "1"  # noqa
import gi
gi.require_version('GLib', '2.0')  # noqa
from gi.repository import GLib

import dbus
import dbus.mainloop.glib

from jackselect.jackcontrol import JackCtlInterface

def catchall(*args, **kw):
    print("Caught signal (in catchall handler) %(interface)s.%(member)s:" % kw)
    arg = object
    for arg in args:
        print("         %s" % (arg,))
    if arg is object:
        print("No arguments")

if __name__ == '__main__':
    dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)

    jackctl = JackCtlInterface()
#~    jackctl._if.connect_to_signal(
#~        handler_function=catchall,
#~        signal_name=None,
#~        interface_keyword='interface',
#~        member_keyword='member')
    jackctl.add_signal_handler(catchall)

    loop = GLib.MainLoop()
    loop.run()
