"""Página "Configurações": pastas, impressão, abreviações, backup e restauração."""

from __future__ import annotations

import os
import tkinter.filedialog as fd
import tkinter.messagebox as mb
from datetime import datetime
from pathlib import Path

import customtkinter as ctk

from .. import __version__, backup, banco, config
from ..preferencias import IMPRIMIR_ABRIR, IMPRIMIR_DIRETO, Preferencias
from . import tema
from .tema import AMARELO, AMARELO_SUAVE, BORDA, CARTAO, FUNDO, TEXTO, TEXTO_2, botao, fonte, icone

MODOS = {"Abrir no leitor de PDF (recomendado)": IMPRIMIR_ABRIR,
         "Enviar direto para a impressora padrão": IMPRIMIR_DIRETO}


def _secao(master, titulo: str, icone_nome: str, descricao: str = "") -> ctk.CTkFrame:
    c = tema.cartao(master)
    c.pack(fill="x", pady=(0, 14))
    cab = ctk.CTkFrame(c, fg_color="transparent")
    cab.pack(fill="x", padx=18, pady=(14, 4))
    ctk.CTkLabel(cab, text="  " + titulo, image=icone(icone_nome, 20, tema.AZUL), compound="left",
                 font=fonte(16, "bold"), text_color=TEXTO).pack(side="left")
    if descricao:
        ctk.CTkLabel(c, text=descricao, font=fonte(12), text_color=TEXTO_2, anchor="w", justify="left",
                     wraplength=900).pack(fill="x", padx=18)
    corpo = ctk.CTkFrame(c, fg_color="transparent")
    corpo.pack(fill="x", padx=18, pady=(8, 16))
    return corpo


class PaginaConfiguracoes(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color=FUNDO, corner_radius=0)
        self.app = app
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        tema.titulo_pagina(self, "Configurações", "Preferências salvas automaticamente nesta máquina.").grid(
            row=0, column=0, sticky="w", padx=28, pady=(24, 12))
        rolagem = ctk.CTkScrollableFrame(self, fg_color=FUNDO, corner_radius=0)
        rolagem.grid(row=1, column=0, sticky="nsew", padx=(28, 12), pady=(0, 12))
        self.r = rolagem
        self._pastas()
        self._impressao()
        self._abreviacoes()
        self._dados()

    @property
    def prefs(self) -> Preferencias:
        return self.app.prefs

    def _salvar(self, msg: str = "Configurações salvas.") -> None:
        try:
            self.prefs.salvar()
            self.app.notificacao.mostrar(msg, "ok", 2.5)
        except OSError as e:
            mb.showerror("Configurações", f"Não foi possível salvar:\n{e}")

    # ------------------------------------------------------------ pastas
    def _linha_pasta(self, corpo, rotulo: str, ajuda: str, atributo: str) -> None:
        f = ctk.CTkFrame(corpo, fg_color="transparent")
        f.pack(fill="x", pady=4)
        f.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(f, text=rotulo, font=fonte(13, "bold"), text_color=TEXTO, anchor="w").grid(
            row=0, column=0, sticky="w")
        ctk.CTkLabel(f, text=ajuda, font=fonte(12), text_color=TEXTO_2, anchor="w").grid(row=1, column=0, sticky="w")
        e = ctk.CTkEntry(f, height=36, corner_radius=8, border_color=BORDA, fg_color="#f8fafc", font=fonte(13))
        e.insert(0, getattr(self.prefs, atributo))
        e.configure(state="readonly")
        e.grid(row=2, column=0, sticky="ew", pady=(4, 0))

        def escolher():
            atual = getattr(self.prefs, atributo)
            p = fd.askdirectory(title=rotulo, initialdir=atual if Path(atual).is_dir() else None, mustexist=False)
            if p:
                setattr(self.prefs, atributo, str(Path(p)))
                e.configure(state="normal")
                e.delete(0, "end")
                e.insert(0, str(Path(p)))
                e.configure(state="readonly")
                self._salvar()

        def abrir():
            p = Path(getattr(self.prefs, atributo))
            p.mkdir(parents=True, exist_ok=True)
            os.startfile(p)  # type: ignore[attr-defined]

        botao(f, "Alterar…", escolher, icone_nome="pasta", estilo="contorno", altura=36).grid(
            row=2, column=1, padx=(8, 0), pady=(4, 0))
        botao(f, "", abrir, icone_nome="abrir", altura=36, largura=40).grid(row=2, column=2, padx=(6, 0),
                                                                             pady=(4, 0))

    def _pastas(self) -> None:
        c = _secao(self.r, "Pastas", "pasta")
        self._linha_pasta(c, "Pasta padrão das notas exportadas do Bling",
                          "Onde o botão 'Adicionar notas fiscais' começa a procurar os PDFs de DANFE.", "pasta_notas")
        self._linha_pasta(c, "Local de armazenamento dos PDFs de etiquetas",
                          "Os PDFs gerados ficam aqui, organizados em subpastas por mês (ex.: 2026-11).",
                          "pasta_pdfs")
        self.v_auto = ctk.BooleanVar(value=self.prefs.salvar_automaticamente)
        ctk.CTkSwitch(c, text="Salvar automaticamente na pasta de PDFs (sem perguntar o nome do arquivo)",
                      variable=self.v_auto, font=fonte(13), text_color=TEXTO, progress_color=tema.AZUL,
                      command=self._mudou_auto).pack(anchor="w", pady=(10, 0))

    def _mudou_auto(self) -> None:
        self.prefs.salvar_automaticamente = self.v_auto.get()
        self._salvar()

    # ------------------------------------------------------------ impressão
    def _impressao(self) -> None:
        c = _secao(self.r, "Impressão", "imprimir")
        ctk.CTkLabel(c, text="Ao imprimir as etiquetas", font=fonte(13, "bold"), text_color=TEXTO, anchor="w").pack(
            anchor="w")
        self.v_modo = ctk.StringVar(value=next(k for k, v in MODOS.items() if v == self.prefs.modo_impressao))
        for rot in MODOS:
            ctk.CTkRadioButton(c, text=rot, variable=self.v_modo, value=rot, font=fonte(13), text_color=TEXTO,
                               fg_color=tema.AZUL, command=self._mudou_impressao).pack(anchor="w", pady=3)
        self.v_abrir = ctk.BooleanVar(value=self.prefs.abrir_apos_gerar)
        ctk.CTkSwitch(c, text="Imprimir logo após gerar o PDF", variable=self.v_abrir, font=fonte(13),
                      text_color=TEXTO, progress_color=tema.AZUL, command=self._mudou_impressao).pack(
            anchor="w", pady=(10, 3))
        self.v_conf = ctk.BooleanVar(value=self.prefs.confirmar_impressao)
        ctk.CTkSwitch(c, text="Perguntar se a impressão deu certo (registra 'Impressão confirmada')",
                      variable=self.v_conf, font=fonte(13), text_color=TEXTO, progress_color=tema.AZUL,
                      command=self._mudou_impressao).pack(anchor="w", pady=3)
        aviso = ctk.CTkFrame(c, fg_color=AMARELO_SUAVE, corner_radius=10)
        aviso.pack(fill="x", pady=(12, 0))
        ctk.CTkLabel(aviso, text="  Na impressora, use sempre 'Tamanho real' / escala 100%. 'Ajustar à página' "
                                 "encolhe as etiquetas e desloca a linha de corte (148,5 mm).",
                     image=icone("aviso", 16, AMARELO), compound="left", font=fonte(12), text_color="#7a3e00",
                     wraplength=860, justify="left").pack(anchor="w", padx=12, pady=8)

    def _mudou_impressao(self) -> None:
        self.prefs.modo_impressao = MODOS[self.v_modo.get()]
        self.prefs.abrir_apos_gerar = self.v_abrir.get()
        self.prefs.confirmar_impressao = self.v_conf.get()
        self._salvar()

    # ------------------------------------------------------------ abreviações
    def _abreviacoes(self) -> None:
        c = _secao(self.r, "Abreviações de transportadoras", "caminhao",
                   "Texto impresso na etiqueta para cada transportadora. A busca é pelo nome exato que aparece na "
                   "DANFE. As abreviações padrão do programa podem ser substituídas, mas não removidas.")
        q = ctk.CTkFrame(c, fg_color=CARTAO, border_width=1, border_color=BORDA, corner_radius=10, height=220)
        q.pack(fill="x")
        q.pack_propagate(False)
        interno = ctk.CTkFrame(q, fg_color=CARTAO)
        interno.pack(fill="both", expand=True, padx=4, pady=4)
        self.tv_ab = tema.tabela(interno, [("nome", "Nome na DANFE", 320, "w"), ("cnpj", "CNPJ", 160, "center"),
                                           ("ab", "Abreviação impressa", 180, "w"), ("orig", "Origem", 90, "center")],
                                 esticar=("nome",), altura=5)
        self.tv_ab.bind("<Double-1>", lambda _e: self._editar_ab())
        bts = ctk.CTkFrame(c, fg_color="transparent")
        bts.pack(fill="x", pady=(10, 0))
        botao(bts, "Adicionar", lambda: self._editar_ab(novo=True), icone_nome="adicionar", estilo="primario").pack(
            side="left")
        botao(bts, "Editar", self._editar_ab, icone_nome="editar").pack(side="left", padx=8)
        botao(bts, "Remover", self._remover_ab, icone_nome="remover").pack(side="left")
        self._carregar_ab()

    def _carregar_ab(self) -> None:
        self.app.cadastro.carregar()
        self.tv_ab.delete(*self.tv_ab.get_children())
        self._ab = {}
        for i, r in enumerate(self.app.cadastro.listar()):
            self._ab[str(i)] = r
            cnpj = r["cnpj"]
            if len(cnpj) == 14:
                cnpj = f"{cnpj[:2]}.{cnpj[2:5]}.{cnpj[5:8]}/{cnpj[8:12]}-{cnpj[12:]}"
            self.tv_ab.insert("", "end", iid=str(i), values=(r["nome"], cnpj, r["abreviacao"], r["origem"]))

    def _editar_ab(self, novo: bool = False) -> None:
        reg = None
        if not novo:
            s = self.tv_ab.selection()
            if not s:
                self.app.notificacao.mostrar("Selecione uma transportadora.", "info")
                return
            reg = self._ab[s[0]]
        DialogoAbreviacao(self, reg, self._salvar_ab)

    def _salvar_ab(self, nome: str, cnpj: str, abrev: str) -> None:
        self.app.cadastro.salvar(nome, cnpj, abrev)
        self._carregar_ab()
        self.app.notificacao.mostrar("Abreviação salva.", "ok", 2.5)

    def _remover_ab(self) -> None:
        s = self.tv_ab.selection()
        if not s:
            return
        r = self._ab[s[0]]
        if r["origem"] != "usuário":
            mb.showinfo("Abreviações", "Esta é uma abreviação padrão do programa e não pode ser removida "
                                       "(pode ser substituída com 'Editar').")
            return
        if mb.askyesno("Remover", f"Remover a abreviação de '{r['nome']}'?"):
            self.app.cadastro.remover(r["nome"])
            self._carregar_ab()

    # ------------------------------------------------------------ dados e backup
    def _dados(self) -> None:
        c = _secao(self.r, "Dados, backup e restauração", "backup",
                   "O histórico, as configurações e as abreviações ficam na pasta de dados abaixo — fora da pasta "
                   "do programa, por isso são preservados ao atualizar ou desinstalar. Um backup automático é "
                   "feito uma vez por dia (os 15 mais recentes são mantidos).")
        f = ctk.CTkFrame(c, fg_color="#f8fafc", corner_radius=10)
        f.pack(fill="x")
        ctk.CTkLabel(f, text=f"Pasta de dados:  {config.PASTA_DADOS}", font=fonte(12), text_color=TEXTO,
                     anchor="w").pack(side="left", padx=12, pady=10)
        botao(f, "Abrir pasta", lambda: self._abrir(config.PASTA_DADOS), icone_nome="pasta", estilo="contorno",
              altura=32).pack(side="right", padx=8)
        bts = ctk.CTkFrame(c, fg_color="transparent")
        bts.pack(fill="x", pady=(12, 0))
        botao(bts, "Criar backup…", self._criar_backup, icone_nome="salvar", estilo="primario", altura=40,
              negrito=True).pack(side="left")
        botao(bts, "Restaurar backup…", self._restaurar_backup, icone_nome="restaurar", estilo="contorno",
              altura=40).pack(side="left", padx=8)
        botao(bts, "Backups automáticos", lambda: self._abrir(config.PASTA_BACKUPS), icone_nome="pasta",
              altura=40).pack(side="left")
        ctk.CTkLabel(c, text=f"CK Etiquetas {__version__}  •  banco de dados versão {banco.VERSAO_ESQUEMA}  •  "
                             "funcionamento 100% offline", font=fonte(11), text_color=TEXTO_2).pack(
            anchor="w", pady=(14, 0))

    @staticmethod
    def _abrir(pasta: Path) -> None:
        Path(pasta).mkdir(parents=True, exist_ok=True)
        os.startfile(pasta)  # type: ignore[attr-defined]

    def _criar_backup(self) -> None:
        destino = fd.asksaveasfilename(
            title="Salvar backup do CK Etiquetas", defaultextension=".zip", filetypes=[("Backup (.zip)", "*.zip")],
            initialdir=str(Path.home() / "Documents"),
            initialfile=f"backup_ck_etiquetas_{datetime.now():%Y-%m-%d_%H%M}.zip")
        if not destino:
            return
        try:
            backup.criar_backup(destino)
        except Exception as e:  # noqa: BLE001
            mb.showerror("Backup", f"Não foi possível criar o backup:\n{e}")
            return
        self.app.notificacao.mostrar("Backup criado com sucesso.", "ok")

    def _restaurar_backup(self) -> None:
        arq = fd.askopenfilename(title="Restaurar backup do CK Etiquetas", filetypes=[("Backup (.zip)", "*.zip")],
                                 initialdir=str(config.PASTA_BACKUPS) if config.PASTA_BACKUPS.is_dir() else None)
        if not arq:
            return
        try:
            m = backup.ler_manifesto(arq)
        except Exception as e:  # noqa: BLE001
            mb.showerror("Restaurar", str(e))
            return
        if not mb.askyesno("Restaurar backup",
                           f"Backup de {m.get('criado_em', '?').replace('T', ' ')} (versão {m.get('versao', '?')}).\n\n"
                           "Os dados atuais (histórico, configurações e abreviações) serão SUBSTITUÍDOS pelos do "
                           "backup. Antes disso, uma cópia de segurança dos dados atuais é salva automaticamente.\n\n"
                           "Continuar?", icon="warning"):
            return
        try:
            seguranca = backup.restaurar_backup(arq)
        except Exception as e:  # noqa: BLE001
            mb.showerror("Restaurar", f"Não foi possível restaurar:\n{e}")
            return
        self.app.prefs = Preferencias.carregar()
        self.app.cadastro.carregar()
        self.app.dados_alterados()
        mb.showinfo("Restaurar", f"Backup restaurado.\n\nCópia dos dados anteriores:\n{seguranca}\n\n"
                                 "Feche e abra o CK Etiquetas para recarregar todas as telas.")


class DialogoAbreviacao(tema.JanelaCK):
    def __init__(self, master, reg: dict | None, ao_salvar):
        super().__init__(master, "Abreviação de transportadora", modal=True)
        self.ao_salvar = ao_salvar
        self.resizable(False, False)
        self.centralizar(520, 360)
        c = tema.cartao(self)
        c.pack(fill="both", expand=True, padx=16, pady=16)
        kw = dict(height=36, corner_radius=8, border_color=BORDA, fg_color="#f8fafc", font=fonte(13))
        self.campos = {}
        for rot, chave, ph in (("Nome exatamente como na DANFE", "nome", "Ex.: RODONAVES - TRANSP.ENC.LTDA."),
                               ("CNPJ (opcional)", "cnpj", "00.000.000/0000-00"),
                               ("Texto impresso na etiqueta", "abreviacao", "Ex.: RODONAVES")):
            ctk.CTkLabel(c, text=rot, font=fonte(12, "bold"), text_color=TEXTO_2, anchor="w").pack(
                fill="x", padx=18, pady=(12, 2))
            e = ctk.CTkEntry(c, placeholder_text=ph, **kw)
            e.pack(fill="x", padx=18)
            if reg and reg.get(chave):
                e.insert(0, reg[chave])
            self.campos[chave] = e
        if reg:
            self.campos["nome"].configure(state="disabled")
        bts = ctk.CTkFrame(c, fg_color="transparent")
        bts.pack(fill="x", padx=18, pady=16, side="bottom")
        botao(bts, "Cancelar", self.destroy).pack(side="right")
        botao(bts, "Salvar", self._salvar, icone_nome="salvar", estilo="primario", negrito=True).pack(
            side="right", padx=8)
        self.bind("<Return>", lambda _e: self._salvar())
        self.bind("<Escape>", lambda _e: self.destroy())

    def _salvar(self) -> None:
        nome = self.campos["nome"].get().strip()
        ab = self.campos["abreviacao"].get().strip()
        if not nome or not ab:
            mb.showerror("Abreviação", "Preencha o nome da transportadora e o texto impresso.", parent=self)
            return
        self.ao_salvar(nome, self.campos["cnpj"].get().strip(), ab)
        self.destroy()


