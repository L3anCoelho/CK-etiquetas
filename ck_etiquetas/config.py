"""Configurações, caminhos e geometria do layout das etiquetas.

Todas as medidas de layout foram extraídas do PDF de referência
(referencias/etiquetas_modelo.pdf) com PyMuPDF. Unidade: pontos PDF
(1 pt = 1/72 pol = 0,3528 mm). Origem no canto superior esquerdo da folha.

A etiqueta SUPERIOR do modelo é a referência canônica: a etiqueta inferior
do modelo foi gerada pelo Word com deslocamentos diferentes por elemento
(NF +413,85 pt, demais +393,10 pt) e com o logotipo distorcido. Para que as
duas etiquetas sejam idênticas e encaixem exatamente nas metades de
148,5 mm, a etiqueta inferior é a superior deslocada de exatamente meia
folha A4.
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path

# ----------------------------------------------------------------- caminhos


def _base_recursos() -> Path:
    """Pasta dos recursos empacotados (funciona também dentro do .exe)."""
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS)  # type: ignore[attr-defined]
    return Path(__file__).resolve().parent.parent


def _base_dados() -> Path:
    """Pasta persistente dos dados do usuário (banco, configurações, abreviações, backups).

    Fica em %LOCALAPPDATA%/CKEtiquetas — fora da pasta de instalação, para que
    atualizar ou desinstalar o programa nunca apague o histórico.
    A variável de ambiente CK_ETIQUETAS_DADOS permite outro local (testes, rede).
    """
    if os.environ.get("CK_ETIQUETAS_DADOS"):
        return Path(os.environ["CK_ETIQUETAS_DADOS"])
    base = os.environ.get("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
    return Path(base) / "CKEtiquetas"


def _pastas_dados_antigas() -> list[Path]:
    """Locais usados pela versão 1.x (pasta 'dados' ao lado do programa)."""
    if getattr(sys, "frozen", False):
        return [Path(sys.executable).resolve().parent / "dados"]
    return [Path(__file__).resolve().parent.parent / "dados"]


PASTA_RECURSOS = _base_recursos()
PASTA_ASSETS = PASTA_RECURSOS / "assets"
PASTA_DADOS = _base_dados()

LOGO_PATH = PASTA_ASSETS / "logo_ck.png"
ICONE_PATH = PASTA_ASSETS / "icone.ico"
TRANSPORTADORAS_PADRAO = PASTA_ASSETS / "transportadoras_padrao.json"
TRANSPORTADORAS_USUARIO = PASTA_DADOS / "transportadoras.json"
HISTORICO_DB = PASTA_DADOS / "ck_etiquetas.db"
PREFERENCIAS_JSON = PASTA_DADOS / "configuracoes.json"
PASTA_BACKUPS = PASTA_DADOS / "backups"


def migrar_dados_antigos() -> list[str]:
    """Copia (uma única vez) abreviações e histórico da pasta 'dados' da v1.x.

    Os arquivos antigos não são apagados. Retorna o que foi migrado.
    """
    import shutil

    feito: list[str] = []
    for antiga in _pastas_dados_antigas():
        if not antiga.is_dir() or antiga.resolve() == PASTA_DADOS.resolve():
            continue
        PASTA_DADOS.mkdir(parents=True, exist_ok=True)
        pares = [(antiga / "transportadoras.json", TRANSPORTADORAS_USUARIO),
                 (antiga / "historico.db", HISTORICO_DB)]
        for origem, destino in pares:
            if origem.is_file() and not destino.exists():
                shutil.copy2(origem, destino)
                feito.append(f"{origem} -> {destino}")
    return feito


# ----------------------------------------------------------------- fontes

PASTA_FONTES_WINDOWS = Path(os.environ.get("WINDIR", r"C:\Windows")) / "Fonts"
PASTA_FONTES_LOCAL = PASTA_ASSETS / "fonts"

# nome lógico -> arquivos aceitos (o primeiro encontrado é usado)
FONTES = {
    "cambria": ["cambria.ttc", "cambria.ttf"],
    "cambria_bold": ["cambriab.ttf"],
    "bookman": ["BOOKOS.TTF", "bookos.ttf"],
}


def localizar_fonte(nome: str) -> Path:
    """Procura a fonte em assets/fonts e depois em C:\\Windows\\Fonts."""
    for pasta in (PASTA_FONTES_LOCAL, PASTA_FONTES_WINDOWS):
        for arquivo in FONTES[nome]:
            caminho = pasta / arquivo
            if caminho.is_file():
                return caminho
    raise FileNotFoundError(
        f"Fonte '{nome}' não encontrada ({', '.join(FONTES[nome])}). "
        "Cambria e Bookman Old Style acompanham o Windows/Office. "
        f"Copie os arquivos para {PASTA_FONTES_LOCAL} se necessário."
    )


# ----------------------------------------------------------------- geometria

MM = 72.0 / 25.4  # pontos por milímetro

A4_LARGURA = 210.0 * MM  # 595,276 pt
A4_ALTURA = 297.0 * MM  # 841,890 pt
METADE_ALTURA = A4_ALTURA / 2.0  # 420,945 pt = 148,5 mm
CENTRO_X = A4_LARGURA / 2.0  # eixo de centralização de todos os textos


@dataclass(frozen=True)
class ElementoTexto:
    fonte: str  # chave de FONTES
    tamanho: float  # pt
    baseline: float  # y da linha de base, relativo ao topo da etiqueta (pt)


@dataclass(frozen=True)
class LayoutEtiqueta:
    # retângulo do logotipo (x0, y0, x1, y1) relativo ao topo da etiqueta
    logo: tuple[float, float, float, float] = (77.15, 67.90, 183.45, 167.00)
    nf: ElementoTexto = ElementoTexto("cambria_bold", 65.03, 129.80)
    numero: ElementoTexto = ElementoTexto("cambria_bold", 125.02, 301.85)
    transporte: ElementoTexto = ElementoTexto("cambria", 28.0, 365.10)
    placa: ElementoTexto = ElementoTexto("bookman", 16.0, 388.37)
    # largura máxima de texto antes de reduzir a fonte (margem de 10 mm)
    largura_maxima: float = A4_LARGURA - 2 * 10.0 * MM


LAYOUT = LayoutEtiqueta()
ETIQUETAS_POR_FOLHA = 2

# ----------------------------------------------------------------- regras

FORMATO_VOLUME = "({atual}/{total}V)"  # conforme modelo: LUZ-TR(01/02V)
MAX_VOLUMES = 999
