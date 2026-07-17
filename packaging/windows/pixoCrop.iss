#define AppName GetEnv("PIXO_APP_NAME")
#if AppName == ""
  #define AppName "pixoCrop"
#endif

#define AppVersion GetEnv("PIXO_APP_VERSION")
#if AppVersion == ""
  #define AppVersion "0.1.0"
#endif

#define SourceDir GetEnv("PIXO_SOURCE_DIR")
#if SourceDir == ""
  #define SourceDir "..\..\dist\pixoCrop"
#endif

#define OutputDir GetEnv("PIXO_OUTPUT_DIR")
#if OutputDir == ""
  #define OutputDir "..\..\release"
#endif

#define RootDir GetEnv("PIXO_ROOT_DIR")
#if RootDir == ""
  #define RootDir "..\.."
#endif

#define WizardImageFile GetEnv("PIXO_WIZARD_IMAGE")
#if WizardImageFile == ""
  #define WizardImageFile "..\..\build\packaging\windows-wizard.bmp"
#endif

#define WizardSmallImageFile GetEnv("PIXO_WIZARD_SMALL_IMAGE")
#if WizardSmallImageFile == ""
  #define WizardSmallImageFile "..\..\build\packaging\windows-small.bmp"
#endif

[Setup]
AppId={{7D1E0915-8970-4F94-9B0D-43D5B7416152}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher=PixoGlace
AppPublisherURL=https://github.com/PixoGlace/pixoCrop
AppSupportURL=https://github.com/PixoGlace/pixoCrop/issues
AppUpdatesURL=https://github.com/PixoGlace/pixoCrop/releases
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
LicenseFile={#RootDir}\LICENSE
OutputDir={#OutputDir}
OutputBaseFilename={#AppName}-windows-x64-setup
SetupIconFile={#RootDir}\assets\pixoCrop.ico
WizardImageFile={#WizardImageFile}
WizardSmallImageFile={#WizardSmallImageFile}
WizardImageStretch=no
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
UninstallDisplayIcon={app}\{#AppName}.exe

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "french"; MessagesFile: "compiler:Languages\French.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "{#SourceDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppName}.exe"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppName}.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\{#AppName}.exe"; Description: "{cm:LaunchProgram,{#StringChange(AppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent
