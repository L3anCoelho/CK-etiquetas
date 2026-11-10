"""Importação múltipla de PDFs, geração em lote e histórico."""

import pymupdf
import pytest
from conftest import NOTAS_EXEMPLO, criar_variante

from ck_etiquetas.gerador_pdf import gerar_pdf
from ck_etiquetas.lote import importar_arquivos, numeros_repetidos, validar_lista
from ck_etiquetas.validacao import ERRO, status
from ck_etiquetas.volumes import expandir_etiquetas, total_etiquetas

# volumes variados para que a soma não coincida por acaso com o número de notas
VOLUMES = [1, 2, 1, 3, 1, 2, 1, 1, 4, 2]


@pytest.fixture
def arquivos_individuais(tmp_path):
    """10 PDFs com uma DANFE cada (NFs 9001..9010), a partir da DANFE real."""
    return [
        criar_variante(tmp_path / f"nf_{9001 + i}.pdf", (i % 7) * 2, numero=9001 + i, volumes=v)
        for i, v in enumerate(VOLUMES)
    ]


def _textos_por_metade(pdf):
    """[(texto metade superior, texto metade inferior), ...] por página."""
    out = []
    with pymupdf.open(pdf) as doc:
        for p in doc:
            meio = p.rect.height / 2
            cima = p.get_text(clip=pymupdf.Rect(0, 0, p.rect.width, meio))
            baixo = p.get_text(clip=pymupdf.Rect(0, meio, p.rect.width, p.rect.height))
            out.append((" ".join(cima.split()), " ".join(baixo.split())))
    return out


@pytest.mark.parametrize("n", [2, 5, 10])
def test_importacao_simultanea(n, arquivos_individuais, cadastro, tmp_path, pasta_saida):
    res = importar_arquivos(arquivos_individuais[:n], [], cadastro)
    assert res.arquivos_lidos == n and not res.falhas and res.duplicadas == 0
    assert [nf.numero for nf in res.novas] == [str(9001 + i) for i in range(n)]  # ordem da seleção
    assert all(status(p) == "OK" for p in validar_lista(res.novas))
    assert total_etiquetas(res.novas) == sum(VOLUMES[:n])

    rel = gerar_pdf(expandir_etiquetas(res.novas), pasta_saida / f"teste_lote_{n}_arquivos.pdf")
    assert rel.etiquetas == sum(VOLUMES[:n])
    assert rel.folhas == (sum(VOLUMES[:n]) + 1) // 2


def test_pdf_com_varias_notas(cadastro):
    res = importar_arquivos([NOTAS_EXEMPLO], [], cadastro)
    assert [nf.numero for nf in res.novas] == ["7928", "7929", "7930", "7931", "7932", "7933", "7927"]
    assert total_etiquetas(res.novas) == 7


def test_selecao_mista(arquivos_individuais, cadastro, tmp_path, pasta_saida):
    """PDF com várias notas + PDFs individuais, incluindo uma NF que já está no PDF múltiplo."""
    repetida = criar_variante(tmp_path / "7930_avulsa.pdf", 4)  # mesma NF 7930 do PDF múltiplo
    sel = [arquivos_individuais[0], NOTAS_EXEMPLO, repetida, arquivos_individuais[1]]
    res = importar_arquivos(sel, [], cadastro)
    nums = [nf.numero for nf in res.novas]
    assert nums == ["9001", "7928", "7929", "7930", "7931", "7932", "7933", "7927", "9002"]
    assert res.duplicadas == 1
    assert any("7930_avulsa.pdf" in a and "todas" in a for a in res.avisos)
    assert total_etiquetas(res.novas) == VOLUMES[0] + 7 + VOLUMES[1]
    rel = gerar_pdf(expandir_etiquetas(res.novas), pasta_saida / "teste_lote_misto.pdf")
    assert rel.etiquetas == 10 and rel.folhas == 5


def test_adicionar_depois_nao_apaga_e_nao_duplica(arquivos_individuais, cadastro):
    lista = importar_arquivos(arquivos_individuais[:3], [], cadastro).novas
    # 2ª adição: um arquivo novo e dois que já estão na lista
    res = importar_arquivos([arquivos_individuais[2], arquivos_individuais[3], arquivos_individuais[0]], lista,
                            cadastro)
    assert [nf.numero for nf in res.novas] == ["9004"]
    assert res.duplicadas == 2
    lista += res.novas
    assert [nf.numero for nf in lista] == ["9001", "9002", "9003", "9004"]


def test_mesmo_arquivo_duas_vezes_na_selecao(arquivos_individuais, cadastro):
    res = importar_arquivos([arquivos_individuais[0], arquivos_individuais[0]], [], cadastro)
    assert [nf.numero for nf in res.novas] == ["9001"]


def test_arquivo_invalido_nao_interrompe_o_lote(arquivos_individuais, cadastro, tmp_path):
    ruim = tmp_path / "corrompido.pdf"
    ruim.write_bytes(b"isto nao e um pdf")
    res = importar_arquivos([arquivos_individuais[0], ruim, arquivos_individuais[1]], [], cadastro)
    assert [nf.numero for nf in res.novas] == ["9001", "9002"]
    assert [a for a, _ in res.falhas] == ["corrompido.pdf"]


def test_ordem_e_paginacao_do_exemplo(tmp_path, cadastro, pasta_saida):
    """NF 7928 (1 vol), 7929 (2 vol), 7930 (1 vol) -> 2 folhas, na ordem da tabela."""
    arqs = [criar_variante(tmp_path / "a.pdf", 0), criar_variante(tmp_path / "b.pdf", 2, volumes=2),
            criar_variante(tmp_path / "c.pdf", 4)]
    notas = importar_arquivos(arqs, [], cadastro).novas
    destino = pasta_saida / "teste_lote_exemplo_7928_7930.pdf"
    gerar_pdf(expandir_etiquetas(notas), destino)
    paginas = _textos_por_metade(destino)
    assert len(paginas) == 2
    (c1, b1), (c2, b2) = paginas
    assert "7928" in c1 and "(01/01V)" in c1
    assert "7929" in b1 and "(01/02V)" in b1
    assert "7929" in c2 and "(02/02V)" in c2
    assert "7930" in b2 and "(01/01V)" in b2


def test_total_impar_deixa_metade_inferior_em_branco(arquivos_individuais, cadastro, tmp_path):
    notas = importar_arquivos(arquivos_individuais[:3], [], cadastro).novas  # 1+2+1 = 4 -> par
    notas = notas[:2]  # 1+2 = 3 etiquetas
    destino = tmp_path / "impar.pdf"
    gerar_pdf(expandir_etiquetas(notas), destino)
    cima, baixo = _textos_por_metade(destino)[-1]
    assert "9002" in cima and baixo == ""


def test_numero_repetido_na_lista_bloqueia(arquivos_individuais, cadastro):
    notas = importar_arquivos(arquivos_individuais[:3], [], cadastro).novas
    notas[2].numero = "9001"  # usuário editou para o número de outra nota
    assert numeros_repetidos(notas) == {2: 0}
    probs = validar_lista(notas)
    assert status(probs[2]) == "PENDENTE" and status(probs[0]) == "OK"
    assert any(p.nivel == ERRO and "repetida" in p.mensagem for p in probs[2])
