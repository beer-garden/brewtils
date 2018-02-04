import logging
from threading import Event, Thread


class StoppableThread(Thread):
    """Thread class with a stop() method. The thread itself has to check
    regularly for the stopped() condition."""

    def __init__(self, **kwargs):
        self.logger = kwargs.pop('logger', logging.getLogger(__name__))
        self._stop_event = Event()

        Thread.__init__(self, **kwargs)

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
