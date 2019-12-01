# -*- coding: utf-8 -*-
"""Base class for D-BUS service interface wrappers."""

import logging
from functools import partial

import dbus


log = logging.getLogger(__name__)


class DBUSBaseInterface:
    """Base class for D-BUS service interface wrappers.

    This is an abstract base class. Sub-classes ned to define the following
    class or instance attributes:

    * service - the name of the D-BUS service
    * interface - the name of the D-BUS accessed via this class
    * object_path = the path to the service object providing the interface

    """

    def __init__(self, ctl=None, bus=None):
        if not ctl:
            ctl = self.get_controller(bus)

        self._if = dbus.Interface(ctl, self.interface)

    def get_controller(self, bus=None):
        if not bus:
            bus = dbus.SessionBus()
        return bus.get_object(self.service, self.object_path)

    def _async_handler(self, *args, **kw):
        name = kw.get('name')
        callback = kw.get('callback')

        if args and isinstance(args[0], dbus.DBusException):
            log.error("Async call failed name=%s: %s", name, args[0])
            return

        if callback:
            callback(*args, name=name)

    def call_async(self, meth, args=None, name=None, callback=None):
        if callback:
            handler = partial(self._async_handler, callback=callback,
                              name=name or meth)
            kw = dict(reply_handler=handler, error_handler=handler)
        else:
            kw = {}

        return getattr(self._if, meth)(*args or [], **kw)

    def add_signal_handler(self, handler, signal=None):
        return self._if.connect_to_signal(
            signal_name=signal,
            handler_function=handler,
            interface_keyword='interface',
            member_keyword='signal')
