GTK+ Integration
================

If you are building a Gtk application, you might want to have a look at the code inside the
``frontend`` package. It contains a sample Gtk+ app to embed the emulator.

Rendering
---------
A renderer for ``Gtk.DrawingArea`` is available, using software rendering. A hardware accelerated
renderer is planned.

To use it:

.. code-block:: python

    import cairo
    from gi.repository import Gtk
    from desmume.emulator import DeSmuME
    from desmume.frontend.gtk_drawing_area_desmume import AbstractRenderer

    emu = DeSmuME()

    renderer = AbstractRenderer.impl(emu)
    renderer.init()

    # Example signal handlers:
    def on_wDrawScreen_main_draw_event(self, widget: Gtk.DrawingArea, ctx: cairo.Context, *args):
        return renderer.screen(screen_width, screen_height, ctx, 1)

    def on_wDrawScreen_main_configure_event(self, widget: Gtk.DrawingArea, *args):
        renderer.reshape(widget, 0)
        return True

    def on_wDrawScreen_sub_draw_event(self, widget: Gtk.DrawingArea, ctx: cairo.Context, *args):
        return renderer.screen(screen_width, screen_height, ctx, 1)

    def on_wDrawScreen_sub_configure_event(self, widget: Gtk.DrawingArea, *args):
        renderer.reshape(widget, 1)
        return True
