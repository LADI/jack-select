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
DEFAULT_PRESET = object()


def get_qjackctl_presets(qjackctl_conf):
    config = configparser.ConfigParser()
    config.optionxform = lambda option: option
    config.read(qjackctl_conf)

    if 'Presets' in config:
        preset_names = {v for k, v in config['Presets'].items()
                        if k != 'DefPreset'}
    else:
        preset_names = set()

    try:
        default_preset = config.get('Presets', 'DefPreset')
    except configparser.Error:
        default_preset = preset_names[0] if preset_names else DEFAULT_PRESET

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
                preset_names.add(DEFAULT_PRESET)

            setting = setting.lower()
            value = config.get('Settings', name)

            if preset_name in preset_names:
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
            else:
                log.warning("Unknown preset: %s" % preset_name)

    return list(preset_names), settings, default_preset


def _test():
    from xdg import BaseDirectory as xdgbase

    qjackctl_conf = xdgbase.load_first_config('rncbc.org/QjackCtl.conf')

    if qjackctl_conf:
        presets, _, default_preset = get_qjackctl_presets(qjackctl_conf)
        for preset in presets:
            print(preset, "*" if preset == default_preset else '')


if __name__ == '__main__':
    _test()
