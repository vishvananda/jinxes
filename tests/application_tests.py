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
Tests for the jinxes application module
"""

import curses
import locale
import unittest

import mox

from jinxes import application


class TestApp(application.Application):
    """Test app which supports dynamic method setting on init."""
    def __init__(self, scr, **kwargs):
        for key, value in kwargs.iteritems():
            setattr(self, key, value)
        super(TestApp, self).__init__(scr)


class CursesTestCase(unittest.TestCase):
    """Tests usage of curses and scr."""
    def setUp(self):
        super(CursesTestCase, self).setUp()
        self.mox = mox.Mox()

    def tearDown(self):
        super(CursesTestCase, self).tearDown()
        application.curses = curses
        application.locale = locale

    def test_run_curses(self):

        class FakeApp(application.Application):
            def run():
                pass

        application.locale = self.mox.CreateMockAnything()
        application.curses = self.mox.CreateMockAnything()
        scr = FakeScr()
        application.locale.LC_ALL = locale.LC_ALL
        application.locale.setlocale(locale.LC_ALL, "")
        application.curses.wrapper(FakeApp)
        self.mox.ReplayAll()
        application.run(FakeApp)
        self.mox.VerifyAll()

    def test_create_curses(self):

        def run():
            pass

        application.curses = self.mox.CreateMockAnything()
        scr = self.mox.CreateMockAnything()

        application.curses.COLOR_PAIRS = 10
        application.curses.curs_set(0)
        application.curses.init_pair(1, mox.IgnoreArg(), mox.IgnoreArg())
        application.curses.color_pair(1).AndReturn(1)
        scr.bkgdset(ord(' '), 1)
        scr.nodelay(1)
        self.mox.ReplayAll()
        TestApp(scr, run=run)
        self.mox.VerifyAll()


class FakeCurses(object):
    """Fake implementation of curses which does nothing."""
    COLOR_PAIRS = 10
    ERR = curses.ERR

    def curs_set(self, value):
        pass

    def init_pair(self, int_id, fg_color, bg_color):
        pass

    def color_pair(self, int_id):
        return int_id


class FakeScr(object):
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


class ApplicationTestCase(unittest.TestCase):
    """Test application methods.

    Fakes Curses and Screen to focus on app functionality.
    """

    def setUp(self):
        super(ApplicationTestCase, self).setUp()
        application.curses = FakeCurses()
        self.scr = FakeScr()

    def tearDown(self):
        super(ApplicationTestCase, self).tearDown()
        application.curses = curses

    def test_create(self):

        def run():
            pass
        TestApp(self.scr, run=run)

    def test_exit(self):

        def tick(current):
            raise application.Exit()
        TestApp(self.scr, tick=tick)