# -*- coding: utf-8 -*-
"""Set up an udev monitor to be notified about changes in attached sound devices."""

import logging

from pyudev import Context, Monitor
from .pyudev_gobject import MonitorObserver


log = logging.getLogger(__name__)


class AlsaDevMonitor:
    def __init__(self, callback):
        # set up udev device monitor
        context = Context()
        self._monitor = Monitor.from_netlink(context)
        self._monitor.filter_by(subsystem="sound")
        self._observer = MonitorObserver(self._monitor)
        self._observer.connect("device-event", callback)

    def start(self):
        log.debug("Starting AlsaDevMonitor...")
        self._monitor.start()
