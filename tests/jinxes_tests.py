# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright (c) 2012 Vishvananda Ishaya
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.
"""
Tests for the jinxes library
"""

import curses
import unittest

from jinxes import actor
from jinxes import application


class TestScr(object):
    def bkgdset(self, *args, **kwargs):
        pass

    def nodelay(self, *args, **kwargs):
        pass

    def clear(self):
        pass

    def border(self):
        pass

    def refresh(self):
        pass

    def getch(self):
        return curses.ERR

    def addstr(self, y, x, text, brush):
        pass

    def getmaxyx(self):
        return 10, 10


class TestApp(application.Application):
    def __init__(self, scr, **kwargs):
        for key, value in kwargs.iteritems():
            setattr(self, key, value)
        super(TestApp, self).__init__(scr)


class TestCurses(object):
    COLOR_PAIRS = 10
    ERR = curses.ERR

    def curs_set(self, value):
        pass

    def init_pair(self, int_id, fg_color, bg_color):
        pass

    def color_pair(self, int_id):
        return int_id


class TestNotifier(object):
    def notify_created(self, actor):
        pass

    def notify_moved(self, actor):
        pass

    def notify_visible(self, actor):
        pass


class ApplicationTestCase(unittest.TestCase):
    """Test application functionality"""

    def setUp(self):
        super(ApplicationTestCase, self).setUp()
        application.curses = TestCurses()

    def tearDown(self):
        super(ApplicationTestCase, self).tearDown()
        application.curses = curses

    def test_create(self):

        def run():
            pass
        TestApp(TestScr(), run=run)

    def test_exit(self):

        def tick(current):
            raise application.Exit()
        TestApp(TestScr(), tick=tick)


class ActorTestCase(unittest.TestCase):
    """Test actor functionality"""

    def test_create_actor(self):
        actor.Actor(TestNotifier(), 0, 0, 'A', None)
