"""Histórico permanente das notas fiscais processadas.

Uma linha por NF (tabela `notas`, identificada pela chave de acesso ou por
emitente+série+número) e um registro por acontecimento (tabela `eventos`):

  PDF_GERADO            primeira geração das etiquetas da NF
  REIMPRESSAO           nova geração de uma NF que já tinha etiquetas
  IMPRESSAO_SOLICITADA  o usuário mandou imprimir (abriu o PDF / enviou à impressora)
  IMPRESSAO_CONFIRMADA  o usuário confirmou que as etiquetas saíram corretamente

Gerar ou enviar o PDF NUNCA marca a nota como impressa: só a confirmação
explícita do usuário faz isso. Nada é apagado.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

from . import banco, config
from .banco import (IMPRESSAO_CONFIRMADA, IMPRESSAO_SOLICITADA, PDF_GERADO, REIMPRESSAO,
                    ROTULOS_STATUS)
from .lote import identificador
from .modelos import NotaFiscal

GERACOES = (PDF_GERADO, REIMPRESSAO)


def formatar_data(iso: str | None, com_hora: bool = True) -> str:
    if not iso:
        return "—"
    try:
        return datetime.fromisoformat(iso).strftime("%d/%m/%Y %H:%M" if com_hora else "%d/%m/%Y")
    except ValueError:
        return iso


@dataclass(frozen=True)
class Registro:
    id: int
    identificador: str
    chave: str
    numero: str
    numero_impresso: str
    serie: str
    emitente: str
    emitente_cnpj: str
    transportadora: str
    transportadora_nome: str
    placa: str
    volumes: int
    etiquetas: int
    status: str
    geracoes: int
    primeira_geracao_em: str | None
    ultima_geracao_em: str | None
    impressao_solicitada_em: str | None
    impressao_confirmada_em: str | None
    pdf_gerado: str
    arquivo_origem: str

    @property
    def status_rotulo(self) -> str:
        return ROTULOS_STATUS.get(self.status, self.status)

    @property
    def impressa(self) -> bool:
        return self.status == IMPRESSAO_CONFIRMADA

    @property
    def data_formatada(self) -> str:
        return formatar_data(self.ultima_geracao_em)

    def como_nota(self) -> NotaFiscal:
        """Reconstrói a nota a partir do histórico (para reimprimir sem o PDF original)."""
        return NotaFiscal(
            numero_original=self.numero, serie=self.serie, chave=self.chave, emitente=self.emitente,
            emitente_cnpj=self.emitente_cnpj, transportadora_nome=self.transportadora_nome,
            numero=self.numero_impresso, transportadora=self.transportadora, volumes=self.volumes,
            placa=self.placa, transportadora_confirmada=True, excecao_sem_placa=not self.placa,
            excecao_placa_fora_padrao=True, arquivo_origem=self.arquivo_origem,
        )


@dataclass(frozen=True)
class Evento:
    id: int
    nota_id: int
    tipo: str
    data_hora: str
    etiquetas: int
    pdf: str
    detalhe: str
    numero_impresso: str = ""
    transportadora: str = ""

    @property
    def rotulo(self) -> str:
        return ROTULOS_STATUS.get(self.tipo, self.tipo)

    @property
    def data_formatada(self) -> str:
        return formatar_data(self.data_hora)


@dataclass(frozen=True)
class Estatisticas:
    notas_processadas: int
    etiquetas_geradas: int
    etiquetas_confirmadas: int
    notas_hoje: int
    aguardando_confirmacao: int


def _registro(row) -> Registro:
    return Registro(**{k: row[k] for k in row.keys()})


class Historico:
    def __init__(self, arquivo: str | Path | None = None):
        self.arquivo = Path(arquivo) if arquivo else config.HISTORICO_DB
        banco.preparar(self.arquivo)

    def _con(self):
        return banco.conectar(self.arquivo)

    # ------------------------------------------------------------ consulta
    def consultar(self, nf: NotaFiscal) -> Registro | None:
        with self._con() as con:
            row = con.execute("SELECT * FROM notas WHERE identificador = ?", (identificador(nf),)).fetchone()
        return _registro(row) if row else None

    def obter(self, nota_id: int) -> Registro | None:
        with self._con() as con:
            row = con.execute("SELECT * FROM notas WHERE id = ?", (nota_id,)).fetchone()
        return _registro(row) if row else None

    def ja_processadas(self, notas: list[NotaFiscal]) -> dict[int, Registro]:
        """Índice na lista -> registro existente, só para as notas que já têm etiquetas geradas."""
        if not notas:
            return {}
        idents = [identificador(nf) for nf in notas]
        with self._con() as con:
            rows = con.execute(
                f"SELECT * FROM notas WHERE identificador IN ({','.join('?' * len(idents))})", idents
            ).fetchall()
        por_ident = {r["identificador"]: _registro(r) for r in rows}
        return {i: por_ident[ident] for i, ident in enumerate(idents) if ident in por_ident}

    def eventos(self, nota_id: int) -> list[Evento]:
        with self._con() as con:
            rows = con.execute(
                "SELECT id, nota_id, tipo, data_hora, etiquetas, pdf, detalhe FROM eventos "
                "WHERE nota_id = ? ORDER BY data_hora DESC, id DESC", (nota_id,)
            ).fetchall()
        return [Evento(*r) for r in rows]

    def pesquisar(self, *, nf: str = "", placa: str = "", transportadora: str = "", status: str = "",
                  data_inicial: date | None = None, data_final: date | None = None,
                  mais_recentes_primeiro: bool = True, limite: int = 2000) -> list[Registro]:
        sql = ["SELECT * FROM notas WHERE 1=1"]
        args: list = []
        if nf.strip():
            sql.append("AND (numero_impresso LIKE ? OR numero LIKE ? OR chave LIKE ?)")
            t = f"%{nf.strip().lstrip('0') or nf.strip()}%"
            args += [t, t, f"%{nf.strip()}%"]
        if placa.strip():
            sql.append("AND REPLACE(placa, '-', '') LIKE ?")
            args.append(f"%{placa.strip().upper().replace('-', '')}%")
        if transportadora:
            sql.append("AND transportadora = ?")
            args.append(transportadora)
        if status:
            sql.append("AND status = ?")
            args.append(status)
        if data_inicial:
            sql.append("AND ultima_geracao_em >= ?")
            args.append(data_inicial.isoformat())
        if data_final:
            sql.append("AND ultima_geracao_em < date(?, '+1 day')")
            args.append(data_final.isoformat())
        sql.append(f"ORDER BY ultima_geracao_em {'DESC' if mais_recentes_primeiro else 'ASC'}, id "
                   f"{'DESC' if mais_recentes_primeiro else 'ASC'} LIMIT ?")
        args.append(limite)
        with self._con() as con:
            return [_registro(r) for r in con.execute(" ".join(sql), args).fetchall()]

    def transportadoras(self) -> list[str]:
        with self._con() as con:
            return [r[0] for r in con.execute(
                "SELECT DISTINCT transportadora FROM notas WHERE transportadora <> '' ORDER BY 1")]

    def estatisticas(self, hoje: date | None = None) -> Estatisticas:
        hoje = hoje or date.today()
        with self._con() as con:
            notas = con.execute("SELECT COUNT(*) FROM notas").fetchone()[0]
            geradas = con.execute(
                "SELECT COALESCE(SUM(etiquetas), 0) FROM eventos WHERE tipo IN (?, ?)", GERACOES).fetchone()[0]
            confirmadas = con.execute(
                "SELECT COALESCE(SUM(etiquetas), 0) FROM eventos WHERE tipo = ?", (IMPRESSAO_CONFIRMADA,)
            ).fetchone()[0]
            n_hoje = con.execute(
                "SELECT COUNT(DISTINCT nota_id) FROM eventos WHERE tipo IN (?, ?) "
                "AND data_hora >= ? AND data_hora < date(?, '+1 day')",
                (*GERACOES, hoje.isoformat(), hoje.isoformat()),
            ).fetchone()[0]
            aguardando = con.execute(
                "SELECT COUNT(*) FROM notas WHERE status <> ?", (IMPRESSAO_CONFIRMADA,)).fetchone()[0]
        return Estatisticas(notas, geradas, confirmadas, n_hoje, aguardando)

    def ultimas_operacoes(self, limite: int = 12) -> list[Evento]:
        with self._con() as con:
            rows = con.execute(
                "SELECT e.id, e.nota_id, e.tipo, e.data_hora, e.etiquetas, e.pdf, e.detalhe, "
                "n.numero_impresso, n.transportadora FROM eventos e JOIN notas n ON n.id = e.nota_id "
                "ORDER BY e.data_hora DESC, e.id DESC LIMIT ?", (limite,)
            ).fetchall()
        return [Evento(*r) for r in rows]

    # ------------------------------------------------------------ gravação
    def registrar_geracao(self, notas: list[NotaFiscal], pdf: str | Path, quando: datetime | None = None,
                          detalhe: str = "") -> list[int]:
        """Registra a geração do PDF para cada NF. Retorna os ids das notas, na mesma ordem.

        NF nova -> status PDF_GERADO. NF já existente -> mesma linha (sem duplicar),
        status REIMPRESSAO e um novo evento.
        """
        ts = (quando or datetime.now()).isoformat(timespec="seconds")
        ids: list[int] = []
        with self._con() as con:
            for nf in notas:
                ident = identificador(nf)
                etq = nf.volumes or 0
                row = con.execute("SELECT id FROM notas WHERE identificador = ?", (ident,)).fetchone()
                dados = (nf.transportadora, nf.transportadora_nome, nf.placa, etq, etq, ts, str(pdf))
                if row is None:
                    cur = con.execute(
                        "INSERT INTO notas (identificador, chave, numero, numero_impresso, serie, emitente, "
                        "emitente_cnpj, transportadora, transportadora_nome, placa, volumes, etiquetas, "
                        "ultima_geracao_em, pdf_gerado, status, geracoes, primeira_geracao_em, arquivo_origem) "
                        "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,1,?,?)",
                        (ident, nf.chave, nf.numero_original or nf.numero, nf.numero, nf.serie, nf.emitente,
                         nf.emitente_cnpj, *dados, PDF_GERADO, ts, nf.arquivo_origem),
                    )
                    nota_id, tipo = cur.lastrowid, PDF_GERADO
                else:
                    nota_id, tipo = row["id"], REIMPRESSAO
                    con.execute(
                        "UPDATE notas SET transportadora = ?, transportadora_nome = COALESCE(NULLIF(?, ''), "
                        "transportadora_nome), placa = ?, volumes = ?, etiquetas = ?, ultima_geracao_em = ?, "
                        "pdf_gerado = ?, status = ?, geracoes = geracoes + 1, impressao_solicitada_em = NULL "
                        "WHERE id = ?",
                        (*dados, REIMPRESSAO, nota_id),
                    )
                con.execute(
                    "INSERT INTO eventos (nota_id, tipo, data_hora, etiquetas, pdf, detalhe) VALUES (?,?,?,?,?,?)",
                    (nota_id, tipo, ts, etq, str(pdf), detalhe),
                )
                ids.append(nota_id)
        return ids

    def registrar_solicitacao(self, nota_ids: list[int], pdf: str | Path = "",
                              quando: datetime | None = None, detalhe: str = "") -> None:
        """O usuário mandou imprimir. Não significa que imprimiu."""
        ts = (quando or datetime.now()).isoformat(timespec="seconds")
        with self._con() as con:
            for nid in nota_ids:
                con.execute(
                    "UPDATE notas SET impressao_solicitada_em = ?, "
                    "status = CASE WHEN status = ? THEN ? ELSE status END WHERE id = ?",
                    (ts, PDF_GERADO, IMPRESSAO_SOLICITADA, nid),
                )
                con.execute(
                    "INSERT INTO eventos (nota_id, tipo, data_hora, etiquetas, pdf, detalhe) "
                    "SELECT id, ?, ?, etiquetas, ?, ? FROM notas WHERE id = ?",
                    (IMPRESSAO_SOLICITADA, ts, str(pdf), detalhe, nid),
                )

    def confirmar_impressao(self, nota_ids: list[int], quando: datetime | None = None,
                            detalhe: str = "") -> None:
        """Confirmação explícita do usuário de que as etiquetas foram impressas."""
        ts = (quando or datetime.now()).isoformat(timespec="seconds")
        with self._con() as con:
            for nid in nota_ids:
                con.execute("UPDATE notas SET status = ?, impressao_confirmada_em = ? WHERE id = ?",
                            (IMPRESSAO_CONFIRMADA, ts, nid))
                con.execute(
                    "INSERT INTO eventos (nota_id, tipo, data_hora, etiquetas, pdf, detalhe) "
                    "SELECT id, ?, ?, etiquetas, pdf_gerado, ? FROM notas WHERE id = ?",
                    (IMPRESSAO_CONFIRMADA, ts, detalhe, nid),
                )


__all__ = ["Historico", "Registro", "Evento", "Estatisticas", "formatar_data", "PDF_GERADO",
           "IMPRESSAO_SOLICITADA", "IMPRESSAO_CONFIRMADA", "REIMPRESSAO", "ROTULOS_STATUS"]
