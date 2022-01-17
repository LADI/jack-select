# -*- coding: utf-8 -*-
"""Read JACK presets and their settings from QjackCtl's configuration file."""

import configparser
import logging


log = logging.getLogger(__name__)
PARAM_MAPPING = {
    'chan': ('driver', ('inchannels', 'outchannels')),
    'clocksource': 'clock-source',
    'driver': ('engine', 'driver'),
    'frames': 'period',
    'indevice': 'capture',
    'inlatency': 'input-latency',
    'interface': 'device',
    'mididriver': 'midi-driver',
    'outdevice': 'playback',
    'outlatency': 'output-latency',
    'periods': 'nperiods',
    'portmax': ('engine', 'port-max'),
    'priority': ('engine', 'realtime-priority'),
    'realtime': ('engine', 'realtime'),
    'samplerate': 'rate',
    'selfconnectmode': 'self-connect-mode',
    'servername': ('engine', 'name'),
    'slavedrivers': ('engine', 'slave-drivers'),
    'timeout': ('engine', 'client-timeout'),
    'verbose': ('engine', 'verbose'),
    # 'snoop': '???'
}
VALUE_MAPPING = {
    'clock-source': {
        'c': 0,
        'h': 1,
        's': 2,
    },
    'dither': {
        0: b'n',
        1: b'r',
        2: b's',
        3: b't',
    },
    'self-connect-mode': {
        0: b' ',
        1: b'e',
        2: b'E',
        3: b'a',
        4: b'A',
    }
}
ALLOWED_VALUES = {
    'clock-source': VALUE_MAPPING['clock-source'].values(),
    'dither': VALUE_MAPPING['dither'].values(),
    'midi-driver': ('none', 'seq', 'raw'),
    'self-connect-mode': VALUE_MAPPING['self-connect-mode'].values(),
}
NULL_DEFAULT_VALUES = (
    'client-timeout',
    'inchannels',
    'input-latency',
    'nperiods',
    'outchannels',
    'output-latency',
    'period',
    'port-max',
    'rate',
    'realtime-priority',
    'wait'
)
DEFAULT_PRESET = '(default)'


def get_qjackctl_presets(qjackctl_conf, ignore_default=False):
    config = configparser.ConfigParser()
    config.optionxform = lambda option: option
    config.read(qjackctl_conf)

    preset_names = set()
    settings = {}

    if 'Settings' in config:
        for name in sorted(config['Settings']):
            try:
                preset_name, param = name.split('\\', 1)
            except ValueError:
                # The default (nameless) preset was saved.
                # It uses settings keys without a preset name prefix.
                param = name
                preset_name = DEFAULT_PRESET

            preset_names.add(preset_name)
            param = param.lower()
            value = config.get('Settings', name)
            param = PARAM_MAPPING.get(param, param)

            if isinstance(param, tuple):
                component, param = param
            else:
                component = 'driver'

            if preset_name not in settings:
                settings[preset_name] = {}

            if component not in settings[preset_name]:
                settings[preset_name][component] = {}

            if not isinstance(param, (tuple, list)):
                param = (param,)

            if value == 'false':
                value = False
            elif value == 'true':
                value = True
            # Dirty way of stripping string quoting
            # it's not clear when values get quoted in Qt settings files
            elif (
                len(value) >= 2 and
                (
                    (value.startswith("'") and value.endswith("'")) or
                    (value.startswith('"') and value.endswith('"'))
                )
            ):
                value = value[1:-1]
            elif value == '':
                value = None
            else:
                try:
                    value = int(value)
                except (TypeError, ValueError):
                    pass

            for p in param:
                if p in VALUE_MAPPING:
                    value = VALUE_MAPPING[p].get(value, value)
                elif p in ALLOWED_VALUES and value not in ALLOWED_VALUES[p]:
                    value = None
                elif p in NULL_DEFAULT_VALUES and value == 0:
                    value = None

                settings[preset_name][component][p] = value

    if (ignore_default and DEFAULT_PRESET in settings and len(settings) > 1):
        del settings[DEFAULT_PRESET]

        if DEFAULT_PRESET in preset_names:
            preset_names.remove(DEFAULT_PRESET)

    default_preset = config.get('Presets', 'DefPreset', fallback=None)

    if default_preset not in preset_names:
        default_preset = None

    if not default_preset and DEFAULT_PRESET in preset_names:
        default_preset = DEFAULT_PRESET

    return list(preset_names), settings, default_preset


def _test():
    from xdg import BaseDirectory as xdgbase

    qjackctl_conf = xdgbase.load_first_config('rncbc.org/QjackCtl.conf')

    if qjackctl_conf:
        presets, settings, default = get_qjackctl_presets(qjackctl_conf, True)
        for preset in sorted(presets):
            print("%s:%s\n" % (preset, " *" if preset == default else ''))
            print("[engine]")

            for setting, value in sorted(settings[preset]['engine'].items()):
                print("%s: %r" % (setting, value))

            print("\n[driver]")

            for setting, value in sorted(settings[preset]['driver'].items()):
                print("%s: %r" % (setting, value))

            print()


if __name__ == '__main__':
    _test()
