"""Geração do PDF de etiquetas (A4 retrato, 2 etiquetas por folha).

Cada texto é posicionado pela LINHA DE BASE extraída do modelo e
centralizado no eixo vertical da folha, com as mesmas fontes e tamanhos.
A etiqueta inferior é a superior deslocada exatamente meia folha
(148,5 mm), de modo que não há deslocamento progressivo entre etiquetas
nem entre páginas.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import pymupdf

from . import config
from .config import LAYOUT, ElementoTexto
from .modelos import Etiqueta
from .volumes import paginar

_cache_fontes: dict[str, pymupdf.Font] = {}


def fonte(nome: str) -> pymupdf.Font:
    if nome not in _cache_fontes:
        _cache_fontes[nome] = pymupdf.Font(fontfile=str(config.localizar_fonte(nome)))
    return _cache_fontes[nome]


@dataclass
class Relatorio:
    folhas: int = 0
    etiquetas: int = 0
    ajustes: list[str] = field(default_factory=list)


def _texto_centralizado(
    tw: pymupdf.TextWriter, texto: str, el: ElementoTexto, dy: float, rel: Relatorio, desc: str
) -> None:
    f = fonte(el.fonte)
    tamanho = el.tamanho
    largura = f.text_length(texto, fontsize=tamanho)
    if largura > LAYOUT.largura_maxima:
        # só reduz quando o texto não caberia na folha
        tamanho = tamanho * LAYOUT.largura_maxima / largura
        largura = f.text_length(texto, fontsize=tamanho)
        rel.ajustes.append(
            f"{desc} '{texto}': fonte reduzida de {el.tamanho:g} para {tamanho:.1f} pt para caber na largura."
        )
    tw.append((config.CENTRO_X - largura / 2.0, el.baseline + dy), texto, font=f, fontsize=tamanho)


def _desenhar_etiqueta(
    pagina: pymupdf.Page, et: Etiqueta, slot: int, logo_xref: int, rel: Relatorio
) -> int:
    dy = slot * config.METADE_ALTURA
    x0, y0, x1, y1 = LAYOUT.logo
    rect_logo = pymupdf.Rect(x0, y0 + dy, x1, y1 + dy)
    if logo_xref:
        pagina.insert_image(rect_logo, xref=logo_xref, keep_proportion=False)
    else:
        logo_xref = pagina.insert_image(rect_logo, filename=str(config.LOGO_PATH), keep_proportion=False)

    tw = pymupdf.TextWriter(pagina.rect)
    _texto_centralizado(tw, "NF", LAYOUT.nf, dy, rel, "NF")
    _texto_centralizado(tw, et.numero, LAYOUT.numero, dy, rel, "Número")
    _texto_centralizado(tw, et.linha_transporte, LAYOUT.transporte, dy, rel, "Transportadora")
    if et.placa:
        _texto_centralizado(tw, et.placa, LAYOUT.placa, dy, rel, "Placa")
    tw.write_text(pagina, color=(0, 0, 0))
    return logo_xref


def montar_documento(etiquetas: list[Etiqueta]) -> tuple[pymupdf.Document, Relatorio]:
    if not config.LOGO_PATH.is_file():
        raise FileNotFoundError(f"Logotipo não encontrado: {config.LOGO_PATH}")
    doc = pymupdf.open()
    rel = Relatorio()
    logo_xref = 0
    for folha in paginar(etiquetas):
        pagina = doc.new_page(width=config.A4_LARGURA, height=config.A4_ALTURA)
        for slot, et in enumerate(folha):
            logo_xref = _desenhar_etiqueta(pagina, et, slot, logo_xref, rel)
            rel.etiquetas += 1
        rel.folhas += 1
    doc.set_metadata(
        {
            "title": "Etiquetas de expedição — CK Autoshop",
            "author": "CK Autoshop",
            "creator": "CK Etiquetas",
            "producer": "CK Etiquetas / PyMuPDF",
        }
    )
    # Remove avisos repetidos mantendo a ordem
    rel.ajustes = list(dict.fromkeys(rel.ajustes))
    return doc, rel


def gerar_pdf(etiquetas: list[Etiqueta], destino: str | Path) -> Relatorio:
    if not etiquetas:
        raise ValueError("Nenhuma etiqueta para gerar.")
    doc, rel = montar_documento(etiquetas)
    try:
        doc.subset_fonts()  # embute só os glifos usados (arquivo menor)
    except Exception:
        pass  # sem subconjunto: arquivo maior, mas idêntico visualmente
    destino = Path(destino)
    destino.parent.mkdir(parents=True, exist_ok=True)
    doc.save(destino, garbage=4, deflate=True)
    doc.close()
    return rel
