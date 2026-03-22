; =====================================================
;  DentalApp — Script de instalación (Inno Setup 6)
;  Para compilar: abrir con Inno Setup y presionar F9
; =====================================================

#define AppName      "DentalApp"
#define AppVersion 1.2.4
#define AppPublisher "DentalApp"
#define AppURL       "https://github.com/gaelorte22-dotcom/dental_app"
#define AppExeName   "DentalApp.exe"
#define AppICO       "diente.ico"

[Setup]
; Información básica
AppId={{A1B2C3D4-E5F6-7890-ABCD-EF1234567890}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} v{#AppVersion}
AppPublisher={#AppPublisher}
AppPublisherURL={#AppURL}
AppSupportURL={#AppURL}
AppUpdatesURL={#AppURL}

; Directorio de instalación
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes

; Archivos de salida
OutputDir=dist\installer
OutputBaseFilename=DentalApp_Setup_v{#AppVersion}
SetupIconFile={#AppICO}
Compression=lzma2/ultra64
SolidCompression=yes

; Apariencia
WizardStyle=modern
WizardResizable=yes

; Permisos — no requiere admin si no es necesario
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog

; Versión mínima de Windows (Windows 10)
MinVersion=10.0

[Languages]
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"

[Tasks]
Name: "desktopicon";    Description: "Crear icono en el Escritorio";     GroupDescription: "Iconos adicionales:"; Flags: checkedonce
Name: "startmenuicon";  Description: "Crear acceso en Menú de Inicio";   GroupDescription: "Iconos adicionales:"; Flags: checkedonce

[Files]
; Ejecutable principal
Source: "dist\DentalApp.exe"; DestDir: "{app}"; Flags: ignoreversion

; Ícono
Source: "diente.ico"; DestDir: "{app}"; Flags: ignoreversion

; Carpeta de archivos de pacientes (se crea vacía)
; Source: "archivos_pacientes\*"; DestDir: "{app}\archivos_pacientes"; Flags: ignoreversion recursesubdirs createallsubdirs; Check: DirExists(ExpandConstant('{src}\archivos_pacientes'))

[Icons]
; Acceso directo en el escritorio
Name: "{autodesktop}\{#AppName}";          Filename: "{app}\{#AppExeName}"; IconFilename: "{app}\diente.ico"; Tasks: desktopicon

; Acceso directo en menú de inicio
Name: "{autostartmenu}\{#AppName}\{#AppName}";    Filename: "{app}\{#AppExeName}"; IconFilename: "{app}\diente.ico"; Tasks: startmenuicon
Name: "{autostartmenu}\{#AppName}\Desinstalar";   Filename: "{uninstallexe}"

[Run]
; Opción de ejecutar al terminar la instalación
Filename: "{app}\{#AppExeName}"; Description: "Abrir {#AppName} ahora"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
; Limpiar base de datos y archivos al desinstalar
Type: filesandordirs; Name: "{app}\dental_clinic.db"
Type: filesandordirs; Name: "{app}\archivos_pacientes"
Type: filesandordirs; Name: "{app}\license.key"

[Code]
// Verificar si hay una versión anterior instalada
function InitializeSetup(): Boolean;
begin
  Result := True;
end;

// Mensaje de bienvenida personalizado
function GetWelcomeMessage(Param: String): String;
begin
  Result := 'Bienvenido al instalador de DentalApp v{#AppVersion}.' + #13#10 + #13#10 +
            'Este programa instalará DentalApp en tu computadora.' + #13#10 + #13#10 +
            'Se recomienda cerrar todas las aplicaciones antes de continuar.';
end;
