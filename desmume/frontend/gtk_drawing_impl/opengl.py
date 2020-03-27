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
import cairo
from gi.repository import Gtk

from desmume.frontend.gtk_drawing_area_desmume import AbstractRenderer


class OpenGLRenderer(AbstractRenderer):
    def init(self):
        pass  # todo

    def screen(self, base_w, base_h, ctx: cairo.Context, display_id: int):
        pass  # todo

    def reshape(self, draw: Gtk.DrawingArea, display_id: int):
        pass  # todo
