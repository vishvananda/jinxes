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
Actor Class for jinxes library
"""

import uuid


class Actor(object):

    def __init__(self, app, x, y, text, brush, moved=None):
        self.app = app
        self.x = x
        self.y = y
        self.text = text
        self.brush = brush
        self.id = unicode(uuid.uuid4())
        self.app.notify_created(self)
        self.moved = moved
        self.visible = True

    @property
    def size(self):
        return len(self.text)

    @property
    def utf8(self):
        return self.text.encode('utf_8')

    def move(self, current, x, y):
        if self.app.try_move(self, current, x, y):
            self.app.notify_moving(self)
            self.x = x
            self.y = y
            self.moved = current

    def _get_visible(self):
        return self._visible

    def _set_visible(self, value):
        self._visible = value
        self.app.notify_visible(self)

    visible = property(_get_visible, _set_visible)

    def _get_moved(self):
        return self._moved

    def _set_moved(self, value):
        self._moved = value
        self.app.notify_moved(self)

    moved = property(_get_moved, _set_moved)

    def collisions(self, other, x=None, y=None):
        """Returns a set of coordinates to check for collisions.

        We pass other to allow Actors to have different collision
        patterns with different types of actors.

        We optionally pass x and y to support checking collisions
        on potential locations"""
        if x is None:
            x = self.x
        if y is None:
            y = self.y
        coords = []
        for offset in xrange(self.size):
            coords.append((x + offset, y))
        return set(coords)
