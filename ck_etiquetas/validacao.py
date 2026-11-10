"""Validação dos campos obrigatórios de cada nota."""

from __future__ import annotations

import re
from dataclasses import dataclass

from .config import MAX_VOLUMES

# Placa antiga: AAA9999  |  Mercosul: AAA9A99
RE_PLACA_ANTIGA = re.compile(r"[A-Z]{3}\d{4}")
RE_PLACA_MERCOSUL = re.compile(r"[A-Z]{3}\d[A-Z]\d{2}")
RE_PLACA = re.compile(r"[A-Z]{3}\d[A-Z0-9]\d{2}")

ERRO = "erro"
AVISO = "aviso"


@dataclass(frozen=True)
class Problema:
    campo: str
    nivel: str
    mensagem: str


def placa_valida(placa: str) -> bool:
    p = (placa or "").strip().upper()
    return bool(RE_PLACA_ANTIGA.fullmatch(p) or RE_PLACA_MERCOSUL.fullmatch(p))


def normalizar_placa(placa: str) -> str:
    return re.sub(r"[\s\-]", "", (placa or "").upper())


def validar(nf) -> list[Problema]:
    probs: list[Problema] = []

    # A. número da NF
    if not nf.numero:
        probs.append(Problema("NF", ERRO, "Número da NF não identificado."))
    elif not re.fullmatch(r"\d{1,9}", nf.numero) or int(nf.numero) == 0:
        probs.append(Problema("NF", ERRO, f"Número da NF inválido: '{nf.numero}'."))

    # B. transportadora
    if not nf.transportadora.strip():
        probs.append(Problema("Transportadora", ERRO, "Transportadora não identificada."))
    elif not nf.transportadora_confirmada:
        probs.append(
            Problema(
                "Transportadora",
                ERRO,
                f"Transportadora não confirmada ('{nf.transportadora_nome}'). "
                "Confirme o texto a imprimir (duplo clique na linha).",
            )
        )

    # C. volumes
    if nf.volumes is None:
        probs.append(Problema("Volumes", ERRO, "Quantidade de volumes não identificada."))
    elif not (1 <= nf.volumes <= MAX_VOLUMES):
        probs.append(Problema("Volumes", ERRO, f"Quantidade de volumes inválida: {nf.volumes}."))

    # D. placa do veículo do cliente
    if not nf.placa:
        if not nf.excecao_sem_placa:
            probs.append(Problema("Placa", ERRO, "Placa não identificada nas observações. Preencha manualmente."))
    elif not placa_valida(nf.placa):
        if nf.excecao_placa_fora_padrao:
            probs.append(Problema("Placa", AVISO, f"Placa fora do padrão aceita pelo usuário: {nf.placa}."))
        else:
            probs.append(
                Problema("Placa", ERRO, f"Placa '{nf.placa}' fora do padrão (AAA9999 ou AAA9A99).")
            )

    for aviso in nf.avisos_extracao:
        probs.append(Problema("Extração", AVISO, aviso))
    if nf.excecao_sem_placa and not nf.placa:
        probs.append(Problema("Placa", AVISO, "Etiqueta sem placa (exceção confirmada pelo usuário)."))
    return probs


def status(probs: list[Problema]) -> str:
    if any(p.nivel == ERRO for p in probs):
        return "PENDENTE"
    if any(p.nivel == AVISO for p in probs):
        return "CONFERIR"
    return "OK"
