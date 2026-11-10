"""Diálogos do histórico: nota já processada, detalhes, reimpressão e confirmação de impressão."""

from __future__ import annotations

import tkinter.messagebox as mb

import customtkinter as ctk

from .. import impressao, operacoes
from ..historico import (IMPRESSAO_CONFIRMADA, IMPRESSAO_SOLICITADA, PDF_GERADO, REIMPRESSAO, Registro,
                         formatar_data)
from ..modelos import NotaFiscal
from . import tema
from .tema import (AMARELO, AMARELO_SUAVE, AZUL, AZUL_SUAVE, CARTAO, TEXTO, TEXTO_2, VERDE, VERDE_SUAVE,
                   botao, fonte, icone)

SO_NOVAS = "so_novas"
TODAS = "todas"

CORES_STATUS = {
    PDF_GERADO: (AZUL, AZUL_SUAVE),
    IMPRESSAO_SOLICITADA: (AMARELO, AMARELO_SUAVE),
    IMPRESSAO_CONFIRMADA: (VERDE, VERDE_SUAVE),
    REIMPRESSAO: ("#7c3aed", "#f1eafe"),
}


# ------------------------------------------------------------------ ações compartilhadas
def acao_reimprimir(parent, app, registros: list[Registro]) -> bool:
    """Gera novamente as etiquetas pelo histórico, solicita a impressão e pede confirmação."""
    if not registros:
        return False
    n_etq = sum(r.etiquetas for r in registros)
    nums = ", ".join(r.numero_impresso for r in registros[:10]) + ("…" if len(registros) > 10 else "")
    if not mb.askyesno("Reimprimir", f"Gerar novamente {n_etq} etiqueta(s) de {len(registros)} nota(s)?\n\n"
                                     f"NF {nums}\n\nSerá registrado no histórico como reimpressão.", parent=parent):
        return False
    try:
        destino, rel, ids = operacoes.reimprimir(registros, app.prefs, app.historico)
    except Exception as e:  # noqa: BLE001
        mb.showerror("Reimprimir", f"Não foi possível gerar o PDF:\n{e}", parent=parent)
        return False
    try:
        como = impressao.solicitar_impressao(destino, app.prefs.modo_impressao)
        app.historico.registrar_solicitacao(ids, destino, detalhe=como)
    except Exception as e:  # noqa: BLE001
        mb.showwarning("Reimprimir", f"PDF gerado em:\n{destino}\n\nmas não foi possível abri-lo:\n{e}",
                       parent=parent)
    app.dados_alterados()
    app.notificacao.mostrar(f"Reimpressão gerada: {rel.etiquetas} etiqueta(s).", "ok")
    if app.prefs.confirmar_impressao and perguntar_confirmacao_impressao(parent, len(ids), rel.etiquetas):
        app.historico.confirmar_impressao(ids, detalhe="reimpressão")
        app.dados_alterados()
        app.notificacao.mostrar("Impressão confirmada.", "ok")
    return True


def acao_abrir_pdf(parent, registro: Registro) -> None:
    try:
        impressao.abrir_pdf(registro.pdf_gerado)
    except Exception as e:  # noqa: BLE001
        mb.showinfo("PDF não encontrado", f"{e}\n\nUse 'Reimprimir' para gerar o PDF de novo a partir do histórico.",
                    parent=parent)


def perguntar_confirmacao_impressao(parent, n_notas: int, n_etiquetas: int) -> bool:
    d = _DialogoConfirmacao(parent, n_notas, n_etiquetas)
    return d.perguntar()


class _DialogoConfirmacao(tema.JanelaCK):
    def __init__(self, master, n_notas: int, n_etiquetas: int):
        super().__init__(master, "Confirmar impressão", modal=True)
        self.resultado = False
        self.resizable(False, False)
        self.centralizar(500, 270)
        c = tema.cartao(self)
        c.pack(fill="both", expand=True, padx=16, pady=16)
        ctk.CTkLabel(c, text="  As etiquetas foram impressas corretamente?", image=icone("imprimir", 22, AZUL),
                     compound="left", font=fonte(16, "bold"), text_color=TEXTO).pack(anchor="w", padx=18, pady=(18, 6))
        ctk.CTkLabel(c, text=f"{n_notas} nota(s) • {n_etiquetas} etiqueta(s).\n\nConfira se todas saíram, em "
                             "tamanho real (escala 100%), antes de confirmar. Se ainda não imprimiu, escolha "
                             "'Ainda não' — dá para confirmar depois pelo Histórico.",
                     font=fonte(13), text_color=TEXTO_2, justify="left", wraplength=430).pack(anchor="w", padx=18)
        bts = ctk.CTkFrame(c, fg_color="transparent")
        bts.pack(fill="x", padx=18, pady=16, side="bottom")
        botao(bts, "Ainda não", self.destroy, altura=38).pack(side="right")
        botao(bts, "Sim, confirmar impressão", self._sim, icone_nome="confirmado", estilo="sucesso", altura=38,
              negrito=True).pack(side="right", padx=8)
        self.bind("<Escape>", lambda _e: self.destroy())

    def _sim(self) -> None:
        self.resultado = True
        self.destroy()

    def perguntar(self) -> bool:
        self.wait_window()
        return self.resultado


# ------------------------------------------------------------------ nota já processada
class DialogoDuplicadas(tema.JanelaCK):
    """Exibido antes de gerar quando há NFs que já possuem etiquetas. resultado: TODAS, SO_NOVAS ou None."""

    def __init__(self, master, app, notas: list[NotaFiscal], ja: dict[int, Registro]):
        super().__init__(master, "Nota fiscal já processada", modal=True)
        self.app = app
        self.resultado: str | None = None
        self.centralizar(1040, 540)
        self.minsize(980, 440)
        n_rep, n_novas = len(ja), len(notas) - len(ja)

        alerta = ctk.CTkFrame(self, fg_color=AMARELO_SUAVE, corner_radius=12, border_width=1,
                              border_color="#f5d49a")
        alerta.pack(fill="x", padx=18, pady=(18, 10))
        msg = ("ATENÇÃO: Esta nota fiscal já possui etiquetas geradas anteriormente." if n_rep == 1 else
               f"ATENÇÃO: {n_rep} notas fiscais já possuem etiquetas geradas anteriormente.")
        ctk.CTkLabel(alerta, text="  " + msg, image=icone("aviso", 22, AMARELO), compound="left",
                     font=fonte(15, "bold"), text_color="#7a3e00").pack(anchor="w", padx=16, pady=(12, 2))
        ctk.CTkLabel(alerta, text=f"{len(notas)} nota(s) na lista: {n_rep} já processada(s) e {n_novas} nova(s). "
                                  "Confira a data da última geração e o status da impressão.",
                     font=fonte(12), text_color="#7a3e00").pack(anchor="w", padx=16, pady=(0, 12))

        quadro = tema.cartao(self)
        quadro.pack(fill="both", expand=True, padx=18)
        interno = ctk.CTkFrame(quadro, fg_color=CARTAO)
        interno.pack(fill="both", expand=True, padx=6, pady=6)
        self.tv = tema.tabela(interno, [
            ("nf", "NF", 80, "center"), ("transp", "Transportadora", 160, "w"), ("placa", "Placa", 90, "center"),
            ("vol", "Volumes", 70, "center"), ("data", "Última geração", 140, "center"),
            ("status", "Status da impressão", 170, "center"), ("ger", "Gerações", 80, "center"),
        ], esticar=("transp",), altura=6)
        self._regs: dict[str, Registro] = {}
        for i in sorted(ja):
            r = ja[i]
            self._regs[str(i)] = r
            self.tv.insert("", "end", iid=str(i), values=(r.numero_impresso, r.transportadora, r.placa or "—",
                                                         r.volumes, r.data_formatada, r.status_rotulo, r.geracoes))
        if self.tv.get_children():
            self.tv.selection_set(self.tv.get_children()[0])
        self.tv.bind("<Double-1>", lambda _e: self._ver())

        bts = ctk.CTkFrame(self, fg_color="transparent")
        bts.pack(fill="x", padx=18, pady=16)
        botao(bts, "Visualizar registro anterior", self._ver, icone_nome="ver", estilo="contorno").pack(side="left")
        botao(bts, "Abrir PDF anterior", self._abrir, icone_nome="abrir", estilo="contorno").pack(side="left", padx=8)
        botao(bts, "Cancelar", self.destroy).pack(side="right")
        botao(bts, f"Reimprimir / gerar novamente ({len(notas)})", self._todas, icone_nome="imprimir",
              estilo="perigo").pack(side="right", padx=8)
        b = botao(bts, f"Gerar só as novas ({n_novas})", self._novas, icone_nome="etiqueta", estilo="sucesso",
                  negrito=True)
        b.pack(side="right")
        if n_novas == 0:
            b.configure(state="disabled")
        self.bind("<Escape>", lambda _e: self.destroy())

    def _sel(self) -> Registro | None:
        s = self.tv.selection()
        return self._regs.get(s[0]) if s else None

    def _ver(self) -> None:
        r = self._sel()
        if r:
            DialogoDetalhes(self, self.app, r, permitir_acoes=False)

    def _abrir(self) -> None:
        r = self._sel()
        if r:
            acao_abrir_pdf(self, r)

    def _todas(self) -> None:
        if mb.askyesno("Gerar novamente",
                       "Confirma gerar novamente as etiquetas das notas já processadas?\n\n"
                       "Elas serão registradas como reimpressão (o registro anterior é mantido).", parent=self):
            self.resultado = TODAS
            self.destroy()

    def _novas(self) -> None:
        self.resultado = SO_NOVAS
        self.destroy()

    def perguntar(self) -> str | None:
        self.wait_window()
        return self.resultado


# ------------------------------------------------------------------ detalhes
class DialogoDetalhes(tema.JanelaCK):
    def __init__(self, master, app, registro: Registro, permitir_acoes: bool = True):
        super().__init__(master, f"NF {registro.numero_impresso} — detalhes", modal=True)
        self.app = app
        self.r = registro
        self.centralizar(840, 740)
        self.minsize(720, 640)
        r = registro

        cab = ctk.CTkFrame(self, fg_color="transparent")
        cab.pack(fill="x", padx=20, pady=(18, 8))
        ctk.CTkLabel(cab, text=f"NF {r.numero_impresso}", font=fonte(24, "bold"), text_color=TEXTO).pack(side="left")
        cor, fundo = CORES_STATUS.get(r.status, (TEXTO_2, "#eef2f7"))
        tema.selo_status(cab, r.status_rotulo, cor, fundo).pack(side="left", padx=12)

        dados = tema.cartao(self)
        dados.pack(fill="x", padx=20)
        campos = [
            ("Número completo", r.numero), ("Série", r.serie or "—"),
            ("Emitente", r.emitente or "—"), ("CNPJ do emitente", _cnpj(r.emitente_cnpj)),
            ("Chave de acesso", _chave(r.chave)), ("Transportadora", r.transportadora or "—"),
            ("Nome na DANFE", r.transportadora_nome or "—"), ("Placa", r.placa or "(sem placa)"),
            ("Volumes / etiquetas", f"{r.volumes} / {r.etiquetas}"), ("Gerações", str(r.geracoes)),
            ("Primeira geração", formatar_data(r.primeira_geracao_em)),
            ("Última geração", formatar_data(r.ultima_geracao_em)),
            ("Impressão solicitada", formatar_data(r.impressao_solicitada_em)),
            ("Impressão confirmada", formatar_data(r.impressao_confirmada_em)),
            ("PDF gerado", r.pdf_gerado or "—"), ("PDF de origem (DANFE)", r.arquivo_origem or "—"),
        ]
        grade = ctk.CTkFrame(dados, fg_color="transparent")
        grade.pack(fill="x", padx=16, pady=12)
        grade.grid_columnconfigure((1, 3), weight=1)
        largos = {"Chave de acesso", "Emitente", "PDF gerado", "PDF de origem (DANFE)", "Nome na DANFE"}
        lin = col = 0
        for rot, val in campos:
            if rot in largos:
                if col:
                    lin, col = lin + 1, 0
                ctk.CTkLabel(grade, text=rot, font=fonte(12), text_color=TEXTO_2, anchor="w").grid(
                    row=lin, column=0, sticky="w", pady=2)
                ctk.CTkLabel(grade, text=val, font=fonte(12, "bold"), text_color=TEXTO, anchor="w", wraplength=560,
                             justify="left").grid(row=lin, column=1, columnspan=3, sticky="w", padx=10, pady=2)
                lin += 1
                continue
            ctk.CTkLabel(grade, text=rot, font=fonte(12), text_color=TEXTO_2, anchor="w").grid(
                row=lin, column=col, sticky="w", pady=2)
            ctk.CTkLabel(grade, text=val, font=fonte(12, "bold"), text_color=TEXTO, anchor="w").grid(
                row=lin, column=col + 1, sticky="w", padx=10, pady=2)
            col += 2
            if col == 4:
                lin, col = lin + 1, 0

        ctk.CTkLabel(self, text="Linha do tempo", font=fonte(14, "bold"), text_color=TEXTO, anchor="w").pack(
            fill="x", padx=22, pady=(14, 4))
        quadro = tema.cartao(self)
        quadro.pack(fill="both", expand=True, padx=20)
        interno = ctk.CTkFrame(quadro, fg_color=CARTAO)
        interno.pack(fill="both", expand=True, padx=6, pady=6)
        tv = tema.tabela(interno, [("data", "Data e hora", 140, "center"), ("evento", "Evento", 170, "w"),
                                   ("etq", "Etiquetas", 80, "center"), ("det", "Detalhe", 300, "w")],
                         esticar=("det",), altura=4)
        try:
            eventos = app.historico.eventos(r.id)
        except Exception:  # noqa: BLE001
            eventos = []
        for i, e in enumerate(eventos):
            tv.insert("", "end", values=(e.data_formatada, e.rotulo, e.etiquetas, e.detalhe or e.pdf),
                      tags=("par",) if i % 2 else ())

        bts = ctk.CTkFrame(self, fg_color="transparent")
        bts.pack(fill="x", padx=20, pady=16)
        botao(bts, "Abrir PDF", lambda: acao_abrir_pdf(self, r), icone_nome="abrir", estilo="contorno").pack(
            side="left")
        if permitir_acoes:
            botao(bts, "Reimprimir", self._reimprimir, icone_nome="imprimir", estilo="primario").pack(
                side="left", padx=8)
            if r.status != IMPRESSAO_CONFIRMADA:
                botao(bts, "Confirmar impressão", self._confirmar, icone_nome="confirmado", estilo="sucesso").pack(
                    side="left")
        botao(bts, "Fechar", self.destroy).pack(side="right")
        self.bind("<Escape>", lambda _e: self.destroy())

    def _reimprimir(self) -> None:
        if acao_reimprimir(self, self.app, [self.r]):
            self.destroy()

    def _confirmar(self) -> None:
        if mb.askyesno("Confirmar impressão", f"Confirmar que as etiquetas da NF {self.r.numero_impresso} "
                                              "foram impressas corretamente?", parent=self):
            self.app.historico.confirmar_impressao([self.r.id], detalhe="confirmado pelo histórico")
            self.app.dados_alterados()
            self.app.notificacao.mostrar("Impressão confirmada.", "ok")
            self.destroy()


def _cnpj(c: str) -> str:
    return f"{c[:2]}.{c[2:5]}.{c[5:8]}/{c[8:12]}-{c[12:]}" if len(c) == 14 and c.isdigit() else (c or "—")


def _chave(c: str) -> str:
    return " ".join(c[i:i + 4] for i in range(0, len(c), 4)) if c else "—"
