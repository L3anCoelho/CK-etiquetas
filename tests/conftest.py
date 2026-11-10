"""Fixtures: PDFs de teste derivados da DANFE real do Bling.

Os casos especiais (sem placa, sem volumes, nome longo, 2/3 volumes,
página duplicada) são criados a partir de páginas reais, apagando o valor
original por redação e escrevendo o novo valor na mesma posição — assim o
layout continua sendo exatamente o do Bling.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import pymupdf
import pytest

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

# os testes nunca usam a pasta de dados real (%LOCALAPPDATA%\CKEtiquetas)
import os
import tempfile

os.environ["CK_ETIQUETAS_DADOS"] = tempfile.mkdtemp(prefix="ck_etiquetas_testes_")

NOTAS_EXEMPLO = RAIZ / "referencias" / "notas_exemplo.pdf"
MODELO = RAIZ / "referencias" / "etiquetas_modelo.pdf"


def _substituir(pagina: pymupdf.Page, rect: pymupdf.Rect, novo: str | None) -> None:
    pagina.add_redact_annot(rect)
    pagina.apply_redactions(images=pymupdf.PDF_REDACT_IMAGE_NONE)
    if novo:
        pagina.insert_text((rect.x0 + 0.5, rect.y1 - 2.1), novo, fontname="helv", fontsize=7)


def _rect_valor_abaixo_de(pagina: pymupdf.Page, rotulo: str, y_min: float = 0) -> pymupdf.Rect:
    r = next(r for r in pagina.search_for(rotulo) if r.y0 > y_min)
    linhas = [
        pymupdf.Rect(l["bbox"])
        for b in pagina.get_text("dict")["blocks"]
        for l in b.get("lines", [])
        if abs(l["bbox"][0] - r.x0) < 4 and r.y1 - 1 < l["bbox"][1] < r.y1 + 9
    ]
    return linhas[0]


def _trocar_numero(p: pymupdf.Page, numero: int) -> None:
    """Troca o Nº da NF (cabeçalho e canhoto) e o número dentro da chave de acesso."""
    alvos = []
    for b in p.get_text("dict")["blocks"]:
        for l in b.get("lines", []):
            t = " ".join(s["text"] for s in l["spans"]).strip()
            digitos = t.replace(" ", "")
            if re.fullmatch(r"N\S{0,2} \d{6,9}", t):
                alvos.append((pymupdf.Rect(l["bbox"]), f"Nº {numero:06d}", "hebo", 9.75, 2.9))
            elif re.fullmatch(r"\d{44}", digitos):
                nova = digitos[:25] + f"{numero:09d}" + digitos[34:]
                alvos.append((pymupdf.Rect(l["bbox"]), " ".join(nova[i:i + 4] for i in range(0, 44, 4)),
                              "helv", 7, 2.1))
    for rect, _t, _f, _s, _d in alvos:
        p.add_redact_annot(rect)
    p.apply_redactions(images=pymupdf.PDF_REDACT_IMAGE_NONE)
    for rect, texto, fonte, tam, desc in alvos:
        p.insert_text((rect.x0, rect.y1 - desc), texto, fontname=fonte, fontsize=tam)


def criar_variante(destino: Path, pagina_origem: int, *, volumes=None, placa="manter", transportadora=None,
                   cnpj=None, duplicar=False, numero: int | None = None) -> Path:
    src = pymupdf.open(NOTAS_EXEMPLO)
    doc = pymupdf.open()
    doc.insert_pdf(src, from_page=pagina_origem, to_page=pagina_origem)
    p = doc[0]
    y_transp = p.search_for("Transportador/Volumes")[0].y0
    if volumes is not None:
        _substituir(p, _rect_valor_abaixo_de(p, "Quantidade", y_transp), str(volumes) if volumes != "" else None)
    if transportadora is not None:
        r_nome = _rect_valor_abaixo_de(p, "Nome", y_transp)
        r_nome.x1 = 186  # até o início da coluna "Frete por conta"
        _substituir(p, r_nome, transportadora)
    if cnpj is not None:
        _substituir(p, _rect_valor_abaixo_de(p, "CNPJ/CPF", y_transp), cnpj)
    if numero is not None:
        _trocar_numero(p, numero)
    if placa != "manter":
        r = p.search_for("Placa T")[0]
        r.x1 = r.x0 + 60
        _substituir(p, r, f"Placa {placa}" if placa else None)
    doc.save(destino)
    if duplicar:
        unico = pymupdf.open(destino)
        dup = pymupdf.open()
        dup.insert_pdf(unico)
        dup.insert_pdf(unico)
        unico.close()
        dup.save(destino.with_name("tmp_" + destino.name))
        dup.close()
        destino.unlink()
        destino.with_name("tmp_" + destino.name).rename(destino)
    return destino


@pytest.fixture(scope="session")
def pasta_saida() -> Path:
    p = RAIZ / "saida_testes"
    p.mkdir(exist_ok=True)
    return p


@pytest.fixture
def cadastro(tmp_path):
    from ck_etiquetas.transportadoras import CadastroTransportadoras

    return CadastroTransportadoras(arquivo_usuario=tmp_path / "transportadoras.json")
