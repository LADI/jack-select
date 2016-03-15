# -*- coding: utf-8 -*-
"""Control and configure a JACK server via DBus."""

import logging

from functools import partial

import dbus


log = logging.getLogger(__name__)
SETTINGS = {
    'engine': (
        'realtime',
        ('realtime-priority', dbus.Int32),
        'port-max',
        'verbose',
        ('client-timeout', dbus.Int32),
    ),
    'driver': (
        'driver',
        'capture',
        'playback',
        'device',
        'rate',
        'period',
        'nperiods',
        'outchannels',
        'inchannels',
        ('channels', dbus.Int32),
        'midi',
        'hwmon',
        'hwmeter',
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
            handler = partial(self._async_handler, callback=callback, name=name)
            kw = dict(reply_handler=handler, error_handler=handler)
        else:
            kw = {}
        return getattr(self._if, meth)(*args, **kw)


class JackCtlInterface(JackBaseInterface):
    interface = "org.jackaudio.JackControl"

    def is_started(self, cb=None):
        return self.call_async('IsStarted', 'is_started', cb)

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


class JackCfgInterface(JackBaseInterface):
    interface = "org.jackaudio.Configure"

    def engine_has_feature(self, feature):
        try:
            features = self._if.ReadContainer(["driver"])[1]
        except:
            features = ()
        return dbus.String(feature) in features

    def get_engine_parameter(self, parameter, fallback=None):
        if not self.engine_has_feature(parameter):
            return fallback
        else:
            try:
                return self._if.GetParameterValue(["engine", parameter])[2]
            except:
                return fallback

    def set_engine_parameter(self, parameter, value, optional=True):
        if not self.engine_has_feature(parameter):
            return False
        elif optional:
            pvalue = self._if.GetParameterValue(["engine", parameter])

            if pvalue is None:
                return False

            if value != pvalue[2]:
                return bool(self._if.SetParameterValue(["engine", parameter],
                                                       value))
            else:
                return False
        else:
            return bool(self._if.SetParameterValue(["engine", parameter],
                                                   value))

    def driver_has_feature(self, feature):
        try:
            features = self._if.ReadContainer(["driver"])[1]
        except:
            features = ()
        return dbus.String(feature) in features

    def get_driver_parameter(self, parameter, fallback=None):
        if not self.driver_has_feature(parameter):
            return fallback
        else:
            try:
                return self._if.GetParameterValue(["driver", parameter])[2]
            except:
                return fallback

    def set_driver_parameter(self, parameter, value, optional=True):
        if not self.driver_has_feature(parameter):
            return False
        elif optional:
            if value != self._if.GetParameterValue(["driver", parameter])[2]:
                return bool(self._if.SetParameterValue(["driver", parameter],
                                                       value))
            else:
                return False
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
                    self._if.ResetParameterValue([component, setting])
                    continue

                if stype:
                    value = stype(value)
                elif isinstance(value, bool):
                    value = dbus.Boolean(value)
                elif isinstance(value, int):
                    value = dbus.UInt32(value)
                elif isinstance(value, str):
                    value = dbus.String(value)
                else:
                    log.warning("Unknown type %s for setting '%s' = %r.",
                                type(value), setting, value)

                if component == 'engine':
                    self.set_engine_parameter(setting, value)
                elif component == 'driver':
                    self.set_driver_parameter(setting, value)
