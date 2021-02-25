# -*- coding: utf-8 -*-

import logging
from threading import Event, Thread


class StoppableThread(Thread):
    """Thread class with a stop() method. The thread itself has to check
    regularly for the stopped() condition."""

    def __init__(self, **kwargs):
        self._stop_event = Event()

        if "logger" in kwargs:
            self.logger = kwargs["logger"]
        elif "logger_name" in kwargs:
            self.logger = logging.getLogger(kwargs["logger_name"])
        else:
            self.logger = logging.getLogger(__name__)

        filtered_kwargs = {
            k: v for k, v in kwargs.items() if k not in ("logger", "logger_name")
        }

        Thread.__init__(self, **filtered_kwargs)

    def stop(self):
        """Sets the stop event"""
        self.logger.debug("Stopping thread: %s", self.name)
        self._stop_event.set()

    def stopped(self):
        """Determines if stop has been called yet."""
        return self._stop_event.isSet()

    def wait(self, timeout=None):
        """Delegate wait call to threading.Event"""
        return self._stop_event.wait(timeout)
