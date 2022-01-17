"""D-BUS service interface for jack-select."""

import logging
import os

import dbus
import dbus.service


log = logging.getLogger(__name__)

DBUS_NAME = "de.chrisarndt.JackSelectService"
DBUS_PATH = "/de/chrisarndt/JackSelectApp"
DBUS_INTERFACE = "de.chrisarndt.JackSelectInterface"


class JackSelectService(dbus.service.Object):
    def __init__(self, app, bus=None):
        if bus is None:
            bus = dbus.SessionBus()

        # we need to keep a reference to the BusName
        # otherwise it gets garbage-collected and the service vanishes
        self.bus_name = dbus.service.BusName(DBUS_NAME, bus)
        super().__init__(bus, DBUS_PATH)
        self.app = app

    @dbus.service.method(dbus_interface=DBUS_INTERFACE, out_signature="i")
    def GetPid(self):
        """Get the PID of the currently running JACK-Select process."""
        log.debug("DBus client requested PID.")
        return os.getpid()

    @dbus.service.method(dbus_interface=DBUS_INTERFACE)
    def Exit(self):
        """Exit JACK-Select."""
        log.debug("DBus client requested application exit.")
        self.app.quit()

    @dbus.service.method(dbus_interface=DBUS_INTERFACE)
    def OpenMenu(self):
        """Open the JACK-Select popup menu."""
        log.debug("DBus client requested opening menu.")
        self.app.open_menu()

    @dbus.service.method(dbus_interface=DBUS_INTERFACE, in_signature="s")
    def ActivatePreset(self, preset):
        """Activate the JACK configuration preset with the given name."""
        log.debug("DBus client requested activating preset '%s'." % preset)
        self.app.activate_preset(preset=preset)

    @dbus.service.method(dbus_interface=DBUS_INTERFACE)
    def ActivateDefaultPreset(self):
        """Activate the default JACK configuration preset."""
        log.debug("DBus client requested activating default preset.")
        self.app.activate_default_preset()

    @dbus.service.method(dbus_interface=DBUS_INTERFACE)
    def StopJackServer(self):
        """Stop the JACK server."""
        log.debug("DBus client requested stopping JACK server.")
        self.app.stop_jack_server()
