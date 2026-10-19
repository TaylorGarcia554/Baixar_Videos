# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all

# Coleta dados, binários e imports ocultos de cada pacote importante
ctk_d,  ctk_b,  ctk_h  = collect_all("customtkinter")
img_d,  img_b,  img_h  = collect_all("imageio_ffmpeg")
ytd_d,  ytd_b,  ytd_h  = collect_all("yt_dlp")
crt_d,  crt_b,  crt_h  = collect_all("certifi")   # certificados HTTPS do yt-dlp

a = Analysis(
    ["app.py"],
    pathex=[],
    binaries  = ctk_b  + img_b  + ytd_b  + crt_b,
    datas     = ctk_d  + img_d  + ytd_d  + crt_d  + [("icone.ico", ".")],
    hiddenimports = ctk_h + img_h + ytd_h + crt_h + [
        "certifi",
        "yt_dlp.extractor",
        "yt_dlp.postprocessor",
        "tkinter",
        "tkinter.filedialog",
        "tkinter.messagebox",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["matplotlib", "numpy", "pandas", "scipy", "notebook"],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="MioBaixador",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,          # Sem janela de terminal
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    icon="icone.ico",
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="MioBaixador",
)
