"""
It is 2020 and Glade still doesn't support passing anything but Glade-defined objects as user data.
The GTK2 C++ Glade frontend had a custom Glade "parser" that worked around this, but we don't.
So instead, enjoy this!
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
from gi.repository import Gtk


def widget_to_primitive(w: Gtk.Widget):
    name = Gtk.Buildable.get_name(w)
    if name.startswith("%d:"):
        return int(name[3:])
    elif name.startswith("%f:"):
        return float(name[3:])
    raise ValueError("Invalid widget for widget_to_primitive.")
