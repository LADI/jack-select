#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os

from gi.repository import GLib

import dbus
import dbus.service
import dbus.mainloop.glib


DBUS_NAME = 'de.chrisarndt.JackSelectService'
DBUS_PATH = '/de/chrisarndt/JackSelectApp'
DBUS_INTERFACE = 'de.chrisarndt.JackSelectInterface'


class JackSelectService(dbus.service.Object):
    def __init__(self, app, bus=None):
        if bus is None:
            bus = dbus.SessionBus()

        self.bus_name = dbus.service.BusName(DBUS_NAME, bus)
        dbus.service.Object.__init__(self, bus, DBUS_PATH)
        self.app = app

    @dbus.service.method(dbus_interface=DBUS_INTERFACE, out_signature='i')
    def GetPid(self):
        return os.getpid()

    @dbus.service.method(dbus_interface=DBUS_INTERFACE,
                         in_signature='', out_signature='')
    def Exit(self):
        mainloop.quit()

    @dbus.service.method(dbus_interface=DBUS_INTERFACE,
                         in_signature='', out_signature='')
    def OpenMenu(self):
        print("Opening menu...")


if __name__ == '__main__':
    dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)

    bus = dbus.SessionBus()
    service = JackSelectService(None, bus)
    mainloop = GLib.MainLoop()
    print("Running JackSelectService service.")
    mainloop.run()
