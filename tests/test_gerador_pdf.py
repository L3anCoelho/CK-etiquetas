"""Testes de layout: dimensões, posições, fontes e alinhamento das duas metades."""

import pymupdf
import pytest
from conftest import MODELO, NOTAS_EXEMPLO

from ck_etiquetas import config
from ck_etiquetas.extrator import ler_notas, preparar_notas
from ck_etiquetas.gerador_pdf import gerar_pdf
from ck_etiquetas.modelos import Etiqueta, NotaFiscal
from ck_etiquetas.volumes import expandir_etiquetas

TOL = 0.3  # pt (~0,1 mm)


def textos(pagina):
    out = []
    for b in pagina.get_text("dict")["blocks"]:
        for l in b.get("lines", []):
            for s in l["spans"]:
                t = s["text"].replace("‑", "-").strip()
                if t:
                    out.append({"t": t, "font": s["font"], "size": s["size"], "x": s["origin"][0],
                                "y": s["origin"][1], "bbox": pymupdf.Rect(s["bbox"])})
    return out


def referencia_superior():
    """Spans da etiqueta superior do modelo (canônica)."""
    p = pymupdf.open(MODELO)[0]
    return [s for s in textos(p) if s["y"] < 421]


def ets_7951(n):
    return [Etiqueta("7951", "LUZ-TR", i, n, "TXH3E46") for i in range(1, n + 1)]


def test_dimensoes_a4(tmp_path):
    gerar_pdf(ets_7951(2), tmp_path / "a.pdf")
    p = pymupdf.open(tmp_path / "a.pdf")[0]
    assert p.rect.width / config.MM == pytest.approx(210.0, abs=0.01)
    assert p.rect.height / config.MM == pytest.approx(297.0, abs=0.01)


def test_etiqueta_superior_igual_ao_modelo(tmp_path):
    gerar_pdf(ets_7951(2), tmp_path / "a.pdf")
    gerada = [s for s in textos(pymupdf.open(tmp_path / "a.pdf")[0]) if s["y"] < config.METADE_ALTURA]
    ref = {s["t"].strip(): s for s in referencia_superior()}
    for s in gerada:
        r = ref[s["t"]]
        assert s["size"] == pytest.approx(r["size"], abs=0.01), s["t"]
        assert s["y"] == pytest.approx(r["y"], abs=TOL), s["t"]
        assert s["x"] == pytest.approx(r["x"], abs=TOL), s["t"]
        # mesma família tipográfica (o modelo usa subconjunto 'ABCDEF+Nome')
        fam_ref = r["font"].split("+")[-1].replace("-", "").replace(" ", "").lower()
        fam_ger = s["font"].replace(" ", "").replace("Regular", "").lower()
        assert fam_ger.startswith(fam_ref[:7]), (s["font"], r["font"])


def test_logo_na_posicao_do_modelo(tmp_path):
    gerar_pdf(ets_7951(2), tmp_path / "a.pdf")
    doc = pymupdf.open(tmp_path / "a.pdf")
    p = doc[0]
    xrefs = {img[0] for img in p.get_images()}
    assert len(xrefs) == 1  # um único logotipo embutido, reutilizado
    rects = sorted(p.get_image_rects(xrefs.pop()), key=lambda r: r.y0)
    assert len(rects) == 2
    ref = pymupdf.Rect(config.LAYOUT.logo)
    for i, r in enumerate(rects):
        esperado = ref + (0, i * config.METADE_ALTURA, 0, i * config.METADE_ALTURA)
        for a, b in zip(r, esperado):
            assert a == pytest.approx(b, abs=0.05)


def test_metades_identicas_e_sem_deslocamento_entre_paginas(tmp_path):
    """Teste 10: a etiqueta inferior é a superior + exatamente 148,5 mm,
    e a página 3 tem as mesmas posições da página 1."""
    gerar_pdf(ets_7951(6), tmp_path / "a.pdf")
    doc = pymupdf.open(tmp_path / "a.pdf")
    assert doc.page_count == 3
    base = None
    for pagina in doc:
        ts = textos(pagina)
        sup = [s for s in ts if s["y"] < config.METADE_ALTURA]
        inf = [s for s in ts if s["y"] >= config.METADE_ALTURA]
        assert len(sup) == len(inf) == 4
        for a, b in zip(sup, inf):
            assert b["y"] - a["y"] == pytest.approx(config.METADE_ALTURA, abs=0.01)
            assert b["size"] == a["size"]
            if a["t"] != b["t"]:  # só a numeração do volume pode variar
                assert a["t"].startswith("LUZ-TR(")
            else:
                assert b["x"] == pytest.approx(a["x"], abs=0.01)
        pos = [(round(s["x"], 2), round(s["y"], 2)) for s in sup]
        base = base or pos
        assert pos == base
        # nada ultrapassa a folha nem cruza a linha de corte
        for s in sup:
            assert s["bbox"].y1 < config.METADE_ALTURA
        for s in ts:
            assert 0 < s["bbox"].x0 and s["bbox"].x1 < config.A4_LARGURA and s["bbox"].y1 < config.A4_ALTURA


def test_um_volume_metade_inferior_vazia(tmp_path):
    """Teste 1."""
    gerar_pdf(ets_7951(1), tmp_path / "a.pdf")
    p = pymupdf.open(tmp_path / "a.pdf")[0]
    assert all(s["y"] < config.METADE_ALTURA for s in textos(p))
    assert len(p.get_image_rects(p.get_images()[0][0])) == 1


def test_tres_volumes_duas_folhas(tmp_path):
    """Teste 3."""
    gerar_pdf(ets_7951(3), tmp_path / "a.pdf")
    doc = pymupdf.open(tmp_path / "a.pdf")
    assert doc.page_count == 2
    t2 = textos(doc[1])
    assert [s["t"] for s in t2] == ["NF", "7951", "LUZ-TR(03/03V)", "TXH3E46"]


def test_nome_longo_reduz_fonte_e_cabe(tmp_path):
    """Teste 9 (geração): texto muito longo é reduzido só o necessário."""
    nome = "TRANSPORTADORA EXPRESSO SAO MIGUEL PAULISTA LTDA"
    rel = gerar_pdf([Etiqueta("7928", nome, 1, 1, "TDM2E09")], tmp_path / "a.pdf")
    assert rel.ajustes
    p = pymupdf.open(tmp_path / "a.pdf")[0]
    linha = next(s for s in textos(p) if s["t"].startswith("TRANSPORTADORA"))
    assert linha["bbox"].x0 >= 10 * config.MM - 1
    assert linha["bbox"].x1 <= config.A4_LARGURA - 10 * config.MM + 1
    assert linha["size"] < 28


def test_ponta_a_ponta_pdf_real(tmp_path, cadastro, pasta_saida):
    """Teste 4/5: 7 NFs reais -> 7 etiquetas -> 4 folhas."""
    res = ler_notas(NOTAS_EXEMPLO)
    preparar_notas(res.notas, cadastro)
    destino = pasta_saida / "teste_notas_exemplo.pdf"
    rel = gerar_pdf(expandir_etiquetas(res.notas), destino)
    assert (rel.folhas, rel.etiquetas) == (4, 7)
    doc = pymupdf.open(destino)
    primeiras = [s["t"] for s in textos(doc[0])]
    assert primeiras == ["NF", "7928", "RODONAVES(01/01V)", "TDM2E09",
                         "NF", "7929", "RODONAVES(01/01V)", "TDK1D43"]


@pytest.mark.parametrize("nome,notas", [
    ("teste_01_um_volume", [(7928, 1)]),
    ("teste_02_dois_volumes", [(7951, 2)]),
    ("teste_03_tres_volumes", [(7951, 3)]),
    ("teste_04_duas_nfs", [(7928, 1), (7929, 1)]),
    ("teste_D_mix", [(7928, 1), (7929, 2), (7930, 1)]),
])
def test_gera_pdfs_de_exemplo(pasta_saida, nome, notas):
    nfs = [NotaFiscal(numero=str(n), volumes=v, transportadora="LUZ-TR", placa="TXH3E46",
                      transportadora_confirmada=True) for n, v in notas]
    ets = expandir_etiquetas(nfs)
    rel = gerar_pdf(ets, pasta_saida / f"{nome}.pdf")
    assert rel.etiquetas == sum(v for _, v in notas)
    assert rel.folhas == (rel.etiquetas + 1) // 2
