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
from typing import Dict, Optional, List

from gi.repository import Gtk, Gdk

from desmume.controls import key_names, Keys, key_names_localized
from desmume.frontend.widget_to_primitive import widget_to_primitive


class KeyboardControlsDialogController:
    """This dialog shows the keyboard controls."""
    def __init__(self, parent_window: Gtk.Window):
        path = os.path.abspath(os.path.dirname(__file__))
        # SkyTemple translation support
        try:
            from skytemple.core.ui_utils import make_builder
            self.builder = make_builder(os.path.join(path, "PyDeSmuMe_controls.glade"))
        except ImportError:
            self.builder = Gtk.Builder()
            self.builder.add_from_file(os.path.join(path, "PyDeSmuMe_controls.glade"))
        self.window: Gtk.Window = self.builder.get_object('wKeybConfDlg')
        self.window.set_transient_for(parent_window)
        self.window.set_attached_to(parent_window)
        self._keyboard_cfg: Optional[List[int]] = None
        self._tmp_key = None
        self.builder.connect_signals(self)

    def run(self, keyboard_cfg: List[int]) -> Optional[List[int]]:
        """Configure the keyboard configuration provided using the dialog,
        returns the new keyboard config if changed, else None."""
        self._keyboard_cfg = keyboard_cfg.copy()
        for i in range(0, Keys.NB_KEYS):
            b = self.builder.get_object(f"button_{key_names[i]}")
            b.set_label(f"{key_names_localized[i]} : {Gdk.keyval_name(self._keyboard_cfg[i])}")
        response = self.window.run()

        self.window.hide()
        if response == Gtk.ResponseType.OK:
            return self._keyboard_cfg

    # KEYBOARD CONFIG / KEY DEFINITION
    def on_wKeyDlg_key_press_event(self, widget: Gtk.Widget, event: Gdk.EventKey, *args):
        self._tmp_key = event.keyval
        self.builder.get_object("label_key").set_text(Gdk.keyval_name(self._tmp_key))
        return True

    def on_button_kb_key_clicked(self, w, *args):
        key = widget_to_primitive(w)
        dlg = self.builder.get_object("wKeyDlg")
        key -= 1  # key = bit position, start with
        self._tmp_key = self._keyboard_cfg[key]
        self.builder.get_object("label_key").set_text(Gdk.keyval_name(self._tmp_key))
        if dlg.run() == Gtk.ResponseType.OK:
            self._keyboard_cfg[key] = self._tmp_key
            self.builder.get_object(f"button_{key_names[key]}").set_label(f"{key_names_localized[key]} : {Gdk.keyval_name(self._tmp_key)}")

        dlg.hide()

    # Joystick configuration / Key definition
    def on_button_joy_key_clicked(self, w, *args):
        pass  # not part of this

    def gtk_widget_hide_on_delete(self, w: Gtk.Widget, *args):
        w.hide_on_delete()
        return True
