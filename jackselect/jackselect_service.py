"""D-BUS service interface for jack-select."""

import logging
import os

import dbus
import dbus.service


log = logging.getLogger(__name__)

DBUS_NAME = 'de.chrisarndt.JackSelectService'
DBUS_PATH = '/de/chrisarndt/JackSelectApp'
DBUS_INTERFACE = 'de.chrisarndt.JackSelectInterface'


class JackSelectService(dbus.service.Object):
    def __init__(self, app, bus=None):
        if bus is None:
            bus = dbus.SessionBus()

        # we need to keep a reference to the BusName
        # otherwise it gets garbage-collected and the service vanishes
        self.bus_name = dbus.service.BusName(DBUS_NAME, bus)
        super().__init__(bus, DBUS_PATH)
        self.app = app

    @dbus.service.method(dbus_interface=DBUS_INTERFACE, out_signature='i')
    def GetPid(self):
        log.debug("DBus client requested PID.")
        return os.getpid()

    @dbus.service.method(dbus_interface=DBUS_INTERFACE)
    def Exit(self):
        log.debug("DBus client requested application exit.")
        self.app.quit()

    @dbus.service.method(dbus_interface=DBUS_INTERFACE)
    def OpenMenu(self):
        log.debug("DBus client requested opening menu.")
        self.app.gui.on_popup_menu_open()

    @dbus.service.method(dbus_interface=DBUS_INTERFACE, in_signature='s')
    def ActivatePreset(self, preset):
        log.debug("DBus client requested activating preset '%s'." % preset)
        self.app.activate_preset(preset=preset)

    @dbus.service.method(dbus_interface=DBUS_INTERFACE)
    def ActivateDefaultPreset(self):
        log.debug("DBus client requested activating default preset.")
        self.app.activate_default_preset()

    @dbus.service.method(dbus_interface=DBUS_INTERFACE)
    def StopJackServer(self):
        log.debug("DBus client requested stopping JACK server.")
        self.app.stop_jack_server()
