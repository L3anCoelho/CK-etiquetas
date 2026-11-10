# -*- mode: python ; coding: utf-8 -*-
# Empacotamento do CK Etiquetas (PyInstaller, modo pasta).
#
#   pyinstaller empacotamento\CKEtiquetas.spec --noconfirm --distpath dist --workpath build
#   (ou simplesmente:  powershell -ExecutionPolicy Bypass -File empacotamento\build.ps1)
#
# Resultado: dist\CKEtiquetas\CKEtiquetas.exe  (+ pasta _internal com Python, bibliotecas e recursos)
import os
from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files
from PyInstaller.utils.win32.versioninfo import (FixedFileInfo, StringFileInfo, StringStruct, StringTable,
                                                 VarFileInfo, VarStruct, VSVersionInfo)

RAIZ = Path(SPECPATH).parent  # noqa: F821 (SPECPATH é definido pelo PyInstaller)
VERSAO = (2, 0, 0, 0)

datas = [
    (str(RAIZ / "assets" / "logo_ck.png"), "assets"),
    (str(RAIZ / "assets" / "icone.ico"), "assets"),
    (str(RAIZ / "assets" / "transportadoras_padrao.json"), "assets"),
]
datas += collect_data_files("customtkinter")
datas += collect_data_files("tkinterdnd2")  # arrastar e soltar PDFs na janela

# Fontes do layout das etiquetas: embutidas para funcionar em PCs sem Office
# (Bookman Old Style vem com o Office, não com o Windows).
FONTES_WINDOWS = Path(os.environ.get("WINDIR", r"C:\Windows")) / "Fonts"


def achar_fonte(nomes):
    for pasta in (RAIZ / "assets" / "fonts", FONTES_WINDOWS):
        for nome in nomes:
            if (pasta / nome).is_file():
                return pasta / nome
    raise SystemExit(f"Fonte obrigatória não encontrada: {nomes}. Copie o arquivo para assets/fonts.")


for nomes in (("cambria.ttc", "cambria.ttf"), ("cambriab.ttf",), ("BOOKOS.TTF", "bookos.ttf")):
    datas.append((str(achar_fonte(nomes)), "assets/fonts"))

versao = VSVersionInfo(
    ffi=FixedFileInfo(filevers=VERSAO, prodvers=VERSAO),
    kids=[
        StringFileInfo([StringTable("041604B0", [
            StringStruct("CompanyName", "CK Autoshop"),
            StringStruct("FileDescription", "CK Etiquetas - Gerador de Etiquetas de Expedição"),
            StringStruct("FileVersion", ".".join(map(str, VERSAO))),
            StringStruct("InternalName", "CKEtiquetas"),
            StringStruct("OriginalFilename", "CKEtiquetas.exe"),
            StringStruct("ProductName", "CK Etiquetas"),
            StringStruct("ProductVersion", "2.0"),
            StringStruct("LegalCopyright", "CK Autoshop"),
        ])]),
        VarFileInfo([VarStruct("Translation", [0x0416, 1200])]),
    ],
)

a = Analysis(
    [str(RAIZ / "main.py")],
    pathex=[str(RAIZ)],
    datas=datas,
    hiddenimports=[],
    excludes=["pytest", "numpy", "pandas", "matplotlib", "IPython"],
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="CKEtiquetas",
    console=False,
    icon=str(RAIZ / "assets" / "icone.ico"),
    version=versao,
)
coll = COLLECT(exe, a.binaries, a.datas, name="CKEtiquetas")
