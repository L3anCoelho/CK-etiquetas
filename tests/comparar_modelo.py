"""Comparação visual/numérica entre o PDF gerado e o modelo de referência.

Uso:  python tests/comparar_modelo.py [pasta_saida]

Gera o caso do modelo (NF 7951, LUZ-TR, 2 volumes, placa TXH3E46) e:
  1. compara as coordenadas de cada texto com as do modelo;
  2. renderiza ambos a 150 dpi e mede a diferença de pixels da etiqueta
     superior (canônica);
  3. salva uma sobreposição (modelo em vermelho, gerado em azul).
"""

from __future__ import annotations

import sys
from pathlib import Path

import pymupdf

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from ck_etiquetas.gerador_pdf import gerar_pdf  # noqa: E402
from ck_etiquetas.modelos import Etiqueta  # noqa: E402

MODELO = RAIZ / "referencias" / "etiquetas_modelo.pdf"


def spans(pagina: pymupdf.Page) -> list[tuple[str, str, float, tuple]]:
    out = []
    for b in pagina.get_text("dict")["blocks"]:
        for l in b.get("lines", []):
            for s in l["spans"]:
                t = s["text"].replace("‑", "-").strip()
                if t:
                    out.append((t, s["font"].split("+")[-1], round(s["size"], 2), s["origin"], s["bbox"]))
    return out


def gerar_caso_modelo(destino: Path) -> Path:
    ets = [Etiqueta("7951", "LUZ-TR", i, 2, "TXH3E46") for i in (1, 2)]
    gerar_pdf(ets, destino)
    return destino


def comparar(pasta: Path) -> dict:
    pasta.mkdir(parents=True, exist_ok=True)
    gerado = gerar_caso_modelo(pasta / "caso_modelo_7951.pdf")
    m = pymupdf.open(MODELO)[0]
    g = pymupdf.open(gerado)[0]
    res = {"pagina_modelo_pt": (m.rect.width, m.rect.height), "pagina_gerada_pt": (g.rect.width, g.rect.height)}

    sm, sg = spans(m), spans(g)
    linhas = []
    for t, f, s, o, _ in sg:
        ref = [x for x in sm if x[0] == t and abs(x[3][1] - o[1]) < 30]
        if ref:
            _, fr, sr, orf, _ = ref[0]
            linhas.append((t, f, fr, s, sr, round(o[0] - orf[0], 2), round(o[1] - orf[1], 2)))
        else:
            linhas.append((t, f, None, s, None, None, None))
    res["textos"] = linhas

    # pixel diff da etiqueta superior (metade de cima) a 150 dpi
    dpi = 150
    clip = pymupdf.Rect(0, 0, 595.25, 420.9)
    pm = m.get_pixmap(dpi=dpi, clip=clip, colorspace=pymupdf.csGRAY)
    pg = g.get_pixmap(dpi=dpi, clip=clip, colorspace=pymupdf.csGRAY)
    w, h = min(pm.width, pg.width), min(pm.height, pg.height)
    a, b = pm.samples, pg.samples
    diff = 0
    tinta = 0
    for y in range(h):
        ra, rb = y * pm.stride, y * pg.stride
        for x in range(w):
            va, vb = a[ra + x], b[rb + x]
            if va < 128 or vb < 128:
                tinta += 1
                if (va < 128) != (vb < 128):
                    diff += 1
    res["pixels_tinta"] = tinta
    res["pixels_diferentes"] = diff
    res["percentual_diferente"] = round(100 * diff / max(tinta, 1), 2)

    # sobreposição visual: modelo vermelho, gerado azul, coincidente preto
    from PIL import Image, ImageChops

    full_m = m.get_pixmap(dpi=100, colorspace=pymupdf.csGRAY)
    full_g = g.get_pixmap(dpi=100, colorspace=pymupdf.csGRAY)
    im_m = Image.frombytes("L", (full_m.width, full_m.height), full_m.samples)
    im_g = Image.frombytes("L", (full_g.width, full_g.height), full_g.samples).resize(im_m.size)
    sobre = Image.merge("RGB", (im_g, ImageChops.darker(im_m, im_g), im_m))
    sobre.save(pasta / "sobreposicao_modelo_vs_gerado.png")
    return res


if __name__ == "__main__":
    pasta = Path(sys.argv[1]) if len(sys.argv) > 1 else RAIZ / "saida_testes"
    r = comparar(pasta)
    print("Página modelo (pt):", r["pagina_modelo_pt"], " gerada (pt):", r["pagina_gerada_pt"])
    print(f"{'texto':18} {'fonte gerada':20} {'fonte modelo':20} {'tam':>6} {'tam ref':>7} {'dx':>7} {'dy':>7}")
    for t in r["textos"]:
        print(f"{t[0]:18} {t[1]:20} {str(t[2]):20} {t[3]:>6} {str(t[4]):>7} {str(t[5]):>7} {str(t[6]):>7}")
    print(f"Etiqueta superior: {r['pixels_diferentes']} de {r['pixels_tinta']} px com tinta diferem "
          f"({r['percentual_diferente']}%)")
