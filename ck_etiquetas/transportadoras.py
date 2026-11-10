"""Cadastro de abreviações de transportadoras.

Nomes desconhecidos NUNCA são abreviados automaticamente: a nota fica
pendente até o usuário confirmar o texto a ser impresso.
A busca é feita por CNPJ (mais confiável) e depois por nome normalizado.
"""

from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path

from . import config


def normalizar_nome(nome: str) -> str:
    sem_acento = unicodedata.normalize("NFKD", nome).encode("ascii", "ignore").decode()
    return re.sub(r"\s+", " ", sem_acento.upper()).strip()


def normalizar_cnpj(cnpj: str) -> str:
    return re.sub(r"\D", "", cnpj or "")


class CadastroTransportadoras:
    def __init__(self, arquivo_usuario: Path | None = None, arquivo_padrao: Path | None = None):
        self.arquivo_usuario = arquivo_usuario or config.TRANSPORTADORAS_USUARIO
        self.arquivo_padrao = arquivo_padrao or config.TRANSPORTADORAS_PADRAO
        self.registros: list[dict] = []
        self.carregar()

    def carregar(self) -> None:
        self.registros = []
        for arq in (self.arquivo_padrao, self.arquivo_usuario):
            if arq and Path(arq).is_file():
                with open(arq, encoding="utf-8") as f:
                    for r in json.load(f).get("transportadoras", []):
                        self._mesclar(r)

    def _mesclar(self, novo: dict) -> None:
        novo = {
            "nome": novo.get("nome", ""),
            "cnpj": normalizar_cnpj(novo.get("cnpj", "")),
            "abreviacao": novo.get("abreviacao", "").strip(),
        }
        for r in self.registros:
            if (novo["cnpj"] and r["cnpj"] == novo["cnpj"]) or (
                normalizar_nome(r["nome"]) == normalizar_nome(novo["nome"])
            ):
                r.update({k: v for k, v in novo.items() if v})
                return
        self.registros.append(novo)

    def buscar_detalhado(self, nome: str, cnpj: str = "") -> tuple[str | None, str]:
        """Retorna (abreviação, motivo). motivo: 'nome', 'cnpj' ou ''.

        Só a coincidência de NOME é considerada confirmada. Coincidência
        apenas de CNPJ (nome diferente do cadastrado) vira sugestão que o
        usuário precisa confirmar.
        """
        n = normalizar_nome(nome)
        if n:
            for r in self.registros:
                if normalizar_nome(r["nome"]) == n and r["abreviacao"]:
                    return r["abreviacao"], "nome"
        c = normalizar_cnpj(cnpj)
        if c:
            for r in self.registros:
                if r["cnpj"] == c and r["abreviacao"]:
                    return r["abreviacao"], "cnpj"
        return None, ""

    def buscar(self, nome: str, cnpj: str = "") -> str | None:
        """Abreviação confirmada (por nome) ou None."""
        abrev, motivo = self.buscar_detalhado(nome, cnpj)
        return abrev if motivo == "nome" else None

    def _ler_usuario(self) -> dict:
        if self.arquivo_usuario.is_file():
            with open(self.arquivo_usuario, encoding="utf-8") as f:
                return json.load(f)
        return {"transportadoras": []}

    def _gravar_usuario(self, dados: dict) -> None:
        self.arquivo_usuario.parent.mkdir(parents=True, exist_ok=True)
        with open(self.arquivo_usuario, "w", encoding="utf-8") as f:
            json.dump(dados, f, ensure_ascii=False, indent=2)
        self.carregar()

    def listar(self) -> list[dict]:
        """Todas as abreviações (padrão + usuário), com a origem de cada uma."""
        do_usuario = {normalizar_nome(r.get("nome", "")) for r in self._ler_usuario().get("transportadoras", [])}
        return [dict(r, origem="usuário" if normalizar_nome(r["nome"]) in do_usuario else "padrão")
                for r in self.registros]

    def remover(self, nome: str) -> bool:
        """Remove do cadastro do usuário. Abreviações padrão do programa não podem ser removidas."""
        dados = self._ler_usuario()
        lista = dados.get("transportadoras", [])
        restantes = [r for r in lista if normalizar_nome(r.get("nome", "")) != normalizar_nome(nome)]
        if len(restantes) == len(lista):
            return False
        dados["transportadoras"] = restantes
        self._gravar_usuario(dados)
        return True

    def salvar(self, nome: str, cnpj: str, abreviacao: str) -> None:
        """Grava/atualiza a abreviação no arquivo do usuário."""
        dados = {"transportadoras": []}
        if self.arquivo_usuario.is_file():
            with open(self.arquivo_usuario, encoding="utf-8") as f:
                dados = json.load(f)
        lista = dados.setdefault("transportadoras", [])
        c = normalizar_cnpj(cnpj)
        for r in lista:
            if (c and normalizar_cnpj(r.get("cnpj", "")) == c) or normalizar_nome(
                r.get("nome", "")
            ) == normalizar_nome(nome):
                r.update({"nome": nome, "cnpj": cnpj, "abreviacao": abreviacao})
                break
        else:
            lista.append({"nome": nome, "cnpj": cnpj, "abreviacao": abreviacao})
        self.arquivo_usuario.parent.mkdir(parents=True, exist_ok=True)
        with open(self.arquivo_usuario, "w", encoding="utf-8") as f:
            json.dump(dados, f, ensure_ascii=False, indent=2)
        self.carregar()
