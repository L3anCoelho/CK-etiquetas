"""Envio das etiquetas para impressão (Windows).

Nenhuma destas funções marca a nota como impressa: elas só registram que a
impressão foi SOLICITADA. A confirmação é sempre feita pelo usuário.
"""

from __future__ import annotations

import os
from pathlib import Path

from .preferencias import IMPRIMIR_DIRETO


def abrir_pdf(caminho: str | Path) -> None:
    caminho = Path(caminho)
    if not caminho.is_file():
        raise FileNotFoundError(f"O PDF não está mais neste local:\n{caminho}")
    os.startfile(caminho)  # type: ignore[attr-defined]


def solicitar_impressao(caminho: str | Path, modo: str) -> str:
    """Abre o PDF no leitor (padrão) ou envia direto à impressora padrão.

    Retorna uma descrição do que foi feito, para o histórico.
    """
    caminho = Path(caminho)
    if not caminho.is_file():
        raise FileNotFoundError(f"O PDF não está mais neste local:\n{caminho}")
    if modo == IMPRIMIR_DIRETO:
        try:
            os.startfile(caminho, "print")  # type: ignore[attr-defined]
            return "enviado à impressora padrão"
        except OSError:
            # leitor de PDF sem o verbo "imprimir": abre para o usuário imprimir
            os.startfile(caminho)  # type: ignore[attr-defined]
            return "aberto no leitor de PDF (impressão direta indisponível)"
    os.startfile(caminho)  # type: ignore[attr-defined]
    return "aberto no leitor de PDF para impressão"
