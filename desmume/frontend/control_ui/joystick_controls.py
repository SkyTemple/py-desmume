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
import gettext
import os
from typing import Dict, Optional, List

from gi.repository import Gtk, Gdk

from desmume.controls import key_names, Keys, key_names_localized
from desmume.emulator import DeSmuME_Input
from desmume.frontend.widget_to_primitive import widget_to_primitive
from desmume.i18n_util import _


class JoystickControlsDialogController:
    """This dialog shows the joystick controls."""
    def __init__(self, parent_window: Gtk.Window):
        path = os.path.abspath(os.path.dirname(__file__))
        # SkyTemple translation support
        try:
            from skytemple.core.ui_utils import make_builder
            self.builder = make_builder(os.path.join(path, "PyDeSmuMe_controls.glade"))
        except ImportError:
            self.builder = Gtk.Builder()
            self.builder.add_from_file(os.path.join(path, "PyDeSmuMe_controls.glade"))
        self.window: Gtk.Window = self.builder.get_object('wJoyConfDlg')
        self.window.set_transient_for(parent_window)
        self.window.set_attached_to(parent_window)
        self._joystick_cfg: Optional[List[int]] = None
        self._emulator_input: DeSmuME_Input = None
        self.builder.connect_signals(self)

    def run(self,
            joystick_cfg: List[int],
            emulator_input: DeSmuME_Input,
            emulator_is_running: bool
            ) -> List[int]:
        """Configure the joystick configuration provided using the dialog,
        is is immediately changed in the debugger The new/old (if canceled) config is also returned."""
        self._joystick_cfg = joystick_cfg
        self._emulator_input = emulator_input
        if self._emulator_input.joy_number_connected() < 1 or emulator_is_running:
            if self._emulator_input.joy_number_connected() < 1:
                text = _("You don't have any joypads!")
            else:
                text = _("Can't configure joystick while the game is running!")

            md = Gtk.MessageDialog(None,
                                   Gtk.DialogFlags.DESTROY_WITH_PARENT | Gtk.DialogFlags.MODAL, Gtk.MessageType.ERROR,
                                   Gtk.ButtonsType.OK, text,
                                   title="Error!")
            md.set_position(Gtk.WindowPosition.CENTER)
            md.run()
            md.destroy()
        else:
            for i in range(0, Keys.NB_KEYS):
                b = self.builder.get_object(f"button_joy_{key_names[i]}")
                b.set_label(f"{key_names_localized[i]} : {self._joystick_cfg[i]}")
            self.window.run()
            self.window.hide()

        return self._joystick_cfg

    # KEYBOARD CONFIG / KEY DEFINITION
    def on_wKeyDlg_key_press_event(self, widget: Gtk.Widget, event: Gdk.EventKey, *args):
        pass  # not part of this

    def on_button_kb_key_clicked(self, w, *args):
        pass  # not part of this

    # Joystick configuration / Key definition
    def on_button_joy_key_clicked(self, w, *args):
        key = widget_to_primitive(w)
        dlg = self.builder.get_object("wJoyDlg")
        key -= 1  # key = bit position, start with
        dlg.show_now()
        # Need to force event processing. Otherwise, popup won't show up.
        while Gtk.events_pending():
            Gtk.main_iteration()

        joykey = self._emulator_input.joy_get_set_key(key)

        self._joystick_cfg[key] = joykey

        self.builder.get_object(f"button_joy_{key_names[key]}").set_label(f"{key_names_localized[key]} : {joykey}")

        dlg.hide()

    def gtk_widget_hide_on_delete(self, w: Gtk.Widget, *args):
        w.hide_on_delete()
        return True
