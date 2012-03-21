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

    def __init__(self, app, x, y, lines, updated=None, fg=None, bg=None):
        self.app = app
        self.x = x
        self.y = y
        self.lines = lines
        self.fg = fg
        self.bg = bg
        self.id = unicode(uuid.uuid4())
        self.app.notify_created(self)
        self.updated = updated
        self.visible = True
        self.transparent = False

    def _get_lines(self):
        return self._lines

    def _set_lines(self, value):
        if isinstance(value, basestring):
            self._lines = value.split('\n')
        else:
            self._lines = value
        self.hsize = max(len(line) for line in self.lines)
        self.vsize = len(self.lines)

    lines = property(_get_lines, _set_lines)

    def move(self, current, x, y):
        if self.app.try_move(self, current, x, y):
            self.app.notify_moving(self)
            self.x = x
            self.y = y
            self.updated = current
            self.app.notify_moved(self)

    def _get_visible(self):
        return self._visible

    def _set_visible(self, value):
        if value != getattr(self, '_visible', None):
            self._visible = value
            self.app.notify_visible(self)

    visible = property(_get_visible, _set_visible)

    def _get_updated(self):
        return self._updated

    def _set_updated(self, value):
        self._updated = value
        self.app.notify_updated(self)

    updated = property(_get_updated, _set_updated)

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
        for xoffset in xrange(self.hsize):
            for yoffset in xrange(self.vsize):
                if ord(self.lines[yoffset][xoffset]):
                    coords.append((x + xoffset, y + yoffset))
        return set(coords)
