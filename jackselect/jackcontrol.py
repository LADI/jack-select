# -*- coding: utf-8 -*-
"""Control and configure a JACK server via D-BUS."""

import logging

import dbus

from .dbusinterface import DBUSBaseInterface


log = logging.getLogger(__name__)

SETTINGS = {
    'engine': (
        ('client-timeout', dbus.Int32),
        ('clock-source', dbus.UInt32),
        ('driver', dbus.String),
        ('name', dbus.String),
        ('port-max', dbus.UInt32),
        ('realtime', dbus.Boolean),
        ('realtime-priority', dbus.Int32),
        ('replace-registry', dbus.Boolean),
        ('self-connect-mode', dbus.Byte),
        ('slave-drivers', dbus.String),
        ('sync', dbus.Boolean),
        ('temporary', dbus.Boolean),
        ('verbose', dbus.Boolean),
    ),
    'driver': (
        ('capture', dbus.String),
        ('device', dbus.String),
        ('dither', dbus.Byte),
        ('hwmeter', dbus.Boolean),
        ('hwmon', dbus.Boolean),
        ('inchannels', dbus.UInt32),
        ('midi-driver', dbus.String),
        ('monitor', dbus.Boolean),
        ('nperiods', dbus.UInt32),
        ('outchannels', dbus.UInt32),
        ('period', dbus.UInt32),
        ('playback', dbus.String),
        ('rate', dbus.UInt32),
        ('shorts', dbus.Boolean),
        ('softmode', dbus.Boolean),
    )
}


class JackBaseInterface(DBUSBaseInterface):
    service = "org.jackaudio.service"
    object_path = "/org/jackaudio/Controller"


class JackCtlInterface(JackBaseInterface):
    interface = "org.jackaudio.JackControl"

    def exit(self, cb=None, error_cb=None):
        return self.call_async('Exit', name='is_started', callback=cb,
                               error_callback=error_cb)

    def is_started(self, cb=None, error_cb=None):
        return self.call_async('IsStarted', name='is_started', callback=cb,
                               error_callback=error_cb)

    def is_realtime(self, cb=None, error_cb=None):
        return self.call_async('IsRealtime', name='is_realtime', callback=cb,
                               error_callback=error_cb)

    def start_server(self, cb=None, error_cb=None):
        return self.call_async('StartServer', name='start_server', callback=cb,
                               error_callback=error_cb)

    def stop_server(self, cb=None, error_cb=None):
        return self.call_async('StopServer', name='stop_server', callback=cb,
                               error_callback=error_cb)

    def get_latency(self, cb=None, error_cb=None):
        return self.call_async('GetLatency', name='latency', callback=cb,
                               error_callback=error_cb)

    def get_load(self, cb=None, error_cb=None):
        return self.call_async('GetLoad', name='load', callback=cb,
                               error_callback=error_cb)

    def get_period(self, cb=None, error_cb=None):
        return self.call_async('GetBufferSize', name='period', callback=cb,
                               error_callback=error_cb)

    def get_sample_rate(self, cb=None, error_cb=None):
        return self.call_async('GetSampleRate', name='samplerate', callback=cb,
                               error_callback=error_cb)

    def get_xruns(self, cb=None, error_cb=None):
        return self.call_async('GetXruns', name='xruns', callback=cb)

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
