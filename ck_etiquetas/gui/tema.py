"""Identidade visual do CK Etiquetas: cores, fontes, ícones e componentes reutilizáveis."""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from tkinter import ttk

import customtkinter as ctk
from PIL import Image, ImageDraw, ImageFont

from .. import config

# ------------------------------------------------------------------ cores
AZUL = "#1565c0"
AZUL_HOVER = "#0f4fa0"
AZUL_ESCURO = "#0b2a5b"  # menu lateral
AZUL_MENU_ATIVO = "#1d4f9c"
AZUL_MENU_HOVER = "#163e7d"
AZUL_SUAVE = "#e8f1fc"
FUNDO = "#f3f6fa"
CARTAO = "#ffffff"
BORDA = "#e2e8f0"
TEXTO = "#1e293b"
TEXTO_2 = "#64748b"
TEXTO_3 = "#94a3b8"
VERDE = "#15803d"
VERDE_HOVER = "#116430"
VERDE_SUAVE = "#e7f6ec"
AMARELO = "#b45309"
AMARELO_SUAVE = "#fff7e6"
VERMELHO = "#c62828"
VERMELHO_HOVER = "#9f1f1f"
VERMELHO_SUAVE = "#fdecec"
CINZA_BOTAO = "#eef2f7"
CINZA_BOTAO_HOVER = "#e2e8f0"

FAMILIA = "Segoe UI"


def fonte(tamanho: int = 13, peso: str = "normal") -> ctk.CTkFont:
    return ctk.CTkFont(family=FAMILIA, size=tamanho, weight=peso)


# ------------------------------------------------------------------ ícones
# Segoe Fluent Icons (Windows 11) / Segoe MDL2 Assets (Windows 10): mesmos códigos.
ICONES = {
    "dashboard": 0xE9D2, "etiqueta": 0xE8EC, "historico": 0xE81C, "config": 0xE713,
    "adicionar": 0xE710, "remover": 0xE74D, "limpar": 0xE894, "subir": 0xE70E, "descer": 0xE70D,
    "editar": 0xE70F, "ver": 0xE890, "imprimir": 0xE749, "abrir": 0xE8E5, "pasta": 0xE838,
    "ok": 0xE73E, "aviso": 0xE7BA, "erro": 0xEA39, "info": 0xE946, "buscar": 0xE721,
    "backup": 0xE8F1, "restaurar": 0xE777, "calendario": 0xE787, "atualizar": 0xE72C,
    "documento": 0xE8A5, "pdf": 0xEA90, "caminhao": 0xE806, "confirmado": 0xE930, "relogio": 0xE823,
    "filtro": 0xE71C, "salvar": 0xE74E, "lista": 0xEA37, "checklist": 0xE762, "caixa": 0xE7B8,
}


@lru_cache(maxsize=1)
def _arquivo_fonte_icones() -> str | None:
    pasta = Path(os.environ.get("WINDIR", r"C:\Windows")) / "Fonts"
    for nome in ("SegoeIcons.ttf", "segmdl2.ttf"):
        if (pasta / nome).is_file():
            return str(pasta / nome)
    return None


@lru_cache(maxsize=256)
def _imagem_icone(nome: str, tamanho: int, cor: str) -> Image.Image | None:
    arq = _arquivo_fonte_icones()
    if not arq or nome not in ICONES:
        return None
    px = tamanho * 3  # renderiza maior para ficar nítido em telas com escala
    f = ImageFont.truetype(arq, px)
    img = Image.new("RGBA", (px, px), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    caractere = chr(ICONES[nome])
    x0, y0, x1, y1 = d.textbbox((0, 0), caractere, font=f)
    d.text(((px - (x1 - x0)) / 2 - x0, (px - (y1 - y0)) / 2 - y0), caractere, font=f, fill=cor)
    return img


def icone(nome: str, tamanho: int = 18, cor: str = TEXTO) -> ctk.CTkImage | None:
    """Ícone como imagem. None se a fonte de ícones não existir (o botão fica só com texto)."""
    img = _imagem_icone(nome, tamanho, cor)
    return ctk.CTkImage(light_image=img, dark_image=img, size=(tamanho, tamanho)) if img else None


@lru_cache(maxsize=1)
def _imagem_logo() -> Image.Image | None:
    try:
        img = Image.open(config.LOGO_PATH).convert("RGBA")
    except OSError:
        return None
    return img.crop(img.getbbox())


def logo(largura: int) -> ctk.CTkImage | None:
    img = _imagem_logo()
    if img is None:
        return None
    return ctk.CTkImage(light_image=img, dark_image=img, size=(largura, round(img.height * largura / img.width)))


# ------------------------------------------------------------------ componentes
_ESTILOS_BOTAO = {
    "primario": dict(fg_color=AZUL, hover_color=AZUL_HOVER, text_color="white", cor_icone="#ffffff"),
    "sucesso": dict(fg_color=VERDE, hover_color=VERDE_HOVER, text_color="white", cor_icone="#ffffff"),
    "perigo": dict(fg_color=VERMELHO, hover_color=VERMELHO_HOVER, text_color="white", cor_icone="#ffffff"),
    "secundario": dict(fg_color=CINZA_BOTAO, hover_color=CINZA_BOTAO_HOVER, text_color=TEXTO, cor_icone=TEXTO),
    "contorno": dict(fg_color=CARTAO, hover_color=AZUL_SUAVE, text_color=AZUL, cor_icone=AZUL,
                     border_width=1, border_color="#bcd3f0"),
}


def botao(master, texto: str, comando=None, *, icone_nome: str | None = None, estilo: str = "secundario",
          altura: int = 36, largura: int = 0, tamanho_fonte: int = 13, negrito: bool = False) -> ctk.CTkButton:
    e = dict(_ESTILOS_BOTAO[estilo])
    cor_icone = e.pop("cor_icone")
    img = icone(icone_nome, 16 if altura < 44 else 18, cor_icone) if icone_nome else None
    return ctk.CTkButton(
        master, text=texto, command=comando, image=img, compound="left", height=altura,
        width=largura or 0, corner_radius=8, font=fonte(tamanho_fonte, "bold" if negrito else "normal"),
        text_color_disabled=TEXTO_3, **e,
    )


def cartao(master, **kw) -> ctk.CTkFrame:
    return ctk.CTkFrame(master, fg_color=CARTAO, corner_radius=12, border_width=1, border_color=BORDA, **kw)


def titulo_pagina(master, titulo: str, subtitulo: str = "") -> ctk.CTkFrame:
    f = ctk.CTkFrame(master, fg_color="transparent")
    ctk.CTkLabel(f, text=titulo, font=fonte(24, "bold"), text_color=TEXTO, anchor="w").pack(anchor="w")
    if subtitulo:
        ctk.CTkLabel(f, text=subtitulo, font=fonte(13), text_color=TEXTO_2, anchor="w").pack(anchor="w")
    return f


class CartaoIndicador(ctk.CTkFrame):
    """Card com ícone, valor grande e legenda."""

    def __init__(self, master, titulo: str, icone_nome: str, cor: str = AZUL, fundo_icone: str = AZUL_SUAVE,
                 compacto: bool = False):
        super().__init__(master, fg_color=CARTAO, corner_radius=12, border_width=1, border_color=BORDA)
        self.grid_columnconfigure(1, weight=1)
        tam = 36 if compacto else 46
        caixa = ctk.CTkFrame(self, width=tam, height=tam, corner_radius=10, fg_color=fundo_icone)
        caixa.grid(row=0, column=0, rowspan=2, padx=(14, 10), pady=12)
        caixa.grid_propagate(False)
        ctk.CTkLabel(caixa, text="", image=icone(icone_nome, 18 if compacto else 22, cor)).place(
            relx=0.5, rely=0.5, anchor="center")
        self.valor = ctk.CTkLabel(self, text="0", font=fonte(20 if compacto else 26, "bold"), text_color=TEXTO,
                                  anchor="w")
        self.valor.grid(row=0, column=1, sticky="sw", padx=(0, 12), pady=(10 if compacto else 12, 0))
        ctk.CTkLabel(self, text=titulo, font=fonte(12), text_color=TEXTO_2, anchor="w").grid(
            row=1, column=1, sticky="nw", padx=(0, 12), pady=(0, 10 if compacto else 12))

    def definir(self, valor) -> None:
        self.valor.configure(text=f"{valor:,}".replace(",", ".") if isinstance(valor, int) else str(valor))


class Notificacao:
    """Aviso flutuante (canto inferior direito) para sucesso, erro e informações."""

    CORES = {"ok": (VERDE, "confirmado"), "erro": (VERMELHO, "erro"), "aviso": (AMARELO, "aviso"),
             "info": (AZUL, "info")}

    def __init__(self, raiz):
        self.raiz = raiz
        self._frame: ctk.CTkFrame | None = None
        self._job = None

    def mostrar(self, mensagem: str, tipo: str = "ok", segundos: float = 4.0) -> None:
        self.fechar()
        cor, ic = self.CORES.get(tipo, self.CORES["info"])
        f = ctk.CTkFrame(self.raiz, fg_color=cor, corner_radius=10)
        ctk.CTkLabel(f, text="  " + mensagem, image=icone(ic, 18, "#ffffff"), compound="left",
                     text_color="white", font=fonte(13, "bold"), wraplength=420, justify="left").pack(
            padx=16, pady=10)
        f.place(relx=1.0, rely=1.0, x=-24, y=-24, anchor="se")
        f.lift()
        self._frame = f
        self._job = self.raiz.after(int(segundos * 1000), self.fechar)

    def fechar(self) -> None:
        if self._job:
            try:
                self.raiz.after_cancel(self._job)
            except Exception:  # noqa: BLE001
                pass
            self._job = None
        if self._frame is not None:
            self._frame.destroy()
            self._frame = None


class JanelaCK(ctk.CTkToplevel):
    """Janela secundária com o ícone da CK (o CustomTkinter troca o ícone após ~200 ms)."""

    def __init__(self, master, titulo: str, geometria: str | None = None, modal: bool = False):
        super().__init__(master)
        self.title(titulo)
        self.configure(fg_color=FUNDO)
        if geometria:
            self.geometry(geometria)
        self.transient(master)
        self.after(250, self._aplicar_icone)
        if modal:
            self.after(60, self._modal)

    def _aplicar_icone(self) -> None:
        try:
            self.iconbitmap(str(config.ICONE_PATH))
        except Exception:  # noqa: BLE001
            pass

    def _modal(self) -> None:
        try:
            self.grab_set()
            self.focus_force()
        except Exception:  # noqa: BLE001
            pass

    def centralizar(self, largura: int, altura: int) -> None:
        m = self.master.winfo_toplevel()
        x = m.winfo_rootx() + (m.winfo_width() - largura) // 2
        y = m.winfo_rooty() + (m.winfo_height() - altura) // 3
        self.geometry(f"{largura}x{altura}+{max(x, 0)}+{max(y, 0)}")


# ------------------------------------------------------------------ tabelas
def configurar_estilo_tabelas(raiz) -> None:
    s = ttk.Style(raiz)
    s.theme_use("clam")
    s.configure("CK.Treeview", background=CARTAO, fieldbackground=CARTAO, foreground=TEXTO, rowheight=36,
                font=(FAMILIA, 10), borderwidth=0, relief="flat")
    s.configure("CK.Treeview.Heading", background="#f1f5f9", foreground=TEXTO_2, font=(FAMILIA, 10, "bold"),
                relief="flat", borderwidth=0, padding=(8, 8))
    s.map("CK.Treeview.Heading", background=[("active", "#e2e8f0")])
    s.map("CK.Treeview", background=[("selected", "#cfe2fb")], foreground=[("selected", TEXTO)])
    s.layout("CK.Treeview", [("CK.Treeview.treearea", {"sticky": "nswe"})])
    s.configure("CK.Vertical.TScrollbar", background="#e2e8f0", troughcolor=CARTAO, bordercolor=CARTAO,
                arrowcolor=TEXTO_2, relief="flat", gripcount=0)


def tabela(master, colunas: list[tuple[str, str, int, str]], esticar: tuple[str, ...] = (),
           selecao: str = "browse", altura: int = 10) -> ttk.Treeview:
    """Treeview no estilo CK dentro de `master` (com barra de rolagem). colunas: (id, título, largura, anchor)."""
    tv = ttk.Treeview(master, columns=[c[0] for c in colunas], show="headings", selectmode=selecao,
                      style="CK.Treeview", height=altura)
    for cid, titulo, larg, anc in colunas:
        tv.heading(cid, text=titulo, anchor=anc if anc != "e" else "center")
        tv.column(cid, width=larg, minwidth=40, anchor=anc, stretch=cid in esticar)
    sb = ttk.Scrollbar(master, orient="vertical", command=tv.yview, style="CK.Vertical.TScrollbar")
    tv.configure(yscrollcommand=sb.set)
    tv.grid(row=0, column=0, sticky="nsew", padx=(1, 0), pady=1)
    sb.grid(row=0, column=1, sticky="ns", pady=1)
    master.grid_rowconfigure(0, weight=1)
    master.grid_columnconfigure(0, weight=1)
    tv.tag_configure("par", background="#fafbfd")
    tv.tag_configure("OK", background=VERDE_SUAVE)
    tv.tag_configure("CONFERIR", background=AMARELO_SUAVE)
    tv.tag_configure("PENDENTE", background=VERMELHO_SUAVE)
    tv.bind("<MouseWheel>", lambda e: tv.yview_scroll(int(-e.delta / 120), "units"))
    return tv


def selo_status(master, texto: str, cor: str, fundo: str) -> ctk.CTkLabel:
    return ctk.CTkLabel(master, text=f"  {texto}  ", fg_color=fundo, text_color=cor, corner_radius=8,
                        font=fonte(12, "bold"), height=24)
