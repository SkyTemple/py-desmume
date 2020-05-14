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

import os

import gi

from desmume.emulator import DeSmuME
from desmume.frontend.controller import MainController

gi.require_version('Gtk', '3.0')

from gi.repository import Gtk, GLib
from gi.repository.Gtk import Window


def main():
    path = os.path.abspath(os.path.dirname(__file__))

    # Load desmume
    emu = DeSmuME()

    # Init joysticks
    emu.input.joy_init()

    # Load Builder and Window
    builder = Gtk.Builder()
    builder.add_from_file(os.path.join(path, "PyDeSmuMe.glade"))
    main_window: Window = builder.get_object("wMainW")
    main_window.set_role("PyDeSmuME")
    GLib.set_application_name("PyDeSmuME")
    GLib.set_prgname("pydesmume")
    # TODO: Deprecated but the only way to set the app title on GNOME...?
    main_window.set_wmclass("PyDeSmuME", "PyDeSmuME")

    # Load main window + controller
    MainController(builder, main_window, emu)

    main_window.present()
    Gtk.main()
    del emu

    # Uninit SDL
    # TODO


if __name__ == '__main__':
    # TODO: At the moment the demo frontend doesn't support any cli arguments.
    main()
