#define MyAppName "NeuroEphys AI"
#ifndef MyAppVersion
  #define MyAppVersion "1.2.3"
#endif
#define MyAppPublisher "NeuroEphys AI team"
#define MyAppURL "https://github.com/CarbonLack/neuroflow-ai"
#define MyAppExeName "NeuroEphysAI.exe"

[Setup]
AppId={{F3B46A92-A8DD-4D4E-8F65-6BBEEC64A6CE}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}/issues
AppUpdatesURL={#MyAppURL}/releases
DefaultDirName={localappdata}\Programs\NeuroEphysAI
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0
OutputDir=..\release\v1.2.3
OutputBaseFilename=NeuroEphysAI-Setup-{#MyAppVersion}
SetupIconFile=..\assets\brand\neuroephys-ai.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
UninstallDisplayName={#MyAppName} {#MyAppVersion}
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
SetupLogging=yes
CloseApplications=yes
InfoBeforeFile=..\README_FIRST.md
VersionInfoVersion={#MyAppVersion}
VersionInfoCompany={#MyAppPublisher}
VersionInfoDescription={#MyAppName} installer
VersionInfoProductName={#MyAppName}
VersionInfoProductVersion={#MyAppVersion}

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

#ifdef FullBuild
[Types]
Name: "full"; Description: "推荐：完整 GPU/Kilosort 安装 / Recommended Full GPU/Kilosort"
Name: "compact"; Description: "仅通用核心（不安装 GPU/Kilosort） / Core only"
Name: "custom"; Description: "自定义 / Custom"; Flags: iscustom

[Components]
Name: "core"; Description: "NeuroEphys AI 通用分析核心（必选） / Core application (required)"; Types: full compact custom; Flags: fixed
Name: "gpu"; Description: "Kilosort 4 + PyTorch/CUDA GPU 后端（推荐，约 4 GB 安装空间） / Full GPU backend"; Types: full
#endif

[Tasks]
Name: "desktopicon"; Description: "创建桌面快捷方式 / Create a desktop shortcut"; GroupDescription: "快捷方式 / Shortcuts"; Flags: checkedonce

[Files]
#ifdef FullBuild
; The Full installer exposes a genuine component choice. The shared core is
; always installed; the large Torch and Kilosort trees are optional on disk.
; The first and default setup type is the tested Full configuration.
Source: "..\dist\NeuroEphysAI\*"; DestDir: "{app}"; Excludes: "_internal\torch\*,_internal\torch-*.dist-info\*,_internal\kilosort\*,_internal\kilosort-*.dist-info\*"; Flags: ignoreversion recursesubdirs createallsubdirs; Components: core
Source: "..\dist\NeuroEphysAI\_internal\torch\*"; DestDir: "{app}\_internal\torch"; Flags: ignoreversion recursesubdirs createallsubdirs; Components: gpu
Source: "..\dist\NeuroEphysAI\_internal\torch-2.11.0+cu128.dist-info\*"; DestDir: "{app}\_internal\torch-2.11.0+cu128.dist-info"; Flags: ignoreversion recursesubdirs createallsubdirs skipifsourcedoesntexist; Components: gpu
Source: "..\dist\NeuroEphysAI\_internal\kilosort\*"; DestDir: "{app}\_internal\kilosort"; Flags: ignoreversion recursesubdirs createallsubdirs; Components: gpu
Source: "..\dist\NeuroEphysAI\_internal\kilosort-4.1.7.dist-info\*"; DestDir: "{app}\_internal\kilosort-4.1.7.dist-info"; Flags: ignoreversion recursesubdirs createallsubdirs skipifsourcedoesntexist; Components: gpu
#else
Source: "..\dist\NeuroEphysAI\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
#endif

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"
Name: "{group}\卸载 {#MyAppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "启动 {#MyAppName} / Launch {#MyAppName}"; Flags: nowait postinstall skipifsilent
