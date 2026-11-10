"""Página "Histórico": pesquisa das notas processadas, detalhes, reimpressão e PDF salvo."""

from __future__ import annotations

import tkinter.messagebox as mb
from datetime import date, datetime, timedelta

import customtkinter as ctk

from ..historico import IMPRESSAO_CONFIRMADA, ROTULOS_STATUS
from . import tema
from .dialogo_historico import CORES_STATUS, DialogoDetalhes, acao_abrir_pdf, acao_reimprimir
from .tema import BORDA, CARTAO, FUNDO, TEXTO, TEXTO_2, VERMELHO, botao, fonte

TODAS_TRANSP = "Todas as transportadoras"
TODOS_STATUS = "Todos os status"
PERIODOS = ["Hoje", "7 dias", "30 dias", "Tudo", "Período"]


def _data(txt: str) -> date | None:
    txt = txt.strip()
    if not txt:
        return None
    for fmt in ("%d/%m/%Y", "%d/%m/%y", "%Y-%m-%d"):
        try:
            return datetime.strptime(txt, fmt).date()
        except ValueError:
            pass
    raise ValueError(txt)


class PaginaHistorico(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color=FUNDO, corner_radius=0)
        self.app = app
        self.sujo = True
        self._job = None
        self._regs: dict = {}
        self.recentes_primeiro = True
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        cab = ctk.CTkFrame(self, fg_color="transparent")
        cab.grid(row=0, column=0, sticky="ew", padx=28, pady=(24, 12))
        cab.grid_columnconfigure(0, weight=1)
        tema.titulo_pagina(cab, "Histórico", "Todas as notas fiscais processadas, mesmo sem o PDF original."
                           ).grid(row=0, column=0, sticky="w")
        dir_ = ctk.CTkFrame(cab, fg_color="transparent")
        dir_.grid(row=0, column=1, sticky="e")
        self.lb_total = ctk.CTkLabel(dir_, text="", font=fonte(13), text_color=TEXTO_2)
        self.lb_total.pack(anchor="e")
        lin = ctk.CTkFrame(dir_, fg_color="transparent")
        lin.pack(anchor="e", pady=(6, 0))
        self.cb_ordem = ctk.CTkSegmentedButton(lin, values=["Mais recentes", "Mais antigas"], height=32,
                                               font=fonte(12), command=self._ordem_mudou,
                                               selected_color=tema.AZUL, selected_hover_color=tema.AZUL_HOVER)
        self.cb_ordem.set("Mais recentes")
        self.cb_ordem.pack(side="left")
        botao(lin, "Limpar filtros", self._limpar_filtros, icone_nome="limpar", altura=32).pack(side="left", padx=(8, 0))

        self._montar_filtros()
        self._montar_tabela()
        self._montar_acoes()

    # ------------------------------------------------------------ montagem
    def _montar_filtros(self) -> None:
        f = tema.cartao(self)
        f.grid(row=1, column=0, sticky="ew", padx=28, pady=(0, 12))
        f.grid_columnconfigure((0, 1, 2, 3), weight=1)

        def rotulo(col, texto):
            ctk.CTkLabel(f, text=texto, font=fonte(12, "bold"), text_color=TEXTO_2, anchor="w").grid(
                row=0, column=col, sticky="w", padx=(14, 6), pady=(12, 2))

        rotulo(0, "Número da NF")
        rotulo(1, "Placa")
        rotulo(2, "Transportadora")
        rotulo(3, "Status")
        kw = dict(height=36, corner_radius=8, border_color=BORDA, fg_color="#f8fafc", font=fonte(13))
        self.e_nf = ctk.CTkEntry(f, placeholder_text="Ex.: 7928", **kw)
        self.e_nf.grid(row=1, column=0, sticky="ew", padx=(14, 6))
        self.e_placa = ctk.CTkEntry(f, placeholder_text="Ex.: ABC1D23", **kw)
        self.e_placa.grid(row=1, column=1, sticky="ew", padx=6)
        for e in (self.e_nf, self.e_placa):
            e.bind("<KeyRelease>", lambda _e: self._agendar())
        kc = dict(height=36, corner_radius=8, border_color=BORDA, fg_color="#f8fafc", button_color="#e2e8f0",
                  button_hover_color="#cbd5e1", text_color=TEXTO, font=fonte(13), dropdown_font=fonte(13),
                  state="readonly", command=lambda _v: self._pesquisar())
        self.cb_transp = ctk.CTkComboBox(f, values=[TODAS_TRANSP], **kc)
        self.cb_transp.set(TODAS_TRANSP)
        self.cb_transp.grid(row=1, column=2, sticky="ew", padx=6)
        self._status_por_rotulo = {v: k for k, v in ROTULOS_STATUS.items()}
        self.cb_status = ctk.CTkComboBox(f, values=[TODOS_STATUS, *ROTULOS_STATUS.values()], **kc)
        self.cb_status.set(TODOS_STATUS)
        self.cb_status.grid(row=1, column=3, sticky="ew", padx=(6, 14))

        lin = ctk.CTkFrame(f, fg_color="transparent")
        lin.grid(row=2, column=0, columnspan=4, sticky="ew", padx=14, pady=(10, 12))
        ctk.CTkLabel(lin, text="", image=tema.icone("calendario", 16, TEXTO_2)).pack(side="left")
        ctk.CTkLabel(lin, text=" Período", font=fonte(12, "bold"), text_color=TEXTO_2).pack(side="left", padx=(0, 8))
        self.seg_periodo = ctk.CTkSegmentedButton(lin, values=PERIODOS, command=self._periodo_mudou, height=32,
                                                  font=fonte(12), selected_color=tema.AZUL,
                                                  selected_hover_color=tema.AZUL_HOVER)
        self.seg_periodo.set("30 dias")
        self.seg_periodo.pack(side="left")
        ke = dict(height=32, width=110, corner_radius=8, border_color=BORDA, fg_color="#f8fafc", font=fonte(12))
        ctk.CTkLabel(lin, text="de", text_color=TEXTO_2, font=fonte(12)).pack(side="left", padx=(14, 4))
        self.e_ini = ctk.CTkEntry(lin, placeholder_text="dd/mm/aaaa", **ke)
        self.e_ini.pack(side="left")
        ctk.CTkLabel(lin, text="até", text_color=TEXTO_2, font=fonte(12)).pack(side="left", padx=4)
        self.e_fim = ctk.CTkEntry(lin, placeholder_text="dd/mm/aaaa", **ke)
        self.e_fim.pack(side="left")
        for e in (self.e_ini, self.e_fim):
            e.bind("<KeyRelease>", lambda _e: self._datas_digitadas())
        self.lb_erro_data = ctk.CTkLabel(lin, text="", text_color=VERMELHO, font=fonte(12))
        self.lb_erro_data.pack(side="left", padx=8)

        self._periodo_mudou("30 dias", pesquisar=False)

    def _montar_tabela(self) -> None:
        q = tema.cartao(self)
        q.grid(row=2, column=0, sticky="nsew", padx=28, pady=(0, 12))
        interno = ctk.CTkFrame(q, fg_color=CARTAO)
        interno.pack(fill="both", expand=True, padx=8, pady=8)
        self.tv = tema.tabela(interno, [
            ("nf", "NF", 70, "center"), ("transp", "Transportadora", 150, "w"), ("placa", "Placa", 90, "center"),
            ("vol", "Volumes", 70, "center"), ("data", "Data  ▼", 130, "center"), ("status", "Status", 150, "center"),
            ("ger", "Gerações", 70, "center"),
        ], esticar=("transp",), selecao="extended")
        self.tv.heading("data", command=self._alternar_ordem)
        for st, (cor, fundo) in CORES_STATUS.items():
            self.tv.tag_configure(st, foreground=cor)
        self.tv.bind("<Double-1>", lambda _e: self._detalhes())
        self.tv.bind("<Return>", lambda _e: self._detalhes())
        self.vazio = ctk.CTkLabel(q, text="Nenhuma nota encontrada com estes filtros.", font=fonte(14),
                                  text_color=TEXTO_2, fg_color=CARTAO)

    def _montar_acoes(self) -> None:
        a = ctk.CTkFrame(self, fg_color="transparent")
        a.grid(row=3, column=0, sticky="ew", padx=28, pady=(0, 22))
        botao(a, "Ver detalhes", self._detalhes, icone_nome="ver", estilo="contorno", altura=40).pack(side="left")
        botao(a, "Reimprimir", self._reimprimir, icone_nome="imprimir", estilo="primario", altura=40,
              negrito=True).pack(side="left", padx=8)
        botao(a, "Confirmar impressão", self._confirmar, icone_nome="confirmado", estilo="sucesso",
              altura=40).pack(side="left")
        botao(a, "Abrir PDF salvo", self._abrir_pdf, icone_nome="abrir", estilo="contorno", altura=40).pack(
            side="left", padx=8)
        botao(a, "Atualizar", self._pesquisar, icone_nome="atualizar", altura=40).pack(side="right")

    # ------------------------------------------------------------ filtros
    def ao_mostrar(self) -> None:
        try:
            transps = self.app.historico.transportadoras()
        except Exception:  # noqa: BLE001
            transps = []
        self.cb_transp.configure(values=[TODAS_TRANSP, *transps])
        if self.sujo:
            self._pesquisar()

    def _agendar(self) -> None:
        if self._job:
            self.after_cancel(self._job)
        self._job = self.after(250, self._pesquisar)

    def _periodo_mudou(self, valor: str, pesquisar: bool = True) -> None:
        hoje = date.today()
        ini = {"Hoje": hoje, "7 dias": hoje - timedelta(days=6), "30 dias": hoje - timedelta(days=29)}.get(valor)
        if valor != "Período":
            for e, v in ((self.e_ini, ini), (self.e_fim, hoje if ini else None)):
                e.delete(0, "end")
                if v:
                    e.insert(0, v.strftime("%d/%m/%Y"))
        if pesquisar:
            self._pesquisar()

    def _datas_digitadas(self) -> None:
        self.seg_periodo.set("Período")
        self._agendar()

    def _ordem_mudou(self, valor: str) -> None:
        self.recentes_primeiro = valor == "Mais recentes"
        self.tv.heading("data", text="Data  ▼" if self.recentes_primeiro else "Data  ▲")
        self._pesquisar()

    def _alternar_ordem(self) -> None:
        novo = "Mais antigas" if self.recentes_primeiro else "Mais recentes"
        self.cb_ordem.set(novo)
        self._ordem_mudou(novo)

    def _limpar_filtros(self) -> None:
        self.e_nf.delete(0, "end")
        self.e_placa.delete(0, "end")
        self.cb_transp.set(TODAS_TRANSP)
        self.cb_status.set(TODOS_STATUS)
        self.seg_periodo.set("Tudo")
        self._periodo_mudou("Tudo")

    def _pesquisar(self) -> None:
        self._job = None
        try:
            ini, fim = _data(self.e_ini.get()), _data(self.e_fim.get())
            self.lb_erro_data.configure(text="")
        except ValueError:
            self.lb_erro_data.configure(text="Data inválida (use dd/mm/aaaa)")
            return
        transp = self.cb_transp.get()
        st = self._status_por_rotulo.get(self.cb_status.get(), "")
        try:
            regs = self.app.historico.pesquisar(
                nf=self.e_nf.get(), placa=self.e_placa.get(),
                transportadora="" if transp == TODAS_TRANSP else transp, status=st,
                data_inicial=ini, data_final=fim, mais_recentes_primeiro=self.recentes_primeiro)
        except Exception as e:  # noqa: BLE001
            mb.showerror("Histórico", f"Não foi possível consultar o histórico:\n{e}")
            return
        sel = set(self.tv.selection())
        self.tv.delete(*self.tv.get_children())
        self._regs = {}
        for r in regs:
            iid = str(r.id)
            self._regs[iid] = r
            self.tv.insert("", "end", iid=iid, tags=(r.status,), values=(
                r.numero_impresso, r.transportadora, r.placa or "—", r.volumes, r.data_formatada,
                r.status_rotulo, r.geracoes))
        manter = [s for s in sel if self.tv.exists(s)]
        if manter:
            self.tv.selection_set(manter)
        if regs:
            self.vazio.place_forget()
        else:
            self.vazio.place(relx=0.5, rely=0.5, anchor="center")
        n_etq = sum(r.etiquetas for r in regs)
        self.lb_total.configure(text=f"{len(regs)} nota(s) • {n_etq} etiqueta(s)")
        self.sujo = False

    # ------------------------------------------------------------ ações
    def _selecionados(self):
        return [self._regs[s] for s in self.tv.selection() if s in self._regs]

    def _um(self):
        sel = self._selecionados()
        if not sel:
            self.app.notificacao.mostrar("Selecione uma nota na tabela.", "info")
            return None
        return sel[0]

    def _detalhes(self) -> None:
        r = self._um()
        if r:
            DialogoDetalhes(self, self.app, self.app.historico.obter(r.id) or r)

    def _reimprimir(self) -> None:
        sel = self._selecionados()
        if not sel:
            self.app.notificacao.mostrar("Selecione uma ou mais notas para reimprimir.", "info")
            return
        acao_reimprimir(self, self.app, sel)

    def _confirmar(self) -> None:
        sel = [r for r in self._selecionados() if r.status != IMPRESSAO_CONFIRMADA]
        if not sel:
            self.app.notificacao.mostrar("Selecione notas com impressão ainda não confirmada.", "info")
            return
        nums = ", ".join(r.numero_impresso for r in sel[:10]) + ("…" if len(sel) > 10 else "")
        if mb.askyesno("Confirmar impressão", f"Confirmar que as etiquetas de {len(sel)} nota(s) foram impressas "
                                              f"corretamente?\n\nNF {nums}"):
            self.app.historico.confirmar_impressao([r.id for r in sel], detalhe="confirmado pelo histórico")
            self.app.dados_alterados()
            self.app.notificacao.mostrar(f"Impressão confirmada para {len(sel)} nota(s).", "ok")

    def _abrir_pdf(self) -> None:
        r = self._um()
        if r:
            acao_abrir_pdf(self, r)
