# TRCC Live2D / 实时模型叠加

中文：为第三方开源 TRCC Linux 的 Windows 版添加 Live2D 实时透明叠加。非利民或 Live2D 官方产品。

English: Real-time transparent Live2D overlays for the Windows version of third-party TRCC Linux. Not an official Thermalright or Live2D product.

## 功能 / Features

- Classic / PixiJS 6、LipsyncPatch / PixiJS 7、Cubism Native SDK / OpenGL 三种适配器。
  Three adapters, with the native backend using official Cubism Native SDK through third-party live2d-py.
- 缩放、位置、分辨率、表情、动作、温度联动、部件透明度、自动眨眼与呼吸。
  Scale, position, resolution, expressions, motions, temperature reactions, part opacity, blinking and breathing.
- 参数实时更新并保存；帧率设置 **4–30 FPS**，TRCC 帧源以 30 FPS 调度。
  Live persistent settings; **4–30 FPS** rendering and a 30 FPS TRCC source schedule.
- 蒙版覆盖模型开关；温度文字保持在上方。
  Optional mask above the model, with metrics on top.

实际屏幕帧率取决于模型、分辨率、GPU 和 USB 传输，30 FPS 为软件上限。

Actual panel throughput depends on model, resolution, GPU and USB transport. 30 FPS is the software ceiling.

## 安装 / Installation

Windows 10/11 x64、Python 3.12、Node.js 20+。先安装基础 TRCC 的设备驱动及 Windows 服务。

Requires Windows 10/11 x64, Python 3.12, Node.js 20+, device drivers and the base TRCC Windows service.

```powershell
py -3.12 -m pip install trcc-linux==9.12.2
py -3.12 install.py
py -3.12 tools/customize_about.py
.\run.ps1
```

在模块页开启 Live2D，选择自己的 `.model3.json` 和官方 Cubism Core for Web，再连接设备、启用叠加层。多个 TRCC 界面应共用一个后台，避免 USB 争用。

Enable Live2D in Modules, select your model3.json and official Cubism Core for Web, connect the device and enable the overlay. Multiple TRCC interfaces must share one backend to avoid USB contention.

## 原生 OpenGL / Native OpenGL

原生后端通过 Qt 离屏 OpenGL 和四个遮罩缓冲输出透明 RGBA，不使用 Chromium 或 PNG 编解码。已在 RTX 5060 上验证模型渲染和 TRCC 帧源读取；尚未测得统一的资源降幅。

Native rendering uses Qt offscreen OpenGL and four mask buffers, transferring RGBA without Chromium or PNG encoding. Model rendering and TRCC frame-source reading were tested on RTX 5060; no universal resource savings are claimed.

WebGL 随机场景动作尚未全部移植到原生后端。Windows 硬件兼容性由基础 TRCC 决定。

The WebGL random scenario gesture scheduler is not fully ported to native. Windows device compatibility depends on base TRCC.

## 关于页 / About

`tools/customize_about.py` 移除指定 Inspired by 段落、介绍和社区标语；保留依赖署名及许可证。

The customization script removes the requested inspiration prose, introduction and slogan, retaining dependency attribution and licenses.

## 许可及源码范围 / Licensing and source scope

本项目 GPL-3.0-or-later，见 LICENSE。TRCC、PixiJS、live2d-py、官方 Cubism Core 和模型分别遵守各自许可。

Project: GPL-3.0-or-later; see LICENSE. TRCC, PixiJS, live2d-py, official Cubism Core and model assets retain their respective licenses.

源码不含用户模型、纹理、Cubism Core、浏览器、Python 环境、日志、令牌或个人配置。模型和 Core 请自行获取。

Source excludes user models, textures, Cubism Core, browser binaries, Python environments, logs, credentials and personal settings. Obtain model assets and Core separately.

上游 / Upstream: https://github.com/Lexonight1/thermalright-trcc-linux
