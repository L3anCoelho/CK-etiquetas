"""Janela de conferência/edição dos dados de uma nota."""

from __future__ import annotations

import tkinter.messagebox as mb

import customtkinter as ctk

from ..modelos import NotaFiscal
from ..validacao import normalizar_placa, placa_valida
from . import tema


class DialogoEdicao(tema.JanelaCK):
    def __init__(self, master, nf: NotaFiscal, cadastro, ao_salvar):
        super().__init__(master, f"Conferir NF {nf.numero_original or '?'}", modal=True)
        self.nf = nf
        self.cadastro = cadastro
        self.ao_salvar = ao_salvar
        self.resizable(False, False)

        pad = {"padx": 14, "pady": (6, 0)}
        f = ctk.CTkFrame(self, fg_color="transparent")
        f.pack(fill="both", expand=True, padx=10, pady=10)
        f.grid_columnconfigure(1, weight=1)

        def rotulo(lin, texto):
            ctk.CTkLabel(f, text=texto, anchor="w", font=ctk.CTkFont(weight="bold")).grid(
                row=lin, column=0, sticky="w", **pad
            )

        rotulo(0, "Nº da NF")
        self.e_nf = ctk.CTkEntry(f, width=320)
        self.e_nf.insert(0, nf.numero)
        self.e_nf.grid(row=0, column=1, sticky="ew", **pad)
        ctk.CTkLabel(
            f, text=f"Original na DANFE: {nf.numero_original or '—'}   (página {nf.pagina or '—'})",
            text_color="gray50", anchor="w",
        ).grid(row=1, column=1, sticky="w", padx=14)

        rotulo(2, "Transportadora")
        self.e_transp = ctk.CTkEntry(f, width=320)
        self.e_transp.insert(0, nf.transportadora)
        self.e_transp.grid(row=2, column=1, sticky="ew", **pad)
        ctk.CTkLabel(
            f, text=f"Nome na DANFE: {nf.transportadora_nome or '— não identificado —'}",
            text_color="gray50", anchor="w", wraplength=380, justify="left",
        ).grid(row=3, column=1, sticky="w", padx=14)
        self.v_confirma = ctk.BooleanVar(value=nf.transportadora_confirmada)
        ctk.CTkCheckBox(
            f, text="Confirmo o texto da transportadora que será impresso", variable=self.v_confirma
        ).grid(row=4, column=1, sticky="w", **pad)
        self.v_salvar = ctk.BooleanVar(value=False)
        self.cb_salvar = ctk.CTkCheckBox(
            f, text="Salvar como abreviação padrão desta transportadora", variable=self.v_salvar
        )
        self.cb_salvar.grid(row=5, column=1, sticky="w", **pad)
        if not nf.transportadora_nome:
            self.cb_salvar.configure(state="disabled")

        rotulo(6, "Volumes")
        self.e_vol = ctk.CTkEntry(f, width=120)
        self.e_vol.insert(0, "" if nf.volumes is None else str(nf.volumes))
        self.e_vol.grid(row=6, column=1, sticky="w", **pad)
        ctk.CTkLabel(
            f, text=f"Campo 'Quantidade' na DANFE: {nf.volumes_original or '— vazio —'}",
            text_color="gray50", anchor="w",
        ).grid(row=7, column=1, sticky="w", padx=14)

        rotulo(8, "Placa do cliente")
        self.e_placa = ctk.CTkEntry(f, width=160)
        self.e_placa.insert(0, nf.placa)
        self.e_placa.grid(row=8, column=1, sticky="w", **pad)
        ctk.CTkLabel(
            f, text="Formatos: AAA9999 (antiga) ou AAA9A99 (Mercosul). Placa das observações, "
            "não a do caminhão.", text_color="gray50", anchor="w", wraplength=380, justify="left",
        ).grid(row=9, column=1, sticky="w", padx=14)
        self.v_sem_placa = ctk.BooleanVar(value=nf.excecao_sem_placa)
        ctk.CTkCheckBox(
            f, text="Exceção: gerar etiqueta SEM placa", variable=self.v_sem_placa
        ).grid(row=10, column=1, sticky="w", **pad)
        self.v_fora_padrao = ctk.BooleanVar(value=nf.excecao_placa_fora_padrao)
        ctk.CTkCheckBox(
            f, text="Exceção: aceitar placa fora do padrão brasileiro", variable=self.v_fora_padrao
        ).grid(row=11, column=1, sticky="w", **pad)

        if nf.avisos_extracao:
            ctk.CTkLabel(
                f, text="Avisos da leitura:\n• " + "\n• ".join(nf.avisos_extracao),
                text_color="#b26a00", anchor="w", justify="left", wraplength=500,
            ).grid(row=12, column=0, columnspan=2, sticky="w", padx=14, pady=(10, 0))

        botoes = ctk.CTkFrame(f, fg_color="transparent")
        botoes.grid(row=13, column=0, columnspan=2, sticky="e", pady=(16, 4), padx=14)
        tema.botao(botoes, "Cancelar", self.destroy, largura=110).pack(
            side="right", padx=(8, 0)
        )
        tema.botao(botoes, "Salvar", self._salvar, icone_nome="salvar", estilo="primario", largura=110).pack(side="right")
        self.bind("<Return>", lambda _e: self._salvar())
        self.bind("<Escape>", lambda _e: self.destroy())
        self.e_nf.focus_set()

    def _salvar(self) -> None:
        numero = self.e_nf.get().strip()
        if numero and not numero.isdigit():
            mb.showerror("NF inválida", "O número da NF deve conter apenas dígitos.", parent=self)
            return
        vol_txt = self.e_vol.get().strip()
        if vol_txt and not vol_txt.isdigit():
            mb.showerror("Volumes inválidos", "Informe a quantidade de volumes como número inteiro.", parent=self)
            return
        placa = normalizar_placa(self.e_placa.get())
        if placa and not placa_valida(placa) and not self.v_fora_padrao.get():
            if not mb.askyesno(
                "Placa fora do padrão",
                f"A placa '{placa}' não está no formato AAA9999 nem AAA9A99.\n\n"
                "Deseja manter assim? (a nota ficará pendente até marcar a exceção)",
                parent=self,
            ):
                return
        transp = self.e_transp.get().strip()

        nf = self.nf
        nf.numero = str(int(numero)) if numero else ""
        nf.volumes = int(vol_txt) if vol_txt else None
        nf.placa = placa
        nf.excecao_sem_placa = self.v_sem_placa.get()
        nf.excecao_placa_fora_padrao = self.v_fora_padrao.get()
        if transp != nf.transportadora:
            nf.transportadora = transp
        nf.transportadora_confirmada = bool(transp) and self.v_confirma.get()
        if self.v_salvar.get() and transp and nf.transportadora_nome:
            self.cadastro.salvar(nf.transportadora_nome, nf.transportadora_cnpj, transp)
            nf.transportadora_confirmada = True
        self.ao_salvar(nf, salvou_abreviacao=self.v_salvar.get())
        self.destroy()
