"""Visualização de impressão das etiquetas (escala real ou ajustada)."""

from __future__ import annotations

import tkinter as tk

import customtkinter as ctk
import pymupdf
from PIL import Image, ImageTk

from .. import config
from . import tema


class JanelaVisualizacao(tema.JanelaCK):
    def __init__(self, master, doc: pymupdf.Document, avisos: list[str] | None = None):
        super().__init__(master, "Visualização das etiquetas", "900x900")
        self.doc = doc
        self._imagens: list[ImageTk.PhotoImage] = []
        self.modo = ctk.StringVar(value="ajustar")

        topo = ctk.CTkFrame(self)
        topo.pack(fill="x", padx=8, pady=(8, 0))
        ctk.CTkLabel(
            topo, text=f"{doc.page_count} folha(s) A4  •  2 etiquetas por folha",
            font=ctk.CTkFont(weight="bold"),
        ).pack(side="left", padx=8)
        ctk.CTkSegmentedButton(
            topo, values=["ajustar", "tamanho real (100%)"], variable=self.modo,
            command=lambda _v: self._renderizar(),
        ).pack(side="right", padx=8, pady=6)

        aviso = (
            "IMPRESSÃO: escolha 'Tamanho real' / escala 100% — NÃO use 'Ajustar à página'. "
            "A linha tracejada vermelha marca o corte (148,5 mm) e aparece só aqui, não no PDF."
        )
        if avisos:
            aviso += "\n" + "\n".join(avisos)
        ctk.CTkLabel(self, text=aviso, text_color="#b26a00", wraplength=860, justify="left").pack(
            fill="x", padx=12, pady=4
        )

        quadro = tk.Frame(self, bg="#7f7f7f")
        quadro.pack(fill="both", expand=True, padx=8, pady=8)
        self.canvas = tk.Canvas(quadro, bg="#7f7f7f", highlightthickness=0)
        sy = tk.Scrollbar(quadro, orient="vertical", command=self.canvas.yview)
        sx = tk.Scrollbar(quadro, orient="horizontal", command=self.canvas.xview)
        self.canvas.configure(yscrollcommand=sy.set, xscrollcommand=sx.set)
        sy.pack(side="right", fill="y")
        sx.pack(side="bottom", fill="x")
        self.canvas.pack(side="left", fill="both", expand=True)
        self.canvas.bind("<MouseWheel>", lambda e: self.canvas.yview_scroll(int(-e.delta / 120), "units"))
        self.canvas.bind("<Configure>", lambda _e: self._renderizar() if self.modo.get() == "ajustar" else None)
        self.protocol("WM_DELETE_WINDOW", self._fechar)
        self.after(100, self._renderizar)

    def _zoom(self) -> float:
        if self.modo.get().startswith("tamanho"):
            # pixels por polegada informados pelo Windows / 72 pt por polegada
            return self.winfo_fpixels("1i") / 72.0
        largura = max(self.canvas.winfo_width() - 40, 200)
        return largura / config.A4_LARGURA

    def _renderizar(self) -> None:
        z = self._zoom()
        self.canvas.delete("all")
        self._imagens.clear()
        y = 20
        for pagina in self.doc:
            pix = pagina.get_pixmap(matrix=pymupdf.Matrix(z, z), alpha=False)
            img = ImageTk.PhotoImage(Image.frombytes("RGB", (pix.width, pix.height), pix.samples))
            self._imagens.append(img)
            self.canvas.create_image(20, y, image=img, anchor="nw")
            meio = y + config.METADE_ALTURA * z
            self.canvas.create_line(20, meio, 20 + pix.width, meio, fill="red", dash=(6, 4))
            y += pix.height + 20
        self.canvas.configure(scrollregion=(0, 0, 40 + int(config.A4_LARGURA * z), y))

    def _fechar(self) -> None:
        self.doc.close()
        self.destroy()
