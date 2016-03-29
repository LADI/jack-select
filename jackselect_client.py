#!/usr/bin/env python
# -*- coding: utf-8 -*-

import dbus
import dbus.service


DBUS_NAME = 'de.chrisarndt.JackSelectService'
DBUS_PATH = '/de/chrisarndt/JackSelectApp'
DBUS_INTERFACE = 'de.chrisarndt.JackSelectInterface'

def get_dbus_client(bus=None):
    if bus is None:
        bus = dbus.SessionBus()

    obj = bus.get_object(DBUS_NAME, DBUS_PATH)
    return dbus.Interface(obj, DBUS_INTERFACE)

print("JACK-Select PID: %i" % get_dbus_client().GetPid())
