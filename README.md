# CK Etiquetas 2.0

Gerador de etiquetas de expedição da **CK Autoshop**. Lê os PDFs de DANFEs exportados manualmente do
Bling, extrai **NF, transportadora, volumes e placa do cliente**, permite conferir/corrigir e gera um PDF
A4 com **2 etiquetas por folha** (uma por volume), no layout do modelo oficial. Guarda um **histórico
permanente** de todas as notas processadas e controla a impressão.

Funciona 100% local: sem internet, sem API, sem integração com o Bling, sem Word ou Acrobat.

---

## 1. Para a equipe de expedição

### Instalar

1. Execute **`CK_Etiquetas_Setup_v2.0.exe`**.
2. Avance as telas (português). Deixe marcado *"Criar atalho na Área de Trabalho"*.
3. Pronto: abra pelo ícone **CK Etiquetas** na Área de Trabalho ou no menu Iniciar.

Não é preciso instalar Python, VS Code nem nada além do instalador. O programa funciona sem internet.

> Se o Windows mostrar *"O Windows protegeu o computador"* (SmartScreen) ou *"Uma política de Controle de
> Aplicativo bloqueou este arquivo"*, veja a seção [7. Assinatura digital](#7-assinatura-digital-do-executável).

### Usar no dia a dia

| Tela | Para que serve |
|---|---|
| **Dashboard** | Totais reais do banco: notas processadas, etiquetas geradas, etiquetas com impressão confirmada, notas de hoje e as últimas operações. Avisa se há impressões sem confirmação. |
| **Gerar etiquetas** | O fluxo de trabalho (abaixo). |
| **Histórico** | Pesquisa de qualquer NF já processada, sem precisar do PDF original. |
| **Configurações** | Pastas, impressão, abreviações de transportadoras, backup e restauração. |

**Fluxo em *Gerar etiquetas*:**

1. **Adicionar notas fiscais** → escolha um ou vários PDFs do Bling (Ctrl/Shift para vários), ou
   **arraste os PDFs** para a janela. Um PDF pode ter várias notas; páginas em branco são ignoradas.
   Novos arquivos são acrescentados à lista, nunca a substituem; NF repetida é ignorada com aviso.
2. Confira a tabela. **OK** (verde) = pronta • **CONFERIR** (amarelo) = pronta, com aviso •
   **PENDENTE** (vermelho) = falta dado; a geração fica bloqueada. A coluna *Histórico* mostra se a NF
   já teve etiquetas geradas.
3. **Duplo clique** numa linha corrige NF, transportadora, volumes e placa. Remova, limpe ou reordene a lista
   com os botões da barra (a ordem da tabela é a ordem de impressão).
4. **Visualizar** mostra as folhas exatamente como serão impressas.
5. **Gerar todas as etiquetas** cria **um único PDF** com todas as notas.
   - Se alguma NF já tiver etiquetas, aparece: **"ATENÇÃO: Esta nota fiscal já possui etiquetas geradas
     anteriormente"**, com a data da última geração e o status da impressão. Opções: *Visualizar registro
     anterior*, *Abrir PDF anterior*, *Gerar só as novas*, *Reimprimir / gerar novamente* (pede
     confirmação) ou *Cancelar*.
6. **Imprimir** → o PDF abre no leitor (ou vai direto para a impressora, conforme a configuração).
   **Sempre em "Tamanho real" / escala 100%.**
7. Depois de conferir as etiquetas impressas, **Confirmar impressão**. Só isso marca a nota como
   impressa — gerar ou enviar o PDF não marca.

### Status de cada nota no histórico

| Status | Significado |
|---|---|
| **PDF gerado** | Etiquetas geradas, ainda não enviadas para impressão. |
| **Impressão solicitada** | O PDF foi aberto/enviado para imprimir, mas ninguém confirmou que saiu. |
| **Impressão confirmada** | O usuário confirmou que as etiquetas foram impressas corretamente. |
| **Reimpressão** | As etiquetas foram geradas de novo e a nova impressão ainda não foi confirmada. |

Cada evento fica registrado com data e hora na *Linha do tempo* da nota (Histórico → Ver detalhes).

### Histórico

Pesquise por **NF** (com ou sem zeros), **placa**, **transportadora**, **status** e **período**, em ordem
de data crescente ou decrescente. Para cada nota: *Ver detalhes* (todos os dados e a linha do tempo),
*Reimprimir* (gera de novo a partir do histórico — não precisa da DANFE), *Confirmar impressão* e
*Abrir PDF salvo*.

---

## 2. Onde ficam os dados

| O quê | Onde |
|---|---|
| Programa | `%LOCALAPPDATA%\Programs\CK Etiquetas` (ou `C:\Program Files\CK Etiquetas` se instalado como administrador) |
| Banco de dados (histórico) | `%LOCALAPPDATA%\CKEtiquetas\ck_etiquetas.db` |
| Configurações | `%LOCALAPPDATA%\CKEtiquetas\configuracoes.json` |
| Abreviações cadastradas | `%LOCALAPPDATA%\CKEtiquetas\transportadoras.json` |
| Backups automáticos (1 por dia, últimos 15) | `%LOCALAPPDATA%\CKEtiquetas\backups\` |
| PDFs de etiquetas | `Documentos\CK Etiquetas\Etiquetas\AAAA-MM\` (configurável) |

Os dados **nunca** ficam na pasta do programa: atualizar ou desinstalar não apaga histórico,
configurações nem PDFs. Na primeira execução, dados da versão 1.x (pasta `dados` ao lado do programa) são
copiados automaticamente para o novo local (os originais não são apagados).

## 3. Atualização

1. Execute o instalador da versão nova (ex.: `CK_Etiquetas_Setup_v2.1.exe`) no mesmo computador.
2. Se o CK Etiquetas estiver aberto, o instalador pede para fechá-lo.
3. A instalação anterior é substituída; histórico, configurações, abreviações e PDFs são mantidos.
4. Ao abrir, o programa atualiza o banco automaticamente (migrações de esquema, dentro de uma transação:
   se algo falhar, nada é alterado). Um backup automático do dia já terá sido feito antes.

Para quem desenvolve: o `AppId` do `empacotamento\CKEtiquetas.iss` **não pode mudar** entre versões;
mudanças no banco entram como nova função em `banco.MIGRACOES` incrementando `VERSAO_ESQUEMA`.

## 4. Backup e restauração

- **Automático:** ao abrir o programa, uma vez por dia, em `%LOCALAPPDATA%\CKEtiquetas\backups`.
- **Manual:** *Configurações → Criar backup…* gera um `.zip` com banco, configurações e abreviações.
  Guarde-o em um pen drive, rede ou nuvem.
- **Restaurar:** *Configurações → Restaurar backup…* e escolha o `.zip`. Antes de substituir, o programa
  salva automaticamente uma cópia dos dados atuais em `backups\` (`…_antes_restauracao.zip`), então a
  restauração pode ser desfeita. Backups de versões antigas são migrados ao restaurar.
- **Trocar de computador:** crie o backup no PC antigo, instale o programa no novo e restaure o backup.
- Os PDFs de etiquetas não entram no `.zip` (ficam na pasta de PDFs e podem ser regerados pelo histórico).

## 5. Desinstalação

*Configurações do Windows → Aplicativos → CK Etiquetas → Desinstalar* (ou menu Iniciar → *Desinstalar CK
Etiquetas*). Remove só o programa. Para apagar também os dados, exclua manualmente
`%LOCALAPPDATA%\CKEtiquetas` — **faça um backup antes**.

---

## 6. Para desenvolvimento

### Ambiente

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python main.py
```

Python 3.12+. No VS Code, F5 usa a configuração "CK Etiquetas".

### Compilar executável e instalador

Pré-requisito único: Inno Setup 6 (`winget install JRSoftware.InnoSetup`).

```powershell
powershell -ExecutionPolicy Bypass -File empacotamento\build.ps1
```

O script instala as dependências, roda os testes (aborta se falharem), gera o ícone a partir do logotipo,
gera o executável e compila o instalador:

- `dist\CKEtiquetas\CKEtiquetas.exe` — programa (modo pasta; a pasta `_internal` é obrigatória);
- `dist\instalador\CK_Etiquetas_Setup_v2.0.exe` — instalador.

Opções: `-SemTestes`, `-SemInstalador`. O executável inclui Python, CustomTkinter, PyMuPDF, Pillow,
tkinterdnd2, o logotipo, o ícone e as **fontes do layout** (Cambria e Bookman Old Style), copiadas de
`assets\fonts` ou `C:\Windows\Fonts` no momento da compilação — assim as etiquetas saem iguais em PCs sem
Office. (As fontes são da Microsoft; incluí-las no programa de uso interno da empresa pressupõe que os PCs
tenham licença do Windows/Office.)

### Estrutura

```
main.py                         ponto de entrada
ck_etiquetas/
  config.py                     caminhos (recursos, %LOCALAPPDATA%\CKEtiquetas), fontes, geometria do layout
  modelos.py                    NotaFiscal, Etiqueta (formato do volume)
  extrator.py                   leitura das DANFEs (NF, série, chave, emitente, transportadora, volumes, placa)
  validacao.py                  regras dos campos, validação de placa
  lote.py                       importação de vários PDFs, identificação e duplicidade de notas
  volumes.py                    1 etiqueta por volume, 2 por folha            ┐ layout oficial:
  gerador_pdf.py                geração do PDF (PyMuPDF)                     ┘ NÃO alterar
  banco.py                      SQLite: esquema e migrações (PRAGMA user_version)
  historico.py                  histórico de notas e eventos, pesquisa, estatísticas
  operacoes.py                  gerar lote, reimprimir pelo histórico
  impressao.py                  abrir/enviar PDF para impressão
  preferencias.py               configurações do usuário
  backup.py                     backup, restauração, backup automático diário
  transportadoras.py            cadastro de abreviações
  gui/
    app.py                      janela principal, menu lateral, arrastar e soltar
    tema.py                     cores, fontes, ícones, cards, tabelas, notificações
    pagina_dashboard.py         Dashboard
    pagina_gerar.py             Gerar etiquetas
    pagina_historico.py         Histórico
    pagina_configuracoes.py     Configurações
    dialogo_edicao.py           conferência/edição de uma nota
    dialogo_historico.py        nota já processada, detalhes, reimpressão, confirmação de impressão
    visualizacao.py             visualização de impressão
assets/                         logotipo, ícone, abreviações padrão
empacotamento/                  build.ps1, CKEtiquetas.spec (PyInstaller), CKEtiquetas.iss (Inno Setup), gerar_icone.py
referencias/                    DANFEs de exemplo e PDF modelo das etiquetas
tests/                          testes automatizados (pytest)
docs/TESTES.md                  resultado dos testes da versão 2.0 e pendências
```

### Banco de dados

- `notas`: uma linha por NF, identificada pela **chave de acesso** ou, sem chave, por
  **CNPJ do emitente + série + número**. Guarda número completo e impresso, série, emitente, chave,
  transportadora, placa, volumes, etiquetas, status, datas da primeira/última geração, da impressão
  solicitada e confirmada, número de gerações e o caminho do PDF.
- `eventos`: um registro por acontecimento (PDF gerado, reimpressão, impressão solicitada, impressão
  confirmada) com data, hora, etiquetas e PDF. Nada é apagado; gerar de novo não duplica a nota.

### Interface: por que CustomTkinter (e não PySide6)

A interface foi redesenhada (menu lateral, cards, tabelas, ícones Segoe Fluent, notificações) mantendo o
CustomTkinter: atende ao visual desejado, preserva as telas e a lógica que já funcionavam e mantém o
programa pequeno (~40 MB contra ~150 MB+ com Qt). A lógica de negócio não depende da interface, o que
mantém uma migração futura possível.

### Testes

```powershell
python -m pytest -v
python tests\comparar_modelo.py     # sobreposição com o modelo -> saida_testes\sobreposicao_modelo_vs_gerado.png
```

---

## 7. Assinatura digital do executável

Computadores com **Controle Inteligente de Aplicativos / App Control** bloqueiam executáveis sem
assinatura digital, e o SmartScreen mostra um aviso. Para distribuir sem bloqueios, assine o
`CKEtiquetas.exe` e o instalador com um certificado de assinatura de código (ex.: `signtool sign /fd
SHA256 /tr http://timestamp.digicert.com /td SHA256 /a arquivo.exe`), antes e depois do Inno Setup.

## 8. Layout das etiquetas (inalterado)

As medidas foram extraídas do PDF modelo (`referencias/etiquetas_modelo.pdf`) e estão em
`ck_etiquetas/config.py`:

| Elemento | Fonte | Tamanho | Linha de base (a partir do topo da etiqueta) |
|---|---|---|---|
| Logotipo | imagem original | 106,3 × 99,1 pt em (77,15; 67,90) | — |
| "NF" | Cambria Bold | 65,03 pt | 129,80 pt |
| Número | Cambria Bold | 125,02 pt | 301,85 pt |
| Transportadora + volume | Cambria | 28 pt | 365,10 pt |
| Placa | Bookman Old Style | 16 pt | 388,37 pt |

Todos os textos são centralizados. A etiqueta inferior é a superior deslocada **exatamente 148,5 mm**.
Uma etiqueta por volume — `(01/02V)`, `(02/02V)`; acima de 99 volumes, `(001/120V)` —, 2 por folha, na
ordem das notas; com total ímpar, a metade inferior da última folha fica em branco. Se um texto não couber
na largura (margem de 10 mm), só aquela linha tem a fonte reduzida, com aviso.

### Regras de extração

| Campo | Origem na DANFE | Observações |
|---|---|---|
| NF | campo **Nº** (ex.: `007928`) | impresso sem zeros (`7928`); conferido com a chave de acesso |
| Transportadora | **Nome** em *Transportador/Volumes transportados* | abreviação pelo cadastro; nome desconhecido não é abreviado sem confirmação |
| Volumes | **Quantidade** em *Transportador/Volumes transportados* | não é a quantidade de itens |
| Placa | texto **"Placa XXX9X99"** em *Dados adicionais* | nunca a placa do veículo transportador; valida AAA9999 e AAA9A99 |
| Emitente | canhoto *"RECEBEMOS DE …"* e CNPJ da chave de acesso | usado na identificação de notas sem chave |
