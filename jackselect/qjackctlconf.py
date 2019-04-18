# -*- coding: utf-8 -*-
"""Read JACK presets and their settings from QjackCtl's configuration file."""

import configparser
import logging


log = logging.getLogger(__name__)
PARAM_MAPPING = {
    'driver': ('engine', 'driver'),
    'realtime': ('engine', 'realtime'),
    'priority': ('engine', 'realtime-priority'),
    'verbose': ('engine', 'verbose'),
    'timeout': ('engine', 'client-timeout'),
    'portmax': ('engine', 'port-max'),
    'samplerate': 'rate',
    'frames': 'period',
    'periods': 'nperiods',
    'interface': 'device',
    'indevice': 'capture',
    'outdevice': 'playback',
    'chan': 'channels',
    'inlatency': 'input-latency',
    'outlatency': 'output-latency',
    'mididriver': 'midi',
    # 'snoop': '???'
}
DEFAULT_PRESET = '(default)'


def get_qjackctl_presets(qjackctl_conf, ignore_default=False):
    config = configparser.ConfigParser()
    config.optionxform = lambda option: option
    config.read(qjackctl_conf)

    preset_names = set()
    settings = {}

    if 'Settings' in config:
        for name in config['Settings']:
            try:
                preset_name, setting = name.split('\\', 1)
            except ValueError:
                # The default (nameless) preset was saved.
                # It uses settings keys without a preset name prefix.
                setting = name
                preset_name = DEFAULT_PRESET

            preset_names.add(preset_name)
            setting = setting.lower()
            value = config.get('Settings', name)
            setting = PARAM_MAPPING.get(setting, setting)

            if isinstance(setting, tuple):
                component, setting = setting
            else:
                component = 'driver'

            if preset_name not in settings:
                settings[preset_name] = {}

            if component not in settings[preset_name]:
                settings[preset_name][component] = {}

            if value == 'false':
                value = False
            elif value == 'true':
                value = True
            elif value == '':
                value = None
            else:
                try:
                    value = int(value)
                except (TypeError, ValueError):
                    pass

            settings[preset_name][component][setting] = value

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
        presets, _, default = get_qjackctl_presets(qjackctl_conf, True)
        for preset in sorted(presets):
            print(preset, "*" if preset == default else '')


if __name__ == '__main__':
    _test()
