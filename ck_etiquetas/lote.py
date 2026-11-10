"""Importação de vários PDFs de DANFEs para um único lote de etiquetas.

Aceita qualquer combinação de arquivos: PDF com uma nota, PDF com várias
notas, vários PDFs de uma vez e novos PDFs adicionados depois. As notas já
carregadas nunca são substituídas: as novas entram no fim da lista, na
ordem dos arquivos e das páginas, e notas repetidas (mesma chave de acesso,
ou mesmo número+série quando não há chave) são ignoradas com aviso.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from pathlib import Path

from .extrator import ler_notas, preparar_notas
from .modelos import NotaFiscal
from .validacao import ERRO, Problema, validar


def identificador(nf: NotaFiscal) -> str:
    """Identidade da NF: chave de acesso; sem chave, emitente + série + número."""
    if nf.chave:
        return nf.chave
    numero = nf.numero or (str(int(nf.numero_original)) if nf.numero_original.isdigit() else nf.numero_original)
    return f"{nf.emitente_cnpj}-{nf.serie or '0'}-{numero}"


@dataclass
class ResultadoImportacao:
    novas: list[NotaFiscal] = field(default_factory=list)
    avisos: list[str] = field(default_factory=list)
    arquivos_lidos: int = 0
    duplicadas: int = 0
    falhas: list[tuple[str, str]] = field(default_factory=list)  # (arquivo, erro)


def expandir_caminhos(caminhos: Iterable[str | Path]) -> list[Path]:
    """Mantém só PDFs; pastas são trocadas pelos PDFs que contêm (ordem alfabética)."""
    out: list[Path] = []
    for c in caminhos:
        p = Path(c)
        if p.is_dir():
            out.extend(sorted((x for x in p.iterdir() if x.suffix.lower() == ".pdf"), key=lambda x: x.name.lower()))
        elif p.suffix.lower() == ".pdf":
            out.append(p)
    # mesmo arquivo selecionado duas vezes na mesma operação
    vistos: set[str] = set()
    unicos = []
    for p in out:
        k = str(p.resolve()).lower()
        if k not in vistos:
            vistos.add(k)
            unicos.append(p)
    return unicos


def importar_arquivos(
    caminhos: Iterable[str | Path],
    existentes: list[NotaFiscal],
    cadastro=None,
    progresso: Callable[[int, int, str], None] | None = None,
) -> ResultadoImportacao:
    """Lê os PDFs e devolve apenas as notas que ainda não estão em `existentes`.

    `existentes` não é alterada. Se `cadastro` for informado, as novas notas
    já saem com os campos editáveis preenchidos (abreviação etc.).
    """
    res = ResultadoImportacao()
    arquivos = expandir_caminhos(caminhos)
    ids = {identificador(nf): nf for nf in existentes}

    for i, caminho in enumerate(arquivos, start=1):
        if progresso:
            progresso(i, len(arquivos), caminho.name)
        try:
            leitura = ler_notas(caminho)
        except Exception as e:  # noqa: BLE001 - arquivo corrompido, protegido etc.
            res.falhas.append((caminho.name, str(e)))
            res.avisos.append(f"{caminho.name}: não foi possível ler o arquivo ({e}).")
            continue
        res.arquivos_lidos += 1
        for a in leitura.avisos:
            res.avisos.append(f"{caminho.name}: {a}")
        if leitura.paginas_vazias:
            res.avisos.append(
                f"{caminho.name}: {len(leitura.paginas_vazias)} página(s) em branco ignorada(s) "
                f"({', '.join(map(str, leitura.paginas_vazias))})."
            )
        repetidas = []
        for nf in leitura.notas:
            nf.arquivo_origem = str(caminho)
            ident = identificador(nf)
            if ident in ids:
                anterior = ids[ident]
                origem = Path(anterior.arquivo_origem).name if anterior.arquivo_origem else "lista"
                repetidas.append(f"{nf.numero_original.lstrip('0')} (já carregada de {origem})")
                continue
            ids[ident] = nf
            res.novas.append(nf)
        if repetidas:
            res.duplicadas += len(repetidas)
            if len(repetidas) == len(leitura.notas):
                res.avisos.append(
                    f"{caminho.name}: todas as {len(repetidas)} nota(s) já estavam na lista — nada adicionado."
                )
            else:
                res.avisos.append(f"{caminho.name}: NF repetida ignorada — " + "; ".join(repetidas) + ".")

    if cadastro is not None and res.novas:
        cadastro.carregar()
        preparar_notas(res.novas, cadastro)
    return res


def numeros_repetidos(notas: list[NotaFiscal]) -> dict[int, int]:
    """Índice -> índice da primeira ocorrência, para NFs com o mesmo número impresso.

    Pega repetições que a importação não consegue ver, por exemplo quando o
    usuário edita o número de uma nota para o de outra.
    """
    primeira: dict[str, int] = {}
    out: dict[int, int] = {}
    for i, nf in enumerate(notas):
        if not nf.numero:
            continue
        if nf.numero in primeira:
            out[i] = primeira[nf.numero]
        else:
            primeira[nf.numero] = i
    return out


def validar_lista(notas: list[NotaFiscal]) -> list[list[Problema]]:
    """Validação de cada nota + checagem de NF repetida na lista."""
    probs = [validar(nf) for nf in notas]
    for i, j in numeros_repetidos(notas).items():
        probs[i].insert(
            0,
            Problema("NF", ERRO, f"NF {notas[i].numero} repetida na lista (linha {j + 1}). "
                                 "Remova uma delas para não duplicar etiquetas."),
        )
    return probs
