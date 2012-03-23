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
import weakref


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
        scr.bkgdset(ord(self.BG_CHAR), self.default_brush)
        scr.nodelay(1)
        self.scr = scr
        self.actors = {}
        self.paused = False
        self.brush_stacks = {}
        self.run()

    def notify_created(self, actor):
        self.actors[actor.id] = actor

    def notify_destroyed(self, actor):
        self.clear_location_cache(actor)
        del self.actors[actor.id]

    def notify_visible(self, actor):
        if actor.visible:
            self.set_location_cache(actor)
        else:
            self.clear_location_cache(actor)

    def notify_moving(self, actor):
        pass
        self.clear_location_cache(actor)

    def notify_animating(self, actor):
        pass
        self.clear_location_cache(actor)

    def notify_moved(self, actor):
        pass

    def notify_animated(self, actor):
        pass

    def notify_updated(self, actor):
        self.set_location_cache(actor)

    def initialize(self, current):
        self.dirty = True
        self.scr.clear()
        self.bottom, self.right = self.scr.getmaxyx()
        self.actors_by_location = {}
        for x in xrange(self.right):
            for y in xrange(self.bottom):
                self.actors_by_location[(x, y)] = []
        self.dirty_by_location = {}
        self.top = 0
        self.left = 0
        self.bottom -= 1
        self.right -= 1

    def border(self):
        self.scr.border()
        self.top += 1
        self.left += 1
        self.bottom -= 1
        self.right -= 1

    def try_move(self, actor, current, floatx, floaty):
        x = int(floatx)
        y = int(floaty)
        xvel, yvel = None, None
        if actor.bordered:
            if x < self.left:
                floatx = -floatx
                xvel = -xvel
            elif x + actor.hsize >= self.right:
                floatx = floatx - (floatx - self.right)
                xvel = -xvel
            if y < self.top:
                floaty = -floaty
                yvel = -yvel
            elif y + actor.vsize >= self.bottomx:
                floaty = floaty - (floaty - self.bottom)
                yvel = -yvel
        if xvel:
            actor.xvel = xvel
        if yvel:
            actor.xvel = yvel
        if actor.collides:
            for other in self.actors.itervalues():
                if not other.collides:
                    continue
                collisions = actor.collisions(other, x, y)
                collisions = collisions.intersection(other.collisions(actor))
                if other != actor and collisions:
                    return self.collide(actor, other, current,
                                        collisions, floatx, floaty)
        return floatx, floaty

    def set_location_cache(self, actor):
        for xoffset in xrange(actor.hsize):
            for yoffset in xrange(actor.vsize):
                if ord(actor.get_ch(xoffset, yoffset)[0]):
                    x = actor.x + xoffset
                    y = actor.y + yoffset
                    if (x >= 0 and x < self.right
                        and y >= 0 and y < self.bottom):
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
                    x = actor.x + xoffset
                    y = actor.y + yoffset
                    if (x >= 0 and x < self.right
                        and y >= 0 and y < self.bottom):
                        self.dirty_by_location[(x, y)] = True
                        if actor in self.actors_by_location[(x, y)]:
                            self.actors_by_location[(x, y)].remove(actor)

    def get_char_at_loc(self, x, y, ignore=None):
        for actor in reversed(self.actors_by_location[(x, y)]):
            if actor and actor != ignore and not actor.transparent:
                char = actor.get_ch(x - actor.x, y - actor.y)[0]
                if ord(char):
                    return char, actor
        return self.BG_CHAR, None

    def get_colors_at_loc(self, x, y, ignore=None):
        fg = None
        bg = None
        for actor in reversed(self.actors_by_location[(x, y)]):
            if actor and actor != ignore:
                _ch, fg, bg, inverted = actor.get_ch(x - actor.x, y - actor.y)
                if inverted:
                    fg, bg = bg, fg
            if fg and bg:
                return fg, bg
        if not fg:
            fg = self.DEFAULT_FG_COLOR
        if not bg:
            bg = self.DEFAULT_BG_COLOR
        return fg, bg

    def draw_location(self, x, y):
        ch, fg, bg = None, None, None
        for actor in reversed(self.actors_by_location[(x, y)]):
            if actor:
                c, f, b, inv = actor.get_ch(x - actor.x, y - actor.y)
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
        if fg == self.DEFAULT_BG_COLOR:
            raise Exception()

        self.write(x, y, ch, fg, bg)

    def collide(self, actor, other, current, collisions, floatx, floaty):
        """Handle collision between actor and other.

        Return floatx, floaty to allow the movement."""
        return floatx, floaty

    def draw_actor(self, actor, xstart=0, ystart=0,
                   width=None, height=None, clear=False):
        """Draw an actor at location."""
        if width is None:
            width = actor.hsize - xstart
        if height is None:
            height = actor.vsize - ystart
        for xoffset in xrange(xstart, xstart + width):
            for yoffset in xrange(ystart, ystart + height):
                char, fg, bg, inverted = actor.get_ch(xoffset, yoffset)
                if clear:
                    fg, bg = None, None
                x = actor.x + xoffset
                y = actor.y + yoffset
                if (x >= 0 and x <= self.right
                    and y >= 0 and y <= self.bottom
                    and ord(char)):
                    old_char, other = self.get_char_at_loc(x, y, actor)
                    if other and other > actor:
                        continue
                    elif actor.transparent or clear:
                        out = old_char.encode('utf-8')
                    else:
                        out = char.encode('utf-8')
                    if not fg or not bg:
                        oldfg, oldbg = self.get_colors_at_loc(x, y, actor)
                    fg = fg or oldfg
                    bg = bg or oldbg
                    if inverted and not clear:
                        fg, bg = bg, fg
                    self.write(x, y, out, fg, bg)

    def clear_actor(self, actor):
        """Draw an actor at location."""
        self.draw_actor(actor, clear=True)


    def write(self, x, y, text, fg, bg):
        """Write a text string at location with brush."""
        brush = self.get_brush(fg, bg)
        try:
            self.scr.addstr(y, x, text, brush)
        except curses.error:
            if x == self.right and y == self.bottom:
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
        for x in xrange(self.right):
            for y in xrange(self.bottom):
                fg, bg = self.get_colors_at_loc(x, y)
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
        if self.dirty:
            self.scr.refresh()
            self.dirty = False

        for (x, y) in self.dirty_by_location.iterkeys():
            self.draw_location(x, y)
        self.dirty_by_location = {}
