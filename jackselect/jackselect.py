#!/usr/bin/env python
"""A systray app to set the JACK configuration from QjackCtl presets via DBus.
"""

import argparse
import logging
import os
import sys

os.environ['NO_AT_BRIDGE'] = "1"  # noqa
import gi
gi.require_version('Gtk', '3.0')  # noqa
from gi.repository import Gtk, GObject
from gi.repository.GdkPixbuf import Pixbuf

import dbus
import dbus.service

from pkg_resources import resource_filename
from xdg import BaseDirectory as xdgbase

from .jackcontrol import (JackCfgInterface, JackCtlInterface,
                          get_jack_controller)
from .qjackctlconf import get_qjackctl_presets


log = logging.getLogger('jack-select')
DBUS_NAME = 'de.chrisarndt.JackSelectService'
DBUS_PATH = '/de/chrisarndt/JackSelectApp'
DBUS_INTERFACE = 'de.chrisarndt.JackSelectInterface'
INTERVAL_GET_STATS = 500
INTERVAL_CHECK_CONF = 1000
INTERVAL_RESTART = 1000


class Indicator:
    """This class defines a standard GTK3 system tray indicator.

    Class Indicator can be easily reused in any other project.

    """
    def __init__(self, icon, title=None):
        """Create indicator icon and add menu.

        Args:
          icon (str): path to initial icon that will be shown on system panel

        """
        self._icon_cache = {}
        self.icon = Gtk.StatusIcon.new_from_pixbuf(self._get_icon(icon))
        self.menu = Gtk.Menu()
        self.icon.connect('activate', self.on_popup_menu_open)
        self.icon.connect('popup-menu', self.on_popup_menu_open)

        if title:
            self.icon.set_title(title)

    def _get_icon(self, icon):
        """Return icon from package as GdkPixbuf.Pixbuf.

        Extracts the image from package to a file, stores it in the icon cache
        if it's not in there yet and returns it. Otherwise just returns the
        image stored in the cache.

        """
        if icon not in self._icon_cache:
            filename = resource_filename(__name__, "images/%s" % icon)
            self._icon_cache[icon] = Pixbuf.new_from_file(filename)

        return self._icon_cache[icon]

    def set_icon(self, icon):
        """Set new icon in system tray.

        Args:
          icon (str): path to file with new icon

        """
        self.icon.set_from_pixbuf(self._get_icon(icon))

    def add_menu_item(self, command=None, title=None, icon=None):
        """Add mouse right click menu item.

        Args:
          command (callable): function that will be called after left mouse
          click on title
          title (str): label that will be shown in menu

        """
        if icon:
            m_item = Gtk.ImageMenuItem(title)
            image = Gtk.Image.new_from_pixbuf(self._get_icon(icon))
            m_item.set_image(image)
        else:
            m_item = Gtk.MenuItem()
            m_item.set_label(title)

        if command:
            m_item.connect('activate', command)

        self.menu.append(m_item)
        return m_item

    def add_separator(self):
        """Add separator between labels in the popup menu."""
        m_item = Gtk.SeparatorMenuItem()
        self.menu.append(m_item)
        self.menu.show_all()

    def on_popup_menu_open(self, widget=None, button=None, *args):
        """Systray was clicked to open popup menu."""
        self.menu.popup(None, None, Gtk.StatusIcon.position_menu,
                        widget or self.icon, button or 1,
                        Gtk.get_current_event_time())


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
        self.app.activate_preset()

    @dbus.service.method(dbus_interface=DBUS_INTERFACE)
    def StopJackServer(self):
        log.debug("DBus client requested stopping JACK server.")
        self.app.stop_jack_server()


class JackSelectApp:
    """A simple systray application to select a JACK configuration preset."""

    def __init__(self, bus=None):
        if bus is None:
            bus = dbus.SessionBus()

        self.gui = Indicator('jack.png', "JACK-Select")
        self.gui.icon.set_has_tooltip(True)
        self.gui.icon.connect("query-tooltip", self.tooltip_query)
        self.jack_status = {}
        self.tooltext = "No status available."
        dbus_obj = get_jack_controller(bus)
        self.jackctl = JackCtlInterface(dbus_obj)
        self.jackcfg = JackCfgInterface(dbus_obj)
        self.presets = None
        self.active_preset = None
        self.load_presets()
        GObject.timeout_add(INTERVAL_CHECK_CONF, self.load_presets)
        GObject.timeout_add(INTERVAL_GET_STATS, self.get_jack_stats)
        self.jackctl.is_started(self.receive_jack_status)
        self.jackctl.add_signal_handler(self.handle_jackctl_signal)
        self.dbus_service = JackSelectService(self, bus)

    def load_presets(self):
        qjackctl_conf = xdgbase.load_first_config('rncbc.org/QjackCtl.conf')

        if qjackctl_conf:
            mtime = os.path.getmtime(qjackctl_conf)
            if mtime > getattr(self, '_conf_mtime', 0):
                log.debug("QjackCtl configuration file mtime changed or "
                          "previously unknown.")
                log.debug("(Re-)Reading configuration.")
                (
                    presets,
                    self.settings,
                    self.default_preset
                ) = get_qjackctl_presets(qjackctl_conf)
                self.presets = {name.replace('_', ' '): name for name in presets}
                self.create_menu()
            self._conf_mtime = mtime
        elif self.presets or self.presets is None:
            log.warning("QjackCtl configuration file not found.")

            if __debug__ and self.presets:
                log.debug("Removing stored presets.")

            self.presets = {}
            self.settings = {}
            self.default_preset = None
            self.create_menu()

        return True  # keep function scheduled

    def create_menu(self):
        log.debug("Building menu.")
        self.gui.menu = Gtk.Menu()

        if self.presets:
            for displayname in sorted(self.presets):
                self.gui.add_menu_item(self.activate_preset, displayname)
        else:
            item = self.gui.add_menu_item(None, "No presets found")
            item.set_sensitive(False)

        self.gui.add_separator()
        self.menu_stop = self.gui.add_menu_item(
            self.stop_jack_server, "Stop JACK Server", icon='stop.png')
        self.menu_stop.set_sensitive(bool(self.jack_status.get('is_started')))
        self.gui.add_separator()
        self.menu_quit = self.gui.add_menu_item(
            self.quit, "Quit",
            icon='quit.png')
        self.gui.menu.show_all()

    def receive_jack_status(self, value, name=None):
        if name == 'is_started':
            if value != self.jack_status.get('is_started'):
                if value:
                    self.gui.set_icon('started.png')
                    log.info("JACK server started.")
                    self.menu_stop.set_sensitive(True)
                else:
                    self.gui.set_icon('stopped.png')
                    log.info("JACK server stopped.")
                    self.tooltext = "JACK server stopped."
                    self.menu_stop.set_sensitive(False)

        self.jack_status[name] = value

        if self.jack_status.get('is_started'):
            try:
                if self.active_preset:
                    self.tooltext = "<b>[%s]</b>\n" % self.active_preset
                else:
                    self.tooltext = "<i><b>Unknown configuration</b></i>\n"

                self.tooltext += ("%(samplerate)i Hz / %(period)i frames "
                                  "(%(latency)0.1f ms)\n" % self.jack_status)
                self.tooltext += "RT: %s " % (
                    "yes" if self.jack_status.get('is_realtime') else "no")
                self.tooltext += ("load: %(load)i%% xruns: %(xruns)i" %
                                  self.jack_status)

            except KeyError:
                self.tooltext = "No status available."

    def handle_jackctl_signal(self, *args, signal=None, **kw):
        if signal == 'ServerStarted':
            self.receive_jack_status(True, name='is_started')
        elif signal == 'ServerStopped':
            self.receive_jack_status(False, name='is_started')

    def get_jack_stats(self):
        if self.jackctl and self.jack_status.get('is_started'):
            cb = self.receive_jack_status
            self.jackctl.is_realtime(cb)
            self.jackctl.get_sample_rate(cb)
            self.jackctl.get_period(cb)
            self.jackctl.get_load(cb)
            self.jackctl.get_xruns(cb)
            self.jackctl.get_latency(cb)

        return True  # keep function scheduled

    def tooltip_query(self, widget, x, y, keyboard_mode, tooltip):
        """Set tooltip for the systray icon."""
        if self.jackctl:
            tooltip.set_markup(self.tooltext)
        else:
            tooltip.set_text("No JACK-DBus connection")

        return True

    def activate_preset(self, m_item=None, **kwargs):
        if m_item:
            preset = self.presets.get(m_item.get_label())
        else:
            preset = kwargs.get('preset', self.default_preset)

        settings = self.settings.get(preset)

        if preset and settings:
            self.jackcfg.activate_preset(settings)
            log.info("Activated preset: %s", preset)

            if __debug__:
                s = []
                for component, settings in settings.items():
                    s.append("[%s]" % component)
                    s.extend(["%s: %r" % (k, v)
                             for k, v in sorted(settings.items())])
                    s.append('')

                log.debug("Settings: %s", "\n".join(s))

            self.stop_jack_server()
            GObject.timeout_add(INTERVAL_RESTART, self.start_jack_server)
            self.active_preset = preset
        else:
            log.error("Unknown preset '%s'. Ignoring it.", preset)

    def start_jack_server(self, *args, **kwargs):
        if self.jackctl and not self.jack_status.get('is_started'):
            self.jackctl.start_server()

    def stop_jack_server(self, *args, **kwargs):
        if self.jackctl and self.jack_status.get('is_started'):
            self.jackctl.stop_server()

    def quit(self, *args):
        log.debug("Exiting main loop.")
        Gtk.main_quit()


def get_dbus_client(bus=None):
    if bus is None:
        bus = dbus.SessionBus()

    obj = bus.get_object(DBUS_NAME, DBUS_PATH)
    return dbus.Interface(obj, DBUS_INTERFACE)


def main(args=None):
    """Main function to be used when called as a script."""
    from dbus.mainloop.glib import DBusGMainLoop

    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('-d', '--default', action="store_true",
                    help="Activate default preset.")
    ap.add_argument('-v', '--verbose', action="store_true",
                    help="Be verbose about what the script does.")
    ap.add_argument('preset', nargs='?',
                    help="JACK configuration preset to activate on startup.")

    args = ap.parse_args(args if args is not None else sys.argv[1:])

    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO,
                        format="[%(name)s] %(levelname)s: %(message)s")

    # the mainloop needs to be set before creating the session bus instance
    DBusGMainLoop(set_as_default=True)
    bus = dbus.SessionBus()

    try:
        client = get_dbus_client(bus)
        log.debug("JACK-Select DBus service detected.")

        if args.default:
            log.debug("Activating default preset.")
            client.ActivateDefaultPreset()
        elif args.preset:
            log.debug("Activating preset '%s'.", args.preset)
            client.ActivatePreset(args.preset)
        else:
            log.debug("Opening menu...")
            client.OpenMenu()
    except dbus.DBusException:
        JackSelectApp(bus)
        try:
            return Gtk.main()
        except KeyboardInterrupt:
            return "Interrupted."


if __name__ == '__main__':
    sys.exit(main() or 0)
