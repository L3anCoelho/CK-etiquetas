"""Histórico permanente, controle de impressão, migrações, backup e preferências."""

import json
import sqlite3
import zipfile
from dataclasses import replace
from datetime import date, datetime

import pytest
from conftest import criar_variante

from ck_etiquetas import backup, banco, config
from ck_etiquetas.historico import (IMPRESSAO_CONFIRMADA, IMPRESSAO_SOLICITADA, PDF_GERADO, REIMPRESSAO,
                                    Historico)
from ck_etiquetas.lote import identificador, importar_arquivos
from ck_etiquetas.preferencias import IMPRIMIR_ABRIR, Preferencias
from ck_etiquetas.volumes import expandir_etiquetas

D1 = datetime(2026, 11, 3, 9, 0)
D2 = datetime(2026, 11, 10, 14, 30)


@pytest.fixture
def notas(tmp_path, cadastro):
    arqs = [criar_variante(tmp_path / f"n{i}.pdf", i * 2, numero=9200 + i, volumes=v)
            for i, v in enumerate([1, 2, 3])]
    return importar_arquivos(arqs, [], cadastro).novas


@pytest.fixture
def hist(tmp_path):
    return Historico(tmp_path / "dados" / "ck_etiquetas.db")


def test_campos_salvos(hist, notas):
    hist.registrar_geracao(notas, "C:/pdfs/lote.pdf", quando=D1)
    r = hist.consultar(notas[1])
    assert r.numero == "009201" and r.numero_impresso == "9201"  # número completo e impresso
    assert r.serie == "1" and r.chave == notas[1].chave and r.identificador == notas[1].chave
    assert r.emitente == "CK AUTOSHOP COMERCIO E SOLUÇÕES AUTOMOTIVAS LTDA"
    assert r.emitente_cnpj == "49126933000119"
    assert r.transportadora == "RODONAVES" and r.placa == notas[1].placa
    assert r.volumes == 2 and r.etiquetas == 2
    assert r.status == PDF_GERADO and r.ultima_geracao_em == "2026-11-03T09:00:00"
    assert r.impressao_confirmada_em is None and r.pdf_gerado == "C:/pdfs/lote.pdf"


def test_gerar_nao_marca_como_impressa(hist, notas):
    ids = hist.registrar_geracao(notas, "a.pdf", quando=D1)
    assert all(not hist.obter(i).impressa for i in ids)
    hist.registrar_solicitacao(ids, "a.pdf", quando=D1)
    r = hist.obter(ids[0])
    assert r.status == IMPRESSAO_SOLICITADA and not r.impressa and r.impressao_confirmada_em is None
    hist.confirmar_impressao(ids[:1], quando=D2)
    r = hist.obter(ids[0])
    assert r.status == IMPRESSAO_CONFIRMADA and r.impressao_confirmada_em == "2026-11-10T14:30:00"
    assert hist.obter(ids[1]).status == IMPRESSAO_SOLICITADA
    assert [e.tipo for e in hist.eventos(ids[0])] == [IMPRESSAO_CONFIRMADA, IMPRESSAO_SOLICITADA, PDF_GERADO]


def test_reimpressao_nao_duplica_registro(hist, notas):
    ids1 = hist.registrar_geracao(notas, "a.pdf", quando=D1)
    hist.confirmar_impressao(ids1, quando=D1)
    ids2 = hist.registrar_geracao([notas[0]], "b.pdf", quando=D2)
    assert ids2 == ids1[:1]  # mesma linha
    assert len(hist.pesquisar()) == 3
    r = hist.obter(ids1[0])
    assert r.status == REIMPRESSAO and r.geracoes == 2 and r.pdf_gerado == "b.pdf"
    assert r.primeira_geracao_em == "2026-11-03T09:00:00" and r.ultima_geracao_em == "2026-11-10T14:30:00"
    assert r.impressao_confirmada_em == "2026-11-03T09:00:00"  # confirmação anterior preservada
    tipos = [e.tipo for e in hist.eventos(r.id)]
    assert tipos == [REIMPRESSAO, IMPRESSAO_CONFIRMADA, PDF_GERADO]
    hist.confirmar_impressao([r.id], quando=D2)
    assert hist.obter(r.id).status == IMPRESSAO_CONFIRMADA


def test_deteccao_de_duplicadas(hist, notas):
    hist.registrar_geracao(notas[:2], "a.pdf", quando=D1)
    ja = hist.ja_processadas(notas)
    assert set(ja) == {0, 1} and ja[1].numero_impresso == "9201"


def test_identificacao_sem_chave(hist, notas):
    sem_chave = replace(notas[0], chave="")
    assert identificador(sem_chave) == "49126933000119-1-9200"  # emitente-série-número
    hist.registrar_geracao([sem_chave], "a.pdf")
    assert hist.consultar(sem_chave) is not None
    assert hist.consultar(replace(sem_chave, serie="2")) is None
    assert hist.consultar(replace(sem_chave, emitente_cnpj="11111111000111")) is None
    assert hist.consultar(notas[0]) is None  # com chave é outra identidade


def test_persistencia_apos_fechar_e_reabrir(tmp_path, notas):
    arq = tmp_path / "ck_etiquetas.db"
    ids = Historico(arq).registrar_geracao(notas, "a.pdf")
    Historico(arq).confirmar_impressao(ids[:1])
    del ids
    novo = Historico(arq)  # "reinício" do programa
    assert len(novo.pesquisar()) == 3
    assert novo.consultar(notas[0]).impressa


def test_pesquisa_e_filtros(hist, notas):
    hist.registrar_geracao(notas[:1], "a.pdf", quando=D1)
    hist.registrar_geracao(notas[1:], "b.pdf", quando=D2)
    hist.confirmar_impressao([hist.consultar(notas[2]).id])
    assert [r.numero_impresso for r in hist.pesquisar(nf="9201")] == ["9201"]
    assert [r.numero_impresso for r in hist.pesquisar(nf="009201")] == ["9201"]
    assert [r.numero_impresso for r in hist.pesquisar(placa=notas[0].placa.lower())] == ["9200"]
    assert len(hist.pesquisar(transportadora="RODONAVES")) == 3
    assert hist.pesquisar(transportadora="CARVALIMA") == []
    assert [r.numero_impresso for r in hist.pesquisar(status=IMPRESSAO_CONFIRMADA)] == ["9202"]
    assert [r.numero_impresso for r in hist.pesquisar(data_inicial=date(2026, 11, 3),
                                                      data_final=date(2026, 11, 3))] == ["9200"]
    assert len(hist.pesquisar(data_inicial=date(2026, 11, 4))) == 2
    assert hist.pesquisar(mais_recentes_primeiro=False)[0].numero_impresso == "9200"
    assert hist.pesquisar()[-1].numero_impresso == "9200"
    assert hist.transportadoras() == ["RODONAVES"]


def test_estatisticas_reais(hist, notas):
    vazio = hist.estatisticas(hoje=date(2026, 11, 10))
    assert (vazio.notas_processadas, vazio.etiquetas_geradas, vazio.notas_hoje) == (0, 0, 0)
    ids = hist.registrar_geracao(notas, "a.pdf", quando=D1)  # 1+2+3 = 6 etiquetas
    hist.confirmar_impressao(ids[1:2], quando=D1)  # 2 etiquetas
    hist.registrar_geracao(notas[2:], "b.pdf", quando=D2)  # reimpressão: +3
    e = hist.estatisticas(hoje=date(2026, 11, 10))
    assert e.notas_processadas == 3
    assert e.etiquetas_geradas == 9
    assert e.etiquetas_confirmadas == 2
    assert e.notas_hoje == 1
    assert e.aguardando_confirmacao == 2
    ult = hist.ultimas_operacoes(2)
    assert [(o.tipo, o.numero_impresso) for o in ult] == [(REIMPRESSAO, "9202"), (IMPRESSAO_CONFIRMADA, "9201")]


def test_reimprimir_sem_o_pdf_original(hist, notas):
    hist.registrar_geracao(notas, "a.pdf")
    r = hist.consultar(notas[2])
    assert expandir_etiquetas([r.como_nota()]) == expandir_etiquetas([notas[2]])
    assert identificador(r.como_nota()) == r.identificador


# --------------------------------------------------------------- migrações


def test_migracao_do_banco_beta(tmp_path):
    arq = tmp_path / "ck_etiquetas.db"
    con = sqlite3.connect(arq)
    con.executescript("""
        CREATE TABLE impressoes (id INTEGER PRIMARY KEY AUTOINCREMENT, data_hora TEXT, nf TEXT, serie TEXT,
          chave TEXT, transportadora TEXT, volumes INTEGER, placa TEXT, arquivo_origem TEXT,
          arquivo_gerado TEXT, reimpressao INTEGER);
        INSERT INTO impressoes VALUES (1,'2026-11-09T10:00:00','7928','1',
          '35261149126933000119550010000079281245505840','RODONAVES',1,'TDM2E09','o.pdf','g1.pdf',0);
        INSERT INTO impressoes VALUES (2,'2026-11-09T11:00:00','7928','1',
          '35261149126933000119550010000079281245505840','RODONAVES',1,'TDM2E09','o.pdf','g2.pdf',1);
        INSERT INTO impressoes VALUES (3,'2026-11-09T11:00:00','7929','1','','RODONAVES',2,'TDK1D43','o.pdf','g2.pdf',0);
    """)
    con.close()
    h = Historico(arq)
    regs = h.pesquisar(mais_recentes_primeiro=False)
    assert [(r.numero_impresso, r.numero, r.geracoes, r.status) for r in regs] == [
        ("7928", "007928", 2, REIMPRESSAO), ("7929", "007929", 1, PDF_GERADO)]
    assert regs[0].emitente_cnpj == "49126933000119" and regs[0].pdf_gerado == "g2.pdf"
    assert h.estatisticas().etiquetas_geradas == 4
    con = sqlite3.connect(arq)
    assert con.execute("SELECT COUNT(*) FROM impressoes_beta").fetchone()[0] == 3  # dados antigos mantidos
    assert con.execute("PRAGMA user_version").fetchone()[0] == banco.VERSAO_ESQUEMA
    con.close()
    Historico(arq)  # reabrir não migra de novo
    assert len(Historico(arq).pesquisar()) == 2


def test_banco_de_versao_mais_nova_nao_e_corrompido(tmp_path):
    arq = tmp_path / "ck_etiquetas.db"
    con = sqlite3.connect(arq)
    con.execute(f"PRAGMA user_version = {banco.VERSAO_ESQUEMA + 1}")
    con.close()
    with pytest.raises(RuntimeError, match="versão mais nova"):
        Historico(arq)


def test_migracao_falha_e_desfeita(tmp_path, monkeypatch):
    arq = tmp_path / "ck_etiquetas.db"

    def quebra(con):
        con.execute("CREATE TABLE parcial (x)")
        raise RuntimeError("falhou no meio")

    monkeypatch.setitem(banco.MIGRACOES, 0, quebra)
    with pytest.raises(RuntimeError):
        banco.preparar(arq)
    con = sqlite3.connect(arq)
    assert con.execute("SELECT name FROM sqlite_master WHERE name='parcial'").fetchone() is None
    assert con.execute("PRAGMA user_version").fetchone()[0] == 0
    con.close()


def test_migra_pasta_dados_da_versao_1(tmp_path, monkeypatch):
    antiga = tmp_path / "instalacao" / "dados"
    antiga.mkdir(parents=True)
    (antiga / "transportadoras.json").write_text('{"transportadoras": []}', encoding="utf-8")
    nova = tmp_path / "LocalAppData" / "CKEtiquetas"
    monkeypatch.setattr(config, "PASTA_DADOS", nova)
    monkeypatch.setattr(config, "TRANSPORTADORAS_USUARIO", nova / "transportadoras.json")
    monkeypatch.setattr(config, "HISTORICO_DB", nova / "ck_etiquetas.db")
    monkeypatch.setattr(config, "_pastas_dados_antigas", lambda: [antiga])
    assert len(config.migrar_dados_antigos()) == 1
    assert (nova / "transportadoras.json").is_file() and (antiga / "transportadoras.json").is_file()
    assert config.migrar_dados_antigos() == []  # só uma vez


def test_pasta_de_dados_padrao_fora_da_instalacao(monkeypatch):
    monkeypatch.delenv("CK_ETIQUETAS_DADOS", raising=False)
    monkeypatch.setenv("LOCALAPPDATA", r"C:\Users\x\AppData\Local")
    p = config._base_dados()
    assert str(p) == r"C:\Users\x\AppData\Local\CKEtiquetas"


# --------------------------------------------------------------- backup


def test_backup_e_restauracao(tmp_path, notas):
    pasta = tmp_path / "dados"
    h = Historico(pasta / "ck_etiquetas.db")
    h.registrar_geracao(notas[:1], "a.pdf")
    p = Preferencias.carregar(pasta / "configuracoes.json")
    p.pasta_pdfs = "X:/etiquetas"
    p.salvar()
    arq = backup.criar_backup(tmp_path / "bk.zip", pasta)
    with zipfile.ZipFile(arq) as z:
        assert {"ck_etiquetas.db", "configuracoes.json", "manifesto.json"} <= set(z.namelist())
    assert backup.ler_manifesto(arq)["esquema"] == banco.VERSAO_ESQUEMA

    h.registrar_geracao(notas[1:], "b.pdf")  # dados posteriores ao backup
    p.pasta_pdfs = "Y:/outra"
    p.salvar()
    seguranca = backup.restaurar_backup(arq, pasta)
    assert len(Historico(pasta / "ck_etiquetas.db").pesquisar()) == 1
    assert Preferencias.carregar(pasta / "configuracoes.json").pasta_pdfs == "X:/etiquetas"
    assert seguranca.is_file()  # dados de antes da restauração foram guardados
    backup.restaurar_backup(seguranca, pasta)
    assert len(Historico(pasta / "ck_etiquetas.db").pesquisar()) == 3


def test_restaurar_arquivo_invalido(tmp_path):
    ruim = tmp_path / "x.zip"
    with zipfile.ZipFile(ruim, "w") as z:
        z.writestr("qualquer.txt", "x")
    with pytest.raises(ValueError, match="manifesto"):
        backup.restaurar_backup(ruim, tmp_path / "dados")


def test_backup_automatico_um_por_dia(tmp_path, notas):
    pasta = tmp_path / "dados"
    Historico(pasta / "ck_etiquetas.db").registrar_geracao(notas[:1], "a.pdf")
    assert backup.backup_automatico(pasta) is not None
    assert backup.backup_automatico(pasta) is None
    assert len(list((pasta / "backups").glob("*_auto.zip"))) == 1


# --------------------------------------------------------------- preferências


def test_preferencias(tmp_path):
    arq = tmp_path / "configuracoes.json"
    p = Preferencias.carregar(arq)
    assert p.modo_impressao == IMPRIMIR_ABRIR and p.confirmar_impressao and p.pasta_pdfs
    p.salvar_automaticamente = False
    p.salvar()
    assert Preferencias.carregar(arq).salvar_automaticamente is False
    arq.write_text("{corrompido", encoding="utf-8")
    assert Preferencias.carregar(arq).salvar_automaticamente is True  # volta ao padrão
    arq.write_text(json.dumps({"modo_impressao": "xyz", "chave_desconhecida": 1}), encoding="utf-8")
    assert Preferencias.carregar(arq).modo_impressao == IMPRIMIR_ABRIR


def test_cadastro_listar_e_remover(cadastro):
    cadastro.salvar("TRANSPORTES TESTE LTDA", "11.222.333/0001-81", "TESTE")
    origens = {r["abreviacao"]: r["origem"] for r in cadastro.listar()}
    assert origens == {"RODONAVES": "padrão", "CARVALIMA": "padrão", "TESTE": "usuário"}
    assert cadastro.remover("Transportes Teste Ltda")
    assert cadastro.buscar("TRANSPORTES TESTE LTDA") is None
    assert not cadastro.remover("RODONAVES - TRANSP.ENC.LTDA.")  # padrão não é removível


# --------------------------------------------------------------- reimpressão (operações)


def _spans(pdf):
    import pymupdf

    with pymupdf.open(pdf) as doc:
        return [[(s["text"], s["font"], round(s["size"], 2), round(s["origin"][0], 2), round(s["origin"][1], 2))
                 for b in p.get_text("dict")["blocks"] for l in b.get("lines", []) for s in l["spans"]]
                for p in doc]


def test_reimpressao_identica_ao_original(tmp_path, notas, hist):
    from ck_etiquetas import operacoes

    prefs = Preferencias.carregar(tmp_path / "cfg.json")
    prefs.pasta_pdfs = str(tmp_path / "pdfs")
    original = operacoes.destino_automatico(prefs, notas)
    rel, ids = operacoes.gerar_lote(notas, original, hist)
    assert rel.etiquetas == 6 and rel.folhas == 3
    assert original.parent.name == date.today().strftime("%Y-%m")  # organizado por mês

    regs = [hist.obter(i) for i in ids]
    destino, rel2, ids2 = operacoes.reimprimir(regs, prefs, hist)
    assert ids2 == ids and destino != original and "_reimpressao" in destino.name
    assert _spans(destino) == _spans(original)  # mesmo texto, fontes, tamanhos e posições
    assert all(hist.obter(i).status == REIMPRESSAO and hist.obter(i).geracoes == 2 for i in ids)

    # reimprimir só uma nota gera um PDF só com ela (o PDF antigo tinha o lote inteiro)
    d3, rel3, _ = operacoes.reimprimir([hist.obter(ids[1])], prefs, hist)
    assert rel3.etiquetas == 2 and rel3.folhas == 1


def test_destino_automatico_nao_sobrescreve(tmp_path, notas):
    from ck_etiquetas import operacoes

    prefs = Preferencias.carregar(tmp_path / "cfg.json")
    prefs.pasta_pdfs = str(tmp_path / "pdfs")
    d1 = operacoes.destino_automatico(prefs, notas)
    d1.parent.mkdir(parents=True)
    d1.write_bytes(b"x")
    d2 = operacoes.destino_automatico(prefs, notas)
    assert d2 != d1 and not d2.exists()
