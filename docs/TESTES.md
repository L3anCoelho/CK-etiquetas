# CK Etiquetas 2.0 — resultado dos testes

Data: 10/11/2026 • Windows 11 Pro (10.0.26200) • Python 3.14.7 • PyInstaller 6 • Inno Setup 6.7.3

Suíte automatizada: **78 testes, 78 aprovados** (`python -m pytest`). O `empacotamento\build.ps1` roda a
suíte antes de compilar e aborta se algum teste falhar.

| # | Teste obrigatório | Situação | Como foi verificado |
|---|---|---|---|
| 1 | Importação de PDF com uma nota | ✅ Aprovado | `test_lote.py`, `test_extracao.py` |
| 2 | Importação de PDF com várias notas | ✅ Aprovado | DANFE real com 7 notas e 7 páginas em branco; seleção de 2, 5 e 10 PDFs; seleção mista |
| 3 | Extração dos quatro campos | ✅ Aprovado | `test_extracao.py` (NF, transportadora, volumes, placa) + série, chave e emitente |
| 4 | Geração de múltiplos volumes | ✅ Aprovado | `(01/02V)`, `(02/02V)`, `(01/03V)`…; exemplo 7928/7929/7930 conferido metade a metade |
| 5 | Duas etiquetas por folha A4 | ✅ Aprovado | `test_gerador_pdf.py`, `test_lote.py` (inclui total ímpar com metade inferior em branco) |
| 6 | Preservação do layout original | ✅ Aprovado | `gerador_pdf.py`, `volumes.py` e a geometria em `config.py` **não foram alterados**; testes de posição/fonte/tamanho contra o modelo continuam passando; reimpressão pelo histórico gera PDF com texto, fontes, tamanhos e posições idênticos ao original |
| 7 | Salvamento permanente do histórico | ✅ Aprovado | SQLite em `%LOCALAPPDATA%\CKEtiquetas`; `test_persistencia_apos_fechar_e_reabrir` |
| 8 | Detecção de notas duplicadas | ✅ Aprovado | na importação (mesma chave em arquivos diferentes), na lista (número editado) e no histórico (chave, ou emitente+série+número) |
| 9 | Reimpressão | ✅ Aprovado | mesma linha da nota (sem duplicar), status *Reimpressão*, evento com data/hora, confirmação anterior preservada |
| 10 | Fechamento e reabertura do aplicativo | ✅ Aprovado | interface aberta, fechada e reaberta no mesmo banco (dados mantidos); executável `CKEtiquetas.exe` aberto sobre um banco existente mostrando os dados corretos |
| 11 | Atualização sem perda de dados | ⚠️ Parcial | **Verificado:** dados ficam fora da pasta do programa; migração do banco da 2.0-beta e da pasta `dados` da 1.x; migração com falha é desfeita; banco de versão mais nova não é alterado; restauração de backup antigo. **Pendente:** executar o instalador por cima de uma instalação existente (ver abaixo) |
| 12 | Instalação em ambiente Windows limpo | ⏳ Pendente | o instalador foi compilado, mas **não pôde ser executado** neste PC (ver abaixo) |
| 13 | Funcionamento sem Python instalado | ⚠️ Parcial | `CKEtiquetas.exe` executado: Python, Tcl/Tk, Pillow e tkdnd são carregados de `_internal` (nenhuma DLL do Python do sistema). O teste num PC realmente sem Python está pendente |
| 14 | Funcionamento sem internet | ✅ Aprovado (por análise) | o código não importa nenhum módulo de rede (`urllib`, `requests`, `socket`, `http`); não há API nem integração com o Bling. Não foi feito teste com a placa de rede desligada |
| 15 | Desinstalação sem perda dos dados | ⏳ Pendente (garantido por projeto) | o desinstalador só remove a pasta do programa; os dados ficam em `%LOCALAPPDATA%\CKEtiquetas` e os PDFs em Documentos. Execução real pendente (ver abaixo) |

Também testados: backup/restauração (inclui backup de segurança automático antes de restaurar e rejeição
de arquivo inválido), backup automático diário, preferências (arquivo corrompido volta ao padrão),
cadastro de abreviações, estatísticas do Dashboard calculadas do banco, pesquisa e filtros do Histórico
(NF, placa, transportadora, status, período, ordenação) e controle de impressão (gerar ≠ imprimir;
só a confirmação marca como impressa). A interface foi exercitada em todas as telas, inclusive no tamanho
mínimo da janela (1040×660).

## Pendência: execução do instalador

Neste computador, o **Controle Inteligente de Aplicativos** do Windows bloqueia o
`CK_Etiquetas_Setup_v2.0.exe` por não ter assinatura digital ("Uma política de Controle de Aplicativo
bloqueou este arquivo"). O `CKEtiquetas.exe` foi executado normalmente.

Para concluir os testes 11, 12, 13 e 15, em um PC sem esse bloqueio (ou após assinar os arquivos —
README, seção 7):

1. **Instalação limpa (12, 13):** em um Windows sem Python, execute o instalador. Confira: atalho na Área
   de Trabalho e no menu Iniciar com o ícone da CK, *CK Etiquetas* em *Aplicativos instalados*, o programa
   abre pelo atalho, ícone correto na barra de tarefas.
2. **Uso (14):** desconecte a rede, importe um PDF, gere, imprima e confirme.
3. **Atualização (11):** com algumas notas no histórico, execute o instalador de novo (ou uma versão nova).
   O histórico e as configurações devem continuar iguais.
4. **Desinstalação (15):** desinstale pelo Windows. `%LOCALAPPDATA%\CKEtiquetas` e os PDFs em
   `Documentos\CK Etiquetas` devem continuar existindo; reinstalando, o histórico volta a aparecer.
