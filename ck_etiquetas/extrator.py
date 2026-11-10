"""Leitura das DANFEs (PDF exportado do Bling) e extração dos 4 campos.

Estratégia: em vez de procurar padrões soltos no texto, o extrator localiza
cada SEÇÃO da DANFE pelo título (ex.: "Transportador/Volumes transportados")
e, dentro dela, o RÓTULO do campo (fonte menor) e o VALOR imediatamente
abaixo, alinhado à esquerda com o rótulo. Isso evita confundir, por exemplo,
a "Quantidade" de volumes com a quantidade de itens, ou a placa do caminhão
com a placa do veículo do cliente.

O PDF de origem é aberto somente para leitura e nunca é alterado.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path

import pymupdf

from .modelos import NotaFiscal
from .validacao import RE_PLACA

TAM_TITULO_MIN = 7.5  # títulos de seção ("Transportador/...") têm 8 pt
TAM_ROTULO_MAX = 6.5  # rótulos de campo têm 6 pt; valores têm 7 pt


@dataclass
class Linha:
    x0: float
    y0: float
    x1: float
    y1: float
    tamanho: float
    texto: str

    @property
    def norm(self) -> str:
        return _sem_acento(self.texto).upper().strip()


@dataclass
class ResultadoLeitura:
    notas: list[NotaFiscal] = field(default_factory=list)
    avisos: list[str] = field(default_factory=list)
    paginas_total: int = 0
    paginas_vazias: list[int] = field(default_factory=list)


def _sem_acento(s: str) -> str:
    return unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()


def _linhas_da_pagina(pagina: pymupdf.Page) -> list[Linha]:
    linhas: list[Linha] = []
    for bloco in pagina.get_text("dict")["blocks"]:
        if bloco.get("type") != 0:
            continue
        for ln in bloco["lines"]:
            texto = " ".join(s["text"] for s in ln["spans"])
            texto = re.sub(r"\s+", " ", texto.replace("\xa0", " ")).strip()
            if not texto:
                continue
            tam = max(s["size"] for s in ln["spans"])
            x0, y0, x1, y1 = ln["bbox"]
            linhas.append(Linha(x0, y0, x1, y1, tam, texto))
    linhas.sort(key=lambda l: (round(l.y0, 1), l.x0))
    return linhas


def _eh_cabecalho_navegador(l: Linha, altura: float) -> bool:
    """Cabeçalho/rodapé inseridos pelo navegador ao imprimir o PDF."""
    t = l.texto
    if "bling.com.br" in t or t == "Bling - DANFE":
        return True
    if re.fullmatch(r"\d{1,4}/\d{1,4}", t) and (l.y0 > altura - 40 or l.y1 < 40):
        return True
    if re.fullmatch(r"\d{2}/\d{2}/\d{4},? \d{2}:\d{2}(:\d{2})?", t) and (
        l.y1 < 40 or l.y0 > altura - 40
    ):
        return True
    return False


# --------------------------------------------------------------- utilitários


def _titulo(linhas: list[Linha], prefixo: str) -> Linha | None:
    p = _sem_acento(prefixo).upper()
    for l in linhas:
        if l.tamanho >= TAM_TITULO_MIN and l.norm.startswith(p):
            return l
    return None


def _limites_secao(linhas: list[Linha], titulo: Linha, altura: float) -> tuple[float, float]:
    """Do fim do título até o próximo título de seção."""
    fim = altura
    for l in linhas:
        if (
            l.y0 > titulo.y1 + 2
            and l.tamanho >= TAM_TITULO_MIN
            and l.x0 < titulo.x0 + 10  # títulos começam na margem esquerda
            and l.y0 < fim
        ):
            fim = l.y0
    return titulo.y1, fim


def _rotulo(linhas: list[Linha], textos: tuple[str, ...], y_ini: float, y_fim: float) -> Linha | None:
    alvos = {_sem_acento(t).upper() for t in textos}
    for l in linhas:
        if y_ini <= l.y0 < y_fim and l.tamanho <= TAM_ROTULO_MAX and l.norm in alvos:
            return l
    return None


def _valor_abaixo(linhas: list[Linha], rotulo: Linha, y_fim: float) -> str:
    """Valor posicionado logo abaixo do rótulo e alinhado à esquerda com ele."""
    candidatos = [
        l
        for l in linhas
        if l is not rotulo
        and l.tamanho > TAM_ROTULO_MAX
        and abs(l.x0 - rotulo.x0) <= 4
        and rotulo.y1 - 1.5 <= l.y0 <= rotulo.y1 + 9
        and l.y0 < y_fim
    ]
    if not candidatos:
        return ""
    candidatos.sort(key=lambda l: l.y0)
    return candidatos[0].texto.strip()


RE_NUMERO_NF = re.compile(r"^N\s*[º°oO\.]*\s*(\d{1,9})$")
RE_EMITENTE = re.compile(r"RECEBEMOS DE (.+?) OS PRODUTOS", re.I)
RE_SERIE = re.compile(r"S[EÉ]RIE:?\s*(\d{1,3})", re.I)
RE_PAGINA = re.compile(r"P[AÁ]GINA:?\s*(\d+)\s*DE\s*(\d+)", re.I)
RE_PLACA_ROTULADA = re.compile(
    r"\bPLACA\b(?:\s+DO\s+VE[IÍ]CULO)?(?:\s+DO\s+CLIENTE)?\s*[:\-–.]?\s*"
    r"([A-Z]{3})\s*-?\s*(\d[A-Z0-9]\d{2})(?![A-Z0-9])",
    re.I,
)
RE_PLACA_SOLTA = re.compile(r"(?<![A-Z0-9])([A-Z]{3})-?(\d[A-Z0-9]\d{2})(?![A-Z0-9])")


def _extrair_chave(linhas: list[Linha]) -> str:
    for l in linhas:
        digitos = re.sub(r"\s", "", l.texto)
        if re.fullmatch(r"\d{44}", digitos):
            return digitos
    return ""


def _extrair_placas(texto_obs: str) -> tuple[list[str], list[str]]:
    """Retorna (placas com rótulo 'Placa', candidatas sem rótulo)."""
    t = _sem_acento(texto_obs).upper()
    rotuladas: list[str] = []
    for m in RE_PLACA_ROTULADA.finditer(t):
        p = m.group(1) + m.group(2)
        if RE_PLACA.fullmatch(p) and p not in rotuladas:
            rotuladas.append(p)
    soltas: list[str] = []
    for m in RE_PLACA_SOLTA.finditer(t):
        p = m.group(1) + m.group(2)
        if RE_PLACA.fullmatch(p) and p not in rotuladas and p not in soltas:
            soltas.append(p)
    return rotuladas, soltas


def _converter_volumes(texto: str) -> int | None:
    t = texto.strip()
    m = re.fullmatch(r"(\d{1,6})(?:[.,]0+)?", t)
    if not m:
        return None
    v = int(m.group(1))
    return v if v > 0 else None


# --------------------------------------------------------------- página


def _eh_danfe(linhas: list[Linha]) -> bool:
    textos = {l.norm for l in linhas}
    return "DANFE" in textos and any(t.startswith("CHAVE DE ACESSO") for t in textos)


def extrair_pagina(pagina: pymupdf.Page) -> tuple[NotaFiscal | None, tuple[int, int] | None, list[Linha]]:
    """Extrai os dados de uma página. Retorna (nota, (pag_atual, pag_total), linhas)."""
    altura = pagina.rect.height
    linhas = [l for l in _linhas_da_pagina(pagina) if not _eh_cabecalho_navegador(l, altura)]
    if not linhas or not _eh_danfe(linhas):
        return None, None, linhas

    nf = NotaFiscal()

    # ---- número, série, chave, paginação
    numeros = [m.group(1) for l in linhas if (m := RE_NUMERO_NF.match(l.texto.strip()))]
    nf.chave = _extrair_chave(linhas)
    numero_chave = nf.chave[25:34] if nf.chave else ""
    if nf.chave:
        nf.emitente_cnpj = nf.chave[6:20]
    for l in linhas:
        if m := RE_EMITENTE.search(l.texto):
            nf.emitente = m.group(1).strip()
            break
    if numeros:
        nf.numero_original = max(set(numeros), key=numeros.count)
        if len(set(int(n) for n in numeros)) > 1:
            nf.avisos_extracao.append(f"Números de NF divergentes na página: {sorted(set(numeros))}.")
    elif numero_chave:
        nf.numero_original = numero_chave
        nf.avisos_extracao.append("Número da NF obtido pela chave de acesso (campo Nº não encontrado).")
    if nf.numero_original and numero_chave and int(nf.numero_original) != int(numero_chave):
        nf.avisos_extracao.append(
            f"Número da NF ({nf.numero_original}) diverge da chave de acesso ({numero_chave}). Confira."
        )
    for l in linhas:
        if m := RE_SERIE.search(l.texto):
            nf.serie = m.group(1)
            break
    pag = None
    for l in linhas:
        if m := RE_PAGINA.search(_sem_acento(l.texto)):
            pag = (int(m.group(1)), int(m.group(2)))
            break

    # ---- transportador / volumes
    tit_transp = _titulo(linhas, "Transportador")
    if tit_transp:
        y_ini, y_fim = _limites_secao(linhas, tit_transp, altura)
        r_nome = _rotulo(linhas, ("Nome", "Razão Social", "Nome / Razão Social"), y_ini, y_fim)
        if r_nome:
            nf.transportadora_nome = _valor_abaixo(linhas, r_nome, y_fim)
        r_cnpj = _rotulo(linhas, ("CNPJ/CPF", "CNPJ / CPF", "CNPJ"), y_ini, y_fim)
        if r_cnpj:
            nf.transportadora_cnpj = _valor_abaixo(linhas, r_cnpj, y_fim)
        r_qtd = _rotulo(linhas, ("Quantidade", "Qtde", "Qtd"), y_ini, y_fim)
        if r_qtd:
            nf.volumes_original = _valor_abaixo(linhas, r_qtd, y_fim)
            nf.volumes = _converter_volumes(nf.volumes_original)
            if nf.volumes_original and nf.volumes is None:
                nf.avisos_extracao.append(
                    f"Quantidade de volumes inválida: '{nf.volumes_original}'."
                )
        r_placa_transp = _rotulo(linhas, ("Placa do veículo",), y_ini, y_fim)
        placa_transp = (
            re.sub(r"[^A-Z0-9]", "", _valor_abaixo(linhas, r_placa_transp, y_fim).upper())
            if r_placa_transp
            else ""
        )
    else:
        placa_transp = ""
        nf.avisos_extracao.append("Seção 'Transportador/Volumes transportados' não encontrada.")

    # ---- dados adicionais / observações -> placa do veículo do cliente
    tit_obs = _titulo(linhas, "Dados adicionais")
    if tit_obs:
        y_ini, y_fim = _limites_secao(linhas, tit_obs, altura)
        r_fisco = next(
            (l for l in linhas if l.y0 >= y_ini and l.norm.startswith("RESERVADO AO FISCO")), None
        )
        x_lim = r_fisco.x0 - 1 if r_fisco else pagina.rect.width / 2
        obs = [
            l
            for l in linhas
            if y_ini <= l.y0 < y_fim and l.x0 < x_lim and l.norm not in ("OBSERVACOES", "INFORMACOES COMPLEMENTARES")
        ]
        texto_obs = "\n".join(l.texto for l in obs)
        rotuladas, soltas = _extrair_placas(texto_obs)
        if len(rotuladas) == 1:
            nf.placa_original = rotuladas[0]
            if placa_transp and rotuladas[0] == placa_transp:
                nf.avisos_extracao.append(
                    "Placa das observações é igual à placa do veículo transportador. Confira."
                )
        elif len(rotuladas) > 1:
            nf.avisos_extracao.append(
                f"Mais de uma placa nas observações ({', '.join(rotuladas)}). Informe a correta."
            )
        elif soltas:
            nf.avisos_extracao.append(
                f"Placa não identificada com o rótulo 'Placa'. Possível candidata: "
                f"{', '.join(soltas)} — confirme manualmente."
            )
    else:
        nf.avisos_extracao.append("Seção 'Dados adicionais' não encontrada.")

    return nf, pag, linhas


# --------------------------------------------------------------- documento


def ler_notas(caminho: str | Path) -> ResultadoLeitura:
    res = ResultadoLeitura()
    caminho = Path(caminho)
    with pymupdf.open(caminho) as doc:  # somente leitura
        res.paginas_total = doc.page_count
        vistas: dict[str, int] = {}  # chave (ou nº+série) -> índice em res.notas
        for i, pagina in enumerate(doc, start=1):
            nf, pag, linhas = extrair_pagina(pagina)
            if nf is None:
                if not linhas:
                    res.paginas_vazias.append(i)
                else:
                    res.avisos.append(f"Página {i}: não reconhecida como DANFE — ignorada.")
                continue
            nf.pagina = i
            ident = nf.chave or f"{nf.numero_original}-{nf.serie}"
            if ident in vistas:
                anterior = res.notas[vistas[ident]]
                if pag and pag[0] > 1:
                    continue  # continuação de DANFE com várias páginas
                res.avisos.append(
                    f"Página {i}: NF {nf.numero_original} repetida (já lida na página "
                    f"{anterior.pagina}) — ignorada para não duplicar etiquetas."
                )
                continue
            vistas[ident] = len(res.notas)
            res.notas.append(nf)
    if not res.notas:
        res.avisos.append("Nenhuma DANFE encontrada no arquivo.")
    return res


def preparar_notas(notas: list[NotaFiscal], cadastro) -> None:
    """Preenche os campos editáveis a partir dos dados extraídos."""
    for nf in notas:
        nf.numero = str(int(nf.numero_original)) if nf.numero_original.isdigit() else ""
        nf.placa = nf.placa_original
        abrev, motivo = (
            cadastro.buscar_detalhado(nf.transportadora_nome, nf.transportadora_cnpj)
            if nf.transportadora_nome
            else (None, "")
        )
        if motivo == "nome":
            nf.transportadora = abrev
            nf.transportadora_confirmada = True
        elif motivo == "cnpj":
            # CNPJ conhecido, mas nome diferente do cadastro: só sugestão
            nf.transportadora = abrev
            nf.transportadora_confirmada = False
            nf.avisos_extracao.append(
                f"CNPJ da transportadora cadastrado como '{abrev}', mas o nome na DANFE é diferente. "
                "Confirme a abreviação."
            )
        else:
            # nome completo como sugestão; precisa de confirmação do usuário
            nf.transportadora = nf.transportadora_nome
            nf.transportadora_confirmada = False
