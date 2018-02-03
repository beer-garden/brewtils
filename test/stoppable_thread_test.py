import unittest

from mock import Mock

from brewtils.stoppable_thread import StoppableThread


class StoppableThreadTest(unittest.TestCase):

    def setUp(self):
        self.thread = StoppableThread()

    def test_init_stop_not_set(self):
        self.assertFalse(self.thread._stop_event.isSet())

    def test_init_logger_passed_in(self):
        fake_logger = Mock()
        t = StoppableThread(logger=fake_logger)
        self.assertEqual(t.logger, fake_logger)

    def test_stop(self):
        self.thread.stop()
        self.assertTrue(self.thread._stop_event.isSet())

    def test_stopped_true(self):
        self.thread._stop_event.set()
        self.assertTrue(self.thread.stopped())

    def test_stopped_false(self):
        self.assertFalse(self.thread.stopped())

    def test_wait(self):
        event_mock = Mock()
        self.thread._stop_event = event_mock
        self.thread.wait(1)
        event_mock.wait.assert_called_once_with(1)
