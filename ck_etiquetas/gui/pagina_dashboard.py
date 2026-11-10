"""Página "Dashboard": indicadores reais do banco de dados e últimas operações."""

from __future__ import annotations

from datetime import date

import customtkinter as ctk

from . import tema
from .dialogo_historico import CORES_STATUS
from .tema import (AMARELO, AMARELO_SUAVE, CARTAO, FUNDO, TEXTO, TEXTO_2, VERDE, VERDE_SUAVE, botao, fonte,
                   icone)

DIAS = ["segunda-feira", "terça-feira", "quarta-feira", "quinta-feira", "sexta-feira", "sábado", "domingo"]
MESES = ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto", "setembro", "outubro",
         "novembro", "dezembro"]


class PaginaDashboard(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color=FUNDO, corner_radius=0)
        self.app = app
        self.sujo = True
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(3, weight=1)

        cab = ctk.CTkFrame(self, fg_color="transparent")
        cab.grid(row=0, column=0, sticky="ew", padx=28, pady=(24, 16))
        cab.grid_columnconfigure(0, weight=1)
        self.titulo = tema.titulo_pagina(cab, "Dashboard", self._hoje_por_extenso())
        self.titulo.grid(row=0, column=0, sticky="w")
        botao(cab, "Gerar etiquetas", lambda: app.mostrar("gerar"), icone_nome="etiqueta", estilo="primario",
              altura=42, negrito=True).grid(row=0, column=1, sticky="e")

        cards = ctk.CTkFrame(self, fg_color="transparent")
        cards.grid(row=1, column=0, sticky="ew", padx=28)
        cards.grid_columnconfigure((0, 1, 2, 3), weight=1, uniform="c")
        self.c_notas = tema.CartaoIndicador(cards, "Notas fiscais processadas", "documento")
        self.c_etq = tema.CartaoIndicador(cards, "Etiquetas geradas", "etiqueta")
        self.c_conf = tema.CartaoIndicador(cards, "Etiquetas confirmadas", "confirmado", VERDE,
                                           VERDE_SUAVE)
        self.c_hoje = tema.CartaoIndicador(cards, "Notas processadas hoje", "calendario", "#7c3aed", "#f1eafe")
        for i, c in enumerate((self.c_notas, self.c_etq, self.c_conf, self.c_hoje)):
            c.grid(row=0, column=i, sticky="ew", padx=(0 if i == 0 else 6, 0 if i == 3 else 6))

        self.alerta = ctk.CTkFrame(self, fg_color=AMARELO_SUAVE, corner_radius=12, border_width=1,
                                   border_color="#f5d49a")
        self.lb_alerta = ctk.CTkLabel(self.alerta, text="", image=icone("relogio", 18, AMARELO), compound="left",
                                      font=fonte(13, "bold"), text_color="#7a3e00")
        self.lb_alerta.pack(side="left", padx=14, pady=10)
        botao(self.alerta, "Ver no histórico", self._ver_pendentes, estilo="contorno", altura=32).pack(
            side="right", padx=10)

        ult = tema.cartao(self)
        ult.grid(row=3, column=0, sticky="nsew", padx=28, pady=(14, 24))
        topo = ctk.CTkFrame(ult, fg_color="transparent")
        topo.pack(fill="x", padx=16, pady=(14, 6))
        ctk.CTkLabel(topo, text="Últimas operações", font=fonte(16, "bold"), text_color=TEXTO).pack(side="left")
        botao(topo, "Ver histórico completo", lambda: app.mostrar("historico"), icone_nome="historico",
              estilo="contorno", altura=32).pack(side="right")
        interno = ctk.CTkFrame(ult, fg_color=CARTAO)
        interno.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        self.tv = tema.tabela(interno, [
            ("data", "Data e hora", 150, "center"), ("op", "Operação", 200, "w"), ("nf", "NF", 90, "center"),
            ("transp", "Transportadora", 200, "w"), ("etq", "Etiquetas", 90, "center"),
        ], esticar=("transp", "op"), altura=8)
        for st, (cor, _f) in CORES_STATUS.items():
            self.tv.tag_configure(st, foreground=cor)
        self.tv.bind("<Double-1>", lambda _e: self._abrir_operacao())
        self.vazio = ctk.CTkFrame(ult, fg_color=CARTAO)
        ctk.CTkLabel(self.vazio, text="", image=icone("lista", 40, "#9bb8e0")).pack(pady=(0, 6))
        ctk.CTkLabel(self.vazio, text="Nenhuma operação registrada ainda", font=fonte(15, "bold"),
                     text_color=TEXTO).pack()
        ctk.CTkLabel(self.vazio, text="As gerações e impressões de etiquetas aparecerão aqui.", font=fonte(13),
                     text_color=TEXTO_2).pack(pady=(2, 0))
        self._eventos: dict = {}

    @staticmethod
    def _hoje_por_extenso() -> str:
        d = date.today()
        return f"Resumo da expedição • {DIAS[d.weekday()]}, {d.day} de {MESES[d.month - 1]} de {d.year}"

    def ao_mostrar(self) -> None:
        try:
            e = self.app.historico.estatisticas()
            ops = self.app.historico.ultimas_operacoes(15)
        except Exception as ex:  # noqa: BLE001
            self.app.notificacao.mostrar(f"Erro ao ler o histórico: {ex}", "erro", 6)
            return
        self.c_notas.definir(e.notas_processadas)
        self.c_etq.definir(e.etiquetas_geradas)
        self.c_conf.definir(e.etiquetas_confirmadas)
        self.c_hoje.definir(e.notas_hoje)
        if e.aguardando_confirmacao:
            self.lb_alerta.configure(text=f"  {e.aguardando_confirmacao} nota(s) com impressão ainda não confirmada.")
            self.alerta.grid(row=2, column=0, sticky="ew", padx=28, pady=(14, 0))
        else:
            self.alerta.grid_forget()

        self.tv.delete(*self.tv.get_children())
        self._eventos = {}
        for i, o in enumerate(ops):
            iid = str(o.id)
            self._eventos[iid] = o
            self.tv.insert("", "end", iid=iid, tags=(o.tipo,), values=(
                o.data_formatada, o.rotulo, o.numero_impresso, o.transportadora, o.etiquetas))
        if ops:
            self.vazio.place_forget()
        else:
            self.vazio.place(relx=0.5, rely=0.55, anchor="center")
        self.sujo = False

    def _abrir_operacao(self) -> None:
        sel = self.tv.selection()
        if not sel:
            return
        from .dialogo_historico import DialogoDetalhes

        r = self.app.historico.obter(self._eventos[sel[0]].nota_id)
        if r:
            DialogoDetalhes(self, self.app, r)

    def _ver_pendentes(self) -> None:
        hist = self.app.pagina("historico")
        self.app.mostrar("historico")
        hist._limpar_filtros()


