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
from ctypes import cdll, create_string_buffer, cast, c_char_p, POINTER, c_int, c_char, c_uint16, c_uint8, Structure, \
    c_uint, CFUNCTYPE, c_int8, c_int16, c_uint32, c_int32
from enum import Enum
from typing import Union, Callable, List, Optional

try:
    from PIL import Image
except ImportError:
    from pil import Image

from desmume.controls import add_key, rm_key


SCREEN_WIDTH = 256
SCREEN_HEIGHT = 192
SCREEN_HEIGHT_BOTH = SCREEN_HEIGHT * 2
SCREEN_PIXEL_SIZE = SCREEN_WIDTH * SCREEN_HEIGHT
SCREEN_PIXEL_SIZE_BOTH = SCREEN_WIDTH * SCREEN_HEIGHT_BOTH
NB_STATES = 10

MEMORY_CB_FN = CFUNCTYPE(None, c_uint, c_int)
MemoryCbFn = Callable[[int, int], None]


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
        self.lib = emu.lib
        self.lib.desmume_draw_window_init(bool(auto_pause), bool(use_opengl_if_possible))

    def __del__(self):
        self.destroy()

    def destroy(self):
        self.lib.desmume_draw_window_free()

    def draw(self):
        self.lib.desmume_draw_window_frame()

    def process_input(self):
        self.lib.desmume_draw_window_input()

    def has_quit(self) -> bool:
        return bool(self.lib.desmume_draw_window_has_quit())


class DeSmuME_Input:
    def __init__(self, emu: 'DeSmuME'):
        self.emu = emu
        self.lib = emu.lib
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
            self.lib.desmume_input_joy_uninit()

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


class MemoryAccessor:
    def __init__(self, signed, mem: 'DeSmuME_Memory'):
        self.signed = signed
        self.mem = mem

    def __getitem__(self, key: Union[int, slice]) -> Union[int, bytes, List[int]]:
        if isinstance(key, int):
            return self.mem.read(key, key, 1, self.signed)
        return self.mem.read(key.start, key.stop, key.step, self.signed)

    def __setitem__(self, key: Union[int, slice], value: Union[int, bytes, List[int]]):
        if isinstance(key, int):
            return self.mem.write(key, key, 1, bytes([value]))
        return self.mem.write(key.start, key.stop, key.step, value)

    def read_byte(self, addr: int):
        return self[addr]

    def read_short(self, addr: int):
        return self[addr:addr:2]

    def read_long(self, addr: int):
        return self[addr:addr:4]


class RegisterAccesor:
    def __init__(self, prefix, mem: 'DeSmuME_Memory'):
        self.prefix = prefix
        self.lib = mem.emu.lib

    # <editor-fold desc="register accessors" defaultstate="collapsed">

    def __getitem__(self, item):
        if item == 0:
            return self.r0
        if item == 1:
            return self.r1
        if item == 2:
            return self.r2
        if item == 3:
            return self.r3
        if item == 4:
            return self.r4
        if item == 5:
            return self.r5
        if item == 6:
            return self.r6
        if item == 7:
            return self.r7
        if item == 8:
            return self.r8
        if item == 9:
            return self.r9
        if item == 10:
            return self.r10
        if item == 11:
            return self.r11
        if item == 12:
            return self.r12
        if item == 13:
            return self.r13
        if item == 14:
            return self.r14
        if item == 15:
            return self.r15
        raise ValueError("Invalid register")

    def __setitem__(self, item, value):
        if item == 0:
            self.r0 = value
        if item == 1:
            self.r1 = value
        if item == 2:
            self.r2 = value
        if item == 3:
            self.r3 = value
        if item == 4:
            self.r4 = value
        if item == 5:
            self.r5 = value
        if item == 6:
            self.r6 = value
        if item == 7:
            self.r7 = value
        if item == 8:
            self.r8 = value
        if item == 9:
            self.r9 = value
        if item == 10:
            self.r10 = value
        if item == 11:
            self.r11 = value
        if item == 12:
            self.r12 = value
        if item == 13:
            self.r13 = value
        if item == 14:
            self.r14 = value
        if item == 15:
            self.r15 = value
        raise ValueError("Invalid register")

    @property
    def r0(self):
        return self.lib.desmume_memory_read_register(c_char_p(strbytes(self.prefix + "r0")))

    @r0.setter
    def r0(self, value):
        self.lib.desmume_memory_write_register(c_char_p(strbytes(self.prefix + "r0")), value)

    @property
    def r1(self):
        return self.lib.desmume_memory_read_register(c_char_p(strbytes(self.prefix + "r1")))

    @r1.setter
    def r1(self, value):
        self.lib.desmume_memory_write_register(c_char_p(strbytes(self.prefix + "r1")), value)

    @property
    def r2(self):
        return self.lib.desmume_memory_read_register(c_char_p(strbytes(self.prefix + "r2")))

    @r2.setter
    def r2(self, value):
        self.lib.desmume_memory_write_register(c_char_p(strbytes(self.prefix + "r2")), value)

    @property
    def r3(self):
        return self.lib.desmume_memory_read_register(c_char_p(strbytes(self.prefix + "r3")))

    @r3.setter
    def r3(self, value):
        self.lib.desmume_memory_write_register(c_char_p(strbytes(self.prefix + "r3")), value)

    @property
    def r4(self):
        return self.lib.desmume_memory_read_register(c_char_p(strbytes(self.prefix + "r4")))

    @r4.setter
    def r4(self, value):
        self.lib.desmume_memory_write_register(c_char_p(strbytes(self.prefix + "r4")), value)

    @property
    def r5(self):
        return self.lib.desmume_memory_read_register(c_char_p(strbytes(self.prefix + "r5")))

    @r5.setter
    def r5(self, value):
        self.lib.desmume_memory_write_register(c_char_p(strbytes(self.prefix + "r5")), value)

    @property
    def r6(self):
        return self.lib.desmume_memory_read_register(c_char_p(strbytes(self.prefix + "r6")))

    @r6.setter
    def r6(self, value):
        self.lib.desmume_memory_write_register(c_char_p(strbytes(self.prefix + "r6")), value)

    @property
    def r7(self):
        return self.lib.desmume_memory_read_register(c_char_p(strbytes(self.prefix + "r7")))

    @r7.setter
    def r7(self, value):
        self.lib.desmume_memory_write_register(c_char_p(strbytes(self.prefix + "r7")), value)

    @property
    def r8(self):
        return self.lib.desmume_memory_read_register(c_char_p(strbytes(self.prefix + "r8")))

    @r8.setter
    def r8(self, value):
        self.lib.desmume_memory_write_register(c_char_p(strbytes(self.prefix + "r8")), value)

    @property
    def r9(self):
        return self.lib.desmume_memory_read_register(c_char_p(strbytes(self.prefix + "r9")))

    @r9.setter
    def r9(self, value):
        self.lib.desmume_memory_write_register(c_char_p(strbytes(self.prefix + "r9")), value)

    @property
    def r10(self):
        return self.lib.desmume_memory_read_register(c_char_p(strbytes(self.prefix + "r10")))

    @r10.setter
    def r10(self, value):
        self.lib.desmume_memory_write_register(c_char_p(strbytes(self.prefix + "r10")), value)

    @property
    def r11(self):
        return self.lib.desmume_memory_read_register(c_char_p(strbytes(self.prefix + "r11")))

    @r11.setter
    def r11(self, value):
        self.lib.desmume_memory_write_register(c_char_p(strbytes(self.prefix + "r11")), value)

    @property
    def r12(self):
        return self.lib.desmume_memory_read_register(c_char_p(strbytes(self.prefix + "r12")))

    @r12.setter
    def r12(self, value):
        self.lib.desmume_memory_write_register(c_char_p(strbytes(self.prefix + "r12")), value)

    @property
    def r13(self):
        return self.lib.desmume_memory_read_register(c_char_p(strbytes(self.prefix + "r13")))

    @r13.setter
    def r13(self, value):
        self.lib.desmume_memory_write_register(c_char_p(strbytes(self.prefix + "r13")), value)

    @property
    def r14(self):
        return self.lib.desmume_memory_read_register(c_char_p(strbytes(self.prefix + "r14")))

    @r14.setter
    def r14(self, value):
        self.lib.desmume_memory_write_register(c_char_p(strbytes(self.prefix + "r14")), value)

    @property
    def r15(self):
        return self.lib.desmume_memory_read_register(c_char_p(strbytes(self.prefix + "r15")))

    @r15.setter
    def r15(self, value):
        self.lib.desmume_memory_write_register(c_char_p(strbytes(self.prefix + "r15")), value)

    @property
    def cpsr(self):
        return self.lib.desmume_memory_read_register(c_char_p(strbytes(self.prefix + "cpsr")))

    @cpsr.setter
    def cpsr(self, value):
        self.lib.desmume_memory_write_register(c_char_p(strbytes(self.prefix + "cpsr")), value)

    @property
    def spsr(self):
        return self.lib.desmume_memory_read_register(c_char_p(strbytes(self.prefix + "spsr")))

    @spsr.setter
    def spsr(self, value):
        self.lib.desmume_memory_write_register(c_char_p(strbytes(self.prefix + "spsr")), value)

    # Aliases
    @property
    def sp(self):
        return self.r13

    @sp.setter
    def sp(self, value):
        self.r13 = value

    @property
    def lr(self):
        return self.r14

    @lr.setter
    def lr(self, value):
        self.r14 = value

    @property
    def pc(self):
        return self.r15

    @pc.setter
    def pc(self, value):
        self.r15 = value

    # </editor-fold>


class DeSmuME_Memory:
    def __init__(self, emu: 'DeSmuME'):
        self.emu = emu
        self._unsigned = MemoryAccessor(False, self)
        self._signed = MemoryAccessor(True, self)
        self._register_arm9 = RegisterAccesor("arm9.", self)
        self._register_arm7 = RegisterAccesor("arm7.", self)

        self.emu.lib.desmume_memory_read_byte.restype = c_uint8
        self.emu.lib.desmume_memory_read_byte_signed.restype = c_int8
        self.emu.lib.desmume_memory_read_short.restype = c_uint16
        self.emu.lib.desmume_memory_read_short_signed.restype = c_int16
        self.emu.lib.desmume_memory_read_long.restype = c_uint32
        self.emu.lib.desmume_memory_read_long_signed.restype = c_int32

        self.emu.lib.desmume_memory_write_byte.argtypes = [c_int, c_uint8]
        self.emu.lib.desmume_memory_write_short.argtypes = [c_int, c_uint16]
        self.emu.lib.desmume_memory_write_long.argtypes = [c_int, c_uint32]

        self.emu.lib.desmume_memory_read_register.argtypes = [c_char_p]
        self.emu.lib.desmume_memory_write_register.argtypes = [c_char_p, c_int]

        # Used to make sure that callbacks aren't GCed.
        # TODO: Some way to clean this up again.
        self._registered_cbs = []

    @property
    def unsigned(self):
        return self._unsigned

    @property
    def signed(self):
        return self._signed

    @property
    def register_arm9(self):
        return self._register_arm9

    @property
    def register_arm7(self):
        return self._register_arm7

    def read(self, start: int, end: int, size: int, signed: bool) -> Union[int, bytes, List[int]]:
        """
        Read part of NDS memory.

        Allowed sizes: 1 = byte, 2 = short, 4 = long

        If start and end are equal, returns an integer based on the size and the signed flag.

        If not, but size is 1 and signed is False, returns a bytes object with all bytes between start and end.
        Otherwise returns a list of ints based on size and signed.
        """
        if size is None:
            size = 1
        if start == end:
            # Read a single value, what kind depends on size
            if signed:
                if size == 1:
                    return self.emu.lib.desmume_memory_read_byte_signed(start)
                elif size == 2:
                    return self.emu.lib.desmume_memory_read_short_signed(start)
                elif size == 4:
                    return self.emu.lib.desmume_memory_read_long_signed(start)
            else:
                if size == 1:
                    return self.emu.lib.desmume_memory_read_byte(start)
                elif size == 2:
                    return self.emu.lib.desmume_memory_read_short(start)
                elif size == 4:
                    return self.emu.lib.desmume_memory_read_long(start)
            raise ValueError("Invalid size.")
        # Read a range.
        if signed:
            if size == 1:
                b = []
                for i, addr in enumerate(range(start, end, size)):
                    b.append(self.emu.lib.desmume_memory_read_byte_signed(addr))
            elif size == 2:
                b = []
                for i, addr in enumerate(range(start, end, size)):
                    b.append(self.emu.lib.desmume_memory_read_short_signed(addr))
            elif size == 4:
                b = []
                for i, addr in enumerate(range(start, end, size)):
                    b.append(self.emu.lib.desmume_memory_read_long_signed(addr))
            else:
                raise ValueError("Invalid size.")
        else:
            if size == 1:
                b = bytearray(int(end - start))
                for i, addr in enumerate(range(start, end, size)):
                    b[i] = self.emu.lib.desmume_memory_read_byte(addr)
                b = bytes(b)
            elif size == 2:
                b = []
                for i, addr in enumerate(range(start, end, size)):
                    b.append(self.emu.lib.desmume_memory_read_short(addr))
            elif size == 4:
                b = []
                for i, addr in enumerate(range(start, end, size)):
                    b.append(self.emu.lib.desmume_memory_read_long(addr))
            else:
                raise ValueError("Invalid size.")
        return b

    def write(self, start: int, end: int, size: int, value: Union[bytes, List[int]]):
        if start == end:
            end += 1  # Write at least one.
        if size == 1:
            for i, addr in enumerate(range(start, end, size)):
                self.emu.lib.desmume_memory_write_byte(addr, c_uint8(value[i]))
        elif size == 2:
            for i, addr in enumerate(range(start, end, size)):
                # value must be List[int]
                self.emu.lib.desmume_memory_write_short(addr, c_uint16(value[i]))
        elif size == 4:
            for i, addr in enumerate(range(start, end, size)):
                # value must be List[int]
                self.emu.lib.desmume_memory_write_long(addr, c_uint32(value[i]))
        else:
            raise ValueError("Invalid size.")

    def read_string(self, address: int, codec='windows-1255'):
        """Read a string, beginning at address"""
        max_len = 50
        string_buff = bytearray(max_len)
        cur_byte = self.unsigned.read_byte(address)
        i = 0
        while cur_byte != 0:
            if i >= max_len:
                max_len += 50
                string_buff += bytearray(50)
            string_buff[i] = cur_byte
            i += 1
            cur_byte = self.unsigned.read_byte(address + i)
        return str(memoryview(string_buff)[:i], codec, 'ignore')

    def write_byte(self, addr: int, value: int):
        self.write(addr, addr, 1, [value])

    def write_short(self, addr: int, value: int):
        self.write(addr, addr, 2, [value])

    def write_long(self, addr: int, value: int):
        self.write(addr, addr, 4, [value])

    def register_write(self, address: int, callback: Optional[MemoryCbFn], size=1):
        casted_cbfn = callback
        if callback is not None:
            casted_cbfn = MEMORY_CB_FN(callback)
            self._registered_cbs.append(casted_cbfn)
        self.emu.lib.desmume_memory_register_write(address, size, casted_cbfn)

    def register_read(self, address: int, callback: Optional[MemoryCbFn], size=1):
        casted_cbfn = callback
        if callback is not None:
            casted_cbfn = MEMORY_CB_FN(callback)
            self._registered_cbs.append(casted_cbfn)
        self.emu.lib.desmume_memory_register_read(address, size, casted_cbfn)

    def register_exec(self, address: int, callback: Optional[MemoryCbFn], size=2):
        casted_cbfn = callback
        if callback is not None:
            casted_cbfn = MEMORY_CB_FN(callback)
            self._registered_cbs.append(casted_cbfn)
        self.emu.lib.desmume_memory_register_exec(address, size, casted_cbfn)


class DeSmuME:
    def __init__(self, dl_name: str = None):
        self.lib = None

        # Load the correct library
        if dl_name is None:
            # Try autodetect / CWD
            try:
                if platform.system().lower().startswith('windows'):
                    dl_name = "libdesmume.dll"
                    os.add_dll_directory(os.getcwd())
                elif platform.system().lower().startswith('linux'):
                    dl_name = "libdesmume.so"
                elif platform.system().lower().startswith('darwin'):
                    dl_name = "libdesmume.dylib"
                else:
                    RuntimeError(f"Unknown platform {platform.system()}, can't autodetect DLL to load.")

                self.lib = cdll.LoadLibrary(dl_name)
            except OSError:
                # Okay now try the package directory
                dl_name = os.path.dirname(os.path.realpath(__file__))
                if platform.system().lower().startswith('windows'):
                    os.add_dll_directory(dl_name)
                    dl_name = os.path.join(dl_name, "libdesmume.dll")
                elif platform.system().lower().startswith('linux'):
                    dl_name = os.path.join(dl_name, "libdesmume.so")
                elif platform.system().lower().startswith('darwin'):
                    dl_name = os.path.join(dl_name, "libdesmume.dylib")

                self.lib = cdll.LoadLibrary(dl_name)
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
        self._memory = DeSmuME_Memory(self)
        self._sdl_window = None
        self._raw_buffer_rgbx = None

    def __del__(self):
        if self.lib is not None:
            self.lib.desmume_free()
            self._input.__del__()
            if self._sdl_window:
                self._sdl_window.__del__()
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

    @property
    def memory(self):
        return self._memory

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


def test_movie(emu: 'DeSmuME'):

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


def test_memory_access(emu: 'DeSmuME'):
    # Below tests only works with EU PMD EoS:
    start_of_arm_ov11_eu = 0x22DCB80
    start_of_arm_ov11_us = 0x22DD8E0
    start_of_arm_ov11 = start_of_arm_ov11_eu

    start_of_loop_fn = start_of_arm_ov11 + 0xF24
    start_of_loop_fn_loop = start_of_loop_fn + 0x2C
    start_of_switch_last_return_code = start_of_loop_fn + 0x34
    start_of_call_to_opcode_parsing = start_of_loop_fn + 0x5C - 4

    emu.volume_set(0)

    for i in range(0, 300):
        win.process_input()
        emu.cycle()
        win.draw()

    print("TESTING RANGE UNSIGNED")
    print(emu.memory.unsigned[start_of_loop_fn:start_of_loop_fn+4])
    print(" == bytes(f8432de9) ?")
    print(emu.memory.unsigned[start_of_loop_fn:start_of_loop_fn+4:2])
    print(" == [17400, 59693] ?")
    print(emu.memory.unsigned[start_of_loop_fn:start_of_loop_fn+4:4])
    print(" == [3912057848] ?")

    print("TESTING RANGE SIGNED")
    print(emu.memory.signed[start_of_loop_fn:start_of_loop_fn+4])
    print(" == [-8, 67, 45, -23] ?")
    print(emu.memory.signed[start_of_loop_fn:start_of_loop_fn+4:2])
    print(" == [17400, -5843] ?")
    print(emu.memory.signed[start_of_loop_fn:start_of_loop_fn+4:4])
    print(" == [-382909448] ?")

    print("TESTING SINGLE UNSIGNED")
    print(emu.memory.unsigned[start_of_loop_fn])
    print(" == f8 ?")
    print(emu.memory.unsigned[start_of_loop_fn:start_of_loop_fn:2])
    print(" == 17400 ?")
    print(emu.memory.unsigned[start_of_loop_fn:start_of_loop_fn:4])
    print(" == 3912057848 ?")

    print("TESTING SINGLE SIGNED")
    print(emu.memory.signed[start_of_loop_fn])
    print(" == -8 ?")
    print(emu.memory.signed[start_of_loop_fn:start_of_loop_fn:2])
    print(" == 17400 ?")
    print(emu.memory.signed[start_of_loop_fn:start_of_loop_fn:4])
    print(" == -382909448 ?")

    def test_register_exec_and_read_write(address, size):
        #print(address)
        #print(emu.memory.register_arm9.pc)
        #print(start_of_loop_fn_loop)
        #assert(address == start_of_loop_fn_loop)
        #assert(emu.memory.register_arm9.pc == start_of_loop_fn_loop + 8)
        address_of_struct = emu.memory.register_arm9.r6
        address_cuurent_op_code = emu.memory.unsigned[address_of_struct + 0x1c]
        print(f"{emu.memory.unsigned.read_short(address_cuurent_op_code):0x}")

    def test_register_exec_and_read_write_switch(address, size):
        print(f"LAST RETURN CODE: {emu.memory.register_arm9.r0}")

    emu.memory.register_exec(start_of_call_to_opcode_parsing, test_register_exec_and_read_write)
    emu.memory.register_exec(start_of_switch_last_return_code, test_register_exec_and_read_write_switch)

    emu.reset()

    while not win.has_quit():
        win.process_input()
        emu.cycle()
        win.draw()


def test_manual_fs(emu, win):
    i = 1
    while not win.has_quit():
        win.process_input()
        emu.cycle()
        i += 1
        if i % 20 == 0:
            win.draw()
            i = 1


if __name__ == '__main__':
    emu = DeSmuME()

    #emu.set_language(Language.GERMAN)
    emu.open("../../skyworkcopy.nds")
    win = emu.create_sdl_window(use_opengl_if_possible=True)

    #test_movie(emu)

    #test_memory_access(emu)
    test_manual_fs(emu, win)

    #emu.screenshot().show()
