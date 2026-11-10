"""Banco de dados SQLite local e migrações de esquema.

A versão do esquema fica em PRAGMA user_version. Cada migração é aplicada
uma única vez, dentro de uma transação, e nunca apaga dados: tabelas
antigas são renomeadas e mantidas.

Versões:
  0 -> banco vazio, ou banco da v2.0-beta (tabela "impressoes", 1 linha por impressão)
  1 -> notas (1 linha por NF) + eventos (PDF gerado, impressão solicitada/confirmada, reimpressão)
"""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

VERSAO_ESQUEMA = 1

# status atual da nota (último evento relevante)
PDF_GERADO = "PDF_GERADO"
IMPRESSAO_SOLICITADA = "IMPRESSAO_SOLICITADA"
IMPRESSAO_CONFIRMADA = "IMPRESSAO_CONFIRMADA"
REIMPRESSAO = "REIMPRESSAO"

ROTULOS_STATUS = {
    PDF_GERADO: "PDF gerado",
    IMPRESSAO_SOLICITADA: "Impressão solicitada",
    IMPRESSAO_CONFIRMADA: "Impressão confirmada",
    REIMPRESSAO: "Reimpressão",
}

_V1 = """
CREATE TABLE notas (
    id                       INTEGER PRIMARY KEY AUTOINCREMENT,
    identificador            TEXT    NOT NULL UNIQUE,   -- chave de acesso, ou emitente-série-número
    chave                    TEXT    NOT NULL DEFAULT '',
    numero                   TEXT    NOT NULL,          -- número completo, como na DANFE (ex.: 007928)
    numero_impresso          TEXT    NOT NULL,          -- como sai na etiqueta (ex.: 7928)
    serie                    TEXT    NOT NULL DEFAULT '',
    emitente                 TEXT    NOT NULL DEFAULT '',
    emitente_cnpj            TEXT    NOT NULL DEFAULT '',
    transportadora           TEXT    NOT NULL DEFAULT '',  -- texto impresso (abreviação)
    transportadora_nome      TEXT    NOT NULL DEFAULT '',  -- nome completo na DANFE
    placa                    TEXT    NOT NULL DEFAULT '',
    volumes                  INTEGER NOT NULL DEFAULT 0,
    etiquetas                INTEGER NOT NULL DEFAULT 0,
    status                   TEXT    NOT NULL,
    geracoes                 INTEGER NOT NULL DEFAULT 0,
    primeira_geracao_em      TEXT,
    ultima_geracao_em        TEXT,
    impressao_solicitada_em  TEXT,
    impressao_confirmada_em  TEXT,
    pdf_gerado               TEXT    NOT NULL DEFAULT '',
    arquivo_origem           TEXT    NOT NULL DEFAULT ''
);
CREATE INDEX ix_notas_numero ON notas (numero_impresso);
CREATE INDEX ix_notas_placa ON notas (placa);
CREATE INDEX ix_notas_transp ON notas (transportadora);
CREATE INDEX ix_notas_data ON notas (ultima_geracao_em);

CREATE TABLE eventos (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    nota_id    INTEGER NOT NULL REFERENCES notas (id),
    tipo       TEXT    NOT NULL,   -- PDF_GERADO | REIMPRESSAO | IMPRESSAO_SOLICITADA | IMPRESSAO_CONFIRMADA
    data_hora  TEXT    NOT NULL,   -- ISO 8601, horário local
    etiquetas  INTEGER NOT NULL DEFAULT 0,
    pdf        TEXT    NOT NULL DEFAULT '',
    detalhe    TEXT    NOT NULL DEFAULT ''
);
CREATE INDEX ix_eventos_nota ON eventos (nota_id);
CREATE INDEX ix_eventos_data ON eventos (data_hora);
"""


def _tabelas(con: sqlite3.Connection) -> set[str]:
    return {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}


def _executar_script(con: sqlite3.Connection, script: str) -> None:
    # executescript() faria COMMIT implícito e quebraria a atomicidade da migração
    for comando in script.split(";"):
        if comando.strip():
            con.execute(comando)


def _migrar_0_para_1(con: sqlite3.Connection) -> None:
    antigas = "impressoes" in _tabelas(con)
    if antigas:
        con.execute("ALTER TABLE impressoes RENAME TO impressoes_beta")  # preservada
    _executar_script(con, _V1)
    if not antigas:
        return
    # beta: 1 linha por NF por geração (nf, serie, chave, transportadora, volumes, placa, ...)
    linhas = con.execute(
        "SELECT data_hora, nf, serie, chave, transportadora, volumes, placa, arquivo_origem, arquivo_gerado "
        "FROM impressoes_beta ORDER BY data_hora, id"
    ).fetchall()
    ids: dict[str, int] = {}
    for data, nf, serie, chave, transp, vol, placa, origem, gerado in linhas:
        ident = chave or f"-{serie or '0'}-{int(nf) if str(nf).isdigit() else nf}"
        numero = chave[25:34].lstrip("0").zfill(6) if chave else str(nf).zfill(6)
        if ident not in ids:
            cur = con.execute(
                "INSERT INTO notas (identificador, chave, numero, numero_impresso, serie, emitente_cnpj, "
                "transportadora, placa, volumes, etiquetas, status, geracoes, primeira_geracao_em, "
                "ultima_geracao_em, pdf_gerado, arquivo_origem) VALUES (?,?,?,?,?,?,?,?,?,?,?,1,?,?,?,?)",
                (ident, chave, numero, nf, serie, chave[6:20] if chave else "", transp, placa, vol, vol,
                 PDF_GERADO, data, data, gerado, origem),
            )
            ids[ident] = cur.lastrowid
            tipo = PDF_GERADO
        else:
            con.execute(
                "UPDATE notas SET geracoes = geracoes + 1, status = ?, ultima_geracao_em = ?, pdf_gerado = ?, "
                "transportadora = ?, placa = ?, volumes = ?, etiquetas = ? WHERE id = ?",
                (REIMPRESSAO, data, gerado, transp, placa, vol, vol, ids[ident]),
            )
            tipo = REIMPRESSAO
        con.execute(
            "INSERT INTO eventos (nota_id, tipo, data_hora, etiquetas, pdf, detalhe) VALUES (?,?,?,?,?,?)",
            (ids[ident], tipo, data, vol, gerado, "migrado da versão 2.0-beta"),
        )


MIGRACOES = {0: _migrar_0_para_1}


def preparar(arquivo: Path) -> None:
    """Cria o banco ou atualiza o esquema para a versão atual."""
    arquivo.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(arquivo, timeout=10, isolation_level=None)  # transações manuais
    try:
        versao = con.execute("PRAGMA user_version").fetchone()[0]
        if versao > VERSAO_ESQUEMA:
            raise RuntimeError(
                f"O banco de dados ({arquivo}) é de uma versão mais nova do CK Etiquetas "
                f"(esquema {versao}). Atualize o programa."
            )
        while versao < VERSAO_ESQUEMA:
            con.execute("BEGIN")
            try:
                MIGRACOES[versao](con)
                versao += 1
                con.execute(f"PRAGMA user_version = {versao}")
                con.execute("COMMIT")
            except Exception:
                con.execute("ROLLBACK")
                raise
    finally:
        con.close()


@contextmanager
def conectar(arquivo: Path):
    con = sqlite3.connect(arquivo, timeout=10)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    try:
        with con:  # commit / rollback
            yield con
    finally:
        con.close()


def agora() -> str:
    return datetime.now().isoformat(timespec="seconds")
