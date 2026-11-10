; Instalador do CK Etiquetas (Inno Setup 6) — português do Brasil
;
; Compilar (depois do PyInstaller):
;   "%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe" empacotamento\CKEtiquetas.iss
; ou tudo de uma vez:
;   powershell -ExecutionPolicy Bypass -File empacotamento\build.ps1
;
; Resultado: dist\instalador\CK_Etiquetas_Setup_v2.0.exe
;
; DADOS DO USUÁRIO: o programa grava histórico (SQLite), configurações, abreviações e backups em
; %LOCALAPPDATA%\CKEtiquetas e os PDFs em Documentos\CK Etiquetas. Nenhuma dessas pastas pertence à
; instalação: atualizar ou desinstalar NÃO as apaga.

#define AppNome     "CK Etiquetas"
#define AppVersao   "2.0.0"
#define AppVersaoCurta "2.0"
#define AppEmpresa  "CK Autoshop"
#define AppExe      "CKEtiquetas.exe"
#define AppMutex    "CKEtiquetas_Executando"

[Setup]
; NUNCA altere o AppId: é ele que faz uma versão nova atualizar a instalação existente.
AppId={{EF13B547-5348-4391-A825-23D3D80FA619}
AppName={#AppNome}
AppVersion={#AppVersao}
AppVerName={#AppNome} {#AppVersaoCurta}
AppPublisher={#AppEmpresa}
AppCopyright={#AppEmpresa}
VersionInfoVersion={#AppVersao}
VersionInfoCompany={#AppEmpresa}
VersionInfoDescription=Instalador do {#AppNome}
VersionInfoProductName={#AppNome}
; Sem administrador: instala em %LOCALAPPDATA%\Programs. Com administrador (escolha no início):
; instala em Arquivos de Programas para todos os usuários.
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
DefaultDirName={autopf}\{#AppNome}
DefaultGroupName={#AppNome}
DisableProgramGroupPage=yes
UsePreviousAppDir=yes
OutputDir=..\dist\instalador
OutputBaseFilename=CK_Etiquetas_Setup_v{#AppVersaoCurta}
SetupIconFile=..\assets\icone.ico
UninstallDisplayIcon={app}\{#AppExe}
UninstallDisplayName={#AppNome}
WizardStyle=modern
Compression=lzma2/max
SolidCompression=yes
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0
; pede para fechar o programa se estiver aberto durante a instalação/atualização
AppMutex={#AppMutex}
CloseApplications=yes
RestartApplications=no

[Languages]
Name: "ptbr"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"

[Tasks]
Name: "atalhodesktop"; Description: "Criar atalho na Área de Trabalho"; GroupDescription: "Atalhos:"

[InstallDelete]
; arquivos de versões anteriores do programa (os dados do usuário NÃO ficam aqui)
Type: filesandordirs; Name: "{app}\_internal"
Type: files; Name: "{app}\CK Etiquetas.exe"

[Files]
Source: "..\dist\CKEtiquetas\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#AppNome}"; Filename: "{app}\{#AppExe}"; IconFilename: "{app}\{#AppExe}"; \
  AppUserModelID: "CKAutoshop.CKEtiquetas"; Comment: "Gerador de etiquetas de expedição"
Name: "{group}\Desinstalar {#AppNome}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#AppNome}"; Filename: "{app}\{#AppExe}"; IconFilename: "{app}\{#AppExe}"; \
  AppUserModelID: "CKAutoshop.CKEtiquetas"; Tasks: atalhodesktop

[Run]
Filename: "{app}\{#AppExe}"; Description: "Abrir o {#AppNome}"; Flags: nowait postinstall skipifsilent

[Messages]
ptbr.FinishedLabel=O [name] foi instalado.%n%nO histórico, as configurações e os PDFs ficam guardados fora da pasta do programa e são mantidos nas próximas atualizações.

[UninstallDelete]
; Apenas arquivos do programa. %LOCALAPPDATA%\CKEtiquetas (histórico e backups) é preservado de propósito.
Type: dirifempty; Name: "{app}"
