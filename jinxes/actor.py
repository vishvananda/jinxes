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

    def __init__(self, app, x, y, display, current=None,
                 fg=None, bg=None, inverted=False):
        self.id = unicode(uuid.uuid4())
        self.app = app
        self.z = 0
        self._x = x
        self._y = y
        self._frame = 0.0
        self.fg = fg
        self.bg = bg
        self.inverted = inverted
        self.transparent = False
        self.bordered = False
        self.frame_rate = 30.0
        self.xvel = 0.0
        self.yvel = 0.0
        self.collides = True
        self.display = display
        self.updated = current
        self.visible = True
        self.app.notify_created(self)

    def __cmp__(self, other):
        if not other:
            return -1
        result = cmp(self.z, other.z)
        if result:
            return result
        return cmp(self.id, other.id)

    @property
    def x(self):
        return int(self._x)

    @property
    def y(self):
        return int(self._y)

    @property
    def frame(self):
        return int(self._frame)

    def _get_display(self):
        frame = self._display[self.frame]
        out = []
        for line in frame:
            out.append([char[0] for char in line])
        return out

    def _set_display(self, display):
        if not isinstance(display, list):
            display = [display]
        self._display = []
        for frame in display:
            if isinstance(frame, basestring):
                frame = frame.split('\n')
            outframe = []
            for line in frame:
                outline = []
                for char in line:
                    if len(char) == 1:
                        char = (char, self.fg, self.bg, self.inverted)
                    outline.append(char)
                outframe.append(outline)
            self._display.append(outframe)
        self.frames = len(self._display)
        self.hsize = max(len(line) for line in self._display[0])
        self.vsize = len(self._display[0])

    display = property(_get_display, _set_display)

    def get_ch(self, x, y):
        try:
            return self._display[self.frame][y][x]
        except IndexError:
            return ('\0', None, None, self.inverted)

    def tick(self, current, delta):
        oldframe = self.frame
        newframe = self._frame + delta * self.frame_rate
        while newframe >= self.frames:
            newframe -= self.frames
        if oldframe != int(newframe):
            self.animate(current, newframe)
        else:
            self._frame = newframe
        oldx, oldy = self.x, self.y
        newx = self._x + delta * self.xvel
        newy = self._y + delta * self.yvel
        if oldx != int(newx) or oldy != int(newy):
            self.move(current, newx, newy)
        else:
            self._x = newx
            self._y = newy


    def animate(self, current, frame):
        self.app.notify_animating(self)
        self._frame = frame
        self.updated = current
        self.app.notify_animated(self)

    def move(self, current, x, y):
        x, y = self.app.try_move(self, current, x, y)
        if x is not None or y is not None:
            self.app.notify_moving(self)
            if x is not None:
                self._x = x
            if y is not None:
                self._y = y
            self.moved = current
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
                if ord(self.get_ch(x, y)[0]):
                    coords.append((x + xoffset, y + yoffset))
        return set(coords)

    def destroy(self):
        self.app.notify_destroyed(self)
