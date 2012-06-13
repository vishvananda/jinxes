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
Application classes for the jinxes library
"""


import curses
import locale
import logging
import time


def run(application_class):
    """Run a jinxes application subclass."""
    locale.setlocale(locale.LC_ALL, "")
    curses.wrapper(application_class)


class Exit(Exception):
    """Raise this exception to exit the main application loop."""
    pass


class Application(object):
    """Interactive Curses Application Class

    Abstracts and simplifies curses related calls for input and
    output processing.
    """
    DEFAULT_FG_COLOR = 4
    DEFAULT_BG_COLOR = 16
    BG_CHAR = ' '

    def __init__(self, scr):
        self.logger = logging.getLogger('jinxes')
        curses.curs_set(0)
        self.available_brush_ids = set(xrange(1, curses.COLOR_PAIRS))
        self.allocated_brush_ids = {}
        self.brushes = {}
        self.default_brush = self.get_brush(self.DEFAULT_FG_COLOR,
                                            self.DEFAULT_BG_COLOR)
        scr.nodelay(1)
        self.scr = scr
        scr.bkgdset(ord(self.BG_CHAR), self.default_brush)
        self.actors = {}
        self.paused = False
        self.brush_stacks = {}
        self._border = False
        self.run()

    def notify_created(self, actor):
        self.actors[actor.id] = actor

    def notify_destroyed(self, actor):
        self.clear_location_cache(actor)
        try:
            del self.actors[actor.id]
        except KeyError:
            pass

    def notify_visible(self, actor):
        if actor.visible:
            self.set_location_cache(actor)
        else:
            self.clear_location_cache(actor)

    def notify_moving(self, actor):
        self.clear_location_cache(actor)

    def notify_animating(self, actor):
        self.clear_location_cache(actor)

    def notify_moved(self, actor):
        pass

    def notify_animated(self, actor):
        pass

    def notify_updated(self, actor):
        self.set_location_cache(actor)

    def initialize(self, current):
        self.height, self.width = self.scr.getmaxyx()
        self.top = 0
        self.left = 0
        self.actors_by_location = {}
        for x in xrange(self.width):
            for y in xrange(self.height):
                self.actors_by_location[(x, y)] = []
        self.dirty_by_location = {}
        self.win = curses.newwin(0, 0, 0, 0)
        self.win.bkgd(ord(self.BG_CHAR), self.default_brush)

    def border(self):
        self._border = True
        self.top += 1
        self.left += 1
        self.width -= 2
        self.height -= 2

    def project(self, actor, x=None, y=None):
        """Project actor center into top/left app coordinates
           left, top = 0, 0
           +---+ > 0.0f = (edge of the screen)
           |x  | <- 0.00f - 0.33f = 0
           | o |  <- 0.33f - 0.66f = 1
           |  x|   <- 0.66f - 1.00f = 2
           +---+ > 1.0f = 3 (edge of the screen)
           right, bottom = 2, 2
           width, height = 3, 3
        """
        if x is None:
            x = actor.x
        if y is None:
            y = actor.y
        # find the actor's top left corner
        left = x - actor.hsize * 0.5 / self.width
        top = y - actor.vsize * 0.5 / self.height
        # move x,y for top left into integer coordintates
        x = int(left * self.width + 0.5) + self.left
        y = int(top * self.height + 0.5) + self.top
        return x, y

    @property
    def x1(self):
        return 1.0 / self.width

    @property
    def y1(self):
        return 1.0 / self.height

    def try_move(self, actor, current, floatx, floaty):
        if actor.bordered:
            halfh = actor.hsize * 0.5 / self.width
            halfv = actor.vsize * 0.5 / self.height
            left = 0.0
            top = 0.0
            right = 1.0
            bottom = 1.0
            if floatx < left + halfh:
                if actor.xvel:
                    floatx = (left + halfh) * 2 - floatx
                    actor.xvel = -actor.xvel
                else:
                    floatx = left + halfh
            elif floatx > right - halfh:
                if actor.xvel:
                    floatx = (right - halfh) * 2 - floatx
                    actor.xvel = -actor.xvel
                else:
                    floatx = right - halfh
            if floaty < top + halfv:
                if actor.yvel:
                    floaty = (top + halfv) * 2 - floaty
                    actor.yvel = -actor.yvel
                else:
                    floaty = top + halfv
            elif floaty > bottom - halfv:
                if actor.yvel:
                    floaty = (bottom - halfv) * 2 - floaty
                    actor.yvel = -actor.yvel
                else:
                    floaty = bottom - halfv
        x, y = self.project(actor, floatx, floaty)
        if actor.collides:
            actor_collisions = actor.collisions(x, y)
            all_collisions = {}
            for x, y in actor_collisions:
                try:
                    others = self.actors_by_location[(x, y)]
                except KeyError:
                    continue
                for other in others:
                    if other == actor:
                        continue
                    if not other.collides:
                        continue
                    all_collisions.setdefault(other, []).append((x, y))
            for other, collisions in all_collisions.iteritems():
                if not self.collide(actor, other, current,
                                    collisions, floatx, floaty):
                    return actor.x, actor.y
        return floatx, floaty

    def set_location_cache(self, actor):
        for xoffset in xrange(actor.hsize):
            for yoffset in xrange(actor.vsize):
                if ord(actor.get_ch(xoffset, yoffset)[0]):
                    screenx, screeny = self.project(actor)
                    x = screenx + xoffset
                    y = screeny + yoffset
                    if (x >= self.left and x < self.left + self.width
                        and y >= self.top and y < self.top + self.height):
                        self.dirty_by_location[(x, y)] = True
                        if actor not in self.actors_by_location[(x, y)]:
                            actors = list(self.actors_by_location[(x, y)])
                            for i, other in enumerate(actors):
                                if actor < other:
                                    break
                            else:
                                self.actors_by_location[(x, y)].append(actor)
                                continue
                            self.actors_by_location[(x, y)].insert(i, actor)

    def clear_location_cache(self, actor):
        for xoffset in xrange(actor.hsize):
            for yoffset in xrange(actor.vsize):
                if ord(actor.get_ch(xoffset, yoffset)[0]):
                    screenx, screeny = self.project(actor)
                    x = screenx + xoffset
                    y = screeny + yoffset
                    if (x >= self.left and x < self.left + self.width
                        and y >= self.top and y < self.top + self.height):
                        self.dirty_by_location[(x, y)] = True
                        if actor in self.actors_by_location[(x, y)]:
                            self.actors_by_location[(x, y)].remove(actor)

    def get_location(self, x, y):
        ch, fg, bg = None, None, None
        for actor in reversed(self.actors_by_location[(x, y)]):
            if actor:
                screenx, screeny = self.project(actor)
                c, f, b, inv = actor.get_ch(x - screenx, y - screeny)
                if inv:
                    f, b = b, f
                if ch is None and ord(c) and not actor.transparent:
                    ch = c.encode('utf-8')
                if fg is None:
                    fg = f
                if bg is None:
                    bg = b
                if ch is not None and fg is not None and bg is not None:
                    break

        ch = ch or self.BG_CHAR
        fg = fg or self.DEFAULT_FG_COLOR
        bg = bg or self.DEFAULT_BG_COLOR
        return ch, fg, bg

    def collide(self, actor, other, current, collisions, floatx, floaty):
        """Handle collision between actor and other.

        Return floatx, floaty to allow the movement."""
        return floatx, floaty

    def write(self, x, y, text, fg, bg):
        """Write a text string at location with brush."""
        brush = self.get_brush(fg, bg)
        try:
            self.win.addstr(y, x, text, brush)
        except curses.error:
            if x == self.width - 1 and y == self.height - 1:
                pass

    def get_brush(self, fg_color=None, bg_color=None):
        """Get a brush represented by fg and bg color.

        This brush can be used in further curses calls.  Note that the brush
        is and will be garbage collected if we run out of brushes and it is
        no longer needed.
        """
        if not fg_color:
            fg_color = self.DEFAULT_FG_COLOR
        if not bg_color:
            bg_color = self.DEFAULT_BG_COLOR
        str_id = '%s:%s' % (fg_color, bg_color)
        if not self.brushes.get(str_id):
            try:
                int_id = self.available_brush_ids.pop()
            except KeyError:
                self._collect_brushes()
                try:
                    int_id = self.available_brush_ids.pop()
                except KeyError:
                    raise Exception('out of brushes')
            curses.init_pair(int_id, fg_color, bg_color)
            brush_id = curses.color_pair(int_id)
            self.allocated_brush_ids[str_id] = int_id
            self.brushes[str_id] = brush_id
        return self.brushes[str_id]

    def _collect_brushes(self):
        """Reclaim ids for brushes that are no longer being used."""
        used_brushes = set(['%s:%s' % (self.DEFAULT_FG_COLOR,
                                       self.DEFAULT_BG_COLOR)])
        for x in xrange(self.width):
            for y in xrange(self.height):
                ch, fg, bg = self.get_location(x, y)
                used_brushes.add('%s:%s' % (fg, bg))
        for str_id in self.allocated_brush_ids.keys():
            if str_id not in used_brushes:
                int_id = self.allocated_brush_ids[str_id]
                self.available_brush_ids.append(int_id)
                del self.allocated_brush_ids[str_id]
                del self.brushes[str_id]

    def run(self):
        """Endless processing loop."""
        try:
            updated = current = time.time()
            self.initialize(current)
            while True:
                self.process_input(current)
                if not self.paused:
                    delta = current - updated
                    self.tick(current, delta)
                    updated = current
                self.redraw(current)
                current = time.time()
        except (Exit, KeyboardInterrupt):
            pass

    def process_input(self, current):
        """Input processing."""
        character = self.scr.getch()
        if character != curses.ERR:
            self.process_character(current, character)

    def process_character(self, current, character):
        """Delegate character to method."""
        if character == curses.KEY_RESIZE:
            method_name = 'handle_resize'
        else:
            try:
                method_name = 'handle_%c' % character
            except OverflowError:
                return
        method = getattr(self, method_name, None)
        if method:
            method(current)

    def tick(self, current, delta):
        """Do frame actions."""
        for key in list(self.actors.iterkeys()):
            actor = self.actors[key]
            actor.tick(current, delta)

    def redraw(self, current):
        for (x, y) in self.dirty_by_location.iterkeys():
            ch, fg, bg = self.get_location(x, y)
            self.write(x, y, ch, fg, bg)
        if len(self.dirty_by_location):
            self.dirty_by_location = {}
            if self._border:
                self.win.border()
            self.win.refresh()
