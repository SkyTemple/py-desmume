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
import platform
from ctypes import cdll, create_string_buffer, cast, c_char_p, POINTER, c_int, c_char, c_uint16, c_uint8, Structure
from enum import Enum
from time import sleep

from PIL import Image

from desmume.controls import add_key, rm_key


SCREEN_WIDTH = 256
SCREEN_HEIGHT = 192
SCREEN_HEIGHT_BOTH = SCREEN_HEIGHT * 2
SCREEN_PIXEL_SIZE = SCREEN_WIDTH * SCREEN_HEIGHT
SCREEN_PIXEL_SIZE_BOTH = SCREEN_WIDTH * SCREEN_HEIGHT_BOTH
NB_STATES = 10


def strbytes(s):
    return s.encode('utf-8')


class Language(Enum):
    JAPANESE = 0
    ENGLISH = 1
    FRENCH = 2
    GERMAN = 3
    ITALIAN = 4
    SPANISH = 5


class StartFrom(Enum):
    START_BLANK = 0
    START_SRAM = 1
    START_SAVESTATE = 2


class DeSmuME_SDL_Window:
    def __init__(self, emu: 'DeSmuME', auto_pause=True, use_opengl_if_possible=True):
        self.emu = emu
        self.emu.lib.desmume_draw_window_init(bool(auto_pause), bool(use_opengl_if_possible))

    def __del__(self):
        self.destroy()

    def destroy(self):
        self.emu.lib.desmume_draw_window_free()

    def draw(self):
        self.emu.lib.desmume_draw_window_frame()

    def process_input(self):
        self.emu.lib.desmume_draw_window_input()

    def has_quit(self) -> bool:
        return bool(self.emu.lib.desmume_draw_window_has_quit())


class DeSmuME_Input:
    def __init__(self, emu: 'DeSmuME'):
        self.emu = emu
        self.has_joy = False

    def __del__(self):
        if self.has_joy:
            self.joy_uninit()

    def joy_init(self):
        if not self.has_joy:
            self.emu.lib.desmume_input_joy_init()
            self.has_joy = True

    def joy_uninit(self):
        if self.has_joy:
            self.emu.lib.desmume_input_joy_uninit()

    def joy_number_connected(self) -> int:
        if self.has_joy:
            return self.emu.lib.desmume_input_joy_number_connected()
        raise ValueError("Joystick not initialized.")

    def joy_get_key(self, index: int) -> int:
        if self.has_joy:
            return self.emu.lib.desmume_input_joy_get_key(index)
        raise ValueError("Joystick not initialized.")

    def joy_get_set_key(self, index: int) -> int:
        if self.has_joy:
            return self.emu.lib.desmume_input_joy_get_set_key(index)
        raise ValueError("Joystick not initialized.")

    def joy_set_key(self, index: int, joystick_key_index: int):
        if self.has_joy:
            self.emu.lib.desmume_input_joy_set_key(index, joystick_key_index)
            return
        raise ValueError("Joystick not initialized.")

    def keypad_update(self, keys: int) -> int:
        self.emu.lib.desmume_input_keypad_update.argtypes = [c_uint16]
        return self.emu.lib.desmume_input_keypad_update(keys)

    def keypad_get(self) -> int:
        self.emu.lib.desmume_input_keypad_update.restype = c_uint16
        return self.emu.lib.desmume_input_keypad_get()

    def keypad_add_key(self, key: int):
        old_keypad = self.keypad_get()
        self.keypad_update(add_key(old_keypad, key))

    def keypad_rm_key(self, key: int):
        old_keypad = self.keypad_get()
        self.keypad_update(rm_key(old_keypad, key))

    def touch_set_pos(self, x: int, y: int):
        self.emu.lib.desmume_input_set_touch_pos(x, y)

    def touch_release(self):
        self.emu.lib.desmume_input_release_touch()


class DeSmuME_Savestate:
    def __init__(self, emu: 'DeSmuME'):
        self.emu = emu

    def scan(self):
        self.emu.lib.desmume_savestate_scan()

    def exists(self, slot_id: int):
        return bool(self.emu.lib.desmume_savestate_slot_exists(slot_id))

    def load(self, slot_id: int):
        return self.emu.lib.desmume_savestate_slot_load(slot_id)

    def save(self, slot_id: int):
        return self.emu.lib.desmume_savestate_slot_save(slot_id)

    def load_file(self, file_name: str):
        if not self.emu.lib.desmume_savestate_load(c_char_p(strbytes(file_name))):
            raise RuntimeError("Unable to load savesate.")

    def save_file(self, file_name: str):
        if not self.emu.lib.desmume_savestate_save(c_char_p(strbytes(file_name))):
            raise RuntimeError("Unable to save savesate.")

    def date(self, slot_id: int):
        self.emu.lib.desmume_savestate_slot_date.restype = c_char_p
        return str(self.emu.lib.desmume_savestate_slot_date(slot_id), 'utf-8')


class DeSmuME_Date(Structure):
    _fields_ = [
        ("year", c_int),
        ("month", c_int),
        ("day", c_int),
        ("hour", c_int),
        ("minute", c_int),
        ("second", c_int),
        ("millisecond", c_int),
    ]


class DeSmuME_Movie:
    def __init__(self, emu: 'DeSmuME'):
        self.emu = emu

    def play(self, file_name: str):
        self.emu.lib.desmume_movie_play.restype = c_char_p
        err = self.emu.lib.desmume_movie_play(c_char_p(strbytes(file_name)))
        if err is not None and err != "":
            raise RuntimeError(str(err, 'utf-8'))

    def record(
            self, file_name: str, author_name: str,
            start_from: StartFrom = StartFrom.START_BLANK, sram_save: str = "", rtc_date: DeSmuME_Date = None
    ):
        if not rtc_date:
            self.emu.lib.desmume_movie_record(
                c_char_p(strbytes(file_name)), c_char_p(strbytes(author_name)), start_from.value, c_char_p(strbytes(sram_save))
            )
        else:
            self.emu.lib.desmume_movie_record_from_date(
                c_char_p(strbytes(file_name)), c_char_p(strbytes(author_name)), start_from.value, c_char_p(strbytes(sram_save)), rtc_date
            )

    def stop(self):
        self.emu.lib.desmume_movie_stop()

    def is_active(self):
        return bool(self.emu.lib.desmume_movie_is_active())

    def is_recording(self):
        return bool(self.emu.lib.desmume_movie_is_recording())

    def is_playing(self):
        return bool(self.emu.lib.desmume_movie_is_playing())

    def is_finished(self):
        return bool(self.emu.lib.desmume_movie_is_finished())

    def get_length(self):
        if self.is_active():
            return self.emu.lib.desmume_movie_get_length()
        raise ValueError("No movie is active.")

    def get_name(self):
        if self.is_active():
            self.emu.lib.desmume_movie_get_name.restype = c_char_p
            return self.emu.lib.desmume_movie_get_name()
        raise ValueError("No movie is active.")

    def get_rerecord_count(self):
        if self.is_active():
            return self.emu.lib.desmume_movie_get_rerecord_count()
        raise ValueError("No movie is active.")

    def set_rerecord_count(self, count: int):
        if self.is_active():
            return self.emu.lib.desmume_movie_set_rerecord_count(count)
        raise ValueError("No movie is active.")

    def get_readonly(self):
        if self.is_active():
            return bool(self.emu.lib.desmume_movie_get_readonly())
        raise ValueError("No movie is active.")

    def set_readonly(self, state: bool):
        if self.is_active():
            return self.emu.lib.desmume_movie_set_readonly(state)
        raise ValueError("No movie is active.")

class DeSmuME:
    def __init__(self, dl_name: str = None):
        self.lib = None

        # Load the correct library
        if dl_name is None:
            if platform.system().lower().startswith('windows'):
                dl_name = "libdesmume.dll"
                os.add_dll_directory(os.getcwd())
            elif platform.system().lower().startswith('linux'):
                dl_name = "libdesmume.so"
            elif platform.system().lower().startswith('darwin'):
                dl_name = "libdesmume.dylib"
            else:
                RuntimeError(f"Unknown platform {platform.system()}, can't autodetect DLL to load.")
        else:
            if platform.system().lower().startswith('windows'):
                os.add_dll_directory(os.path.dirname(dl_name))
                dl_name = os.path.basename(dl_name)

        self.lib = cdll.LoadLibrary(dl_name)

        self.lib.desmume_set_savetype(0)

        if self.lib.desmume_init() < 0:
            raise RuntimeError("Failed to init DeSmuME")

        self._input = DeSmuME_Input(self)
        self._savestate = DeSmuME_Savestate(self)
        self._movie = DeSmuME_Movie(self)
        self._sdl_window = None
        self._raw_buffer_rgbx = None

    def __del__(self):
        if self.lib is not None:
            self.lib.desmume_free()
            del self._input
            del self._savestate
            del self._movie
            del self._sdl_window
            self.lib = None

    def destroy(self):
        self.__del__()

    @property
    def input(self):
        return self._input

    @property
    def savestate(self):
        return self._savestate

    @property
    def movie(self):
        return self._movie

    def set_language(self, lang: Language):
        self.lib.desmume_set_language(lang.value)

    def open(self, file_name: str, auto_resume=True):
        if self.lib.desmume_open(c_char_p(strbytes(file_name))) < 0:
            raise RuntimeError("Unable to open ROM file.")
        if auto_resume:
            self.resume()

    def set_savetype(self, value: int):
        # TODO: Enum?
        self.lib.desmume_set_savetype(value)

    def pause(self):
        self.lib.desmume_pause()

    def resume(self, keep_keypad=False):
        if keep_keypad:
            self.input.keypad_update(0)
        self.lib.desmume_resume()

    def reset(self):
        self.lib.desmume_reset()

    def is_running(self) -> bool:
        return bool(self.lib.desmume_running())

    def skip_next_frame(self):
        self.lib.desmume_skip_next_frame()

    def cycle(self):
        self.lib.desmume_cycle()

    def has_opengl(self) -> bool:
        return bool(self.lib.desmume_has_opengl())

    def create_sdl_window(self, auto_pause=False, use_opengl_if_possible=True):
        if not self._sdl_window:
            self._sdl_window = DeSmuME_SDL_Window(self, auto_pause, use_opengl_if_possible)
        return self._sdl_window

    def display_buffer(self):
        self.lib.desmume_draw_raw.restype = POINTER(c_uint16)
        return self.lib.desmume_draw_raw()

    def display_buffer_as_rgbx(self, reuse_buffer=True) -> memoryview:
        if reuse_buffer:
            if not self._raw_buffer_rgbx:
                self._raw_buffer_rgbx = create_string_buffer(SCREEN_WIDTH * SCREEN_HEIGHT_BOTH * 4)
            buff = self._raw_buffer_rgbx
        else:
            buff = create_string_buffer(SCREEN_WIDTH * SCREEN_HEIGHT_BOTH * 4)
        self.lib.desmume_draw_raw_as_rgbx(cast(buff, c_char_p))
        # XXX: Yes this is stupid, but cairo NEEDS a bytearray....
        return memoryview(bytearray(buff.raw))

    def screenshot(self) -> Image.Image:
        buff = create_string_buffer(SCREEN_WIDTH * SCREEN_HEIGHT_BOTH * 3)
        self.lib.desmume_screenshot(cast(buff, c_char_p))

        return Image.frombuffer('RGB', (SCREEN_WIDTH, SCREEN_HEIGHT_BOTH), buff.raw, 'raw', 'RGB', 0, 1)

    def get_ticks(self) -> int:
        return self.lib.desmume_sdl_get_ticks()

    def volume_get(self) -> int:
        return self.lib.desmume_volume_get()

    def volume_set(self, volume: int):
        return self.lib.desmume_volume_set(volume)

    def gpu_get_layer_main_enable_state(self, layer_index: int):
        return bool(self.lib.desmume_gpu_get_layer_main_enable_state(layer_index))

    def gpu_get_layer_sub_enable_state(self, layer_index: int):
        return bool(self.lib.desmume_gpu_get_layer_sub_enable_state(layer_index))

    def gpu_set_layer_main_enable_state(self, layer_index: int, state: bool):
        self.lib.desmume_gpu_set_layer_main_enable_state(layer_index, state)

    def gpu_set_layer_sub_enable_state(self, layer_index: int, state: bool):
        self.lib.desmume_gpu_set_layer_sub_enable_state(layer_index, state)


# Testing script

def _print_movie_stats(emu: 'DeSmuME'):
    print("--------------------")
    print(f"Active:    {emu.movie.is_active()}")
    print(f"Playing:   {emu.movie.is_playing()}")
    print(f"Recording: {emu.movie.is_recording()}")
    print(f"Finished:  {emu.movie.is_finished()}")
    if emu.movie.is_active():
        print(f"Length:    {emu.movie.get_length()}")
        print(f"Name:      {emu.movie.get_name()}")
        print(f"Readonly:  {emu.movie.get_readonly()}")
        print(f"RRcount:   {emu.movie.get_rerecord_count()}")

if __name__ == '__main__':
    # TODO: Figure out how to specify this correctly.
    emu = DeSmuME("../../../desmume/desmume/src/frontend/interface/.libs/libdesmume.so")
    #emu = DeSmuME("Y:\\dev\\desmume\\desmume\\src\\frontend\\interface\\windows\\__bins\\DeSmuME Interface-VS2019-Debug.dll")

    emu.set_language(Language.GERMAN)
    emu.open("../../skyworkcopy.nds")
    #emu.open("..\\skyworkcopy.nds")
    win = emu.create_sdl_window(use_opengl_if_possible=True)

    print("> BEFORE")
    _print_movie_stats(emu)

    for i in range(0, 200):
        win.process_input()
        emu.cycle()
        win.draw()

    print("> BEFORE2")
    _print_movie_stats(emu)
    emu.movie.record('/tmp/test.dsm', 'test', StartFrom.START_BLANK, "", DeSmuME_Date(2009, 12, 12, 10, 11, 12, 200))

    for i in range(0, 500):
        win.process_input()
        emu.cycle()
        win.draw()

    emu.movie.set_rerecord_count(100)
    print("> RECORD")
    _print_movie_stats(emu)

    emu.movie.stop()

    for i in range(0, 500):
        win.process_input()
        emu.cycle()
        win.draw()

    print("> STOP")
    _print_movie_stats(emu)

    emu.movie.play('/tmp/test.dsm')

    for i in range(0, 300):
        win.process_input()
        emu.cycle()
        win.draw()

    print("> PLAY")
    _print_movie_stats(emu)

    for i in range(0, 300):
        win.process_input()
        emu.cycle()
        win.draw()

    print("> PLAY END")
    _print_movie_stats(emu)

    while not win.has_quit():
        win.process_input()
        emu.cycle()
        win.draw()

    #emu.screenshot().show()
