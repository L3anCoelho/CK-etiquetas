"""Preferências do usuário (configuracoes.json na pasta de dados)."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, fields
from pathlib import Path

from . import config

# como enviar as etiquetas para a impressora
IMPRIMIR_ABRIR = "abrir"  # abre o PDF no leitor; o usuário imprime em "Tamanho real"
IMPRIMIR_DIRETO = "direto"  # envia para a impressora padrão do Windows


def _documentos() -> Path:
    return Path.home() / "Documents"


@dataclass
class Preferencias:
    # pasta onde o Bling salva os PDFs exportados (início do "Adicionar notas fiscais")
    pasta_notas: str = ""
    # onde os PDFs de etiquetas são guardados
    pasta_pdfs: str = ""
    # salvar automaticamente na pasta de PDFs (organizada por mês) em vez de perguntar
    salvar_automaticamente: bool = True
    modo_impressao: str = IMPRIMIR_ABRIR
    abrir_apos_gerar: bool = True
    confirmar_impressao: bool = True

    def __post_init__(self):
        if not self.pasta_notas:
            self.pasta_notas = str(Path.home() / "Downloads")
        if not self.pasta_pdfs:
            self.pasta_pdfs = str(_documentos() / "CK Etiquetas" / "Etiquetas")
        if self.modo_impressao not in (IMPRIMIR_ABRIR, IMPRIMIR_DIRETO):
            self.modo_impressao = IMPRIMIR_ABRIR

    # ------------------------------------------------------------ arquivo
    @classmethod
    def carregar(cls, arquivo: Path | None = None) -> "Preferencias":
        arquivo = Path(arquivo or config.PREFERENCIAS_JSON)
        dados: dict = {}
        if arquivo.is_file():
            try:
                dados = json.loads(arquivo.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                dados = {}  # arquivo corrompido: volta ao padrão sem travar o programa
        validos = {f.name for f in fields(cls)}
        prefs = cls(**{k: v for k, v in dados.items() if k in validos})
        prefs._arquivo = arquivo
        return prefs

    def salvar(self) -> None:
        arquivo = getattr(self, "_arquivo", None) or config.PREFERENCIAS_JSON
        arquivo = Path(arquivo)
        arquivo.parent.mkdir(parents=True, exist_ok=True)
        tmp = arquivo.with_suffix(".tmp")
        tmp.write_text(json.dumps(asdict(self), ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(arquivo)  # gravação atômica

    def pasta_pdfs_do_mes(self, quando=None) -> Path:
        from datetime import date

        d = quando or date.today()
        return Path(self.pasta_pdfs) / f"{d:%Y-%m}"
