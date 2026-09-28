; ============================================================================
;  QTTrigrs 安装包脚本（Inno Setup 6）
;
;  编译：
;      "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" installer\QTTrigrs.iss
;      或直接双击 installer\build_installer.cmd
;
;  产物：
;      dist\installer\QTTrigrs-1.0.0-setup.exe
;
;  前提：先用 build_nuitka.py 生成 dist\main.dist\（见 README 第 14 节）
; ============================================================================

#define MyAppName "QTTrigrs"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "QTTrigrs"
#define MyAppExeName "QTTrigrs.exe"
; 打包产物目录（相对本脚本所在目录）
#define MySourceDir "..\dist\main.dist"

[Setup]
; AppId 必须固定不变，升级/卸载才认得是同一个程序
AppId={{973CB952-E8C8-41F8-9865-CD3DA7D1A134}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
VersionInfoVersion={#MyAppVersion}
VersionInfoCompany={#MyAppPublisher}
VersionInfoDescription={#MyAppName} 安装程序

; 默认装到 Program Files\QTTrigrs；允许用户在向导里改成“仅为我安装”
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
AllowNoIcons=yes
DisableProgramGroupPage=yes
; dialog = 向导里可选“仅为我安装”；commandline = 支持 /CURRENTUSER /ALLUSERS 静默安装
PrivilegesRequiredOverridesAllowed=dialog commandline

; 许可/致谢页（安装前展示，含 USGS 官方署名）
LicenseFile=LICENSE.txt
DisableWelcomePage=no

; 只允许 64 位 Windows 10 及以上
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0

; 输出：dist\installer\QTTrigrs-1.0.0-setup.exe
OutputDir=..\dist\installer
OutputBaseFilename={#MyAppName}-{#MyAppVersion}-setup
SetupIconFile=..\resources\icons\app.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
UninstallDisplayName={#MyAppName} {#MyAppVersion}

; 体积：167 MB 的产物用 lzma2/max 压得最小
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
SetupLogging=yes

[Languages]
; 第一条是默认语言（简体中文）
Name: "chinesesimplified"; MessagesFile: "ChineseSimplified.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
; 整个打包目录原样安装到 {app}
Source: "{#MySourceDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#MyAppName}}"; Flags: nowait postinstall skipifsilent
