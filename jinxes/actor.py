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
                 fg=None, bg=None, inverted=False, z=0):
        self.id = unicode(uuid.uuid4())
        self.app = app
        self._frame = 0.0
        self.fg = fg
        self.bg = bg
        self.inverted = inverted
        self.transparent = False
        self.bordered = True
        self.frame_rate = 30.0
        self.xvel = 0.0
        self.yvel = 0.0
        self.collides = True
        self.display = display
        self.x = x
        self.y = y
        self.z = z
        self.app.notify_created(self)
        self.updated = current
        self.visible = True

    def __cmp__(self, other):
        if not other:
            return -1
        result = cmp(self.z, other.z)
        if result:
            return result
        return cmp(self.id, other.id)

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
        newx = self.x + delta * self.xvel
        newy = self.y + delta * self.yvel
        self.move(current, newx, newy)


    def animate(self, current, frame):
        self.app.notify_animating(self)
        self._frame = frame
        self.updated = current
        self.app.notify_animated(self)

    def move(self, current, x, y):
        x, y = self.app.try_move(self, current, x, y)
        screenx = self.app.project_x(x, self.hsize)
        screeny = self.app.project_y(y, self.vsize)
        if self.screenx != screenx or self.screeny != screeny:
                self.app.notify_moving(self)
                self.x = x
                self.y = y
                self.moved = current
                self.updated = current
                self.app.notify_moved(self)
        else:
            self.x = x
            self.y = y

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

    def _get_x(self):
        return self._x

    def _set_x(self, value):
        self._x = value
        self.screenx = self.app.project_x(self._x, self.hsize)

    x = property(_get_x, _set_x)

    def _get_y(self):
        return self._y

    def _set_y(self, value):
        self._y = value
        self.screeny = self.app.project_y(self._y, self.vsize)

    y = property(_get_y, _set_y)

    def collisions(self, x=None, y=None):
        """Returns a set of coordinates to check for collisions.

        We optionally pass x and y to support checking collisions
        on potential locations"""
        if x is None:
            x = self.screenx
        if y is None:
            y = self.screeny
        coords = []
        for xoffset in xrange(self.hsize):
            for yoffset in xrange(self.vsize):
                if ord(self.get_ch(xoffset, yoffset)[0]):
                    coords.append((x + xoffset, y + yoffset))
        return set(coords)

    def destroy(self):
        self.app.notify_destroyed(self)
