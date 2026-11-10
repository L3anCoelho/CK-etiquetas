import pytest

from ck_etiquetas.modelos import Etiqueta, NotaFiscal
from ck_etiquetas.validacao import placa_valida
from ck_etiquetas.volumes import expandir_etiquetas, paginar


def nota(numero, volumes, transp="RODONAVES", placa="TDM2E09"):
    return NotaFiscal(numero=numero, volumes=volumes, transportadora=transp, placa=placa,
                      transportadora_confirmada=True)


@pytest.mark.parametrize("placa,ok", [
    ("TDM2E09", True), ("ABC1234", True), ("TXH3E46", True),
    ("TDM2E0", False), ("1DM2E09", False), ("TDME209", False), ("TDM2EE9", False),
    ("COTACAO", False), ("", False), ("TDM2E091", False),
])
def test_placa(placa, ok):
    assert placa_valida(placa) is ok


@pytest.mark.parametrize("total,primeiro,ultimo", [
    (1, "(01/01V)", "(01/01V)"),
    (3, "(01/03V)", "(03/03V)"),
    (10, "(01/10V)", "(10/10V)"),
    (120, "(001/120V)", "(120/120V)"),
])
def test_formato_volume(total, primeiro, ultimo):
    ets = expandir_etiquetas([nota("7951", total, "LUZ-TR")])
    assert len(ets) == total
    assert ets[0].linha_transporte == "LUZ-TR" + primeiro
    assert ets[-1].linha_transporte == "LUZ-TR" + ultimo


def test_exemplo_a_duas_nfs_um_volume():
    folhas = paginar(expandir_etiquetas([nota("7928", 1), nota("7929", 1)]))
    assert len(folhas) == 1
    assert [e.numero for e in folhas[0]] == ["7928", "7929"]


def test_exemplo_b_dois_volumes():
    folhas = paginar(expandir_etiquetas([nota("7951", 2)]))
    assert len(folhas) == 1
    assert [e.texto_volume for e in folhas[0]] == ["(01/02V)", "(02/02V)"]
    # idênticas exceto a numeração do volume
    a, b = folhas[0]
    assert (a.numero, a.transportadora, a.placa, a.volume_total) == (b.numero, b.transportadora, b.placa, b.volume_total)


def test_exemplo_c_tres_volumes():
    folhas = paginar(expandir_etiquetas([nota("7951", 3)]))
    assert [len(f) for f in folhas] == [2, 1]  # metade inferior da 2ª folha vazia
    assert folhas[1][0].texto_volume == "(03/03V)"


def test_exemplo_d_ordem_preservada():
    folhas = paginar(expandir_etiquetas([nota("7928", 1), nota("7929", 2), nota("7930", 1)]))
    seq = [(e.numero, e.texto_volume) for f in folhas for e in f]
    assert seq == [("7928", "(01/01V)"), ("7929", "(01/02V)"), ("7929", "(02/02V)"), ("7930", "(01/01V)")]
    assert len(folhas) == 2


def test_nao_duplica_para_completar_folha():
    ets = expandir_etiquetas([nota("1", 1)])
    assert paginar(ets) == [[Etiqueta("1", "RODONAVES", 1, 1, "TDM2E09")]]
