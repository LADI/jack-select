# -*- coding: utf-8 -*-
"""Control and configure a aj2midid service via D-BUS."""

import logging

from .dbusinterface import DBUSBaseInterface


log = logging.getLogger(__name__)


class A2JCtlInterface(DBUSBaseInterface):
    service = "org.gna.home.a2jmidid"
    interface = "org.gna.home.a2jmidid.control"
    object_path = "/"

    # interface method wrappers

    def exit(self, cb=None):
        return self.call_async("exit", callback=cb)

    def is_started(self, cb=None):
        return self.call_async("is_started", callback=cb)

    def start(self, cb=None):
        return self.call_async("start", callback=cb)

    def stop(self, cb=None):
        return self.call_async("stop", callback=cb)

    def get_hw_export(self, cb=None):
        return self.call_async("get_hw_export", callback=cb)

    def set_hw_export(self, hw_export=True, cb=None):
        return self.call_async("set_hw_export", args=(hw_export,), callback=cb)

    def get_jack_client_name(self, cb=None):
        return self.call_async("get_jack_client_name", callback=cb)

    def get_disable_port_uniqueness(self, cb=None):
        return self.call_async("get_disable_port_uniqueness", callback=cb)

    def set_disable_port_uniqueness(self, disable_port_uniqueness=True, cb=None):
        return self.call_async(
            "set_disable_port_uniqueness", args=(disable_port_uniqueness,), callback=cb
        )

    def map_alsa_to_jack_port(self, alsa_client_id, alsa_port_id, map_playback, cb=None):
        return self.call_async(
            "map_alsa_to_jack_port",
            args=(alsa_client_id, alsa_port_id, map_playback),
            callback=cb,
        )

    def map_jack_port_to_alsa(self, jack_port_name, cb=None):
        return self.call_async("map_jack_port_to_alsa", args=(jack_port_name,), callback=cb)
