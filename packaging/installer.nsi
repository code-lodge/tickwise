; Tickwise NSIS installer for Windows.
;
; Build with:  makensis /DVERSION=1.0.0 packaging\installer.nsi
;
; Expects PyInstaller's dist\Tickwise\ folder to already be built.

!ifndef VERSION
  !define VERSION "1.0.0"
!endif

!define PRODUCT_NAME "Tickwise"
!define PRODUCT_PUBLISHER "code-lodge"
!define PRODUCT_WEB "https://tickwise.app"
!define PRODUCT_DIR_REGKEY "Software\Microsoft\Windows\CurrentVersion\App Paths\Tickwise.exe"
!define PRODUCT_UNINST_KEY "Software\Microsoft\Windows\CurrentVersion\Uninstall\${PRODUCT_NAME}"

SetCompressor /SOLID lzma
RequestExecutionLevel user

Name "${PRODUCT_NAME} ${VERSION}"
OutFile "..\dist\tickwise-setup-${VERSION}.exe"
InstallDir "$LOCALAPPDATA\Programs\Tickwise"
InstallDirRegKey HKCU "${PRODUCT_DIR_REGKEY}" ""
ShowInstDetails show
ShowUnInstDetails show
BrandingText "${PRODUCT_PUBLISHER}"

; ─── Modern UI ─────────────────────────────────────────────────────────
!include "MUI2.nsh"

!define MUI_ABORTWARNING
!define MUI_ICON "icons\tickwise.ico"
!define MUI_UNICON "icons\tickwise.ico"

!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!define MUI_FINISHPAGE_RUN "$INSTDIR\Tickwise.exe"
!insertmacro MUI_PAGE_FINISH

!insertmacro MUI_UNPAGE_WELCOME
!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES
!insertmacro MUI_UNPAGE_FINISH

!insertmacro MUI_LANGUAGE "English"

; ─── Sections ──────────────────────────────────────────────────────────
Section "Tickwise" SecMain
  SectionIn RO
  SetOutPath "$INSTDIR"
  File /r "..\dist\Tickwise\*.*"

  CreateDirectory "$SMPROGRAMS\Tickwise"
  CreateShortcut  "$SMPROGRAMS\Tickwise\Tickwise.lnk"   "$INSTDIR\Tickwise.exe"
  CreateShortcut  "$SMPROGRAMS\Tickwise\Uninstall.lnk"  "$INSTDIR\Uninstall.exe"

  WriteUninstaller "$INSTDIR\Uninstall.exe"

  WriteRegStr HKCU "${PRODUCT_DIR_REGKEY}" "" "$INSTDIR\Tickwise.exe"
  WriteRegStr HKCU "${PRODUCT_UNINST_KEY}" "DisplayName"     "${PRODUCT_NAME}"
  WriteRegStr HKCU "${PRODUCT_UNINST_KEY}" "DisplayVersion"  "${VERSION}"
  WriteRegStr HKCU "${PRODUCT_UNINST_KEY}" "Publisher"       "${PRODUCT_PUBLISHER}"
  WriteRegStr HKCU "${PRODUCT_UNINST_KEY}" "URLInfoAbout"    "${PRODUCT_WEB}"
  WriteRegStr HKCU "${PRODUCT_UNINST_KEY}" "DisplayIcon"     "$INSTDIR\Tickwise.exe"
  WriteRegStr HKCU "${PRODUCT_UNINST_KEY}" "UninstallString" "$INSTDIR\Uninstall.exe"
SectionEnd

Section "Start at login" SecAutostart
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Run" "Tickwise" "$INSTDIR\Tickwise.exe"
SectionEnd

; ─── Uninstaller ───────────────────────────────────────────────────────
Section "Uninstall"
  RMDir /r "$INSTDIR"
  Delete "$SMPROGRAMS\Tickwise\Tickwise.lnk"
  Delete "$SMPROGRAMS\Tickwise\Uninstall.lnk"
  RMDir  "$SMPROGRAMS\Tickwise"
  DeleteRegKey HKCU "${PRODUCT_UNINST_KEY}"
  DeleteRegValue HKCU "Software\Microsoft\Windows\CurrentVersion\Run" "Tickwise"
  DeleteRegValue HKCU "${PRODUCT_DIR_REGKEY}" ""
SectionEnd
