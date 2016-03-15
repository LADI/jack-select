from functools import partial

import dbus

from gi.repository import GLib
from dbus.mainloop.glib import DBusGMainLoop

from jackselect.jackcontrol import *

DBusGMainLoop(set_as_default=True)
jackctl = JackCtlInterface()
jackcfg = JackCfgInterface()

def recv_setting(value, *args, **kw):
    print(value, args, kw)

def get_setting_async(comp, name, handler):
    named_handler = partial(handler, name=name)
    jackcfg._if.GetParameterValue([comp, name],
        reply_handler=named_handler, error_handler=named_handler)

def get_stat_async(meth, name, handler):
    named_handler = partial(handler, name=name)
    getattr(jackctl._if, meth)(reply_handler=named_handler,
                           error_handler=named_handler)

loop = GLib.MainLoop()
get_setting_async("driver", "rate", recv_setting)
get_stat_async("IsStarted", 'is_started', recv_setting)

try:
    loop.run()
except KeyboardInterrupt:
    pass
