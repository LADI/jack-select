# -*- coding: utf-8 -*-
"""Control and configure a JACK server via DBus."""

import logging

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


class JackCfgInterface:
    def __init__(self, jackctl):
        self._dbus = dbus.Interface(jackctl, "org.jackaudio.Configure")

    def engine_has_feature(self, feature):
        try:
            features = self._dbus.ReadContainer(["driver"])[1]
        except:
            features = ()
        return dbus.String(feature) in features

    def get_engine_parameter(self, parameter, fallback=None):
        if not self.engine_has_feature(parameter):
            return fallback
        else:
            try:
                return self._dbus.GetParameterValue(["engine", parameter])[2]
            except:
                return fallback

    def set_engine_parameter(self, parameter, value, optional=True):
        if not self.engine_has_feature(parameter):
            return False
        elif optional:
            pvalue = self._dbus.GetParameterValue(["engine", parameter])

            if pvalue is None:
                return False

            if value != pvalue[2]:
                return bool(self._dbus.SetParameterValue(["engine", parameter],
                                                         value))
            else:
                return False
        else:
            return bool(self._dbus.SetParameterValue(["engine", parameter],
                                                     value))

    def driver_has_feature(self, feature):
        try:
            features = self._dbus.ReadContainer(["driver"])[1]
        except:
            features = ()
        return dbus.String(feature) in features

    def get_driver_parameter(self, parameter, fallback=None):
        if not self.driver_has_feature(parameter):
            return fallback
        else:
            try:
                return self._dbus.GetParameterValue(["driver", parameter])[2]
            except:
                return fallback

    def set_driver_parameter(self, parameter, value, optional=True):
        if not self.driver_has_feature(parameter):
            return False
        elif optional:
            if value != self._dbus.GetParameterValue(["driver", parameter])[2]:
                return bool(self._dbus.SetParameterValue(["driver", parameter],
                                                         value))
            else:
                return False
        else:
            return bool(self._dbus.SetParameterValue(["driver", parameter],
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
                    self._dbus.ResetParameterValue([component, setting])
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
