#define MyAppName "LabelForge"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "Ioannis Fanourakis"
#define MyAppExeName "LabelForge.exe"
#define MyAppURL "https://github.com/GiannisFanourakis"

[Setup]
AppId={{ioannisfanourakis.labelforge}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}

AppComments=Tree-first label hierarchy builder with fast entry (Rules Mode + Free Typing) and print-ready PDF export.

DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes

OutputDir=Output
OutputBaseFilename=LabelForge_{#MyAppVersion}_Setup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern

; Icons
SetupIconFile=..\src\resources\icons\labelforge.ico
UninstallDisplayIcon={app}\{#MyAppExeName}

; Branding images
WizardImageFile=..\installer\branding\wizard_left.bmp
WizardSmallImageFile=..\installer\branding\wizard_small.bmp
WizardImageStretch=no

; Windows metadata
VersionInfoVersion={#MyAppVersion}
VersionInfoCompany={#MyAppPublisher}
VersionInfoDescription={#MyAppName}
VersionInfoTextVersion={#MyAppVersion}
AppCopyright=Copyright (C) {#MyAppPublisher}

ArchitecturesInstallIn64BitMode=x64
PrivilegesRequired=lowest

; Setup pages
LicenseFile=..\LICENSE.txt
InfoBeforeFile=..\installer\FEATURES.txt

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Messages]
WelcomeLabel1=Welcome to the {#MyAppName} setup wizard
WelcomeLabel2=This will install {#MyAppName} {#MyAppVersion} on your computer.%n%n{#MyAppName} helps you build structured label hierarchies and export print-ready PDFs.
FinishedLabel=Setup has finished installing {#MyAppName} on your computer.

[Tasks]
Name: "desktopicon"; Description: "Create a &Desktop icon"; GroupDescription: "Additional icons:"; Flags: unchecked

[Files]
; Frozen build
Source: "..\dist\LabelForge\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

; OSS docs
Source: "..\LICENSE.txt"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\README.md"; DestDir: "{app}"; DestName: "README.md"; Flags: ignoreversion
Source: "..\THIRD_PARTY_NOTICES.txt"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{commondesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch {#MyAppName}"; Flags: nowait postinstall skipifsilent
