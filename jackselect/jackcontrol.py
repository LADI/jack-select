# -*- coding: utf-8 -*-
"""Control and configure a JACK server via DBus."""

import logging

from functools import partial

import dbus


log = logging.getLogger(__name__)
SETTINGS = {
    'engine': (
        ('client-timeout', dbus.Int32),
        'clock-source',
        'driver',
        'name',
        'port-max',
        'realtime',
        ('realtime-priority', dbus.Int32),
        'replace-registry',
        ('self-connect-mode', dbus.Byte),
        'slave-drivers',
        'sync',
        'temporary',
        'verbose',
    ),
    'driver': (
        'capture',
        'device',
        ('dither', dbus.Byte),
        'hwmeter',
        'hwmon',
        'inchannels',
        'midi-driver',
        'monitor',
        'nperiods',
        'outchannels',
        'period',
        'playback',
        'rate',
        'shorts',
        'softmode',
    )
}


def get_jack_controller(bus=None):
    if not bus:
        bus = dbus.SessionBus()
    return bus.get_object("org.jackaudio.service", "/org/jackaudio/Controller")


class JackBaseInterface:
    def __init__(self, jackctl=None):
        if not jackctl:
            jackctl = get_jack_controller()

        self._if = dbus.Interface(jackctl, self.interface)

    def _async_handler(self, *args, **kw):
        name = kw.get('name')
        callback = kw.get('callback')

        if args and isinstance(args[0], dbus.DBusException):
            log.error("Async call failed name=%s: %s", name, args[0])
            return

        if callback:
            callback(*args, name=name)

    def call_async(self, meth, name, callback=None, *args):
        if callback:
            handler = partial(self._async_handler, callback=callback,
                              name=name)
            kw = dict(reply_handler=handler, error_handler=handler)
        else:
            kw = {}
        return getattr(self._if, meth)(*args, **kw)


class JackCtlInterface(JackBaseInterface):
    interface = "org.jackaudio.JackControl"

    def is_started(self, cb=None):
        return self.call_async('IsStarted', 'is_started', cb)

    def is_realtime(self, cb=None):
        return self.call_async('IsRealtime', 'is_realtime', cb)

    def start_server(self, cb=None):
        return self.call_async('StartServer', 'start_server', cb)

    def stop_server(self, cb=None):
        return self.call_async('StopServer', 'stop_server', cb)

    def get_latency(self, cb=None):
        return self.call_async('GetLatency', 'latency', cb)

    def get_load(self, cb=None):
        return self.call_async('GetLoad', 'load', cb)

    def get_period(self, cb=None):
        return self.call_async('GetBufferSize', 'period', cb)

    def get_sample_rate(self, cb=None):
        return self.call_async('GetSampleRate', 'samplerate', cb)

    def get_xruns(self, cb=None):
        return self.call_async('GetXruns', 'xruns', cb)

    def add_signal_handler(self, handler, signal=None):
        return self._if.connect_to_signal(
            signal_name=signal,
            handler_function=handler,
            interface_keyword='interface',
            member_keyword='signal')


class JackCfgInterface(JackBaseInterface):
    interface = "org.jackaudio.Configure"

    def engine_has_feature(self, feature):
        try:
            features = self._if.ReadContainer(["engine"])[1]
        except:  # noqa:E722
            features = ()
        return dbus.String(feature) in features

    def get_engine_parameter(self, parameter, fallback=None):
        if not self.engine_has_feature(parameter):
            return fallback
        else:
            try:
                return self._if.GetParameterValue(["engine", parameter])[2]
            except:  # noqa:E722
                return fallback

    def set_engine_parameter(self, parameter, value, optional=True):
        if not self.engine_has_feature(parameter):
            return 2
        elif optional:
            pvalue = self._if.GetParameterValue(["engine", parameter])

            if pvalue is None:
                return False

            if value != pvalue[2]:
                return bool(self._if.SetParameterValue(["engine", parameter],
                                                       value))
            else:
                return 3
        else:
            return bool(self._if.SetParameterValue(["engine", parameter],
                                                   value))

    def driver_has_feature(self, feature):
        try:
            features = self._if.ReadContainer(["driver"])[1]
        except:  # noqa:E722
            features = ()
        return dbus.String(feature) in features

    def get_driver_parameter(self, parameter, fallback=None):
        if not self.driver_has_feature(parameter):
            return fallback
        else:
            try:
                return self._if.GetParameterValue(["driver", parameter])[2]
            except:  # noqa:E722
                return fallback

    def set_driver_parameter(self, parameter, value, optional=True):
        if not self.driver_has_feature(parameter):
            return 2
        elif optional:
            if value != self._if.GetParameterValue(["driver", parameter])[2]:
                return bool(self._if.SetParameterValue(["driver", parameter],
                                                       value))
            else:
                return 3
        else:
            return bool(self._if.SetParameterValue(["driver", parameter],
                                                   value))

    def activate_preset(self, settings):
        for component in ('engine', 'driver'):
            csettings = settings.get(component, {})

            for setting in SETTINGS[component]:
                if isinstance(setting, tuple):
                    setting, stype = setting
                else:
                    stype = None

                value = csettings.get(setting)

                if value is None:
                    log.debug("Resetting %s.%s", component, setting)
                    self._if.ResetParameterValue([component, setting])
                    continue

                if stype:
                    dbus_value = stype(value)
                elif isinstance(value, bool):
                    dbus_value = dbus.Boolean(value)
                elif isinstance(value, int):
                    dbus_value = dbus.UInt32(value)
                elif isinstance(value, str):
                    dbus_value = dbus.String(value)
                else:
                    log.warning("Unknown type %s for setting '%s' = %r.",
                                type(value), setting, value)
                    dbus_value = value

                if component == 'engine':
                    setter = self.set_engine_parameter
                elif component == 'driver':
                    setter = self.set_driver_parameter

                log.debug("Setting %s.%s = %r", component, setting, value)
                result = setter(setting, dbus_value)

                if result not in (0, 3):
                    log.error("Setting %s setting '%s' failed (value %r), return value %s",
                              component, setting, value, result)
