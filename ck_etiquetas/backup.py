"""Backup e restauração dos dados do CK Etiquetas.

O backup é um .zip com:
  ck_etiquetas.db       banco (cópia consistente via API de backup do SQLite)
  configuracoes.json    preferências
  transportadoras.json  abreviações cadastradas pelo usuário
  manifesto.json        versão do programa, versão do esquema e data

Os PDFs de etiquetas não entram no backup (ficam na pasta configurada e
podem ser regerados pelo histórico).
"""

from __future__ import annotations

import json
import shutil
import sqlite3
import tempfile
import zipfile
from datetime import datetime
from pathlib import Path

from . import __version__, banco, config

ARQ_DB = "ck_etiquetas.db"
ARQ_PREFS = "configuracoes.json"
ARQ_TRANSP = "transportadoras.json"
MANIFESTO = "manifesto.json"
MANTER_AUTOMATICOS = 15


def _copiar_banco(origem: Path, destino: Path) -> None:
    src = sqlite3.connect(origem)
    dst = sqlite3.connect(destino)
    try:
        src.backup(dst)
    finally:
        dst.close()
        src.close()


def criar_backup(destino: str | Path, pasta_dados: Path | None = None) -> Path:
    pasta = Path(pasta_dados or config.PASTA_DADOS)
    destino = Path(destino)
    destino.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        with zipfile.ZipFile(destino, "w", zipfile.ZIP_DEFLATED) as z:
            db = pasta / ARQ_DB
            versao_esquema = 0
            if db.is_file():
                _copiar_banco(db, tmp / ARQ_DB)
                con = sqlite3.connect(tmp / ARQ_DB)
                versao_esquema = con.execute("PRAGMA user_version").fetchone()[0]
                con.close()
                z.write(tmp / ARQ_DB, ARQ_DB)
            for nome in (ARQ_PREFS, ARQ_TRANSP):
                if (pasta / nome).is_file():
                    z.write(pasta / nome, nome)
            z.writestr(MANIFESTO, json.dumps({
                "programa": "CK Etiquetas", "versao": __version__, "esquema": versao_esquema,
                "criado_em": datetime.now().isoformat(timespec="seconds"),
            }, ensure_ascii=False, indent=2))
    return destino


def ler_manifesto(arquivo: str | Path) -> dict:
    with zipfile.ZipFile(arquivo) as z:
        if MANIFESTO not in z.namelist():
            raise ValueError("Arquivo não é um backup do CK Etiquetas (manifesto ausente).")
        m = json.loads(z.read(MANIFESTO))
    if m.get("programa") != "CK Etiquetas":
        raise ValueError("Arquivo não é um backup do CK Etiquetas.")
    return m


def restaurar_backup(arquivo: str | Path, pasta_dados: Path | None = None) -> Path:
    """Substitui os dados atuais pelos do backup.

    Antes, salva automaticamente um backup de segurança dos dados atuais
    (retornado), para que a restauração possa ser desfeita.
    """
    pasta = Path(pasta_dados or config.PASTA_DADOS)
    m = ler_manifesto(arquivo)
    if m.get("esquema", 0) > banco.VERSAO_ESQUEMA:
        raise ValueError("Este backup é de uma versão mais nova do CK Etiquetas. Atualize o programa primeiro.")
    with zipfile.ZipFile(arquivo) as z:
        nomes = set(z.namelist())
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            z.extractall(tmp, [n for n in (ARQ_DB, ARQ_PREFS, ARQ_TRANSP) if n in nomes])
            if ARQ_DB in nomes:
                con = sqlite3.connect(tmp / ARQ_DB)
                try:
                    ok = con.execute("PRAGMA integrity_check").fetchone()[0]
                finally:
                    con.close()
                if ok != "ok":
                    raise ValueError(f"O banco dentro do backup está danificado ({ok}).")
            seguranca = criar_backup(_nome_automatico(pasta, "antes_restauracao"), pasta)
            for nome in (ARQ_DB, ARQ_PREFS, ARQ_TRANSP):
                if nome in nomes:
                    shutil.copy2(tmp / nome, pasta / nome)
    banco.preparar(pasta / ARQ_DB)  # backup antigo: aplica as migrações
    return seguranca


def _nome_automatico(pasta: Path, sufixo: str) -> Path:
    return pasta / "backups" / f"ck_etiquetas_{datetime.now():%Y-%m-%d_%H%M%S}_{sufixo}.zip"


def backup_automatico(pasta_dados: Path | None = None) -> Path | None:
    """Um backup por dia (ao abrir o programa), mantendo os mais recentes."""
    pasta = Path(pasta_dados or config.PASTA_DADOS)
    if not (pasta / ARQ_DB).is_file():
        return None
    pasta_bk = pasta / "backups"
    hoje = datetime.now().strftime("%Y-%m-%d")
    if any(p.name.startswith(f"ck_etiquetas_{hoje}") and p.name.endswith("_auto.zip")
           for p in pasta_bk.glob("*.zip")):
        return None
    novo = criar_backup(_nome_automatico(pasta, "auto"), pasta)
    autos = sorted(pasta_bk.glob("ck_etiquetas_*_auto.zip"))
    for antigo in autos[:-MANTER_AUTOMATICOS]:
        antigo.unlink(missing_ok=True)
    return novo
