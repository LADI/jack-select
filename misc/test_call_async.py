from functools import partial

import dbus

from gi.repository import GLib
from dbus.mainloop.glib import DBusGMainLoop

from jackselect.jackcontrol import *

DBusGMainLoop(set_as_default=True)
jackctl = JackCtlInterface()

def recv_setting(value, *args, **kw):
    print(value, args, kw)


loop = GLib.MainLoop()
jackctl.is_started(recv_setting)

try:
    loop.run()
except KeyboardInterrupt:
    pass
