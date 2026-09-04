[Setup]
AppName=Mió Baixador do Youtube
AppVersion=1.0
AppPublisher=Mió Baixador
DefaultDirName={localappdata}\MioBaixador
DefaultGroupName=Mió Baixador do Youtube
OutputDir=Output
OutputBaseFilename=Setup_MioBaixador
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
SetupIconFile=icone.ico
UninstallDisplayName=Mió Baixador do Youtube

[Languages]
Name: "pt"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"

[Tasks]
Name: "desktopicon"; Description: "Criar ícone na Área de Trabalho"; GroupDescription: "Atalhos:"

[Files]
Source: "dist\MioBaixador\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\Mió Baixador do Youtube"; Filename: "{app}\MioBaixador.exe"
Name: "{userdesktop}\Mió Baixador do Youtube"; Filename: "{app}\MioBaixador.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\MioBaixador.exe"; Description: "Abrir Mió Baixador agora"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{app}"
