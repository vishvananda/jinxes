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
    locale.setlocale(locale.LC_ALL,"")
    curses.wrapper(application_class)


class Brush(int):
    """Boxed version of an int representing a curses brush.

    This allows us to use weak references to track whether a brush
    is still being used.
    """
    pass


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

    def __init__(self, scr):
        self.logger = logging.getLogger('jinxes')
        curses.curs_set(0)
        self.available_brush_ids = set(xrange(1, curses.COLOR_PAIRS))
        self.allocated_brush_ids = {}
        self.brushes = weakref.WeakValueDictionary()
        self.default_brush = self.get_brush(self.DEFAULT_FG_COLOR,
                                            self.DEFAULT_BG_COLOR)
        scr.bkgdset(ord(' '), self.default_brush)
        scr.nodelay(1)
        self.scr = scr
        self.actors = weakref.WeakValueDictionary()
        self.visible_actors = weakref.WeakValueDictionary()
        self.moved_actors = weakref.WeakValueDictionary()
        self.paused = False
        self.run()

    def notify_created(self, actor):
        self.actors[actor.id] = actor

    def notify_visible(self, actor):
        if actor.visible:
            self.visible_actors[actor.id] = self
        else:
            if actor.id in self.visible_actors:
                del self.visible_actors[actor.id]

    def notify_moving(self, actor):
        self.clear(actor.x, actor.y, actor.size)

    def notify_moved(self, actor):
        self.moved_actors[actor.id] = actor

    def initialize(self, current):
        self.dirty = True
        self.scr.clear()
        self.bottom, self.right = self.scr.getmaxyx()
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
        if (x < self.left or x > self.right or
            y < self.top or y > self.bottom):
            return False
        for other in self.actors.itervalues():
            collisions = actor.collisions(other, x, y)
            collisions = collisions.intersection(other.collisions(actor))
            if other != actor and collisions:
                return self.collide(actor, other, current, collisions)
        return True

    def collide(self, actor, other, current, collisions):
        """Handle collision between actor and other.

        Return True to allow the movement."""
        return False

    def draw(self, actor):
        """Draw an actor at location."""
        self.write(actor.x, actor.y, actor.utf8, actor.brush)

    def write(self, x, y, text, brush=None):
        """Write a text string at location with brush."""
        if not brush:
            brush = self.default_brush
        self.scr.addstr(y, x, text, brush)

    def clear(self, x, y, length=1, brush=None):
        """Clear the text at location."""
        self.write(x, y, ' ' * length, brush)

    def get_brush(self, fg_color=None, bg_color=None):
        """Get a brush represented by fg and bg color.

        This brush can be used in further curses calls.  Note that the brush
        is cached using a WeakRef and will be garbage collected if it is no
        longer being used. A brush could be overwritten even if it was used
        to draw something on the screen if the reference discarded and all
        other brush identifiers are used up. To ensure that a brush is not
        overwritten, simply store a reference to the brush.
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
            brush = Brush(curses.color_pair(int_id))
            self.allocated_brush_ids[str_id] = int_id
            self.brushes[str_id] = brush
        return self.brushes[str_id]

    def _collect_brushes(self):
        """Reclaim ids for brushes that are no longer being used."""
        for str_id in self.allocated_brush_ids.keys():
            if str_id not in self.brushes:
                int_id = self.allocated_brush_ids[str_id]
                self.available_brush_ids.append(int_id)
                del self.allocated_brush_ids[str_id]


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

        for actor in self.moved_actors.itervalues():
            if actor.visible:
                self.draw(actor)
        self.moved_actors = weakref.WeakValueDictionary()


