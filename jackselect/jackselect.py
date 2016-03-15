#!/usr/bin/env python
"""A systray app to set the JACK configuration from QJackCtl presets via DBus.
"""

import io
import logging
import os
import sys

os.environ['NO_AT_BRIDGE'] = "1"
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GObject
from gi.repository.GdkPixbuf import Pixbuf


from pkg_resources import resource_filename
from xdg import BaseDirectory as xdgbase

from .jackcontrol import JackCfgInterface, get_jack_controller
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

    def set_refresh(self, timeout, callback, *callback_args):
        """A simple wrapper to simplify setting a timeout.

        Args:
          timeout (int): timeout in milliseconds, after which callback will
          be called
          callback (callable): usually, just a function that will be called
          each time after timeout
          *callback_args (any type): arguments that will be passed to callback
          function

        """
        GObject.timeout_add(timeout, callback, *callback_args)

    def _get_icon(self, icon):
        """Return icon from package as GdkPixbuf.Pixbuf.

        Extracts the image from package to a file, stores it in the icon cache
        if it's not in there yet and returns it. Otherwise just returns the
        image stored in the cache.

        """
        if icon not in self._icon_cache:
            filename = resource_filename("jackselect", "images/%s" % icon)
            self._icon_cache[icon] = Pixbuf.new_from_file(filename)

        return self._icon_cache[icon]

    def set_icon(self, icon):
        """Set new icon in system tray.

        Args:
          icon (str): path to file with new icon

        """
        self.icon.set_from_pixbuf(self._get_icon(icon))

    def add_menu_item(self, command, title=None, icon=None):
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
        self.presets = []
        self.settings = {}
        self.jack_is_started = None
        self.status = "No status available"
        self.create_menu()
        self.jackdbsu = None
        self.refresh_timeout = 500
        self.gui.set_refresh(self.refresh_timeout, self.check_jack_status)
        self.jackctl = get_jack_controller()
        self.jackcfg = JackCfgInterface(self.jackctl)

    def create_menu(self):
        qjackctl_conf = xdgbase.load_first_config('rncbc.org/QjackCtl.conf')

        if qjackctl_conf:
            self.presets, self.settings, _ = get_qjackctl_presets(qjackctl_conf)  # noqa
            for preset in self.presets:
                self.gui.add_menu_item(self.activate_preset, preset)

        self.gui.add_separator()
        self.menu_stop = self.gui.add_menu_item(
            self.stop_jack_server, "Stop JACK Server", icon='stop.png')
        self.gui.add_separator()
        self.menu_quit = self.gui.add_menu_item(
            lambda x: Gtk.main_quit(), "Quit",
            icon='quit.png')
        self.gui.menu.show_all()

    def check_jack_status(self):
        if self.jackctl:
            if self.jackctl.IsStarted():
                sr = self.jackctl.GetSampleRate()
                bufsize = self.jackctl.GetBufferSize()
                load = self.jackctl.GetLoad()
                xruns = self.jackctl.GetXruns()
                latency = self.jackctl.GetLatency()
                self.status = (
                    "%i Hz, %i frames (%0.1f ms), %i%% load, %i xruns" %
                    (sr, bufsize, latency, load, xruns))

                if not self.jack_is_started:
                    self.gui.set_icon('started.png')
                    log.info("JACK server started.")
                    self.jack_is_started = True
            elif self.jack_is_started in (True, None):
                self.gui.set_icon('stopped.png')
                log.info("JACK server stopped.")
                self.status = "JACK server stopped."
                self.jack_is_started = False

        self.menu_stop.set_sensitive(self.jack_is_started)
        return True

    def tooltip_query(self, widget, x, y, keyboard_mode, tooltip):
        """Set tooltip for the systray icon."""
        if self.jackctl:
            tooltip.set_text(self.status)
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

            log.debug("Activated preset: %s", preset)
            log.debug("Settings: %s", "\n".join(s))

            self.stop_jack_server()
            GObject.timeout_add(1000, self.start_jack_server)

    def start_jack_server(self, *args, **kwargs):
        if self.jackctl and not self.jackctl.IsStarted():
            try:
                self.jackctl.StartServer()
            except Exception as exc:
                log.error("Failed to start JACK: %s", exc)
                self.status = str(exc)
            self.check_jack_status()

    def stop_jack_server(self, *args, **kwargs):
        if self.jackctl and self.jackctl.IsStarted():
            try:
                self.jackctl.StopServer()
            except Exception as exc:
                log.error("Failed to stop JACK: %s", exc)
                self.status = str(exc)
            self.check_jack_status()


def main():
    """Main function to be used when called as a script."""
    logging.basicConfig(
        level=logging.DEBUG if '-v' in sys.argv[1:] else logging.INFO,
        format="[%(name)s] %(levelname)s: %(message)s")
    JackSelectApp()
    return Gtk.main()


if __name__ == '__main__':
    sys.exit(main() or 0)
