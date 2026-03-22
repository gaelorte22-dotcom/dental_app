; DentalApp - Instalador
; Para compilar localmente: abrir con Inno Setup y presionar F9

[Setup]
AppId={{A1B2C3D4-E5F6-7890-ABCD-EF1234567890}
AppName=DentalApp
AppVersion=1.3.0.1
AppVerName=DentalApp v1.3.0.1
AppPublisher=DentalApp
AppPublisherURL=https://github.com/gaelorte22-dotcom/dental_app
AppSupportURL=https://github.com/gaelorte22-dotcom/dental_app
AppUpdatesURL=https://github.com/gaelorte22-dotcom/dental_app
DefaultDirName={autopf}\DentalApp
DefaultGroupName=DentalApp
DisableProgramGroupPage=yes
OutputDir=dist\installer
OutputBaseFilename=DentalApp_Setup_v1.3.0.1
SetupIconFile=diente.ico
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
WizardResizable=yes
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
MinVersion=10.0

[Languages]
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"

[Tasks]
Name: "desktopicon";   Description: "Crear icono en el Escritorio";    GroupDescription: "Iconos adicionales:"; Flags: checkedonce
Name: "startmenuicon"; Description: "Crear acceso en Menu de Inicio";  GroupDescription: "Iconos adicionales:"; Flags: checkedonce

[Files]
Source: "dist\DentalApp.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "diente.ico";         DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{autodesktop}\DentalApp";               Filename: "{app}\DentalApp.exe"; IconFilename: "{app}\diente.ico"; Tasks: desktopicon
Name: "{autostartmenu}\DentalApp\DentalApp";   Filename: "{app}\DentalApp.exe"; IconFilename: "{app}\diente.ico"; Tasks: startmenuicon
Name: "{autostartmenu}\DentalApp\Desinstalar"; Filename: "{uninstallexe}"

[Run]
Filename: "{app}\DentalApp.exe"; Description: "Abrir DentalApp ahora"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{app}\dental_clinic.db"
Type: filesandordirs; Name: "{app}\archivos_pacientes"
Type: filesandordirs; Name: "{app}\license.key"

[Code]
function InitializeSetup(): Boolean;
begin
  Result := True;
end;
