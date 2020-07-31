Quick Start
===========
This will help you get started in using the library. Please note that while
the library has basic error handling, passing some incorrect values may crash
the emulator and your application with it.

Run it, load a ROM, display it in a window
------------------------------------------
This is the most basic way to run the emulator. This is most useful when
writing small debugging applications or testing things out:

.. code-block:: python

    from desmume.emulator import DeSmuME

    emu = DeSmuME()
    emu.open('pathtorom.nds')

    # Create the window for the emulator
    window = emu.create_sdl_window()

    # Run the emulation as fast as possible until quit
    while not window.has_quit():
        window.process_input()   # Controls are the default DeSmuME controls, see below.
        emu.cycle()
        window.draw()

        # -- Do your custom stuff here, or use memory hooks. --

Default emulator controls:

- L: q
- R: w
- Y: a
- X: s
- A: x
- B: z
- Start: Return
- Select: Shift Right
- Up: Up, Down: Down, Left: Left, Right: Right

Joystick processing will also be avaiable, if gamepads are connected.

This easy way of running the emulator is not very configurable, the default
key bindings can't be changed.

Accessing memory and registers
------------------------------
You can access and manipulate the memory of the game while.
See :class:`~desmume.emulator.MemoryAccessor` for more
information.

You can also access the registers, see :class:`~desmume.emulator.RegisterAccessor`.

Registering read/write/exec hooks
---------------------------------
You can register custom Python functions, that will be executed when
memory is written to or read from or code is being executed.

See :func:`~desmume.emulator.DeSmuME_Memory.register_exec`,
:func:`~desmume.emulator.DeSmuME_Memory.register_read`,
:func:`~desmume.emulator.DeSmuME_Memory.register_write`.

Custom input processing
-----------------------
For custom input processing, use :class:`~desmume.emulator.DeSmuME_Input`:

.. code-block:: python

    from desmume.controls import keymask, Keys
    from desmume.emulator import DeSmuME

    emu = DeSmuME()

    # Press the A button
    a_keymask = keymask(Keys.KEY_A)
    emu.input.keypad_add_key(a_keymask)
    # Release the A button
    emu.input.keypad_rm_key(a_keymask)

    # Touch the screen
    emu.input.touch_set_pos(10, 20)
    # Move the touch
    emu.input.touch_set_pos(10, 30)
    # Release the touch
    emu.input.touch_release()

Joystick processing is done by the emulator. You can configure the keys however:

.. code-block:: python

    from desmume.emulator import DeSmuME
    # Pause the thread and wait for the user to press a joystick button. Configure
    # this pressed button as the A button.
    emu.input.joy_get_set_key(Keys.KEY_A)

Custom drawing
---------------
You can get the current display buffer and process it manually:

.. code-block:: python

    from desmume.emulator import DeSmuME, SCREEN_PIXEL_SIZE, SCREEN_WIDTH, SCREEN_HEIGHT

    emu = DeSmuME()

    # Example code to convert the framebuffer into two Cairo surfaces for both
    # screens.
    gpu_framebuffer = emu.display_buffer_as_rgbx()

    upper_image = cairo.ImageSurface.create_for_data(
        gpu_framebuffer[:SCREEN_PIXEL_SIZE*4], cairo.FORMAT_RGB24, SCREEN_WIDTH, SCREEN_HEIGHT
    )

    lower_image = cairo.ImageSurface.create_for_data(
        gpu_framebuffer[SCREEN_PIXEL_SIZE*4:], cairo.FORMAT_RGB24, SCREEN_WIDTH, SCREEN_HEIGHT
    )

If you are building a GTK+ app, you might want to have a look at `GTK+ Integration <gtk_integration.html>`_.
