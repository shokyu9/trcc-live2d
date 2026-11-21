# Native renderer

The `native` backend uses official Live2D Cubism Native SDK 5 R5 through
the third-party `live2d-py` 1.0.0 binary binding. This project is not an
official Live2D product. Live2D Core and Framework retain their own licenses;
installing the binding does not replace those license terms.

Runtime: Python 3.12 x64, live2d-py 1.0.0, PyOpenGL 3.1.10, PySide6, NumPy.
Rendering uses a Qt offscreen OpenGL context and framebuffer. Frames are
straight-alpha RGBA with a 12-byte little-endian header: byte count, width,
height. Logs go to stderr. JSON telemetry arrives on stdin; EOF closes the
renderer. No Chromium or PNG encoding is used by this backend.

Supports model3.json, motions, expressions, automatic blinking/breathing,
temperature expressions, parameter overrides, part opacity and frame rate.
The WebGL adapters remain available. Their randomized gesture scheduler is
not yet shared by the native backend.
