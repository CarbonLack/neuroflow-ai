#define MyAppName "NeuroEphys AI"
#ifndef MyAppVersion
  #error MyAppVersion must be supplied by scripts/build_release.ps1
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
OutputDir=..\release\v{#MyAppVersion}
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
#ifndef CoreAppDir
  #error CoreAppDir must point to the validated Standard application directory
#endif
#ifndef GpuOverlayDir
  #error GpuOverlayDir must point to the generated Full-minus-Standard overlay
#endif
; The Full installer exposes a genuine component choice. The shared core
; always installs the independently validated Standard application. The GPU
; component overlays every added or changed file from the validated Full app.
; This avoids an incomplete torch namespace when the user chooses Core only.
Source: "{#CoreAppDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs; Components: core
Source: "{#GpuOverlayDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs; Components: gpu
#else
#ifndef CoreAppDir
  #error CoreAppDir must point to the validated Standard application directory
#endif
Source: "{#CoreAppDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
#endif

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"
Name: "{group}\卸载 {#MyAppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "启动 {#MyAppName} / Launch {#MyAppName}"; Flags: nowait postinstall skipifsilent
