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
import gi

from desmume.controls import Keys, keymask, load_default_config, key_names, load_configured_config
from desmume.emulator import DeSmuME, NB_STATES, SCREEN_WIDTH, SCREEN_HEIGHT
from desmume.frontend.gtk_drawing_area_desmume import AbstractRenderer
from desmume.frontend.widget_to_primitive import widget_to_primitive

gi.require_version('Gtk', '3.0')

from gi.repository import Gtk, Gdk, GLib
from gi.repository.Gtk import *


TICKS_PER_FRAME = 17


class MainController:
    def __init__(self, builder: Builder, window: Window, emu: DeSmuME):
        self.builder = builder
        self.window = window
        self.emu = emu
        self.renderer = AbstractRenderer.impl(emu)

        self._keyboard_cfg, self._joystick_cfg = load_configured_config(emu)
        self._keyboard_tmp = self._keyboard_cfg
        self._boost = False
        self._save_fs = 0
        self._frameskip = 0
        self._boost_fs = 20
        self._registered_main_loop = False
        self._fs_frame_count = 0
        self._fps_frame_count = 0
        self._fps_sec_start = 0
        self._fps = 0
        self._ticks_prev_frame = 0
        self._ticks_cur_frame = 0
        self._fps_limiter_disabled = False
        self._screen_invert = False
        self._click = False
        self._screen_right_force = False
        self._current_screen_width = SCREEN_WIDTH
        self._current_screen_height = SCREEN_HEIGHT
        self._screen_gap = False
        self._screen_no_gap = False
        self._screen_right = False
        self._supress_event = False
        self._tmp_key = None

        self._main_draw = builder.get_object("wDraw_Main")
        self._main_draw.set_events(Gdk.EventMask.ALL_EVENTS_MASK)
        self._main_draw.show()
        self._sub_draw = builder.get_object("wDraw_Sub")
        self._sub_draw.set_events(Gdk.EventMask.ALL_EVENTS_MASK)
        self._sub_draw.show()

        builder.connect_signals(self)

    def on_destroy(self, *args):
        self.emu.destroy()
        Gtk.main_quit()

    def gtk_main_quit(self, *args):
        self.emu.destroy()
        Gtk.main_quit()

    def gtk_widget_hide_on_delete(self, w: Gtk.Widget, *args):
        w.hide_on_delete()
        return True

    def gtk_widget_hide(self, w: Gtk.Widget, *args):
        w.hide()

    # INPUT BUTTONS / KEYBOARD
    def on_wMainW_key_press_event(self, widget: Gtk.Widget, event: Gdk.EventKey, *args):
        key = self.lookup_key(event.keyval)
        # shift,ctrl, both alts
        mask = Gdk.ModifierType.SHIFT_MASK | Gdk.ModifierType.CONTROL_MASK | Gdk.ModifierType.MOD1_MASK | Gdk.ModifierType.MOD5_MASK
        if event.state & mask == 0:
            if event.keyval == self._keyboard_cfg[Keys.KEY_BOOST - 1]:
                self._boost = not self._boost
                if self._boost:
                    self._save_fs = self._frameskip
                    self._frameskip = self._boost_fs
                else:
                    self._frameskip = self._save_fs
                return True
            elif key and self.emu.is_running():
                self.emu.input.keypad_add_key(key)
                return True
        return False

    def on_wMainW_key_release_event(self, widget: Gtk.Widget, event: Gdk.EventKey, *args):
        key = self.lookup_key(event.keyval)
        if key and self.emu.is_running():
            self.emu.input.keypad_rm_key(key)

    # OUTPUT SCREENS
    def on_wDrawScreen_main_draw_event(self, widget: Gtk.DrawingArea, ctx: cairo.Context, *args):
        return self.renderer.screen(self._current_screen_width, self._current_screen_height, ctx, 0 if not self._screen_invert else 1)

    def on_wDrawScreen_main_configure_event(self, widget: Gtk.DrawingArea, *args):
        self.renderer.reshape(widget, 0)
        return True

    def on_wDrawScreen_sub_draw_event(self, widget: Gtk.DrawingArea, ctx: cairo.Context, *args):
        return self.renderer.screen(self._current_screen_width, self._current_screen_height, ctx, 1 if not self._screen_invert else 0)

    def on_wDrawScreen_sub_configure_event(self, widget: Gtk.DrawingArea, *args):
        self.renderer.reshape(widget, 1)
        return True

    # INPUT STYLUS / MOUSE
    def on_wDrawScreen_main_motion_notify_event(self, widget: Gtk.Widget, event: Gdk.EventMotion, *args):
        return self.on_wDrawScreen_motion_notify_event(widget, event, 0)

    def on_wDrawScreen_main_button_release_event(self, widget: Gtk.Widget, event: Gdk.EventButton, *args):
        return self.on_wDrawScreen_button_release_event(widget, event, 0)

    def on_wDrawScreen_main_button_press_event(self, widget: Gtk.Widget, event: Gdk.EventButton, *args):
        return self.on_wDrawScreen_button_press_event(widget, event, 0)

    def on_wDrawScreen_sub_motion_notify_event(self, widget: Gtk.Widget, event: Gdk.EventMotion, *args):
        return self.on_wDrawScreen_motion_notify_event(widget, event, 1)

    def on_wDrawScreen_sub_button_release_event(self, widget: Gtk.Widget, event: Gdk.EventButton, *args):
        return self.on_wDrawScreen_button_release_event(widget, event, 1)

    def on_wDrawScreen_sub_button_press_event(self, widget: Gtk.Widget, event: Gdk.EventButton, *args):
        return self.on_wDrawScreen_button_press_event(widget, event, 1)

    def on_wDrawScreen_motion_notify_event(self, widget: Gtk.Widget, event: Gdk.EventMotion, display_id: int):
        if (display_id == 1 ^ self._screen_invert) and self._click:
            if event.is_hint:
                _, x, y, state = widget.get_window().get_pointer()
            else:
                x = event.x
                y = event.y
                state = event.state
            if state & Gdk.ModifierType.BUTTON1_MASK:
                self.set_touch_pos(x, y)

    def on_wDrawScreen_button_release_event(self, widget: Gtk.Widget, event: Gdk.EventButton, display_id: int):
        if display_id == 1 ^ self._screen_invert and self._click:
            self._click = False
            self.emu.input.touch_release()
        return True

    def on_wDrawScreen_button_press_event(self, widget: Gtk.Widget, event: Gdk.EventButton, display_id: int):
        if event.button == 1:
            if (display_id == 1 ^ self._screen_invert) and self.emu.is_running():
                self._click = True
                _, x, y, state = widget.get_window().get_pointer()
                if state & Gdk.ModifierType.BUTTON1_MASK:
                    self.set_touch_pos(x, y)
        elif event.button == 2:
            # filter out 2x / 3x clicks
            if event.type == Gdk.EventType.BUTTON_PRESS:
                self.rotate(self.renderer.get_screen_rotation() + 90)
        return True

    def on_wDrawScreen_scroll_event(self, widget: Gtk.Widget, event: Gdk.Event, *args):
        zoom_inc = .125
        zoom_min = 0.5
        zoom_max = 2.0

        scale = self.renderer.get_scale()
        if event.delta_y < 0:
            scale += zoom_inc
        elif event.delta_y > 0:
            scale -= zoom_inc

        if scale > zoom_max:
            scale = zoom_max
        elif scale < zoom_min:
            scale = zoom_min

        self.renderer.set_scale(scale)

        self.resize()

        return True

    # MENU FILE
    def on_menu_open_activate(self, *args):
        self.emu.pause()

        dialog = Gtk.FileChooserDialog(
            "Open...",
            self.window,
            Gtk.FileChooserAction.OPEN,
            (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL, Gtk.STOCK_OPEN, Gtk.ResponseType.OK)
        )

        filter_nds = Gtk.FileFilter()
        filter_nds.set_name("Nintendo DS ROMs (*.nds)")
        filter_nds.add_pattern("*.nds")
        dialog.add_filter(filter_nds)

        filter_gba_ds = Gtk.FileFilter()
        filter_gba_ds.set_name("Nintendo DS ROMs with binary loader (*.ds.gba)")
        filter_gba_ds.add_pattern("*.nds")
        dialog.add_filter(filter_gba_ds)

        filter_any = Gtk.FileFilter()
        filter_any.set_name("All files")
        filter_any.add_pattern("*")
        dialog.add_filter(filter_any)

        response = dialog.run()
        fn = dialog.get_filename()
        dialog.destroy()

        if response == Gtk.ResponseType.OK:
            try:
                self.emu.open(fn)
            except RuntimeError:
                md = Gtk.MessageDialog(None,
                                       Gtk.DialogFlags.DESTROY_WITH_PARENT, Gtk.MessageType.ERROR,
                                       Gtk.ButtonsType.OK, f"Unable to load: {fn}",
                                       title="Error!")
                md.set_position(Gtk.WindowPosition.CENTER)
                md.run()
                md.destroy()
            else:
                self.resume()
                self.enable_rom_features()

    def on_menu_pscreen_activate(self, menu_item: Gtk.MenuItem, *args):
        was_running = self.emu.is_running()
        if was_running:
            self.emu.pause()

        dialog = Gtk.FileChooserDialog(
            "Save Screenshot...",
            self.window,
            Gtk.FileChooserAction.SAVE,
            (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL, Gtk.STOCK_SAVE, Gtk.ResponseType.OK)
        )

        filter_png = Gtk.FileFilter()
        filter_png.set_name("PNG Image (*.png)")
        filter_png.add_pattern("*.png")
        dialog.add_filter(filter_png)

        response = dialog.run()
        fn = dialog.get_filename()
        dialog.destroy()

        if response == Gtk.ResponseType.OK:
            self.emu.screenshot().save(fn)

        if was_running:
            self.resume()

    def on_menu_quit_activate(self, menu_item: Gtk.MenuItem, *args):
        self.gtk_main_quit()

    # MENU SAVES
    def on_loadstateXX_activate(self, w: Gtk.Widget, *args):
        slot = widget_to_primitive(w)
        self.emu.savestate.load(slot)

    def on_savestateXX_activate(self, w: Gtk.Widget, *args):
        slot = widget_to_primitive(w)
        self.emu.savestate.save(slot)
        self.update_savestate_menu("loadstate", slot)
        self.update_savestate_menu("savestate", slot)

    def on_savetypeXX_toggled(self, w: Gtk.Widget, *args):
        type = widget_to_primitive(w)
        self.emu.set_savetype(type)

    # MENU EMULATION
    def on_menu_exec_activate(self, menu_item: Gtk.MenuItem, *args):
        self.resume()

    def on_menu_pause_activate(self, menu_item: Gtk.MenuItem, *args):
        self._supress_event = True
        self.builder.get_object("wgt_Exec").set_active(False)
        self._supress_event = False
        self.emu.pause()

    def on_menu_reset_activate(self, menu_item: Gtk.MenuItem, *args):
        self.emu.reset()

    def on_menu_layers_toggled(self, menu_item: Gtk.MenuItem, *args):
        w1 = self.builder.get_object("wvb_1_Main")
        w2 = self.builder.get_object("wvb_2_Sub")
        if menu_item.get_active():
            w1.show()
            w2.show()
        else:
            w1.hide()
            w2.hide()
        self._mainwindow_resize()

    def on_fsXX_activate(self, w, *args):
        self._frameskip = widget_to_primitive(w)

    def on_sizeXX_activate(self, w, *args):
        self.renderer.set_scale(widget_to_primitive(w))
        self.resize()

    # MENU CONFIG
    def on_menu_controls_activate(self, menu_item: Gtk.MenuItem, *args):
        dlg = self.builder.get_object("wKeybConfDlg")
        for i in range(0, Keys.NB_KEYS):
            b = self.builder.get_object(f"button_{key_names[i]}")
            b.set_label(f"{key_names[i]} : {Gdk.keyval_name(self._keyboard_cfg[i])}")
        dlg.show()

    def on_menu_joy_controls_activate(self, menu_item: Gtk.MenuItem, *args):
        if self.emu.input.joy_number_connected() < 1 or self.emu.is_running():
            if self.emu.input.joy_number_connected() < 1:
                text = "You don't have any joystick!"
            else:
                text = "Can't configure joystick while the game is running!"

            md = Gtk.MessageDialog(None,
                                   Gtk.DialogFlags.DESTROY_WITH_PARENT | Gtk.DialogFlags.MODAL, Gtk.MessageType.ERROR,
                                   Gtk.ButtonsType.OK, text,
                                   title="Error!")
            md.set_position(Gtk.WindowPosition.CENTER)
            md.run()
            md.destroy()
        else:
            dlg = self.builder.get_object("wJoyConfDlg")
            for i in range(0, Keys.NB_KEYS):
                b = self.builder.get_object(f"button_joy_{key_names[i]}")
                b.set_label(f"{key_names[i]} : {self._joystick_cfg[i]}")
            dlg.run()

    def on_menu_audio_on_toggled(self, menu_item: Gtk.MenuItem, *args):
        if menu_item.get_active():
            self.emu.volume_set(100)
        else:
            self.emu.volume_set(0)

    def on_menu_gapscreen_toggled(self, menu_item: Gtk.MenuItem, *args):
        self._screen_gap = menu_item.get_active()
        self._mainwindow_resize()

    def on_menu_nogap_toggled(self, menu_item: Gtk.MenuItem, *args):
        self._screen_no_gap = menu_item.get_active()
        self._mainwindow_resize()

    def on_menu_rightscreen_toggled(self, menu_item: Gtk.MenuItem, *args):
        self.rightscreen(menu_item.get_active())

    def on_menu_rotatescreen_toggled(self, w, *args):
        self.rotate(widget_to_primitive(w))

    # MENU ?
    def on_menu_apropos_activate(self, menu_item: Gtk.MenuItem, *args):
        w_about: Gtk.AboutDialog = self.builder.get_object("wAboutDlg")
        w_about.run()

    # TOOLBAR
    def on_wgt_Open_clicked(self, btn: Gtk.ToolButton, *args):
        self.on_menu_open_activate()

    def on_wgt_Exec_toggled(self, btn: Gtk.ToggleToolButton, *args):
        if self._supress_event:
            return
        if btn.get_active():
            self.resume()
        else:
            self.emu.pause()

    def on_wgt_Reset_clicked(self, btn: Gtk.ToolButton, *args):
        self.emu.reset()

    # LAYERS TOGGLE
    def on_wc_1_BGXX_toggled(self, w, *args):
        slot = widget_to_primitive(w)
        self.emu.gpu_set_layer_main_enable_state(slot, self.builder.get_object(f"wc_1_BG{slot}").get_active())

    def on_wc_2_BGXX_toggled(self, w, *args):
        slot = widget_to_primitive(w)
        self.emu.gpu_set_layer_sub_enable_state(slot, self.builder.get_object(f"wc_2_BG{slot}").get_active())

    # KEYBOARD CONFIG / KEY DEFINITION
    def on_wKeyDlg_key_press_event(self, widget: Gtk.Widget, event: Gdk.EventKey, *args):
        self._tmp_key = event.keyval
        self.builder.get_object("label_key").set_text(Gdk.keyval_name(self._tmp_key))
        return True

    def on_wKeybConfDlg_response(self, dialog: Gtk.Dialog, arg1: int, *args):
        if arg1 == Gtk.ResponseType.OK:
            self._keyboard_cfg = self._keyboard_tmp
        dialog.hide()

    def on_button_kb_key_clicked(self, w, *args):
        key = widget_to_primitive(w)
        dlg = self.builder.get_object("wKeyDlg")
        key -= 1  # key = bit position, start with
        self._tmp_key = self._keyboard_tmp[key]
        self.builder.get_object("label_key").set_text(Gdk.keyval_name(self._tmp_key))
        if dlg.run() == Gtk.ResponseType.OK:
            self._keyboard_tmp[key] = self._tmp_key
            self.builder.get_object(f"button_{key_names[key]}").set_label(f"{key_names[key]} : {Gdk.keyval_name(self._tmp_key)}")

        dlg.hide()

    # Joystick configuration / Key definition
    def on_button_joy_key_clicked(self, w, *args):
        key = widget_to_primitive(w)
        dlg = self.builder.get_object("wJoyDlg")
        key -= 1  # key = bit position, start with
        self._tmp_key = self._keyboard_tmp[key]
        dlg.show_now()
        # Need to force event processing. Otherwise, popup won't show up.
        while Gtk.events_pending():
            Gtk.main_iteration()

        joykey = self.emu.input.joy_get_set_key(key)

        self._joystick_cfg[key] = joykey

        self.builder.get_object(f"button_joy_{key_names[key]}").set_label(f"{key_names[key]} : {joykey}")

        dlg.hide()

    def lookup_key(self, keyval):
        key = False
        for i in range(0, Keys.NB_KEYS):
            if keyval == self._keyboard_cfg[i]:
                key = keymask(i)
                break
        return key

    def resume(self):
        self.emu.resume()
        self._supress_event = True
        self.builder.get_object("wgt_Exec").set_active(True)
        self._supress_event = False
        if not self._registered_main_loop:
            self._registered_main_loop = True
            GLib.idle_add(self.emu_cycle)

    def emu_cycle(self):
        if self.emu.is_running():
            skip_frame = False
            if self._frameskip != 0 and (self._fs_frame_count % (self._frameskip + 1) != 0):
                self.emu.skip_next_frame()
                skip_frame = True

            self._fs_frame_count += 1
            self._fps_frame_count += 1

            if not self._fps_sec_start:
                self._fps_sec_start = self.emu.get_ticks()
            if self.emu.get_ticks() - self._fps_sec_start >= 1000:
                self._fps_sec_start = self.emu.get_ticks()
                self._fps = self._fps_frame_count
                self._fps_frame_count = 0
                self.window.set_title(f"PyDeSmuME - {self._fps}fps")

            self.emu.cycle()

            if not skip_frame:
                self._main_draw.queue_draw()
                self._sub_draw.queue_draw()

            self._ticks_cur_frame = self.emu.get_ticks()

            if not self._fps_limiter_disabled:
                if self._ticks_cur_frame - self._ticks_prev_frame < TICKS_PER_FRAME:
                    while self._ticks_cur_frame - self._ticks_prev_frame < TICKS_PER_FRAME:
                        self._ticks_cur_frame = self.emu.get_ticks()

            self._ticks_prev_frame = self.emu.get_ticks()
            return True

        self._main_draw.queue_draw()
        self._sub_draw.queue_draw()
        self._registered_main_loop = False
        return False

    def enable_rom_features(self):
        self.emu.savestate.scan()
        self.update_savestates_menu()
        self._set_sensitve("menu_exec", True)
        self._set_sensitve("menu_pause", True)
        self._set_sensitve("menu_reset", True)
        self._set_sensitve("wgt_Exec", True)
        self._set_sensitve("wgt_Reset", True)

    def update_savestates_menu(self):
        for i in range(1, NB_STATES + 1):
            if self.emu.savestate.exists(i):
                self.update_savestate_menu("loadstate", i)
                self.update_savestate_menu("savestate", i)
            else:
                self.clear_savestate_menu("loadstate", i)
                self.clear_savestate_menu("savestate", i)

    def clear_savestate_menu(self, name, num):
        w: Gtk.MenuItem = self.builder.get_object(f"{name}{num}")
        w.get_child().set_text(f"State {num} (empty)")

    def update_savestate_menu(self, name, num):
        w = self.builder.get_object(f"{name}{num}")
        w.get_child().set_text(f"State {num} ({self.emu.savestate.date(num)})")

    def set_touch_pos(self, x: int, y: int):
        scale = self.renderer.get_scale()
        rotation = self.renderer.get_screen_rotation()
        x /= scale
        y /= scale
        emu_x = x
        emu_y = y
        if rotation == 90 or rotation == 270:
            emu_x = 256 -y
            emu_y = x

        if emu_x < 0:
            emu_x = 0
        elif emu_x > SCREEN_WIDTH - 1:
            emu_x = SCREEN_WIDTH - 1

        if emu_y < 9:
            emu_y = 0
        elif emu_y > SCREEN_HEIGHT:
            emu_y = SCREEN_HEIGHT

        if self._screen_invert:
            emu_x = SCREEN_WIDTH -1 - emu_x
            emu_y = SCREEN_HEIGHT - emu_y

        self.emu.input.touch_set_pos(int(emu_x), int(emu_y))

    def rotate(self, angle):
        if angle >= 360:
            angle -= 360
        self.renderer.set_screen_rotation(angle)
        rotated = angle == 90 or angle == 270
        self._screen_invert = angle >= 180
        self._current_screen_height = SCREEN_HEIGHT
        self._current_screen_width = SCREEN_WIDTH
        if rotated:
            self._current_screen_height = SCREEN_WIDTH
            self._current_screen_width = SCREEN_HEIGHT
        self.rightscreen(rotated)

        self.resize()

    def rightscreen(self, apply):
        table: Gtk.Table = self.builder.get_object("table_layout")
        chk = self.builder.get_object("wvb_2_Sub")
        self._screen_right = apply or self._screen_right_force
        if self._screen_right:
            gtk_table_reattach(table, self._sub_draw, 3, 4, 0, 1, 0, 0, 0, 0)
            gtk_table_reattach(table, chk, 4, 5, 0, 1, 0, 0, 0, 0)
        else:
            gtk_table_reattach(table, self._sub_draw, 1, 2, 2, 3, 0, 0, 0, 0)
            gtk_table_reattach(table, chk, 0, 1, 2, 3, 0, 0, 0, 0)

        table.queue_resize()
        self._mainwindow_resize()

    def resize(self):
        scale = self.renderer.get_scale()

        self._main_draw.set_size_request(self._current_screen_width * scale, self._current_screen_height * scale)
        self._sub_draw.set_size_request(self._current_screen_width * scale, self._current_screen_height * scale)

        self._mainwindow_resize()

    def _set_sensitve(self, name, state):
        w = self.builder.get_object(name)
        w.set_sensitive(state)

    def _mainwindow_resize(self):
        spacer1: Gtk.Widget = self.builder.get_object("misc_sep3")
        spacer2: Gtk.Widget = self.builder.get_object("misc_sep4")

        current_rotation = self.renderer.get_screen_rotation()
        rotated = current_rotation == 90 or current_rotation == 270

        dim1 = dim2 = 66 * self.renderer.get_scale()
        if not self._screen_gap:
            dim1 = dim2 = -1

        if self._screen_no_gap:
            spacer1.hide()
            spacer2.hide()
        else:
            spacer1.show()
            spacer2.show()

        if self._screen_right == rotated:
            if self._screen_right:
                dim2 = -1
            else:
                dim1 = -1

        spacer1.set_size_request(dim1, -1)
        spacer2.set_size_request(-1, dim2)
        self.window.resize(1, 1)


def gtk_table_reattach(
        table: Gtk.Table, w: Gtk.Widget, left_attach: int, right_attach: int, top_attach: int, bottom_attach: int,
        xoptions: int, yoptions: int, xpadding: int, ypadding: int):
    for child in table.get_children():
        if child == w:
            table.child_set_property(child, 'left_attach', left_attach)
            table.child_set_property(child, 'right_attach', right_attach)
            table.child_set_property(child, 'top_attach', top_attach)
            table.child_set_property(child, 'bottom_attach', bottom_attach)
            table.child_set_property(child, 'x-options', xoptions)
            table.child_set_property(child, 'x-padding', xpadding)
            table.child_set_property(child, 'y-options', yoptions)
            table.child_set_property(child, 'y-padding', ypadding)
