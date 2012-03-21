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
Misc utilities for jinxes library
"""


def rgb_to_color(red, green, blue):
    return 16 + red * 36 + green * 6 + blue


def color_to_rgb(color):
    if color >= 232:
        return [0, 0, 0]
    color = color - 16
    components = []
    for x in xrange(3):
        components.append(color % 6)
        color /= 6
    components.reverse()
    return components


def grey_to_color(grey):
    return grey + 232


def color_to_grey(grey):
    return grey - 232

