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
        self.actors = weakref.WeakValueDictionary()
        self.visible_actors = weakref.WeakValueDictionary()
        self.updated_actors = weakref.WeakValueDictionary()
        self.paused = False
        self.brush_stacks = {}
        self.run()

    def notify_created(self, actor):
        self.actors[actor.id] = actor

    def notify_visible(self, actor):
        if actor.visible:
            self.set_location_cache(actor)
            self.visible_actors[actor.id] = actor
        else:
            self.clear_location_cache(actor)
            if actor.id in self.visible_actors:
                del self.visible_actors[actor.id]

    def notify_moving(self, actor):
        self.clear_location_cache(actor)
        self.clear_actor(actor)

    def notify_moved(self, actor):
        self.set_location_cache(actor)

    def notify_updated(self, actor):
        self.set_location_cache(actor)
        self.updated_actors[actor.id] = actor

    def initialize(self, current):
        self.dirty = True
        self.scr.clear()
        self.bottom, self.right = self.scr.getmaxyx()
        self.actors_by_location = []
        for x in xrange(self.right):
            ylist = []
            for y in xrange(self.bottom):
                ylist.append([])
            self.actors_by_location.append(ylist)
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

    def try_move(self, actor, current, x, y):
        if self.paused:
            return False
        if (x < self.left or x + actor.hsize > self.right + 1 or
            y < self.top or y + actor.vsize > self.bottom + 1):
            return False
        for other in self.actors.itervalues():
            collisions = actor.collisions(other, x, y)
            collisions = collisions.intersection(other.collisions(actor))
            if other != actor and collisions:
                return self.collide(actor, other, current, collisions)
        return True

    def set_location_cache(self, actor):
        for xoffset in xrange(actor.hsize):
            for yoffset in xrange(actor.vsize):
                if ord(actor.get_ch(xoffset, yoffset)):
                    x = actor.x + xoffset
                    y = actor.y + yoffset
                    ref = weakref.ref(actor)
                    if ref not in self.actors_by_location[x][y]:
                        self.actors_by_location[x][y].append(ref)

    def clear_location_cache(self, actor):
        for xoffset in xrange(actor.hsize):
            for yoffset in xrange(actor.vsize):
                if ord(actor.get_ch(xoffset, yoffset)):
                    x = actor.x + xoffset
                    y = actor.y + yoffset
                    ref = weakref.ref(actor)
                    if ref in self.actors_by_location[x][y]:
                        self.actors_by_location[x][y].remove(ref)

    def get_char_at_loc(self, x, y, ignore=None):
        if self.actors_by_location[x][y]:
            for item in reversed(self.actors_by_location[x][y]):
                actor = item()
                if actor and actor != ignore and not actor.transparent:
                    return actor.get_ch(x - actor.x, y - actor.y)
        return self.BG_CHAR

    def get_colors_at_loc(self, x, y, ignore=None):
        fg = None
        bg = None
        for item in reversed(self.actors_by_location[x][y]):
            actor = item()
            if actor and actor != ignore:
                if actor.fg:
                    fg = actor.fg
                if actor.bg:
                    bg = actor.bg
            if fg and bg:
                return fg, bg
        if not fg:
            fg = self.DEFAULT_FG_COLOR
        if not bg:
            bg = self.DEFAULT_BG_COLOR
        return fg, bg

    def collide(self, actor, other, current, collisions):
        """Handle collision between actor and other.

        Return True to allow the movement."""
        return False

    def draw_actor(self, actor, xstart=0, ystart=0,
                   width=None, height=None, clear=False):
        """Draw an actor at location."""
        if width is None:
            width = actor.hsize - xstart
        if height is None:
            height = actor.vsize - ystart
        for xoffset in xrange(xstart, xstart + width):
            for yoffset in xrange(ystart, ystart + height):
                char = actor.get_ch(xoffset, yoffset)
                if ord(char):
                    x = actor.x + xoffset
                    y = actor.y + yoffset
                    if actor.transparent or clear:
                        old_char = self.get_char_at_loc(x, y, actor)
                        out = old_char.encode('utf-8')
                    else:
                        out = char.encode('utf-8')
                    fg, bg = None, None
                    if not actor.fg or not actor.bg:
                        fg, bg = self.get_colors_at_loc(x, y, actor)
                    if not clear:
                        fg = actor.fg or fg
                        bg = actor.bg or bg
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
            current = time.time()
            self.initialize(current)
            while True:
                self.process_input(current)
                if not self.paused:
                    self.tick(current)
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

    def tick(self, current):
        """Do frame actions."""
        pass

    def redraw(self, current):
        if self.dirty:
            self.scr.refresh()
            self.dirty = False

        for actor in self.updated_actors.itervalues():
            if actor.visible:
                self.draw_actor(actor)
        self.updated_actors = weakref.WeakValueDictionary()
