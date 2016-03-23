#!/usr/bin/env python
"""A systray app to set the JACK configuration from QjackCtl presets via DBus.
"""

import logging
import os
import sys

os.environ['NO_AT_BRIDGE'] = "1"  # noqa
import gi
gi.require_version('Gtk', '3.0')  # noqa
from gi.repository import Gtk, GObject
from gi.repository.GdkPixbuf import Pixbuf


from pkg_resources import resource_filename
from xdg import BaseDirectory as xdgbase

from .jackcontrol import (JackCfgInterface, JackCtlInterface,
                          get_jack_controller)
from .qjackctlconf import get_qjackctl_presets


log = logging.getLogger('jack-select')


class Indicator:
    """This class defines a standard GTK3 system tray indicator.

    Class Indicator can be easily reused in any other project.

    """
    def __init__(self, icon):
        """Create indicator icon and add menu.

        Args:
          icon (str): path to initial icon that will be shown on system panel

        """
        self._icon_cache = {}
        self.icon = Gtk.StatusIcon.new_from_pixbuf(self._get_icon(icon))

        self.menu = Gtk.Menu()
        self.icon.connect('activate', self.on_popup_menu_open)
        self.icon.connect('popup-menu', self.on_popup_menu_open)

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

    def on_popup_menu_open(self, widget, button=None, *args):
        """Systray was clicked to open popup menu."""
        self.menu.popup(None, None, Gtk.StatusIcon.position_menu, widget,
                        button or 1, Gtk.get_current_event_time())


class JackSelectApp:
    """A simple systray application to select a JACK configuration preset."""

    def __init__(self):
        self.gui = Indicator('jack.png')
        self.gui.icon.set_has_tooltip(True)
        self.gui.icon.connect("query-tooltip", self.tooltip_query)
        self.jack_status = {}
        self.tooltext = "No status available."
        self.jackdbus = None
        dbus_obj = get_jack_controller()
        self.jackctl = JackCtlInterface(dbus_obj)
        self.jackcfg = JackCfgInterface(dbus_obj)
        self.presets = None
        self.load_presets()
        GObject.timeout_add(1000, self.load_presets)
        GObject.timeout_add(500, self.check_jack_status)

    def load_presets(self):
        qjackctl_conf = xdgbase.load_first_config('rncbc.org/QjackCtl.conf')

        if qjackctl_conf:
            mtime = os.path.getmtime(qjackctl_conf)
            if not self.presets or mtime > getattr(self, '_conf_mtime', 0):
                log.debug("Qjackctl configuration file mtime changed / "
                          "previously unknown.")
                log.debug("(Re-)Reading configuration.")
                (
                    self.presets,
                    self.settings,
                    self.default_preset
                ) = get_qjackctl_presets(qjackctl_conf)
                self._conf_mtime = mtime
                self.create_menu()
        elif self.presets or self.presets is None:
            self.log.warning("Qjackctl configuration file not found.")
            if self.presets: self.debug("Removing stored presets.")
            self.presets = []
            self.settings = {}
            self.default_preset = None
            self.create_menu()

        return True  # keep function scheduled

    def create_menu(self):
        log.debug("Building menu.")
        self.gui.menu = Gtk.Menu()

        if self.presets:
            for preset in sorted(self.presets):
                self.gui.add_menu_item(self.activate_preset, preset)
        else:
            item = self.gui.add_menu_item(None, "No presets found")
            item.set_sensitive(False)

        self.gui.add_separator()
        self.menu_stop = self.gui.add_menu_item(
            self.stop_jack_server, "Stop JACK Server", icon='stop.png')
        self.menu_stop.set_sensitive(bool(self.jack_status.get('is_started')))
        self.gui.add_separator()
        self.menu_quit = self.gui.add_menu_item(
            lambda x: Gtk.main_quit(), "Quit",
            icon='quit.png')
        self.gui.menu.show_all()

    def receive_status(self, value, name=None):
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
                self.tooltext = (
                    "%(samplerate)i Hz, %(period)i frames "
                    "(%(latency)0.1f ms), %(load)i%% load, %(xruns)i xruns" %
                    self.jack_status)
            except KeyError:
                self.tooltext = "No status available."

    def check_jack_status(self):
        if self.jackctl:
            self.jackctl.is_started(self.receive_status)
            # Get stats later, after we received running status
            GObject.timeout_add(250, self.get_stats)

        return True  # keep function scheduled

    def get_stats(self):
        if self.jack_status.get('is_started'):
            self.jackctl.get_sample_rate(self.receive_status)
            self.jackctl.get_period(self.receive_status)
            self.jackctl.get_load(self.receive_status)
            self.jackctl.get_xruns(self.receive_status)
            self.jackctl.get_latency(self.receive_status)

    def tooltip_query(self, widget, x, y, keyboard_mode, tooltip):
        """Set tooltip for the systray icon."""
        if self.jackctl:
            tooltip.set_text(self.tooltext)
        else:
            tooltip.set_text("No JACK-DBus connection")

        return True

    def activate_preset(self, m_item, **kwargs):
        preset = m_item.get_label()
        settings = self.settings.get(preset)

        if settings:
            self.jackcfg.activate_preset(settings)

            s = []
            for component, settings in settings.items():
                s.append("[%s]" % component)
                s.extend(["%s: %r" % (k, v)
                         for k, v in sorted(settings.items())])
                s.append('')

            log.info("Activated preset: %s", preset)
            log.debug("Settings: %s", "\n".join(s))

            self.stop_jack_server()
            GObject.timeout_add(1000, self.start_jack_server)

    def start_jack_server(self, *args, **kwargs):
        if self.jackctl and not self.jack_status.get('is_started'):
            self.jackctl.start_server()
            self.check_jack_status()

    def stop_jack_server(self, *args, **kwargs):
        if self.jackctl and self.jack_status.get('is_started'):
            self.jackctl.stop_server()
            self.check_jack_status()


def main():
    """Main function to be used when called as a script."""
    from dbus.mainloop.glib import DBusGMainLoop
    logging.basicConfig(
        level=logging.DEBUG if '-v' in sys.argv[1:] else logging.INFO,
        format="[%(name)s] %(levelname)s: %(message)s")
    DBusGMainLoop(set_as_default=True)
    JackSelectApp()
    return Gtk.main()


if __name__ == '__main__':
    sys.exit(main() or 0)
