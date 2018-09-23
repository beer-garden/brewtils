# -*- coding: utf-8 -*-

import pytest
from mock import Mock

from brewtils.stoppable_thread import StoppableThread


class TestStoppableThread(object):

    @pytest.fixture
    def thread(self):
        return StoppableThread()

    def test_init_stop_not_set(self, thread):
        assert thread._stop_event.isSet() is False

    def test_init_logger_passed_in(self):
        fake_logger = Mock()
        t = StoppableThread(logger=fake_logger)
        assert t.logger == fake_logger

    def test_stop(self, thread):
        thread.stop()
        assert thread._stop_event.isSet() is True

    def test_stopped_true(self, thread):
        thread._stop_event.set()
        assert thread.stopped() is True

    def test_stopped_false(self, thread):
        assert thread.stopped() is False

    def test_wait(self, thread):
        event_mock = Mock()
        thread._stop_event = event_mock
        thread.wait(1)
        event_mock.wait.assert_called_once_with(1)
