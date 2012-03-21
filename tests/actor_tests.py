# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright (c) 2012 Vishvananda Ishaya
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSEo2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.
"""
Tests for the jinxes actor module
"""

import unittest

import mox

from jinxes import actor


class FakeApp(object):
    def notify_created(self, actor):
        pass

    def notify_updated(self, actor):
        pass

    def notify_moved(self, actor):
        pass

    def notify_visible(self, actor):
        pass


class ActorTestCase(unittest.TestCase):
    """Test actor functionality.

    Mocks Application Object to verify interactions with the
    application object.
    """
    def setUp(self):
        super(ActorTestCase, self).setUp()
        self.mox = mox.Mox()
        self.app = FakeApp()

    def test_create_actor(self):
        app = self.mox.CreateMockAnything()
        app.notify_created(mox.IgnoreArg())
        app.notify_updated(mox.IgnoreArg())
        app.notify_visible(mox.IgnoreArg())
        self.mox.ReplayAll()
        actor.Actor(app, 0, 0, 'A')
        self.mox.VerifyAll()

    def test_hsize(self):
        display = 'o'
        actor1 = actor.Actor(FakeApp(), 0, 0, display)
        self.assertEqual(actor1.hsize, 1)
        display = 'oo\n'
        actor1 = actor.Actor(FakeApp(), 0, 0, display)
        self.assertEqual(actor1.hsize, 2)
        display = ('oo\n'
                   'ooo')
        actor1 = actor.Actor(FakeApp(), 0, 0, display)
        self.assertEqual(actor1.hsize, 3)
        display = ('ooo\n'
                   'oo')
        actor1 = actor.Actor(FakeApp(), 0, 0, display)
        self.assertEqual(actor1.hsize, 3)

    def test_vsize(self):
        display = 'o'
        actor1 = actor.Actor(FakeApp(), 0, 0, display)
        self.assertEqual(actor1.vsize, 1)
        display = ('o\n'
                   'o')
        actor1 = actor.Actor(FakeApp(), 0, 0, display)
        self.assertEqual(actor1.vsize, 2)
        display = ('oo\n'
                   'oo\n'
                  '\0o')
        actor1 = actor.Actor(FakeApp(), 0, 0, display)
        self.assertEqual(actor1.vsize, 3)
        display = ('oo\n'
                   'oo\n'
                   'o\0')
        actor1 = actor.Actor(FakeApp(), 0, 0, display)
        self.assertEqual(actor1.vsize, 3)
