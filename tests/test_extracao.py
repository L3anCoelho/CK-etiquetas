import hashlib

import pymupdf
import pytest
from conftest import NOTAS_EXEMPLO, criar_variante

from ck_etiquetas.extrator import ler_notas, preparar_notas
from ck_etiquetas.validacao import ERRO, status, validar

ESPERADO = [  # (página, nº original, transportadora, cnpj, volumes, placa)
    (1, "007928", "RODONAVES - TRANSP.ENC.LTDA.", "44.914.992/0013-71", 1, "TDM2E09"),
    (3, "007929", "RODONAVES - TRANSP.ENC.LTDA.", "44.914.992/0013-71", 1, "TDK1D43"),
    (5, "007930", "RODONAVES - TRANSP.ENC.LTDA.", "44.914.992/0013-71", 1, "TDG7F38"),
    (7, "007931", "RODONAVES - TRANSP.ENC.LTDA.", "44.914.992/0013-71", 1, "TDM2D82"),
    (9, "007932", "RODONAVES - TRANSP.ENC.LTDA.", "44.914.992/0013-71", 1, "TKF2B70"),
    (11, "007933", "CARVALIMA TRANSPORTES LT", "33.070.814/0003-13", 1, "TDG7F14"),
    (13, "007927", "RODONAVES - TRANSP.ENC.LTDA.", "44.914.992/0013-71", 1, "TDK3B96"),
]


def test_multiplas_nfs_no_mesmo_pdf(cadastro):
    """Teste 5: todas as NFs do PDF real, na ordem original."""
    res = ler_notas(NOTAS_EXEMPLO)
    preparar_notas(res.notas, cadastro)
    obtido = [(n.pagina, n.numero_original, n.transportadora_nome, n.transportadora_cnpj, n.volumes, n.placa)
              for n in res.notas]
    assert obtido == ESPERADO
    assert [n.numero for n in res.notas] == ["7928", "7929", "7930", "7931", "7932", "7933", "7927"]
    assert [n.transportadora for n in res.notas] == ["RODONAVES"] * 5 + ["CARVALIMA", "RODONAVES"]
    assert all(status(validar(n)) == "OK" for n in res.notas)


def test_paginas_em_branco_intercaladas():
    """Teste 6: as 7 páginas vazias (só cabeçalho do navegador) são ignoradas."""
    res = ler_notas(NOTAS_EXEMPLO)
    assert res.paginas_total == 14
    assert res.paginas_vazias == [2, 4, 6, 8, 10, 12, 14]
    assert res.avisos == []


def test_numero_confere_com_chave_de_acesso():
    for n in ler_notas(NOTAS_EXEMPLO).notas:
        assert len(n.chave) == 44
        assert int(n.chave[25:34]) == int(n.numero_original)
        assert n.serie == "1"


def test_pdf_de_origem_nao_e_alterado():
    antes = hashlib.sha256(NOTAS_EXEMPLO.read_bytes()).hexdigest()
    ler_notas(NOTAS_EXEMPLO)
    assert hashlib.sha256(NOTAS_EXEMPLO.read_bytes()).hexdigest() == antes


def test_nf_sem_placa(tmp_path, cadastro):
    """Teste 7: sem placa nas observações -> pendente, nada inventado."""
    pdf = criar_variante(tmp_path / "sem_placa.pdf", 0, placa="")
    res = ler_notas(pdf)
    preparar_notas(res.notas, cadastro)
    nf = res.notas[0]
    assert nf.placa == ""
    probs = validar(nf)
    assert status(probs) == "PENDENTE"
    assert any(p.campo == "Placa" and p.nivel == ERRO for p in probs)
    # exceção explícita do usuário libera a geração (com aviso)
    nf.excecao_sem_placa = True
    assert status(validar(nf)) == "CONFERIR"


def test_nf_sem_quantidade_de_volumes(tmp_path, cadastro):
    """Teste 8."""
    pdf = criar_variante(tmp_path / "sem_volume.pdf", 0, volumes="")
    res = ler_notas(pdf)
    preparar_notas(res.notas, cadastro)
    nf = res.notas[0]
    assert nf.volumes is None
    assert any(p.campo == "Volumes" and p.nivel == ERRO for p in validar(nf))


def test_transportadora_nome_longo_desconhecida(tmp_path, cadastro):
    """Teste 9: nome longo é lido inteiro e NÃO é abreviado sem confirmação."""
    nome = "TRANSPORTADORA EXPRESSO SAO MIGUEL PAULISTA LTDA"
    pdf = criar_variante(tmp_path / "nome_longo.pdf", 0, transportadora=nome, cnpj="11.222.333/0001-81")
    res = ler_notas(pdf)
    preparar_notas(res.notas, cadastro)
    nf = res.notas[0]
    assert nf.transportadora_nome == nome
    assert nf.transportadora == nome
    assert not nf.transportadora_confirmada
    assert any(p.campo == "Transportadora" and p.nivel == ERRO for p in validar(nf))
    # após cadastrar a abreviação, as próximas leituras já saem confirmadas
    cadastro.salvar(nome, "", "EXPRESSO SM")
    res2 = ler_notas(pdf)
    preparar_notas(res2.notas, cadastro)
    assert res2.notas[0].transportadora == "EXPRESSO SM"
    assert res2.notas[0].transportadora_confirmada


def test_cnpj_conhecido_com_nome_diferente_exige_confirmacao(tmp_path, cadastro):
    pdf = criar_variante(tmp_path / "cnpj.pdf", 0, transportadora="RODONAVES TRANSPORTES E ENCOMENDAS")
    res = ler_notas(pdf)
    preparar_notas(res.notas, cadastro)
    nf = res.notas[0]
    assert nf.transportadora == "RODONAVES"  # sugestão
    assert not nf.transportadora_confirmada  # mas não confirmada
    assert status(validar(nf)) == "PENDENTE"


@pytest.mark.parametrize("vol", [2, 3, 10])
def test_volumes_lidos_da_secao_transportador(tmp_path, cadastro, vol):
    pdf = criar_variante(tmp_path / f"vol{vol}.pdf", 4, volumes=vol)  # NF 7930 tem 3 itens
    res = ler_notas(pdf)
    assert res.notas[0].volumes == vol  # não confunde com a quantidade de itens (3 x 1,00)


def test_pagina_repetida_nao_duplica(tmp_path):
    pdf = criar_variante(tmp_path / "dup.pdf", 0, duplicar=True)
    res = ler_notas(pdf)
    assert len(res.notas) == 1
    assert any("repetida" in a for a in res.avisos)


def test_placa_do_transportador_nao_e_usada(tmp_path):
    """Preenche 'Placa do veículo' do transportador e confirma que a placa
    extraída continua sendo a das observações."""
    src = pymupdf.open(NOTAS_EXEMPLO)
    doc = pymupdf.open()
    doc.insert_pdf(src, from_page=0, to_page=0)
    p = doc[0]
    r = p.search_for("Placa do ve")[0]
    p.insert_text((r.x0 + 0.5, r.y1 + 7.5), "ABC1234", fontname="helv", fontsize=7)
    destino = tmp_path / "placa_caminhao.pdf"
    doc.save(destino)
    nf = ler_notas(destino).notas[0]
    assert nf.placa_original == "TDM2E09"


def test_pdf_sem_danfe(tmp_path):
    doc = pymupdf.open()
    doc.new_page().insert_text((72, 72), "Documento qualquer")
    doc.new_page()
    destino = tmp_path / "outro.pdf"
    doc.save(destino)
    res = ler_notas(destino)
    assert res.notas == []
    assert res.paginas_vazias == [2]
    assert any("não reconhecida" in a for a in res.avisos)
