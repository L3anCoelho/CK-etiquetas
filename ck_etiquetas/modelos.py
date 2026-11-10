"""Estruturas de dados compartilhadas."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class NotaFiscal:
    # dados extraídos (originais, nunca alterados após a extração)
    numero_original: str = ""  # ex.: "007928"
    serie: str = ""
    chave: str = ""  # chave de acesso, 44 dígitos
    emitente: str = ""  # razão social do emitente (canhoto "RECEBEMOS DE ...")
    emitente_cnpj: str = ""  # só dígitos; da chave de acesso
    transportadora_nome: str = ""  # nome completo como está na DANFE
    transportadora_cnpj: str = ""
    volumes_original: str = ""  # texto bruto do campo Quantidade
    placa_original: str = ""
    pagina: int = 0  # página (1-based) no PDF de origem
    arquivo_origem: str = ""  # caminho completo do PDF de onde a nota foi lida

    # dados editáveis que vão para a etiqueta
    numero: str = ""  # ex.: "7928"
    transportadora: str = ""  # texto impresso (abreviação)
    volumes: int | None = None
    placa: str = ""

    # controle
    transportadora_confirmada: bool = False  # abreviação conhecida ou confirmada
    excecao_sem_placa: bool = False  # usuário autorizou etiqueta sem placa
    excecao_placa_fora_padrao: bool = False  # usuário aceitou placa fora do padrão
    avisos_extracao: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class Etiqueta:
    numero: str
    transportadora: str
    volume_atual: int
    volume_total: int
    placa: str

    @property
    def texto_volume(self) -> str:
        from .config import FORMATO_VOLUME

        largura = max(2, len(str(self.volume_total)))
        return FORMATO_VOLUME.format(
            atual=str(self.volume_atual).zfill(largura),
            total=str(self.volume_total).zfill(largura),
        )

    @property
    def linha_transporte(self) -> str:
        return f"{self.transportadora}{self.texto_volume}"
