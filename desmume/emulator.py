"""
This module contains the Python interface for DeSmuME.

:class:`DeSmuME` is the main entrypoint to load and interact with the emulator.
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
"""
A callback function for the memory hooks. The first parameter of the callback function will receive the watched address,
the second the size of the event that triggered it, in bytes (eg. how many bytes were written / read).
"""


def strbytes(s):
    return s.encode('utf-8')


class Language(Enum):
    """Language codes."""
    JAPANESE = 0
    ENGLISH = 1
    FRENCH = 2
    GERMAN = 3
    ITALIAN = 4
    SPANISH = 5


class StartFrom(Enum):
    """Start codes for movie recording."""
    START_BLANK = 0
    START_SRAM = 1
    START_SAVESTATE = 2


class DeSmuME_SDL_Window:
    """
    A window that displays the emulator and processes touchscreen and keyboard inputs (default keyboard
    configuration only).
    This is meant to be a simple way to use and test the library, for intergration in custom UIs you
    probably want to process input and display manually.

    Should not be instantiated manually!
    """
    def __init__(self, emu: 'DeSmuME', auto_pause=True, use_opengl_if_possible=True):
        self.lib = emu.lib
        self.lib.desmume_draw_window_init(bool(auto_pause), bool(use_opengl_if_possible))

    def __del__(self):
        self.destroy()

    def destroy(self):
        """Destroy the window."""
        self.lib.desmume_draw_window_free()

    def draw(self):
        """Draw the current framebuffer to the window."""
        self.lib.desmume_draw_window_frame()

    def process_input(self):
        """Process the touchscreen input for the current cycle."""
        self.lib.desmume_draw_window_input()

    def has_quit(self) -> bool:
        """Returns true, when the window was closed by the user."""
        return bool(self.lib.desmume_draw_window_has_quit())


class DeSmuME_Input:
    """Manage input processing for the emulator. Should not be instantiated manually!"""
    def __init__(self, emu: 'DeSmuME'):
        self.emu = emu
        self.lib = emu.lib
        self.has_joy = False

    def __del__(self):
        if self.has_joy:
            self.joy_uninit()

    def joy_init(self):
        """Initialize the joystick input processing. Call this to enable automatic joystick input processing."""
        if not self.has_joy:
            self.emu.lib.desmume_input_joy_init()
            self.has_joy = True

    def joy_uninit(self):
        """De-initialize the joystick input processing."""
        if self.has_joy:
            self.lib.desmume_input_joy_uninit()

    def joy_number_connected(self) -> int:
        """Returns the number of connected joysticks. Joysticks must be initialized."""
        if self.has_joy:
            return self.emu.lib.desmume_input_joy_number_connected()
        raise ValueError("Joystick not initialized.")

    def joy_get_key(self, index: int) -> int:
        """Get the joystick key assigned to the specified emulator key. Joysticks must be initialized."""
        if self.has_joy:
            return self.emu.lib.desmume_input_joy_get_key(index)
        raise ValueError("Joystick not initialized.")

    def joy_get_set_key(self, index: int) -> int:
        """
        Pause the thread and wait for the user to press a button.
        This button will be assigned to the specified emulator key. Joysticks must be initialized.
        """
        if self.has_joy:
            return self.emu.lib.desmume_input_joy_get_set_key(index)
        raise ValueError("Joystick not initialized.")

    def joy_set_key(self, index: int, joystick_key_index: int):
        """
        Sets the emulator key ``index`` to the specified joystick key ``joystick_key_index``.
        Joysticks must be initialized.
        """
        if self.has_joy:
            self.emu.lib.desmume_input_joy_set_key(index, joystick_key_index)
            return
        raise ValueError("Joystick not initialized.")

    def keypad_update(self, keys: int) -> int:
        """
        Update the keypad (pressed DS buttons) of currently pressed emulator keys.
        You should probably use ``keypad_add_key`` and ``keypad_rm_key`` instead.
        """
        self.emu.lib.desmume_input_keypad_update.argtypes = [c_uint16]
        return self.emu.lib.desmume_input_keypad_update(keys)

    def keypad_get(self) -> int:
        """Returns the current emulator key keypad (pressed DS buttons)."""
        self.emu.lib.desmume_input_keypad_update.restype = c_uint16
        return self.emu.lib.desmume_input_keypad_get()

    def keypad_add_key(self, key: int):
        """
        Adds a key to the emulators current keymask (presses it). To be used with ``keymask``:

        >>> from desmume.controls import keymask, Keys
        >>> keym = keymask(Keys.KEY_A)
        >>> DeSmuME().input.keypad_add_key(keym)
        """
        old_keypad = self.keypad_get()
        self.keypad_update(add_key(old_keypad, key))

    def keypad_rm_key(self, key: int):
        """
        Removes a key from the emulators current keymask (releases it).
        See ``keypad_add_key`` for a usage example.
        """
        old_keypad = self.keypad_get()
        self.keypad_update(rm_key(old_keypad, key))

    def touch_set_pos(self, x: int, y: int):
        """Set the specified coordinate of the screen to be touched."""
        self.emu.lib.desmume_input_set_touch_pos(x, y)

    def touch_release(self):
        """Tell the emulator, that the user released touching the screen."""
        self.emu.lib.desmume_input_release_touch()


class DeSmuME_Savestate:
    """
    Load and save savestates. Either slots can be used  (maximum number of slots is in the constant ``NB_STATES``),
    or savestates can be directly loaded from / saved to files.

    Should not be instantiated manually!
    """
    def __init__(self, emu: 'DeSmuME'):
        self.emu = emu

    def scan(self):
        """Scan all savestate slots for if they exist or not. Required to be called before calling ``exists``."""
        self.emu.lib.desmume_savestate_scan()

    def exists(self, slot_id: int) -> bool:
        """Returns whether or not a savestate in the specified slot exists."""
        return bool(self.emu.lib.desmume_savestate_slot_exists(slot_id))

    def load(self, slot_id: int):
        """Load the savestate in the specified slot. It needs to exist."""
        return self.emu.lib.desmume_savestate_slot_load(slot_id)

    def save(self, slot_id: int):
        """Save the current game state to the savestate in the specified slot."""
        return self.emu.lib.desmume_savestate_slot_save(slot_id)

    def load_file(self, file_name: str):
        """
        Load a savestate from file.

        :raise: RuntimeError If the savestate could not be loaded.
        """
        if not self.emu.lib.desmume_savestate_load(c_char_p(strbytes(file_name))):
            raise RuntimeError("Unable to load savesate.")

    def save_file(self, file_name: str):
        """
        Save a savestate to file.

        :raise: RuntimeError If the savestate could not be saved.
        """
        if not self.emu.lib.desmume_savestate_save(c_char_p(strbytes(file_name))):
            raise RuntimeError("Unable to save savesate.")

    def date(self, slot_id: int) -> str:
        """Return the date a savestate was saved at as a string."""
        self.emu.lib.desmume_savestate_slot_date.restype = c_char_p
        return str(self.emu.lib.desmume_savestate_slot_date(slot_id), 'utf-8')


class DeSmuME_Date(Structure):
    """A date C struct, to be used with setting a date for movie recording."""
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
    """Record and play movies. Should not be instantiated manually!"""
    def __init__(self, emu: 'DeSmuME'):
        self.emu = emu

    def play(self, file_name: str):
        """
        Load a movie file from a file and play it back.

        :raise: RuntimeError If playback failed.
        """
        self.emu.lib.desmume_movie_play.restype = c_char_p
        err = self.emu.lib.desmume_movie_play(c_char_p(strbytes(file_name)))
        if err is not None and err != "":
            raise RuntimeError(str(err, 'utf-8'))

    def record(
            self, file_name: str, author_name: str,
            start_from: StartFrom = StartFrom.START_BLANK, sram_save: str = "", rtc_date: DeSmuME_Date = None
    ):
        """
        Record a movie.

        :param file_name: The name of the file to save to.
        :param author_name: Name of the author of the movie.
        :param start_from: Where to start the recording from.
        :param sram_save: Filename of the SRAM save to use, optional.
        :param rtc_date: Date to set the real-time-clock to, optional, defaults to now.
        :return:
        """
        if not rtc_date:
            self.emu.lib.desmume_movie_record(
                c_char_p(strbytes(file_name)), c_char_p(strbytes(author_name)), start_from.value, c_char_p(strbytes(sram_save))
            )
        else:
            self.emu.lib.desmume_movie_record_from_date(
                c_char_p(strbytes(file_name)), c_char_p(strbytes(author_name)), start_from.value, c_char_p(strbytes(sram_save)), rtc_date
            )

    def stop(self):
        """Stops the current movie playback."""
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
    """
    Pythonic accessor class for manipulating the memory.

    Access a single unsigned byte of memory at offset 0x100:

    >>> emu_memory = DeSmuME().memory
    >>> emu_memory.unsigned[0x100]
    <<< 3

    Access a subset of the memory as bytes:

    >>> emu_memory = DeSmuME().memory
    >>> emu_memory.unsigned[0x100:0x200]
    <<< bytes(...)

    Access a subset of the memory as signed integers:

    >>> emu_memory = DeSmuME().memory
    >>> emu_memory.signed[0x100:0x200]
    <<< [-3, 2, ...]

    Access a subset of memory as 4-byte unsigned integers:

    >>> emu_memory = DeSmuME().memory
    >>> emu_memory.unsigned[0x100:0x200:4]
    <<< [-236, 1002, ...]

    Writing to memory works the same way. It doesn't matter if you use the signed or unsigned accessor for this, both
    work the same:

    >>> emu_memory = DeSmuME().memory
    >>> emu_memory.unsigned[0x100] = 2

    You can also use the ``read_*`` methods instead for a more verbose way to read the memory as integers.
    For writing those methods can be found in the ``DeSmuME_Memory`` parent object.

    Should not be instantiated manually!

    """
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

    def read_byte(self, addr: int) -> int:
        """Read a 1-byte size integer at the specified address."""
        return self[addr]

    def read_short(self, addr: int) -> int:
        """Read a 2-byte size integer at the specified address."""
        return self[addr:addr:2]

    def read_long(self, addr: int) -> int:
        """Read a 2-byte size integer at the specified address."""
        return self[addr:addr:4]


class RegisterAccessor:
    """
    Access the registers of the emulator. The properties are the register names.
    ``rX`` are the numbered register names, some registers are available via aliases.
    Returned are integers.

    You can also get a register value by accessing this object:

    >>> DeSmuME().memory.register_arm9[0] == DeSmuME().memory.register_arm9.r0
    <<< True

    Should not be instantiated manually!

    """
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
        """Alias for r13."""
        return self.r13

    @sp.setter
    def sp(self, value):
        self.r13 = value

    @property
    def lr(self):
        """Alias for r14."""
        return self.r14

    @lr.setter
    def lr(self, value):
        self.r14 = value

    @property
    def pc(self):
        """Alias for r15."""
        return self.r15

    @pc.setter
    def pc(self, value):
        self.r15 = value

    # </editor-fold>
RegisterAccesor = RegisterAccessor  # Typo alias for backwards-comaptibility.


class DeSmuME_Memory:
    """Access and manipulate the memory of the emulator. Should not be instantiated manually!"""
    def __init__(self, emu: 'DeSmuME'):
        self.emu = emu
        self._unsigned: MemoryAccessor = MemoryAccessor(False, self)
        self._signed: MemoryAccessor = MemoryAccessor(True, self)
        self._register_arm9: RegisterAccessor = RegisterAccessor("arm9.", self)
        self._register_arm7: RegisterAccessor = RegisterAccessor("arm7.", self)

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
    def unsigned(self) -> MemoryAccessor:
        """
        The accessor for accessing the memory values as raw unsigned bytes/ints.

        :type: MemoryAccessor
        """
        return self._unsigned

    @property
    def signed(self) -> MemoryAccessor:
        """
        The accessor for accessing the memory values as signed ints.

        :type: MemoryAccessor
        """
        return self._signed

    @property
    def register_arm9(self) -> RegisterAccessor:
        """
        ARM9 Registers.

        :type: RegisterAccessor
        """
        return self._register_arm9

    @property
    def register_arm7(self) -> RegisterAccessor:
        """
        ARM7 Registers.

        :type: RegisterAccessor
        """
        return self._register_arm7

    def read(self, start: int, end: int, size: int, signed: bool) -> Union[int, bytes, List[int]]:
        """
        Read part of NDS memory. You probably don't want to use this. Use the ``unsigned`` and ``signed``
        properties instead.

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
        """
        Write part of NDS memory. You probably don't want to use this. Use the ``unsigned`` and ``signed``
        properties instead, or the ``write_*`` methods.
        """
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
        """Read a null-terminated string, beginning at address."""
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
        """Write a 1-byte integer to the memory at the specified address."""
        self.write(addr, addr, 1, [value])

    def write_short(self, addr: int, value: int):
        """Write a 2-byte integer to the memory at the specified address."""
        self.write(addr, addr, 2, [value])

    def write_long(self, addr: int, value: int):
        """Write a 4-byte integer to the memory at the specified address."""
        self.write(addr, addr, 4, [value])

    def get_next_instruction(self) -> int:
        """Returns the next instruction to be executed by the ARM9 processor."""
        return self.emu.lib.desmume_memory_get_next_instruction()

    def set_next_instruction(self, address: int):
        """
        Sets the next instruction to be executed by the ARM9 processor.
        You should probably also consider updating the PC.
        """
        self.emu.lib.desmume_memory_set_next_instruction(address)

    def register_write(self, address: int, callback: Optional[MemoryCbFn], size=1):
        """
        Add a memory callback for when the memory at the specified address was changed.

        Setting a callback will override the previously registered one for this address.
        Set callback to None, to remove the callback for this address.

        A usage example can be found for ``register_exec``.

        :param address: The address to monitor.
        :param callback: This callback will be called when the memory was written to. See ``MemoryCbFn``.
        :param size: The maximum size that will be watched. If you set this to 4 for example,
                     a range of (address, address + 3) will be monitored.
        """
        casted_cbfn = callback
        if callback is not None:
            casted_cbfn = MEMORY_CB_FN(callback)
            self._registered_cbs.append(casted_cbfn)
        self.emu.lib.desmume_memory_register_write(address, size, casted_cbfn)

    def register_read(self, address: int, callback: Optional[MemoryCbFn], size=1):
        """
        Add a memory callback for when the memory at the specified address was read.

        Setting a callback will override the previously registered one for this address.
        Set callback to None, to remove the callback for this address.

        A usage example can be found for ``register_exec``.

        :param address: The address to monitor.
        :param callback: This callback will be called when the memory was read. See ``MemoryCbFn``.
        :param size: The maximum size that will be watched. If you set this to 4 for example,
                     a range of (address, address + 3) will be monitored.
        """
        casted_cbfn = callback
        if callback is not None:
            casted_cbfn = MEMORY_CB_FN(callback)
            self._registered_cbs.append(casted_cbfn)
        self.emu.lib.desmume_memory_register_read(address, size, casted_cbfn)

    def register_exec(self, address: int, callback: Optional[MemoryCbFn], size=2):
        """
        Add a memory callback for when the PC processed the operation at the specified address.

        Setting a callback will override the previously registered one for this address.
        Set callback to None, to remove the callback for this address.

        Example (will print 'Hello World', whenever the PC executes the code at 0x022f8818):

        >>> def my_callback(address, size):
        >>>     print("Hello World!")
        >>>
        >>> DeSmuME().memory.register_exec(0x022f8818, my_callback)

        :param address: The address to monitor.
        :param callback: This callback will be called when the operation was executed. See ``MemoryCbFn``.
        :param size: Leave this at 2.
        """
        casted_cbfn = callback
        if callback is not None:
            casted_cbfn = MEMORY_CB_FN(callback)
            self._registered_cbs.append(casted_cbfn)
        self.emu.lib.desmume_memory_register_exec(address, size, casted_cbfn)


class DeSmuME:
    """DeSmuME, the Nintendo DS emulator."""
    def __init__(self, dl_name: str = None):
        """
        Initializes a new emulator instance.
        A path to the shard library for DeSmuME can be passed, if not it will be auto-detected.
        """
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
        """Destroy the emulator and free memory. Calling any method after this WILL result in a crash."""
        self.__del__()

    @property
    def input(self):
        """
        Keyboard and joystick configuration.

        :type: DeSmuME_Input
        """
        return self._input

    @property
    def savestate(self):
        """
        Loading and saving savestates.

        :type: DeSmuME_Savestate
        """
        return self._savestate

    @property
    def movie(self):
        """
        Recording and playing back movies.

        :type: DeSmuME_Movie
        """
        return self._movie

    @property
    def memory(self):
        """
        Accessing and manipulating the memory.

        :type: DeSmuME_Memory
        """
        return self._memory

    def set_language(self, lang: Language):
        """Set the current firmware language."""
        self.lib.desmume_set_language(lang.value)

    def open(self, file_name: str, auto_resume=True):
        """
        Open a ROM by file name.

        If ``auto_resume`` is True, the emulator will automatically begin emulating the game.
        Otherwise the emulator is paused and you may call ``resume`` to unpause it.
        """
        if self.lib.desmume_open(c_char_p(strbytes(file_name))) < 0:
            raise RuntimeError("Unable to open ROM file.")
        if auto_resume:
            self.resume()

    def close(self):
        """
        Close a previously opened ROM, freeing up memory.
        You don't need to call this before opening a new ROM (it is done automatically).
        """
        self.lib.desmume_close()

    def set_savetype(self, value: int):
        """
        Set the type of the SRAM. Please see the DeSmuME documentation for possible values.
        0 is auto-detect and set by default.
        """
        # TODO: Enum?
        self.lib.desmume_set_savetype(value)

    def pause(self):
        """Pause the emulator."""
        self.lib.desmume_pause()

    def resume(self, keep_keypad=False):
        """
        Resume / unpause the emulator. This will reset the keypad (release all keys),
        except if ``keep_keypad`` is provided.
        """
        if keep_keypad:
            self.input.keypad_update(0)
        self.lib.desmume_resume()

    def reset(self):
        """Resets the emulator / restarts the current game."""
        self.lib.desmume_reset()

    def is_running(self) -> bool:
        """Returns ``True``, if a game is loaded and the emulator is running (not paused)."""
        return bool(self.lib.desmume_running())

    def skip_next_frame(self):
        """Tell the emulator to skip the next frame."""
        self.lib.desmume_skip_next_frame()

    def cycle(self, with_joystick=True):
        """
        Cycle one game cycle / frame. Set ``with_joystick`` to
        ``False``, if joystick processing was not initialized.
        """
        self.lib.desmume_cycle(with_joystick)

    def has_opengl(self) -> bool:
        """Returns ``True``, if OpenGL is available for rendering."""
        return bool(self.lib.desmume_has_opengl())

    def create_sdl_window(self, auto_pause=False, use_opengl_if_possible=True) -> DeSmuME_SDL_Window:
        """
        Create an SDL window for drawing the
        emulator in and processing inputs.

        :param auto_pause: Whether or not "tabbing out" of the window pauses the game.
        :param use_opengl_if_possible: Whether or not to use OpenGL for rendering, if available.

        """
        if not self._sdl_window:
            self._sdl_window = DeSmuME_SDL_Window(self, auto_pause, use_opengl_if_possible)
        return self._sdl_window

    def display_buffer(self):
        """Return the display buffer in the internal format. You probably want to use display_buffer_as_rgbx instead."""
        self.lib.desmume_draw_raw.restype = POINTER(c_uint16)
        return self.lib.desmume_draw_raw()

    def display_buffer_as_rgbx(self, reuse_buffer=True) -> memoryview:
        """
        Return the display buffer as RGBX color values,
        see the screen size constants for how many pixels make up lines.
        """
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
        """Convert the current display buffer into a PIL image."""
        buff = create_string_buffer(SCREEN_WIDTH * SCREEN_HEIGHT_BOTH * 3)
        self.lib.desmume_screenshot(cast(buff, c_char_p))

        return Image.frombuffer('RGB', (SCREEN_WIDTH, SCREEN_HEIGHT_BOTH), buff.raw, 'raw', 'RGB', 0, 1)

    def get_ticks(self) -> int:
        """Get the current SDL tick number."""
        return self.lib.desmume_sdl_get_ticks()

    def volume_get(self) -> int:
        """Get the current value (between 0 - 100)."""
        return self.lib.desmume_volume_get()

    def volume_set(self, volume: int):
        """Set the current value (to a value between 0 - 100)."""
        return self.lib.desmume_volume_set(volume)

    def gpu_get_layer_main_enable_state(self, layer_index: int):
        """Get the current display status of the specified layer on the main GPU."""
        return bool(self.lib.desmume_gpu_get_layer_main_enable_state(layer_index))

    def gpu_get_layer_sub_enable_state(self, layer_index: int):
        """Get the current display status of the specified layer on the sub GPU."""
        return bool(self.lib.desmume_gpu_get_layer_sub_enable_state(layer_index))

    def gpu_set_layer_main_enable_state(self, layer_index: int, state: bool):
        """Set the current display status of the specified layer on the main GPU."""
        self.lib.desmume_gpu_set_layer_main_enable_state(layer_index, state)

    def gpu_set_layer_sub_enable_state(self, layer_index: int, state: bool):
        """Set the current display status of the specified layer on the sub GPU."""
        self.lib.desmume_gpu_set_layer_sub_enable_state(layer_index, state)
