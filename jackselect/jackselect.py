#!/usr/bin/env python
"""A systray app to set the JACK configuration from QjackCtl presets via DBus."""

import argparse
import configparser
import logging
import os
import sys

os.environ["NO_AT_BRIDGE"] = "1"  # noqa
import gi

gi.require_version("Gtk", "3.0")  # noqa
from gi.repository import Gtk, GObject

import dbus
from xdg import BaseDirectory as xdgbase

from .a2jcontrol import A2JCtlInterface
from .alsainfo import AlsaInfo
from .devmonitor import AlsaDevMonitor
from .indicator import Indicator
from .jackcontrol import JackCfgInterface, JackCtlInterface
from .jackselect_service import DBUS_NAME, DBUS_INTERFACE, DBUS_PATH, JackSelectService
from .qjackctlconf import get_qjackctl_presets
from .version import __version__


log = logging.getLogger("jack-select")

INTERVAL_GET_STATS = 500
INTERVAL_CHECK_CONF = 1000
INTERVAL_RESTART = 1000
DEFAULT_CONFIG = ("rncbc.org", "QjackCtl.conf")
SETTINGS = ("jack-select", "settings.ini")


class JackSelectApp:
    """A simple systray application to select a JACK configuration preset."""

    def __init__(
        self,
        bus=None,
        config=None,
        alsa_monitor=None,
        a2j_autostart=None,
        a2j_export_hw=None,
        ignore_default=None,
    ):
        self.bus = bus or dbus.SessionBus()

        # load jack-select application settings
        self.load_settings()

        if alsa_monitor is None:
            self.alsa_monitor = self.app_settings.getboolean("general", "alsa_monitor")
        else:
            self.alsa_monitor = alsa_monitor

        if ignore_default is None:
            self.ignore_default = self.app_settings.getboolean("general", "ignore_default")
        else:
            self.ignore_default = ignore_default

        self.gui = Indicator("jack.png", "JACK-Select")
        self.gui.set_tooltip(self.tooltip_query)
        self.jack_status = {}
        self.tooltext = "No status available."

        # a2jmidi D-BUS service controller is created on-demand
        self._a2jctl = None
        self._a2j_autostart = a2j_autostart
        self._a2j_export_hw = a2j_export_hw

        if self.alsa_monitor:
            # get ALSA devices and their parameters
            self.handle_device_change(init=True)
        else:
            self.alsainfo = None

        # load QjackCtl presets
        self.qjackctl_config = config

        self.presets = None
        self.active_preset = None
        self.load_presets()

        # Create Jack control and config D-BUS interfaces
        self.dbus_connect()

        # set up periodic functions to check presets & jack status
        GObject.timeout_add(INTERVAL_CHECK_CONF, self.load_presets)
        GObject.timeout_add(INTERVAL_GET_STATS, self.get_jack_stats)
        self.jackctl.is_started(self.update_jack_status)

        # add & start DBUS service
        self.dbus_service = JackSelectService(self, bus)

        if self.alsa_monitor:
            # set up udev device monitor
            self.alsadevmonitor = AlsaDevMonitor(self.handle_device_change)
            self.alsadevmonitor.start()

    def dbus_connect(self):
        """Create Jack control and config D-BUS interfaces."""
        try:
            log.debug("Connecting to JACK D-BUS interface...")
            self.jackctl = JackCtlInterface(bus=self.bus)
            self.jackcfg = JackCfgInterface(bus=self.bus)
        except dbus.exceptions.DBusException as exc:
            log.warning("Could not connect to JACK D-BUS interface: %s", exc)
            return True
        else:
            log.debug("JACK D-BUS connection established.")
            self.jackctl.add_signal_handler(self.handle_jackctl_signal)

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

    @property
    def a2j_autostart(self):
        return (
            self.app_settings.getboolean("a2jmidi", "autostart")
            if self._a2j_autostart is None
            else self._a2j_autostart
        )

    @a2j_autostart.setter
    def a2j_autostart(self, flag):
        if flag != self.app_settings.getboolean("a2jmidi", "autostart"):
            self.app_settings.set("a2jmidi", "autostart", "yes" if flag else "no")
            self.write_settings()

    @property
    def a2j_export_hw(self):
        return (
            self.app_settings.getboolean("a2jmidi", "export_hw")
            if self._a2j_export_hw is None
            else self._a2j_export_hw
        )

    @a2j_export_hw.setter
    def a2j_export_hw(self, flag):
        if flag != self.app_settings.getboolean("a2jmidi", "export_hw"):
            self.app_settings.set("a2jmidi", "export_hw", "yes" if flag else "no")
            self.write_settings()

    def load_settings(self):
        self.app_settings = configparser.ConfigParser()
        self.app_settings.read_dict(
            {
                "general": {
                    "alsa_monitor": "yes",
                    "ignore_default": "no",
                },
                "a2jmidi": {
                    "autostart": "no",
                    "export_hw": "yes",
                },
            }
        )

        settings_file = xdgbase.load_first_config(*SETTINGS)

        if settings_file:
            log.debug("Loading settings from '%s'.", settings_file)
            self.app_settings.read(settings_file)

    def write_settings(self):
        try:
            settings_file = os.path.join(xdgbase.save_config_path(SETTINGS[0]), SETTINGS[1])
            log.debug("Writing settings to '%s'.", settings_file)
            with open(settings_file, "w") as fp:
                self.app_settings.write(fp)
        except OSError as exc:
            log.error("Could not write settings file '%s': %s", settings_file, exc)

    def load_presets(self, force=False):
        if self.qjackctl_config in (None, DEFAULT_CONFIG):
            qjackctl_config = xdgbase.load_first_config(*DEFAULT_CONFIG)
        else:
            if os.access(self.qjackctl_config, os.R_OK):
                qjackctl_config = self.qjackctl_config
            else:
                qjackctl_config = None

        if qjackctl_config:
            mtime = os.path.getmtime(qjackctl_config)
            changed = mtime > getattr(self, "_conf_mtime", 0)

            if changed:
                log.debug("JACK configuration file mtime changed or previously unknown.")

            if force or changed or self.presets is None:
                log.debug("(Re-)Reading configuration.")
                (
                    preset_names,
                    self.jack_settings,
                    self.default_preset,
                ) = get_qjackctl_presets(qjackctl_config, self.ignore_default)
                self.presets = {name: name.replace("_", " ") for name in preset_names}
                self.create_menu()

            self._conf_mtime = mtime
        elif self.presets or self.presets is None:
            log.warning("Could not access configuration file.")

            if __debug__ and self.presets:
                log.debug("Removing stored presets from memory.")

            self.presets = {}
            self.jack_settings = {}
            self.default_preset = None
            self.create_menu()

        return True  # keep function scheduled

    def check_alsa_settings(self, preset):
        engine = self.jack_settings[preset]["engine"]
        driver = self.jack_settings[preset]["driver"]
        if engine["driver"] != "alsa":
            return True

        dev = driver.get("device")
        if dev and dev not in self.alsainfo.devices:
            log.debug("Device '%s' used by preset '%s' not found.", dev, preset)
            return False

        dev = driver.get("playback")
        if dev and dev not in self.alsainfo.playback_devices:
            log.debug("Playback device '%s' used by preset '%s' not found.", dev, preset)
            return False

        dev = driver.get("capture")
        if dev and dev not in self.alsainfo.capture_devices:
            log.debug("Capture device '%s' used by preset '%s' not found.", dev, preset)
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
                self.gui.add_menu_item(callback, label, enabled=not disabled, data=name)

        else:
            self.gui.add_menu_item(None, "No presets found", enabled=False)

        self.gui.add_separator()
        self.menu_stop = self.gui.add_menu_item(
            self.stop_jack_server,
            "Stop JACK Server",
            icon="stop.png",
            enabled=bool(self.jack_status.get("is_started")),
        )

        if self.a2jctl:
            self.gui.add_separator()
            self.menu_a2jbridge = self.gui.add_submenu("ALSA-MIDI Bridge")
            self.menu_a2j_startstop = self.gui.add_menu_item(
                self.on_start_stop_a2jbridge,
                "ALSA-MIDI Bridge",
                icon="midi.png",
                menu=self.menu_a2jbridge,
            )
            self.menu_a2j_export_hw = self.gui.add_menu_item(
                self.on_a2jbridge_set_export_hw,
                "Export HW Ports",
                is_check=True,
                active=self.a2j_export_hw,
                menu=self.menu_a2jbridge,
            )
            self.menu_a2j_autostart = self.gui.add_menu_item(
                self.on_a2jbridge_autostart,
                "Auto-Start with JACK",
                is_check=True,
                active=self.a2j_autostart,
                menu=self.menu_a2jbridge,
            )
        else:
            self.menu_a2jbridge = None

        self.gui.add_separator()
        self.menu_quit = self.gui.add_menu_item(self.quit, "Quit", icon="quit.png")
        self.gui.menu.show_all()
        self.update_a2jbridge_status()

    def open_menu(self):
        self.gui.on_popup_menu_open()

    def update_jack_status(self, value, name=None):
        jack_started = self.jack_status.get("is_started")
        self.jack_status[name] = value

        if name == "is_started" and value != jack_started:
            if value:
                self.gui.set_icon("started.png")
                log.info("JACK server has started.")
                self.a2jbridge_autostart()
            else:
                self.gui.set_icon("stopped.png")
                self.tooltext = "JACK server is stopped."
                log.info(self.tooltext)

            self.menu_stop.set_sensitive(value)
            self.update_a2jbridge_status()

        if self.jack_status.get("is_started"):
            try:
                if self.active_preset:
                    label = self.presets.get(self.active_preset, self.active_preset)
                    self.tooltext = "<b>[%s]</b>\n" % label
                else:
                    self.tooltext = "<i><b>Unknown configuration</b></i>\n"

                self.tooltext += (
                    "%(samplerate)i Hz / %(period)i frames "
                    "(%(latency)0.1f ms)\n" % self.jack_status
                )
                self.tooltext += "RT: %s " % (
                    "yes" if self.jack_status.get("is_realtime") else "no"
                )
                self.tooltext += "load: %(load)i%% xruns: %(xruns)i" % self.jack_status
            except KeyError:
                self.tooltext = "No status available."

    def update_a2jbridge_status(self, status=None):
        if self.menu_a2jbridge:
            if not self.a2jctl:
                # No a2jmidid service D-BUS interface
                self.menu_a2j_startstop.set_sensitive(False)
                self.menu_a2j_export_hw.set_sensitive(False)
                self.menu_a2j_startstop.set_label("ALSA-MIDI Bridge not available")
            elif self.jack_status.get("is_started"):
                # JACK server started
                if status is None:
                    status = self.a2jctl.is_started()

                if status:
                    # bridge started
                    self.menu_a2j_startstop.set_label("Stop ALSA-MIDI Bridge")
                    self.menu_a2j_export_hw.set_active(self.a2jctl.get_hw_export())
                    self.menu_a2j_export_hw.set_sensitive(False)
                else:
                    # bridge stopped
                    self.menu_a2j_startstop.set_label("Start ALSA-MIDI Bridge")
                    self.menu_a2j_export_hw.set_sensitive(True)

                self.menu_a2j_startstop.set_sensitive(True)
            else:
                # JACK server stopped
                self.menu_a2j_startstop.set_label("ALSA-MIDI Bridge suspended")
                self.menu_a2j_startstop.set_sensitive(False)
                self.menu_a2j_export_hw.set_sensitive(True)

    def handle_device_change(self, observer=None, device=None, init=False):
        if device:
            dev = device.device_path.split("/")[-1]

        if init or (device.action in ("change", "remove") and dev.startswith("card")):
            try:
                log.debug("Sound device change signalled. Collecting ALSA " "device info...")
                self.alsainfo = AlsaInfo(deferred=False)
            except Exception as exc:
                log.warn("Could not get ALSA device list: %s", exc)
                self.alsainfo = None

            if device and device.action != "init":
                self.load_presets(force=True)

    def handle_jackctl_signal(self, *args, signal=None, **kw):
        log.debug("JackCtl signal received: %r", signal)
        if signal == "ServerStarted":
            self.update_jack_status(True, name="is_started")
        elif signal == "ServerStopped":
            self.update_jack_status(False, name="is_started")

    def handle_a2jctl_signal(self, *args, signal=None, **kw):
        if signal == "bridge_started":
            log.debug("a2jmidid bridge STARTED signal received.")
            self.update_a2jbridge_status(True)
        elif signal == "bridge_stopped":
            log.debug("a2jmidid bridge STOPPED signal received.")
            self.update_a2jbridge_status(False)

    def handle_dbus_error(self, *args):
        """Handle errors from async JackCtlInterface calls.

        If the error indicates that the JackCtl D-BUS service vanished,
        invalidate the existing D-BUS interface instances and schedule a
        reconnection attempt.

        """
        log.warning("JackCtl D-BUS call error handler called.")
        if args and isinstance(args[0], dbus.DBusException):
            if "org.freedesktop.DBus.Error.ServiceUnknown" in str(args[0]) and self.jackctl:
                log.warning("JackCtl D-BUS service vanished. Assuming JACK is stopped.")
                self.update_jack_status(False, name="is_started")
                self.jackctl = None
                self.jackcfg = None
                GObject.timeout_add(INTERVAL_GET_STATS, self.dbus_connect)

    def get_jack_stats(self):
        if self.jackctl and self.jack_status.get("is_started"):
            try:
                cb = self.update_jack_status
                ecb = self.handle_dbus_error
                self.jackctl.is_realtime(cb, ecb)
                self.jackctl.get_sample_rate(cb, ecb)
                self.jackctl.get_period(cb, ecb)
                self.jackctl.get_load(cb, ecb)
                self.jackctl.get_xruns(cb, ecb)
                self.jackctl.get_latency(cb, ecb)
            except dbus.exceptions.DBusException:
                log.warning("JackCtl D-BUS service failure. Assuming JACK is stopped.")
                self.update_jack_status(False, name="is_started")

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
            preset = kwargs.get("preset")

        if not preset:
            log.warn("Preset must not be null.")
            return

        settings = self.jack_settings.get(preset)

        if settings:
            if self.jackcfg:
                self.jackcfg.activate_preset(settings)
                log.info("Activated preset: %s", preset)
                self.stop_jack_server()
                GObject.timeout_add(INTERVAL_RESTART, self.start_jack_server)
                self.active_preset = preset
        else:
            log.error("Unknown preset '%s'. Ignoring it.", preset)

    def start_jack_server(self, *args, **kwargs):
        if self.jackctl and not self.jack_status.get("is_started"):
            log.debug("Starting JACK server...")
            try:
                self.jackctl.start_server()
            except Exception as exc:
                log.error("Could not start JACK server: %s", exc)

    def stop_jack_server(self, *args, **kwargs):
        if self.jackctl and self.jack_status.get("is_started"):
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
            log.debug("Export HW ports: %s", "yes" if self.a2j_export_hw else "no")
            self.a2jctl.set_hw_export(self.a2j_export_hw)

            log.debug("Starting ALSA-MIDI to JACK bridge...")
            self.a2jctl.start()
        else:
            log.debug("Stopping ALSA-MIDI to JACK bridge...")
            self.a2jctl.stop()

    def on_a2jbridge_set_export_hw(self, widget, *args):
        self.a2j_export_hw = widget.get_active()
        log.debug("a2jmidid hw export %sabled.", "en" if self.a2j_autostart else "dis")

    def on_a2jbridge_autostart(self, widget, *args):
        self.a2j_autostart = widget.get_active()
        log.debug("a2jmidid auto-start %sabled.", "en" if self.a2j_autostart else "dis")

    def a2jbridge_autostart(self):
        if self.a2jctl and self.a2j_autostart and not self.a2jctl.is_started():
            log.debug("a2jmidid auto-start triggered.")
            self.start_stop_a2jbridge(True)

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

    ap = argparse.ArgumentParser(prog="jack-select", description=__doc__.splitlines()[0])
    ap.add_argument(
        "--version",
        action="version",
        version="%%(prog)s %s" % __version__,
        help="Show program version and exit.",
    )
    ap.add_argument(
        "--a2j-autostart",
        action="store_true",
        default=None,
        help="Autostart ALSA-MIDI to JACK bridge with JACK.",
    )
    ap.add_argument(
        "--a2j-export-hw",
        action="store_true",
        default=None,
        help="Export hardware MIDI ports via ALSA-MIDI to JACK bridge.",
    )
    ap.add_argument(
        "-a",
        "--no-alsa-monitor",
        action="store_false",
        default=None,
        help="Disable ALSA device monitoring and filtering.",
    )
    ap.add_argument(
        "-c",
        "--config",
        metavar="PATH",
        help="Path to configuration file (default: <XDG_CONFIG_HOME>/%s/%s)" % DEFAULT_CONFIG,
    )
    ap.add_argument("-d", "--default", action="store_true", help="Activate default preset.")
    ap.add_argument(
        "-i",
        "--ignore-default",
        action="store_true",
        default=None,
        help="Ignore the nameless '(default)' preset if any other presets are stored in the "
        "configuration.",
    )
    ap.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Be verbose about what the script does.",
    )
    ap.add_argument("preset", nargs="?", help="Configuration preset to activate on startup.")

    args = ap.parse_args(args if args is not None else sys.argv[1:])

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="[%(name)s] %(levelname)s: %(message)s",
    )

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
        if exc.get_dbus_name().endswith("ServiceUnknown"):
            start_gui = True
        else:
            log.warning("Exception: %s", exc)

    log.debug("Args: %s", args)

    if start_gui:
        app = JackSelectApp(
            bus,
            config=args.config,
            a2j_autostart=args.a2j_autostart,
            a2j_export_hw=args.a2j_export_hw,
            alsa_monitor=args.no_alsa_monitor,
            ignore_default=args.ignore_default,
        )

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


if __name__ == "__main__":
    sys.exit(main() or 0)
