"""Janela principal do CK Etiquetas: menu lateral + páginas."""

from __future__ import annotations

import sys
import tkinter.messagebox as mb

import customtkinter as ctk

from .. import __version__, backup, config
from ..historico import Historico
from ..preferencias import Preferencias
from ..transportadoras import CadastroTransportadoras
from . import tema
from .tema import AZUL_ESCURO, AZUL_MENU_ATIVO, AZUL_MENU_HOVER, FUNDO, fonte, icone

try:  # arrastar e soltar arquivos (opcional)
    from tkinterdnd2 import DND_FILES, TkinterDnD

    _BaseDnD: tuple = (TkinterDnD.DnDWrapper,)
except Exception:  # noqa: BLE001
    TkinterDnD = None
    _BaseDnD = ()

ID_APLICATIVO = "CKAutoshop.CKEtiquetas"
MUTEX_INSTALADOR = "CKEtiquetas_Executando"
_MUTEX = None

PAGINAS = [
    ("dashboard", "Dashboard", "dashboard"),
    ("gerar", "Gerar etiquetas", "etiqueta"),
    ("historico", "Histórico", "historico"),
    ("configuracoes", "Configurações", "config"),
]


def _definir_id_aplicativo() -> None:
    """Faz a barra de tarefas usar o ícone da CK (e não o do Python)."""
    if sys.platform == "win32":
        try:
            import ctypes

            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(ID_APLICATIVO)
            # o instalador (AppMutex) usa este nome para pedir que o programa seja fechado antes de atualizar
            global _MUTEX
            _MUTEX = ctypes.windll.kernel32.CreateMutexW(None, False, MUTEX_INSTALADOR)
        except Exception:  # noqa: BLE001
            pass


class App(ctk.CTk, *_BaseDnD):
    def __init__(self, historico: Historico | None = None):
        super().__init__()
        ctk.set_appearance_mode("light")
        ctk.set_default_color_theme("blue")
        self.title("CK Etiquetas")
        self.geometry("1280x800")
        self.minsize(1040, 660)
        self.configure(fg_color=FUNDO)
        try:
            self.iconbitmap(default=str(config.ICONE_PATH))
        except Exception:  # noqa: BLE001
            pass
        tema.configurar_estilo_tabelas(self)

        # serviços compartilhados pelas páginas
        self.prefs = Preferencias.carregar()
        self.historico = historico or Historico()
        self.cadastro = CadastroTransportadoras()
        self.notificacao = tema.Notificacao(self)
        self.dnd_ativo = False

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self._montar_menu()
        self.conteudo = ctk.CTkFrame(self, fg_color=FUNDO, corner_radius=0)
        self.conteudo.grid(row=0, column=1, sticky="nsew")
        self.conteudo.grid_columnconfigure(0, weight=1)
        self.conteudo.grid_rowconfigure(0, weight=1)

        self.paginas: dict[str, ctk.CTkFrame] = {}
        self.pagina_atual = ""
        self._ativar_arrastar_soltar()
        self.mostrar("dashboard")

    # ------------------------------------------------------------ menu lateral
    def _montar_menu(self) -> None:
        menu = ctk.CTkFrame(self, fg_color=AZUL_ESCURO, corner_radius=0, width=232)
        menu.grid(row=0, column=0, sticky="nsw")
        menu.grid_propagate(False)
        menu.grid_columnconfigure(0, weight=1)

        topo = ctk.CTkFrame(menu, fg_color="#ffffff", corner_radius=14)
        topo.grid(row=0, column=0, padx=18, pady=(22, 6), sticky="ew")
        ctk.CTkLabel(topo, text="", image=tema.logo(118)).pack(pady=10)
        ctk.CTkLabel(menu, text="CK Etiquetas", font=fonte(18, "bold"), text_color="white").grid(
            row=1, column=0, pady=(6, 18))

        self._botoes_menu: dict[str, ctk.CTkButton] = {}
        for i, (chave, rotulo, ic) in enumerate(PAGINAS):
            b = ctk.CTkButton(
                menu, text="   " + rotulo, image=icone(ic, 18, "#ffffff"), compound="left", anchor="w",
                height=44, corner_radius=10, fg_color="transparent", hover_color=AZUL_MENU_HOVER,
                text_color="#dbe7f8", font=fonte(14), command=lambda c=chave: self.mostrar(c),
            )
            b.grid(row=i + 2, column=0, padx=14, pady=3, sticky="ew")
            self._botoes_menu[chave] = b
        menu.grid_rowconfigure(len(PAGINAS) + 2, weight=1)

        rod = ctk.CTkFrame(menu, fg_color="transparent")
        rod.grid(row=len(PAGINAS) + 3, column=0, sticky="sew", padx=18, pady=16)
        ctk.CTkLabel(rod, text="CK Autoshop", font=fonte(12, "bold"), text_color="#dbe7f8").pack(anchor="w")
        ctk.CTkLabel(rod, text=f"Versão {__version__}  •  100% offline", font=fonte(11),
                     text_color="#8fa8cc").pack(anchor="w")

    def mostrar(self, chave: str) -> None:
        pagina = self.pagina(chave)
        for c, b in self._botoes_menu.items():
            ativo = c == chave
            b.configure(fg_color=AZUL_MENU_ATIVO if ativo else "transparent",
                        text_color="#ffffff" if ativo else "#dbe7f8",
                        font=fonte(14, "bold" if ativo else "normal"))
        pagina.tkraise()
        self.pagina_atual = chave
        ao_mostrar = getattr(pagina, "ao_mostrar", None)
        if ao_mostrar:
            ao_mostrar()

    def pagina(self, chave: str):
        if chave not in self.paginas:
            if chave == "dashboard":
                from .pagina_dashboard import PaginaDashboard as Classe
            elif chave == "gerar":
                from .pagina_gerar import PaginaGerar as Classe
            elif chave == "historico":
                from .pagina_historico import PaginaHistorico as Classe
            else:
                from .pagina_configuracoes import PaginaConfiguracoes as Classe
            p = Classe(self.conteudo, self)
            p.grid(row=0, column=0, sticky="nsew")
            self.paginas[chave] = p
        return self.paginas[chave]

    def dados_alterados(self) -> None:
        """O histórico mudou: as páginas que mostram dados se atualizam ao serem exibidas."""
        for chave, p in self.paginas.items():
            if hasattr(p, "sujo"):
                p.sujo = True
                if chave == self.pagina_atual:
                    p.ao_mostrar()

    # ------------------------------------------------------------ arrastar e soltar
    def _ativar_arrastar_soltar(self) -> None:
        if TkinterDnD is None:
            return
        try:
            self.TkdndVersion = TkinterDnD._require(self)
            self.drop_target_register(DND_FILES)
            self.dnd_bind("<<Drop>>", self._ao_soltar)
            self.dnd_ativo = True
        except Exception:  # noqa: BLE001 - sem tkdnd: segue só com o botão
            self.dnd_ativo = False

    def _ao_soltar(self, evento):
        caminhos = list(self.tk.splitlist(evento.data))
        self.mostrar("gerar")
        self.paginas["gerar"].importar(caminhos)
        return evento.action


def executar() -> None:
    _definir_id_aplicativo()
    try:
        migrados = config.migrar_dados_antigos()
        historico = Historico()
    except Exception as e:  # noqa: BLE001
        import tkinter as tk

        r = tk.Tk()
        r.withdraw()
        mb.showerror("CK Etiquetas", f"Não foi possível abrir o banco de dados:\n\n{e}\n\n"
                                     f"Pasta de dados: {config.PASTA_DADOS}")
        r.destroy()
        return
    try:
        backup.backup_automatico()
    except Exception:  # noqa: BLE001 - backup automático nunca impede o uso
        pass
    app = App(historico)
    if migrados:
        app.after(800, lambda: app.notificacao.mostrar(
            "Dados da versão anterior migrados para a nova pasta de dados.", "info", 6))
    app.mainloop()
