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
from math import radians

import cairo
from gi.repository import Gtk, Gdk

from desmume.emulator import SCREEN_HEIGHT, SCREEN_WIDTH, DeSmuME, SCREEN_PIXEL_SIZE
from desmume.frontend.gtk_drawing_area_desmume import AbstractRenderer


class SoftwareRenderer(AbstractRenderer):
    def __init__(self, emu: DeSmuME):
        super().__init__(emu)
        self._upper_image = None
        self._lower_image = None
        self.decode_screen()

    def screen(self, base_w, base_h, ctx: cairo.Context, display_id: int):
        if display_id == 0:
            self.decode_screen()

        ctx.translate(base_w * self._scale / 2, base_h * self._scale / 2)
        ctx.rotate(-radians(self._screen_rotation_degrees))
        if self._screen_rotation_degrees == 90 or self._screen_rotation_degrees == 270:
            ctx.translate(-base_h * self._scale / 2, -base_w * self._scale / 2)
        else:
            ctx.translate(-base_w * self._scale / 2, -base_h * self._scale / 2)
        ctx.scale(self._scale, self._scale)
        if display_id == 0:
            ctx.set_source_surface(self._upper_image)
        else:
            ctx.set_source_surface(self._lower_image)
        ctx.get_source().set_filter(cairo.Filter.NEAREST)
        ctx.paint()

    def reshape(self, draw: Gtk.DrawingArea, display_id: int):
        pass

    def decode_screen(self):
        gpu_framebuffer = self._emu.display_buffer_as_rgbx()

        self._upper_image = cairo.ImageSurface.create_for_data(
            gpu_framebuffer[:SCREEN_PIXEL_SIZE*4], cairo.FORMAT_RGB24, SCREEN_WIDTH, SCREEN_HEIGHT
        )

        self._lower_image = cairo.ImageSurface.create_for_data(
            gpu_framebuffer[SCREEN_PIXEL_SIZE*4:], cairo.FORMAT_RGB24, SCREEN_WIDTH, SCREEN_HEIGHT
        )
