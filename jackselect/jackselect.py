#!/usr/bin/env python
"""A systray app to set the JACK configuration from QjackCtl presets via DBus."""

import argparse
import logging
import os
import sys

os.environ['NO_AT_BRIDGE'] = "1"  # noqa
import gi
gi.require_version('Gtk', '3.0')  # noqa
from gi.repository import Gtk, GObject

import dbus
from xdg import BaseDirectory as xdgbase

from .a2jcontrol import A2JCtlInterface
from .alsainfo import AlsaInfo
from .devmonitor import AlsaDevMonitor
from .indicator import Indicator
from .jackcontrol import (JackCfgInterface, JackCtlInterface)
from .jackselect_service import DBUS_NAME, DBUS_INTERFACE, DBUS_PATH, JackSelectService
from .qjackctlconf import get_qjackctl_presets
from .version import __version__


log = logging.getLogger('jack-select')

INTERVAL_GET_STATS = 500
INTERVAL_CHECK_CONF = 1000
INTERVAL_RESTART = 1000
DEFAULT_CONFIG = 'rncbc.org/QjackCtl.conf'


class JackSelectApp:
    """A simple systray application to select a JACK configuration preset."""

    def __init__(self, bus=None, config=None, monitor_devices=True, ignore_default=False):
        self.bus = bus

        if self.bus is None:
            self.bus = dbus.SessionBus()

        self.monitor_devices = monitor_devices
        self.ignore_default = ignore_default
        self.gui = Indicator('jack.png', "JACK-Select")
        self.gui.set_tooltip(self.tooltip_query)
        self.jack_status = {}
        self.tooltext = "No status available."
        self.session_bus = dbus.SessionBus()
        self.jackctl = JackCtlInterface(bus=self.bus)
        self.jackcfg = JackCfgInterface(bus=self.bus)
        # a2jmidi D-BUS service controller is created on-demand
        self._a2jctl = None

        if monitor_devices:
            # get ALSA devices and their parameters
            self.handle_device_change(init=True)
        else:
            self.alsainfo = None

        # load QjackCtl presets
        self.config = config

        self.presets = None
        self.active_preset = None
        self.load_presets()

        # set up periodic functions to check presets & jack status
        GObject.timeout_add(INTERVAL_CHECK_CONF, self.load_presets)
        GObject.timeout_add(INTERVAL_GET_STATS, self.get_jack_stats)
        self.jackctl.is_started(self.receive_jack_status)
        self.jackctl.add_signal_handler(self.handle_jackctl_signal)

        # add & start DBUS service
        self.dbus_service = JackSelectService(self, bus)

        if monitor_devices:
            # set up udev device monitor
            self.alsadevmonitor = AlsaDevMonitor(self.handle_device_change)
            self.alsadevmonitor.start()

    @property
    def a2jctl(self):
        if self._a2jctl is None:
            try:
                self._a2jctl = A2JCtlInterface(bus=self.bus)
            except dbus.DBusException as exc:
                log.warning("Could not connect to a2jmidid D-BUS service.")
                log.debug("D-Bus exception: %s", exc)
            else:
                self._a2jctl.add_signal_handler(self.handle_a2jctl_signal)

        return self._a2jctl

    def load_presets(self, force=False):
        if self.config in (None, DEFAULT_CONFIG):
            qjackctl_conf = xdgbase.load_first_config(DEFAULT_CONFIG)
        else:
            qjackctl_conf = self.config if os.access(self.config, os.R_OK) else None

        if qjackctl_conf:
            mtime = os.path.getmtime(qjackctl_conf)
            changed = mtime > getattr(self, '_conf_mtime', 0)

            if changed:
                log.debug("Configuration file mtime changed or previously unknown.")

            if force or changed or self.presets is None:
                log.debug("(Re-)Reading configuration.")
                (
                    preset_names,
                    self.settings,
                    self.default_preset
                ) = get_qjackctl_presets(qjackctl_conf, self.ignore_default)
                self.presets = {name: name.replace('_', ' ')
                                for name in preset_names}
                self.create_menu()

            self._conf_mtime = mtime
        elif self.presets or self.presets is None:
            log.warning("Could not access configuration file.")

            if __debug__ and self.presets:
                log.debug("Removing stored presets from memory.")

            self.presets = {}
            self.settings = {}
            self.default_preset = None
            self.create_menu()

        return True  # keep function scheduled

    def check_alsa_settings(self, preset):
        engine = self.settings[preset]['engine']
        driver = self.settings[preset]['driver']
        if engine['driver'] != 'alsa':
            return True

        dev = driver.get('device')
        if dev and dev not in self.alsainfo.devices:
            log.debug("Device '%s' used by preset '%s' not found.",
                      dev, preset)
            return False

        dev = driver.get('playback')
        if dev and dev not in self.alsainfo.playback_devices:
            log.debug("Playback device '%s' used by preset '%s' not found.",
                      dev, preset)
            return False

        dev = driver.get('capture')
        if dev and dev not in self.alsainfo.capture_devices:
            log.debug("Capture device '%s' used by preset '%s' not found.",
                      dev, preset)
            return False

        return True

    def create_menu(self):
        log.debug("Building menu.")
        self.gui.clear_menu()

        if self.presets:
            if not self.alsainfo:
                log.debug("ALSA device info not available. Filtering disabled.")

            callback = self.activate_preset
            for name, label in sorted(self.presets.items()):
                disabled = self.alsainfo and not self.check_alsa_settings(name)
                self.gui.add_menu_item(callback, label, active=not disabled, data=name)

        else:
            self.gui.add_menu_item(None, "No presets found", active=False)

        self.gui.add_separator()
        self.menu_stop = self.gui.add_menu_item(self.stop_jack_server,
                                                "Stop JACK Server",
                                                icon='stop.png',
                                                active=bool(self.jack_status.get('is_started')))

        if self.a2jctl:
            self.gui.add_separator()
            self.menu_a2jbridge = self.gui.add_submenu('ALSA-MIDI Bridge')
            self.menu_a2j_startstop = self.gui.add_menu_item(self.on_start_stop_a2jbridge,
                                                             "ALSA-MIDI Bridge",
                                                             icon='midi.png',
                                                             menu=self.menu_a2jbridge)
            self.menu_a2j_hw_export = self.gui.add_menu_item(self.on_a2jbridge_set_hw_export,
                                                             "Export HW Ports",
                                                             is_check=True,
                                                             menu=self.menu_a2jbridge)
        else:
            self.menu_a2jbridge = None

        self.gui.add_separator()
        self.menu_quit = self.gui.add_menu_item(self.quit, "Quit", icon='quit.png')
        self.gui.menu.show_all()

    def open_menu(self):
        self.gui.on_popup_menu_open()

    def receive_jack_status(self, value, name=None):
        jack_started = self.jack_status.get('is_started')
        self.jack_status[name] = value

        if name == 'is_started' and value != jack_started:
            if value:
                self.gui.set_icon('started.png')
                log.info("JACK server has started.")
            else:
                self.gui.set_icon('stopped.png')
                self.tooltext = "JACK server is stopped."
                log.info(self.tooltext)

            self.menu_stop.set_sensitive(value)
            self.update_a2jbridge_status()

        if self.jack_status.get('is_started'):
            try:
                if self.active_preset:
                    label = self.presets.get(self.active_preset,
                                             self.active_preset)
                    self.tooltext = "<b>[%s]</b>\n" % label
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

    def update_a2jbridge_status(self, status=None):
        if self.menu_a2jbridge:
            if not self.a2jctl:
                # No a2jmidid service D-BUS interface
                self.menu_a2j_startstop.set_sensitive(False)
                self.menu_a2j_hw_export.set_sensitive(False)
                self.menu_a2j_startstop.set_label("ALSA-MIDI Bridge not available")
            elif self.jack_status.get('is_started'):
                # JACK server started
                if status is None:
                    status = self.a2jctl.is_started()

                if status:
                    # bridge started
                    self.menu_a2j_startstop.set_label("Stop ALSA-MIDI Bridge")
                    self.menu_a2j_hw_export.set_sensitive(False)
                else:
                    # bridge stopped
                    self.menu_a2j_startstop.set_label("Start ALSA-MIDI Bridge")
                    self.menu_a2j_hw_export.set_sensitive(True)

                self.menu_a2j_startstop.set_sensitive(True)
            else:
                # JACK server stopped
                self.menu_a2j_startstop.set_label("ALSA-MIDI Bridge suspended")
                self.menu_a2j_startstop.set_sensitive(False)
                self.menu_a2j_hw_export.set_sensitive(True)

            self.menu_a2j_hw_export.set_active(self.a2jctl.get_hw_export())

    def handle_device_change(self, observer=None, device=None, init=False):
        if device:
            dev = device.device_path.split('/')[-1]

        if init or (device.action in ('change', 'remove')
                    and dev.startswith('card')):
            try:
                log.debug("Sound device change signalled. Collecting ALSA "
                          "device info...")
                self.alsainfo = AlsaInfo(deferred=False)
            except Exception as exc:
                log.warn("Could not get ALSA device list: %s", exc)
                self.alsainfo = None

            if device and device.action != 'init':
                self.load_presets(force=True)

    def handle_jackctl_signal(self, *args, signal=None, **kw):
        if signal == 'ServerStarted':
            self.receive_jack_status(True, name='is_started')
        elif signal == 'ServerStopped':
            self.receive_jack_status(False, name='is_started')

    def handle_a2jctl_signal(self, *args, signal=None, **kw):
        if signal == 'bridge_started':
            log.debug("a2jmidid bridge STARTED signal received.")
            self.update_a2jbridge_status(True)
        elif signal == 'bridge_stopped':
            log.debug("a2jmidid bridge STOPPED signal received.")
            self.update_a2jbridge_status(False)

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

    def activate_default_preset(self):
        if self.default_preset:
            log.debug("Activating default preset '%s'.", self.default_preset)
            self.activate_preset(preset=self.default_preset)
        else:
            log.warn("No default preset set.")

    def activate_preset(self, m_item=None, **kwargs):
        if m_item:
            preset = m_item.data
        else:
            preset = kwargs.get('preset')

        if not preset:
            log.warn("Preset must not be null.")
            return

        settings = self.settings.get(preset)

        if settings:
            self.jackcfg.activate_preset(settings)
            log.info("Activated preset: %s", preset)
            self.stop_jack_server()
            GObject.timeout_add(INTERVAL_RESTART, self.start_jack_server)
            self.active_preset = preset
        else:
            log.error("Unknown preset '%s'. Ignoring it.", preset)

    def start_jack_server(self, *args, **kwargs):
        if self.jackctl and not self.jack_status.get('is_started'):
            log.debug("Starting JACK server...")
            try:
                self.jackctl.start_server()
            except Exception as exc:
                log.error("Could not start JACK server: %s", exc)

    def stop_jack_server(self, *args, **kwargs):
        if self.jackctl and self.jack_status.get('is_started'):
            self.active_preset = None
            log.debug("Stopping JACK server...")

            try:
                self.jackctl.stop_server()
            except Exception as exc:
                log.error("Could not stop JACK server: %s", exc)

    def on_start_stop_a2jbridge(self, *args):
        self.start_stop_a2jbridge()

    def start_stop_a2jbridge(self, start_stop=None):
        if not self.a2jctl:
            return

        if start_stop is None:
            start_stop = not self.a2jctl.is_started()

        if start_stop:
            log.debug("Starting ALSA MIDI to JACK bridge...")
            self.a2jctl.start()
        else:
            log.debug("Stopping ALSA MIDI to JACK bridge...")
            self.a2jctl.stop()

    def on_a2jbridge_set_hw_export(self, widget, *args):
        if not self.a2jctl:
            return

        active = widget.get_active()

        if active != self.a2jctl.get_hw_export() and not self.a2jctl.is_started():
            log.debug("Exporting HW ports via aj2midid %sabled.", "en" if active else "dis")
            self.a2jctl.set_hw_export(active)

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
    ap.add_argument(
        '--version',
        action="version",
        version="%%(prog)s %s" % __version__,
        help="Show program version and exit.")
    ap.add_argument(
        '-a', '--no-alsa-monitor',
        action="store_true",
        help="Disable ALSA device monitoring and filtering.")
    ap.add_argument(
        '-c', '--config',
        metavar='PATH',
        help="Path to configuration file (default: <XDG_CONFIG_HOME>/%s)" % DEFAULT_CONFIG)
    ap.add_argument(
        '-d', '--default',
        action="store_true",
        help="Activate default preset.")
    ap.add_argument(
        '-i', '--ignore-default',
        action="store_true",
        help="Ignore the nameless '(default)' preset if any other presets are stored in the "
             "configuration.")
    ap.add_argument(
        '-v', '--verbose',
        action="store_true",
        help="Be verbose about what the script does.")
    ap.add_argument(
        'preset',
        nargs='?',
        help="Configuration preset to activate on startup.")

    args = ap.parse_args(args if args is not None else sys.argv[1:])

    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO,
                        format="[%(name)s] %(levelname)s: %(message)s")

    # the mainloop needs to be set before creating the session bus instance
    DBusGMainLoop(set_as_default=True)
    bus = dbus.SessionBus()
    start_gui = False

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
    except dbus.DBusException as exc:
        if exc.get_dbus_name().endswith('ServiceUnknown'):
            start_gui = True
        else:
            log.warning("Exception: %s", exc)

    if start_gui:
        app = JackSelectApp(bus,
                            config=args.config,
                            monitor_devices=not args.no_alsa_monitor,
                            ignore_default=args.ignore_default)

        if args.default:
            # load default preset when mainloop starts
            GObject.timeout_add(0, app.activate_default_preset)
        elif args.preset:
            # load given preset when mainloop starts
            GObject.timeout_add(0, lambda: app.activate_preset(preset=args.preset))

        try:
            return Gtk.main()
        except KeyboardInterrupt:
            return "Interrupted."


if __name__ == '__main__':
    sys.exit(main() or 0)
