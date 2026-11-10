"""Regras de volumes (uma etiqueta por volume) e paginação (2 por folha)."""

from __future__ import annotations

from .config import ETIQUETAS_POR_FOLHA
from .modelos import Etiqueta, NotaFiscal


def expandir_etiquetas(notas: list[NotaFiscal]) -> list[Etiqueta]:
    """Uma etiqueta por volume físico, preservando a ordem das notas."""
    etiquetas: list[Etiqueta] = []
    for nf in notas:
        total = nf.volumes or 0
        for i in range(1, total + 1):
            etiquetas.append(
                Etiqueta(
                    numero=nf.numero,
                    transportadora=nf.transportadora.strip(),
                    volume_atual=i,
                    volume_total=total,
                    placa=nf.placa.strip().upper(),
                )
            )
    return etiquetas


def paginar(etiquetas: list[Etiqueta]) -> list[list[Etiqueta]]:
    """Agrupa em folhas de 2. A última folha pode ter a metade inferior vazia
    (nenhuma etiqueta é duplicada para completar a folha)."""
    n = ETIQUETAS_POR_FOLHA
    return [etiquetas[i : i + n] for i in range(0, len(etiquetas), n)]


def total_etiquetas(notas: list[NotaFiscal]) -> int:
    return sum(nf.volumes or 0 for nf in notas)
