"""Operações de negócio usadas pela interface: gerar lote e reimprimir pelo histórico.

O PDF é sempre produzido por gerador_pdf.gerar_pdf (layout oficial, inalterado).
"""

from __future__ import annotations

from datetime import date, datetime
from pathlib import Path

from .gerador_pdf import Relatorio, gerar_pdf
from .historico import Historico, Registro
from .modelos import NotaFiscal
from .preferencias import Preferencias
from .volumes import expandir_etiquetas


def nome_arquivo(notas: list[NotaFiscal], sufixo: str = "", quando: datetime | None = None) -> str:
    quando = quando or datetime.now()
    nums = [nf.numero for nf in notas]
    faixa = nums[0] if len(nums) == 1 else f"{nums[0]}-{nums[-1]}"
    return f"etiquetas_NF{faixa}{sufixo}_{quando:%Y-%m-%d_%H%M%S}.pdf"


def destino_automatico(prefs: Preferencias, notas: list[NotaFiscal], sufixo: str = "") -> Path:
    """Caminho na pasta de PDFs, organizada por mês, sem sobrescrever arquivos existentes."""
    pasta = prefs.pasta_pdfs_do_mes(date.today())
    destino = pasta / nome_arquivo(notas, sufixo)
    n = 2
    while destino.exists():
        destino = pasta / destino.name.replace(".pdf", f"_{n}.pdf")
        n += 1
    return destino


def gerar_lote(notas: list[NotaFiscal], destino: str | Path, historico: Historico,
               detalhe: str = "") -> tuple[Relatorio, list[int]]:
    """Gera UM PDF com as etiquetas de todas as notas (na ordem) e registra cada NF no histórico."""
    rel = gerar_pdf(expandir_etiquetas(notas), destino)
    ids = historico.registrar_geracao(notas, destino, detalhe=detalhe)
    return rel, ids


def reimprimir(registros: list[Registro], prefs: Preferencias, historico: Historico,
               destino: str | Path | None = None) -> tuple[Path, Relatorio, list[int]]:
    """Gera novamente as etiquetas a partir do histórico (não precisa do PDF original da NF).

    Gera um PDF só com as notas escolhidas — o PDF antigo pode conter outras notas do mesmo lote.
    """
    notas = [r.como_nota() for r in registros]
    destino = Path(destino) if destino else destino_automatico(prefs, notas, "_reimpressao")
    rel, ids = gerar_lote(notas, destino, historico, detalhe="reimpressão pelo histórico")
    return destino, rel, ids
