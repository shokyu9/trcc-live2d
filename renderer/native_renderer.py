"""Cubism Native SDK (live2d-py binding) + offscreen Qt OpenGL RGBA pipe."""
import os
import sys
import json
import struct
import threading
import time
import math

# Native SDK log output must never corrupt the binary stdout channel.
output = os.fdopen(os.dup(sys.stdout.fileno()), "wb", buffering=0)
os.dup2(sys.stderr.fileno(), sys.stdout.fileno())

from PySide6.QtGui import QGuiApplication, QOffscreenSurface, QOpenGLContext, QSurfaceFormat
from PySide6.QtOpenGL import QOpenGLFramebufferObject, QOpenGLFramebufferObjectFormat
from OpenGL import GL
import numpy as np
import live2d

state = {"options": {}, "temperature": None, "warm": 55, "hot": 75}
stop = threading.Event()

def read_input():
    for line in sys.stdin:
        try:
            message = json.loads(line)
            if isinstance(message, dict):
                state.update(message)
        except ValueError:
            pass
    stop.set()

def main():
    model_file, width, height = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
    app = QGuiApplication([])
    fmt = QSurfaceFormat()
    fmt.setVersion(2, 1)
    fmt.setProfile(QSurfaceFormat.OpenGLContextProfile.CompatibilityProfile)
    fmt.setAlphaBufferSize(8)
    surface = QOffscreenSurface(); surface.setFormat(fmt); surface.create()
    context = QOpenGLContext(); context.setFormat(fmt)
    if not context.create() or not context.makeCurrent(surface):
        raise RuntimeError("无法创建原生 OpenGL 上下文")
    fbo_format = QOpenGLFramebufferObjectFormat()
    fbo_format.setAttachment(QOpenGLFramebufferObject.Attachment.CombinedDepthStencil)
    fbo = QOpenGLFramebufferObject(width, height, fbo_format)
    if not fbo.isValid():
        raise RuntimeError("无法创建透明帧缓冲")
    live2d.enableLog(False)
    live2d.init(); live2d.glInit()
    model = live2d.Model()
    model.LoadModelJson(model_file, False)
    model.Resize(width, height)
    model.CreateRenderer(4)
    model.ResetAllParameters()
    model.SaveParameters()
    part_indices = {name: index for index, name in enumerate(model.GetPartIds())}
    model.SetAutoBlink(True); model.SetAutoBreath(True)
    print("NATIVE_GL:" + str(GL.glGetString(GL.GL_RENDERER)), file=sys.stderr)
    threading.Thread(target=read_input, daemon=True).start()
    last_choice = None; band = "normal"; began = time.monotonic()
    try:
        while not stop.is_set():
            tick = time.monotonic(); options = dict(state.get("options", {}))
            fbo.bind(); GL.glViewport(0, 0, width, height)
            GL.glClearColor(0, 0, 0, 0)
            GL.glClear(GL.GL_COLOR_BUFFER_BIT | GL.GL_DEPTH_BUFFER_BIT)
            choice = (options.get("motion"), options.get("expression"))
            if choice != last_choice:
                last_choice = choice
                if choice[0]: model.StartMotion(choice[0], 0, 3)
                if choice[1]: model.SetExpression(choice[1])
                else: model.ResetExpressions()
            temperature = state.get("temperature")
            if isinstance(temperature, (float, int)) and options.get("temperature", True) and not choice[1]:
                next_band = "hot" if temperature >= state.get("hot",75) else "warm" if temperature >= state.get("warm",55) else "normal"
                if next_band != band:
                    band = next_band
                    if band == "normal": model.ResetExpressions()
                    else: model.SetExpression(band)
            model.SetAutoBlink(options.get("autoBlink", True))
            model.SetAutoBreath(False)
            model.Update()
            t = tick - began
            strength = float(options.get("idleStrength",1))
            if options.get("autoBreath",True):
                model.SetParamById("ParamBreath", (math.sin(t*1.6*float(options.get("breathSpeed",1)))+1)/2)
            if not choice[0] and options.get("autoSway",True):
                model.SetParamById("ParamAngleX", math.sin(t*.37)*7*strength)
                model.SetParamById("ParamAngleY", math.sin(t*.29)*4*strength)
            for key, value in options.get("parameters", {}).items():
                model.SetParamById(key, float(value))
            for key, value in options.get("parts", {}).items():
                if key in part_indices:
                    model.SetPartOpacity(part_indices[key], float(value))
            model.Draw()
            raw = GL.glReadPixels(0,0,width,height,GL.GL_RGBA,GL.GL_UNSIGNED_BYTE)
            pixels = np.frombuffer(raw, dtype=np.uint8).reshape(height,width,4)[::-1].copy()
            # Cubism OpenGL renders premultiplied alpha; TRCC accepts straight RGBA.
            alpha = pixels[:,:,3].astype(np.float32)
            nonzero = alpha > 0
            rgb = pixels[:,:,:3].astype(np.float32)
            rgb[nonzero] *= 255.0 / alpha[nonzero,None]
            pixels[:,:,:3] = np.clip(rgb,0,255).astype(np.uint8)
            data = pixels.tobytes()
            output.write(struct.pack("<III",len(data),width,height)); output.write(data)
            app.processEvents()
            stop.wait(max(0, 1/max(4,min(30,int(options.get("fps",8))))-(time.monotonic()-tick)))
    finally:
        del model
        live2d.dispose(); fbo.release(); context.doneCurrent()

if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print("FATAL:" + repr(error), file=sys.stderr)
        raise
