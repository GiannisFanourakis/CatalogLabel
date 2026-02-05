#define MyAppName "CatalogLabel"
#define MyAppVersion "1.0.1"
#define MyAppPublisher "Ioannis Fanourakis"
#define MyAppExeName "CatalogLabel.exe"
#define MyAppURL "https://github.com/GiannisFanourakis"

[Setup]
; IMPORTANT: Keep AppId constant forever (upgrade/uninstall stability).
AppId={{ioannisfanourakis.CatalogLabel}}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}

AppComments=Tree-first label hierarchy builder with fast entry (Rules Mode + Free Typing) and print-ready PDF export.

; Per-user install (no admin prompts; avoids restricted paths)
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
DefaultDirName={userpf}\{#MyAppName}
DisableProgramGroupPage=yes
UsePreviousAppDir=yes

OutputDir=Output
OutputBaseFilename=CatalogLabel_{#MyAppVersion}_Setup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern

; Icons
SetupIconFile=..\src\resources\icons\CatalogLabel.ico
UninstallDisplayIcon={app}\{#MyAppExeName}

; Branding images (relative to installer folder)
WizardImageFile=branding\wizard_left.bmp
WizardSmallImageFile=branding\wizard_small.bmp
WizardImageStretch=no

; Windows metadata
VersionInfoVersion={#MyAppVersion}
VersionInfoCompany={#MyAppPublisher}
VersionInfoDescription={#MyAppName}
VersionInfoTextVersion={#MyAppVersion}
AppCopyright=Copyright (C) {#MyAppPublisher}

ArchitecturesInstallIn64BitMode=x64

; Setup pages
LicenseFile=..\LICENSE.txt
InfoBeforeFile=FEATURES.txt

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Messages]
WelcomeLabel1=Welcome to the {#MyAppName} setup wizard
WelcomeLabel2=This will install {#MyAppName} {#MyAppVersion} on your computer.%n%n{#MyAppName} helps you build structured label hierarchies and export print-ready PDFs.
FinishedLabel=Setup has finished installing {#MyAppName} on your computer.

[Tasks]
Name: "desktopicon"; Description: "Create a &Desktop icon"; GroupDescription: "Additional icons:"; Flags: unchecked

[Files]
; Frozen build (ship EVERYTHING from dist)
Source: "..\dist\CatalogLabel\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

; OSS docs
Source: "..\LICENSE.txt"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\README.md"; DestDir: "{app}"; DestName: "README.md"; Flags: ignoreversion
Source: "..\THIRD_PARTY_NOTICES.txt"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{userprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
; Use userdesktop (NOT commondesktop) to avoid 0x80070005 on machines without rights to Public Desktop
Name: "{userdesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch {#MyAppName}"; Flags: nowait postinstall skipifsilent
