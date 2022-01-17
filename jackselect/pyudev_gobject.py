# -*- coding: utf-8 -*-
# Copyright (C) 2010, 2011, 2012, 2013 Sebastian Wiesner <lunaryorn@gmail.com>

# This library is free software; you can redistribute it and/or modify it
# under the terms of the GNU Lesser General Public License as published by the
# Free Software Foundation; either version 2.1 of the License, or (at your
# option) any later version.

# This library is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE.  See the GNU Lesser General Public License
# for more details.

# You should have received a copy of the GNU Lesser General Public License
# along with this library; if not, write to the Free Software Foundation,
# Inc., 51 Franklin St, Fifth Floor, Boston, MA 02110-1301 USA

"""
pyudev_gobject
==============

Glib integration.

:class:`MonitorObserver` integrates device monitoring into the Glib
mainloop by turning device events into Glib signals.

:mod:`GLib` and :mod:`GObject` must be available for import via
`gi.repository` when importing this module.

.. moduleauthor::  Sebastian Wiesner  <lunaryorn@gmail.com>

"""

from __future__ import unicode_literals

from gi.repository import GLib, GObject


class MonitorObserver(GObject.GObject):
    """An observer for device events integrating into the :mod:`GLib` mainloop.

    This class inherits :class:`~GObject.GObject` to turn device events into
    glib signals.

    >>> from pyudev import Context, Monitor
    >>> from pyudev_gobject import MonitorObserver
    >>> context = Context()
    >>> monitor = Monitor.from_netlink(context)
    >>> monitor.filter_by(subsystem='input')
    >>> observer = MonitorObserver(monitor)
    >>> def device_event(observer, device):
    ...     print('event {0} on device {1}'.format(device.action, device))
    >>> observer.connect('device-event', device_event)
    >>> monitor.start()

    """

    __gsignals__ = {
        # explicitly convert the signal to str, because glib expects the
        # *native* string type of the corresponding python version as type of
        # signal name, and str() is the name of the native string type of both
        # python versions.  We could also remove the "unicode_literals" import,
        # but I don't want to make exceptions to the standard set of future
        # imports used throughout pyudev for the sake of consistency.
        str("device-event"): (
            GObject.SIGNAL_RUN_LAST,
            GObject.TYPE_NONE,
            (GObject.TYPE_PYOBJECT,),
        ),
    }

    def __init__(self, monitor):
        super().__init__()
        self._setup_observer(monitor)

    def _setup_observer(self, monitor):
        self.monitor = monitor
        self.event_source = None
        self.enabled = True

    @property
    def enabled(self):
        """
        Whether this observer is enabled or not.

        If ``True`` (the default), this observer is enabled, and emits events.
        Otherwise it is disabled and does not emit any events.

        """
        return self.event_source is not None

    @enabled.setter
    def enabled(self, value):
        if value and self.event_source is None:
            self.event_source = GLib.io_add_watch(
                self.monitor, GLib.IO_IN, self._process_udev_event
            )
        elif not value and self.event_source is not None:
            GLib.source_remove(self.event_source)
            self.event_source = None

    def _process_udev_event(self, source, condition):
        if condition == GLib.IO_IN:
            device = self.monitor.poll(timeout=0)
            if device is not None:
                self._emit_event(device)
        return True

    def _emit_event(self, device):
        self.emit("device-event", device)


GObject.type_register(MonitorObserver)
