"""
Code for rendering the emulator on a Gtk DrawingArea. Feel free to use this in your own implementations!
Uses the OpenGL screen texture if possible, otherwise renders via Software.
"""
#  Copyright 2020 Marco Köpcke (Parakoopa)
#
#  This file is part of py-desmume.
#
#  py-desmume is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  py-desmume is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with py-desmume.  If not, see <https://www.gnu.org/licenses/>.
from abc import ABC, abstractmethod

import gi

gi.require_version('Gtk', '3.0')

import cairo
from gi.repository import Gtk

from desmume.emulator import DeSmuME


class AbstractRenderer(ABC):
    def __init__(self, emu: DeSmuME):
        self._emu = emu
        self._screen_rotation_degrees = 0
        self._scale = 1.0

    @classmethod
    def impl(cls, emu: DeSmuME) -> 'AbstractRenderer':
        from desmume.frontend.gtk_drawing_impl.opengl import OpenGLRenderer
        from desmume.frontend.gtk_drawing_impl.software import SoftwareRenderer
        # TODO: Implement OpenGL renderer
        if False and emu.has_opengl():
            return OpenGLRenderer(emu)
        else:
            return SoftwareRenderer(emu)

    @abstractmethod
    def init(self):
        pass

    @abstractmethod
    def screen(self, base_w, base_h, ctx: cairo.Context, display_id: int):
        pass

    @abstractmethod
    def reshape(self, draw: Gtk.DrawingArea, display_id: int):
        pass

    def set_scale(self, value):
        self._scale = value

    def get_scale(self):
        return self._scale

    def get_screen_rotation(self):
        return self._screen_rotation_degrees

    def set_screen_rotation(self, value):
        self._screen_rotation_degrees = value
