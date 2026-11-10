"""Página "Gerar etiquetas": importar DANFEs, conferir, gerar o PDF e controlar a impressão."""

from __future__ import annotations

import os
import queue
import threading
import tkinter.filedialog as fd
import tkinter.messagebox as mb
from pathlib import Path

import customtkinter as ctk

from .. import impressao, operacoes
from ..extrator import preparar_notas
from ..gerador_pdf import montar_documento
from ..lote import importar_arquivos, validar_lista
from ..modelos import NotaFiscal
from ..validacao import ERRO, status
from ..volumes import expandir_etiquetas, total_etiquetas
from . import tema
from .dialogo_edicao import DialogoEdicao
from .dialogo_historico import TODAS, DialogoDuplicadas, perguntar_confirmacao_impressao
from .tema import (AMARELO, AZUL, BORDA, CARTAO, FUNDO, TEXTO, TEXTO_2, TEXTO_3, VERDE, VERMELHO, botao,
                   fonte, icone)
from .visualizacao import JanelaVisualizacao


class PaginaGerar(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color=FUNDO, corner_radius=0)
        self.app = app
        self.notas: list[NotaFiscal] = []
        self.avisos_gerais: list[str] = []
        self._problemas: list = []
        self._processadas: dict = {}
        self._fila: queue.Queue = queue.Queue()
        self._lendo = False
        self.ultimo_lote: dict | None = None  # {"ids", "pdf", "notas", "etiquetas", "estado"}

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)
        self._montar_cabecalho()
        self._montar_barra()
        self._montar_tabela()
        self._montar_rodape()
        self._atualizar()

    # ------------------------------------------------------------ montagem
    def _montar_cabecalho(self) -> None:
        cab = ctk.CTkFrame(self, fg_color="transparent")
        cab.grid(row=0, column=0, sticky="ew", padx=28, pady=(24, 12))
        cab.grid_columnconfigure(0, weight=1)
        tema.titulo_pagina(cab, "Gerar etiquetas",
                           "Importe os PDFs de DANFEs exportados do Bling, confira os dados e gere as etiquetas."
                           ).grid(row=0, column=0, sticky="w")
        ind = ctk.CTkFrame(cab, fg_color="transparent")
        ind.grid(row=0, column=1, sticky="e")
        self.ind_notas = tema.CartaoIndicador(ind, "Notas carregadas", "documento", compacto=True)
        self.ind_etq = tema.CartaoIndicador(ind, "Total de etiquetas", "etiqueta", compacto=True)
        self.ind_folhas = tema.CartaoIndicador(ind, "Folhas A4", "imprimir", compacto=True)
        for c in (self.ind_notas, self.ind_etq, self.ind_folhas):
            c.pack(side="left", padx=(10, 0))

    def _montar_barra(self) -> None:
        barra = tema.cartao(self)
        barra.grid(row=1, column=0, sticky="ew", padx=28, pady=(0, 12))
        self.bt_adicionar = botao(barra, "Adicionar notas fiscais", self._adicionar_notas, icone_nome="adicionar",
                                  estilo="primario", altura=40, negrito=True)
        self.bt_adicionar.pack(side="left", padx=(12, 6), pady=12)
        self.bt_remover = botao(barra, "Remover selecionadas", self._remover, icone_nome="remover", altura=40)
        self.bt_remover.pack(side="left", padx=6)
        self.bt_limpar = botao(barra, "Limpar lista", self._limpar, icone_nome="limpar", altura=40)
        self.bt_limpar.pack(side="left", padx=6)
        sep = ctk.CTkFrame(barra, width=1, height=28, fg_color=BORDA)
        sep.pack(side="left", padx=8)
        self.bt_editar = botao(barra, "Editar", self._editar, icone_nome="editar", altura=40)
        self.bt_editar.pack(side="left", padx=6)
        self.bt_subir = botao(barra, "", lambda: self._mover(-1), icone_nome="subir", altura=40, largura=40)
        self.bt_subir.pack(side="left", padx=(6, 2))
        self.bt_descer = botao(barra, "", lambda: self._mover(1), icone_nome="descer", altura=40, largura=40)
        self.bt_descer.pack(side="left", padx=(2, 6))
        self.progresso = ctk.CTkProgressBar(barra, mode="determinate", width=150, progress_color=AZUL)
        self.lb_status = ctk.CTkLabel(barra, text="", text_color=TEXTO_2, font=fonte(12), anchor="e")
        self.lb_status.pack(side="right", padx=14)

    def _montar_tabela(self) -> None:
        self.quadro_tabela = tema.cartao(self)
        self.quadro_tabela.grid(row=2, column=0, sticky="nsew", padx=28, pady=(0, 12))
        interno = ctk.CTkFrame(self.quadro_tabela, fg_color=CARTAO, corner_radius=0)
        interno.pack(fill="both", expand=True, padx=8, pady=8)
        self.tabela = tema.tabela(interno, [
            ("ordem", "#", 36, "center"), ("nf", "NF", 70, "center"), ("transp", "Transportadora", 140, "w"),
            ("placa", "Placa", 90, "center"), ("vol", "Volumes", 70, "center"),
            ("status", "Status", 90, "center"), ("hist", "Histórico", 130, "w"), ("arquivo", "Arquivo", 100, "w"),
        ], esticar=("transp", "hist", "arquivo"), selecao="extended")
        self.tabela.bind("<Double-1>", lambda _e: self._editar())
        self.tabela.bind("<Return>", lambda _e: self._editar())
        self.tabela.bind("<Delete>", lambda _e: self._remover())
        self.tabela.bind("<<TreeviewSelect>>", lambda _e: self._mostrar_mensagens())

        # estado vazio
        self.vazio = ctk.CTkFrame(self.quadro_tabela, fg_color=CARTAO, corner_radius=12)
        ctk.CTkLabel(self.vazio, text="", image=icone("pdf", 56, "#9bb8e0")).pack(pady=(10, 8))
        ctk.CTkLabel(self.vazio, text="Nenhuma nota fiscal carregada", font=fonte(17, "bold"),
                     text_color=TEXTO).pack()
        self.lb_vazio = ctk.CTkLabel(self.vazio, text="", font=fonte(13), text_color=TEXTO_2)
        self.lb_vazio.pack(pady=(4, 14))
        botao(self.vazio, "Adicionar notas fiscais", self._adicionar_notas, icone_nome="adicionar",
              estilo="primario", altura=40, negrito=True).pack()

    def _montar_rodape(self) -> None:
        rod = ctk.CTkFrame(self, fg_color="transparent")
        rod.grid(row=3, column=0, sticky="ew", padx=28, pady=(0, 22))
        rod.grid_columnconfigure(0, weight=1)
        rod.grid_columnconfigure(1, minsize=470)

        msgs = tema.cartao(rod)
        msgs.grid(row=0, column=0, sticky="nsew", padx=(0, 12))
        ctk.CTkLabel(msgs, text="Conferência", font=fonte(13, "bold"), text_color=TEXTO, anchor="w").pack(
            fill="x", padx=16, pady=(10, 0))
        self.caixa_msg = ctk.CTkTextbox(msgs, height=112, wrap="word", fg_color=CARTAO, font=fonte(12),
                                        border_width=0, activate_scrollbars=True)
        self.caixa_msg.pack(fill="both", expand=True, padx=10, pady=(2, 10))
        for tag, cor in (("erro", VERMELHO), ("aviso", AMARELO), ("info", AZUL), ("ok", VERDE)):
            self.caixa_msg.tag_config(tag, foreground=cor)

        acoes = tema.cartao(rod)
        acoes.grid(row=0, column=1, sticky="nsew")
        topo = ctk.CTkFrame(acoes, fg_color="transparent")
        topo.pack(fill="x", padx=14, pady=(14, 8))
        self.bt_visualizar = botao(topo, "Visualizar", self._visualizar, icone_nome="ver", estilo="contorno",
                                   altura=48, largura=140)
        self.bt_visualizar.pack(side="left")
        self.bt_gerar = botao(topo, "Gerar todas as etiquetas", self._gerar, icone_nome="etiqueta",
                              estilo="sucesso", altura=48, largura=260, tamanho_fonte=15, negrito=True)
        self.bt_gerar.pack(side="left", padx=(10, 0))

        # painel do último PDF gerado (controle de impressão)
        self.painel_lote = ctk.CTkFrame(acoes, fg_color="#f8fafc", corner_radius=10)
        self.painel_lote.pack(fill="x", padx=14, pady=(0, 14))
        self.lb_lote = ctk.CTkLabel(self.painel_lote, text="", font=fonte(12), text_color=TEXTO_2, anchor="w",
                                    justify="left", image=None, compound="left")
        self.lb_lote.pack(fill="x", padx=12, pady=(8, 4))
        bts = ctk.CTkFrame(self.painel_lote, fg_color="transparent")
        bts.pack(fill="x", padx=8, pady=(0, 8))
        self.bt_imprimir = botao(bts, "Imprimir", self._imprimir_lote, icone_nome="imprimir", estilo="primario",
                                 altura=34)
        self.bt_imprimir.pack(side="left", padx=4)
        self.bt_confirmar = botao(bts, "Confirmar impressão", self._confirmar_lote, icone_nome="confirmado",
                                  estilo="contorno", altura=34)
        self.bt_confirmar.pack(side="left", padx=4)
        self.bt_pasta = botao(bts, "", self._abrir_pasta_lote, icone_nome="pasta", altura=34, largura=38)
        self.bt_pasta.pack(side="left", padx=4)

    # ------------------------------------------------------------ leitura
    def ao_mostrar(self) -> None:
        self.lb_vazio.configure(
            text=("Arraste os PDFs para esta janela ou clique no botão abaixo.\n" if self.app.dnd_ativo else "")
            + "Um PDF com várias notas ou vários PDFs de uma vez (Ctrl/Shift).")

    def _adicionar_notas(self) -> None:
        pasta = self.app.prefs.pasta_notas
        caminhos = fd.askopenfilenames(
            title="Adicionar notas fiscais (PDFs do Bling) — Ctrl/Shift para vários",
            initialdir=pasta if pasta and Path(pasta).is_dir() else None, filetypes=[("PDF", "*.pdf")])
        if caminhos:
            self.importar(list(caminhos))

    def importar(self, caminhos: list[str]) -> None:
        if self._lendo:
            self.app.notificacao.mostrar("Aguarde: ainda lendo os arquivos anteriores.", "aviso")
            return
        if not caminhos:
            return
        self._lendo = True
        self.bt_adicionar.configure(state="disabled")
        self.lb_status.configure(text="Lendo…", text_color=AZUL)
        self.progresso.set(0)
        self.progresso.pack(side="right", padx=(0, 4))
        existentes = list(self.notas)
        threading.Thread(target=self._ler_em_segundo_plano, args=(caminhos, existentes), daemon=True).start()
        self.after(80, self._verificar_fila)

    def _ler_em_segundo_plano(self, caminhos, existentes) -> None:
        try:
            res = importar_arquivos(caminhos, existentes,
                                    progresso=lambda i, n, nome: self._fila.put(("progresso", (i, n, nome))))
            self._fila.put(("ok", res))
        except Exception as e:  # noqa: BLE001
            self._fila.put(("erro", e))

    def _verificar_fila(self) -> None:
        while True:
            try:
                tipo, dado = self._fila.get_nowait()
            except queue.Empty:
                self.after(80, self._verificar_fila)
                return
            if tipo != "progresso":
                break
            i, n, nome = dado
            self.progresso.set(i / n)
            self.lb_status.configure(text=f"Lendo {i}/{n}: {nome}")
        self.progresso.pack_forget()
        self.bt_adicionar.configure(state="normal")
        self._lendo = False
        if tipo == "erro":
            self.lb_status.configure(text="Falha na leitura", text_color=VERMELHO)
            mb.showerror("Erro ao ler PDF", f"Não foi possível ler os arquivos:\n{dado}")
            return
        res = dado
        self.app.cadastro.carregar()
        preparar_notas(res.novas, self.app.cadastro)
        self.notas.extend(res.novas)
        self.avisos_gerais.extend(res.avisos)
        partes = [f"{res.arquivos_lidos} arquivo(s)", f"{len(res.novas)} nota(s) adicionada(s)"]
        if res.duplicadas:
            partes.append(f"{res.duplicadas} repetida(s) ignorada(s)")
        if res.falhas:
            partes.append(f"{len(res.falhas)} com erro")
        self.lb_status.configure(text="  •  ".join(partes), text_color=TEXTO_2)
        self._atualizar()
        if res.novas:
            self.app.notificacao.mostrar(f"{len(res.novas)} nota(s) adicionada(s).", "ok")
        elif res.falhas:
            self.app.notificacao.mostrar("Nenhuma nota adicionada: falha na leitura.", "erro")
        else:
            self.app.notificacao.mostrar("Nenhuma nota nova encontrada.", "aviso")

    # ------------------------------------------------------------ tabela
    def _atualizar(self) -> None:
        sel = self.tabela.selection()
        self.tabela.delete(*self.tabela.get_children())
        self._problemas = validar_lista(self.notas)
        try:
            self._processadas = self.app.historico.ja_processadas(self.notas)
        except Exception:  # noqa: BLE001 - histórico indisponível não impede a conferência
            self._processadas = {}
        for i, nf in enumerate(self.notas):
            st = status(self._problemas[i])
            reg = self._processadas.get(i)
            hist = f"Gerada em {reg.data_formatada} — {reg.status_rotulo}" if reg else "Nova"
            self.tabela.insert("", "end", iid=str(i), tags=(st,), values=(
                i + 1, nf.numero or "?", nf.transportadora or "— não identificada —",
                nf.placa or ("(sem placa)" if nf.excecao_sem_placa else "?"),
                "?" if nf.volumes is None else nf.volumes, st, hist,
                Path(nf.arquivo_origem).name if nf.arquivo_origem else "",
            ))
        manter = [s for s in sel if self.tabela.exists(s)]
        if manter:
            self.tabela.selection_set(manter)

        n_et = total_etiquetas(self.notas)
        self.ind_notas.definir(len(self.notas))
        self.ind_etq.definir(n_et)
        self.ind_folhas.definir((n_et + 1) // 2)
        tem = bool(self.notas)
        if tem:
            self.vazio.place_forget()
        else:
            self.vazio.place(relx=0.5, rely=0.5, anchor="center")
        for b in (self.bt_visualizar, self.bt_gerar, self.bt_remover, self.bt_limpar, self.bt_editar,
                  self.bt_subir, self.bt_descer):
            b.configure(state="normal" if tem else "disabled")
        self._atualizar_painel_lote()
        self._mostrar_mensagens()

    def _mostrar_mensagens(self) -> None:
        c = self.caixa_msg
        c.configure(state="normal")
        c.delete("1.0", "end")
        for a in self.avisos_gerais:
            c.insert("end", f"• {a}\n", "aviso")
        pend = 0
        for nf, probs in zip(self.notas, self._problemas):
            for p in probs:
                if p.nivel == ERRO:
                    pend += 1
                c.insert("end", f"NF {nf.numero or nf.numero_original or '?'} — {p.campo}: {p.mensagem}\n",
                         "erro" if p.nivel == ERRO else "aviso")
        for i, reg in sorted(self._processadas.items()):
            c.insert("end", f"NF {self.notas[i].numero} — já possui etiquetas geradas em {reg.data_formatada} "
                            f"({reg.status_rotulo}).\n", "info")
        if self.notas and pend == 0:
            c.insert("end", "Todas as notas estão prontas para gerar as etiquetas.\n", "ok")
        if not self.notas and not self.avisos_gerais:
            c.insert("end", "Clique em 'Adicionar notas fiscais' para começar. Duplo clique em uma linha "
                            "permite corrigir NF, transportadora, volumes e placa.\n")
        c.configure(state="disabled")

    def _indices_selecionados(self) -> list[int]:
        return sorted(int(s) for s in self.tabela.selection())

    def _nota_selecionada(self) -> NotaFiscal | None:
        sel = self._indices_selecionados()
        if not sel:
            if len(self.notas) == 1:
                return self.notas[0]
            self.app.notificacao.mostrar("Selecione uma linha da tabela.", "info")
            return None
        foco = self.tabela.focus()
        return self.notas[int(foco)] if foco and int(foco) in sel else self.notas[sel[0]]

    def _editar(self) -> None:
        nf = self._nota_selecionada()
        if nf:
            DialogoEdicao(self, nf, self.app.cadastro, self._apos_edicao)

    def _apos_edicao(self, nf: NotaFiscal, salvou_abreviacao: bool) -> None:
        if salvou_abreviacao:
            for outra in self.notas:
                if outra is not nf and not outra.transportadora_confirmada:
                    ab = self.app.cadastro.buscar(outra.transportadora_nome, outra.transportadora_cnpj)
                    if ab:
                        outra.transportadora, outra.transportadora_confirmada = ab, True
        self._atualizar()

    def _remover(self) -> None:
        sel = self._indices_selecionados()
        if not sel:
            self.app.notificacao.mostrar("Selecione uma ou mais linhas (Ctrl/Shift + clique).", "info")
            return
        nums = ", ".join(self.notas[i].numero or "?" for i in sel[:12]) + ("…" if len(sel) > 12 else "")
        if mb.askyesno("Remover notas", f"Remover {len(sel)} nota(s) da lista?\n\nNF {nums}"):
            for i in reversed(sel):
                del self.notas[i]
            self.tabela.selection_set(())
            self._atualizar()

    def _limpar(self) -> None:
        if self.notas and not mb.askyesno("Limpar lista", f"Remover todas as {len(self.notas)} nota(s) da lista?"):
            return
        self.notas.clear()
        self.avisos_gerais.clear()
        self.lb_status.configure(text="")
        self.tabela.selection_set(())
        self._atualizar()

    def _mover(self, passo: int) -> None:
        sel = self._indices_selecionados()
        if not sel:
            return
        if (passo < 0 and sel[0] == 0) or (passo > 0 and sel[-1] == len(self.notas) - 1):
            return
        for i in (sel if passo < 0 else reversed(sel)):
            self.notas[i], self.notas[i + passo] = self.notas[i + passo], self.notas[i]
        self.tabela.selection_set(())
        self._atualizar()
        self.tabela.selection_set([str(i + passo) for i in sel])
        self.tabela.see(str(sel[0] + passo))

    # ------------------------------------------------------------ geração
    def _pendencias(self) -> list[str]:
        return [f"NF {nf.numero or nf.numero_original or '?'}: {p.mensagem}"
                for nf, probs in zip(self.notas, validar_lista(self.notas)) for p in probs if p.nivel == ERRO]

    def _visualizar(self) -> None:
        ets = expandir_etiquetas([nf for nf in self.notas if nf.volumes and nf.numero])
        if not ets:
            self.app.notificacao.mostrar("Não há etiquetas para visualizar.", "info")
            return
        try:
            doc, rel = montar_documento(ets)
        except Exception as e:  # noqa: BLE001
            mb.showerror("Erro", str(e))
            return
        avisos = list(rel.ajustes)
        pend = self._pendencias()
        if pend:
            avisos.insert(0, f"ATENÇÃO: {len(pend)} pendência(s) — esta visualização ainda não é definitiva.")
        JanelaVisualizacao(self, doc, avisos)

    def _gerar(self) -> None:
        pend = self._pendencias()
        if pend:
            mb.showerror("Pendências encontradas",
                         "Corrija os itens abaixo antes de gerar (duplo clique na linha para editar):\n\n"
                         + "\n".join(pend[:15]) + ("\n…" if len(pend) > 15 else ""))
            return
        notas = list(self.notas)  # ordem da tabela
        try:
            ja = self.app.historico.ja_processadas(notas)
        except Exception as e:  # noqa: BLE001
            mb.showerror("Histórico indisponível", f"Não foi possível consultar o histórico:\n{e}")
            return
        reimpressao = False
        if ja:
            escolha = DialogoDuplicadas(self, self.app, notas, ja).perguntar()
            if escolha is None:
                return
            if escolha == TODAS:
                reimpressao = True
            else:
                notas = [nf for i, nf in enumerate(notas) if i not in ja]
                if not notas:
                    return

        prefs = self.app.prefs
        if prefs.salvar_automaticamente:
            destino = operacoes.destino_automatico(prefs, notas)
        else:
            pasta = Path(prefs.pasta_pdfs)
            pasta.mkdir(parents=True, exist_ok=True)
            esc = fd.asksaveasfilename(title="Salvar etiquetas", initialdir=str(pasta),
                                       initialfile=operacoes.nome_arquivo(notas), defaultextension=".pdf",
                                       filetypes=[("PDF", "*.pdf")])
            if not esc:
                return
            destino = Path(esc)
        origens = {Path(nf.arquivo_origem).resolve() for nf in notas if nf.arquivo_origem}
        if destino.resolve() in origens:
            mb.showerror("Arquivo inválido", "Escolha outro nome: um PDF de notas fiscais não pode ser sobrescrito.")
            return
        try:
            rel, ids = operacoes.gerar_lote(notas, destino, self.app.historico,
                                            detalhe=f"lote de {len(notas)} nota(s)"
                                            + (" — gerado novamente" if reimpressao else ""))
        except PermissionError:
            mb.showerror("Erro ao salvar", "O arquivo está aberto em outro programa. Feche-o e tente novamente.")
            return
        except Exception as e:  # noqa: BLE001
            mb.showerror("Erro ao gerar", str(e))
            return

        self.ultimo_lote = {"ids": ids, "pdf": destino, "notas": len(notas), "etiquetas": rel.etiquetas,
                            "folhas": rel.folhas, "estado": "gerado"}
        self.app.dados_alterados()
        self._atualizar()
        self.app.notificacao.mostrar(f"PDF gerado: {rel.etiquetas} etiqueta(s) em {rel.folhas} folha(s).", "ok")
        if rel.ajustes:
            mb.showinfo("Ajustes aplicados", "\n".join(rel.ajustes))
        if prefs.abrir_apos_gerar:
            self._imprimir_lote()

    # ------------------------------------------------------------ impressão
    def _atualizar_painel_lote(self) -> None:
        lote = self.ultimo_lote
        if not lote:
            self.lb_lote.configure(text="Depois de gerar, imprima e confirme aqui a impressão.",
                                   image=icone("info", 16, TEXTO_3), text_color=TEXTO_3)
            for b in (self.bt_imprimir, self.bt_confirmar, self.bt_pasta):
                b.configure(state="disabled")
            return
        estados = {
            "gerado": ("PDF gerado — aguardando impressão", "pdf", AZUL),
            "solicitado": ("Impressão solicitada — confirme quando as etiquetas saírem", "relogio", AMARELO),
            "confirmado": ("Impressão confirmada", "confirmado", VERDE),
        }
        txt, ic, cor = estados[lote["estado"]]
        self.lb_lote.configure(
            text=f"  {txt}\n  {lote['notas']} nota(s) • {lote['etiquetas']} etiqueta(s) • {Path(lote['pdf']).name}",
            image=icone(ic, 18, cor), text_color=cor)
        self.bt_imprimir.configure(state="normal")
        self.bt_pasta.configure(state="normal")
        self.bt_confirmar.configure(state="disabled" if lote["estado"] == "confirmado" else "normal")

    def _imprimir_lote(self) -> None:
        lote = self.ultimo_lote
        if not lote:
            return
        try:
            como = impressao.solicitar_impressao(lote["pdf"], self.app.prefs.modo_impressao)
        except Exception as e:  # noqa: BLE001
            mb.showerror("Impressão", f"Não foi possível abrir/enviar o PDF:\n{e}")
            return
        self.app.historico.registrar_solicitacao(lote["ids"], lote["pdf"], detalhe=como)
        if lote["estado"] != "confirmado":
            lote["estado"] = "solicitado"
        self.app.dados_alterados()
        self._atualizar()
        if self.app.prefs.confirmar_impressao:
            self.after(700, self._perguntar_confirmacao)

    def _perguntar_confirmacao(self) -> None:
        lote = self.ultimo_lote
        if lote and lote["estado"] == "solicitado":
            if perguntar_confirmacao_impressao(self, lote["notas"], lote["etiquetas"]):
                self._confirmar_lote(perguntar=False)

    def _confirmar_lote(self, perguntar: bool = True) -> None:
        lote = self.ultimo_lote
        if not lote or lote["estado"] == "confirmado":
            return
        if perguntar and not perguntar_confirmacao_impressao(self, lote["notas"], lote["etiquetas"]):
            return
        self.app.historico.confirmar_impressao(lote["ids"])
        lote["estado"] = "confirmado"
        self.app.dados_alterados()
        self._atualizar()
        self.app.notificacao.mostrar("Impressão confirmada e registrada no histórico.", "ok")

    def _abrir_pasta_lote(self) -> None:
        if self.ultimo_lote:
            pasta = Path(self.ultimo_lote["pdf"]).parent
            if pasta.is_dir():
                os.startfile(pasta)  # type: ignore[attr-defined]


