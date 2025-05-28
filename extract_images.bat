@echo off
REM PDF Image Extraction Script - LensCRL
REM Compatible with Windows
REM Version: 1.0

setlocal enabledelayedexpansion

REM Configuration des couleurs (si supportées)
for /f %%A in ('"prompt $H &echo on &for %%B in (1) do rem"') do set BS=%%A

REM Variables par défaut
set "PDF_FILE="
set "OUTPUT_DIR="
set "MANUAL_NAME="
set "GENERATE_REPORT=false"
set "SCRIPT_DIR=%~dp0"
set "EXTRACTOR_SCRIPT=%SCRIPT_DIR%lenscrl.py"

REM Parsing des arguments
:parse_args
if "%~1"=="" goto validate_args
if /i "%~1"=="-p" (
    set "PDF_FILE=%~2"
    shift
    shift
    goto parse_args
)
if /i "%~1"=="--pdf" (
    set "PDF_FILE=%~2"
    shift
    shift
    goto parse_args
)
if /i "%~1"=="-o" (
    set "OUTPUT_DIR=%~2"
    shift
    shift
    goto parse_args
)
if /i "%~1"=="--output" (
    set "OUTPUT_DIR=%~2"
    shift
    shift
    goto parse_args
)
if /i "%~1"=="-m" (
    set "MANUAL_NAME=%~2"
    shift
    shift
    goto parse_args
)
if /i "%~1"=="--manual" (
    set "MANUAL_NAME=%~2"
    shift
    shift
    goto parse_args
)
if /i "%~1"=="-r" (
    set "GENERATE_REPORT=true"
    shift
    goto parse_args
)
if /i "%~1"=="--report" (
    set "GENERATE_REPORT=true"
    shift
    goto parse_args
)
if /i "%~1"=="-h" goto show_help
if /i "%~1"=="--help" goto show_help

echo [91mError: Unknown option '%~1'[0m
goto show_help

:show_help
echo.
echo ================================================
echo LENSCRL v1.0 - PDF IMAGE EXTRACTOR
echo ================================================
echo.
echo Usage: %~nx0 [OPTIONS]
echo.
echo Options:
echo   -p, --pdf FILE        Source PDF file (required)
echo   -o, --output DIR      Output directory (required)
echo   -m, --manual NAME     Manual name (optional)
echo   -r, --report          Generate report
echo   -h, --help            Show this help
echo.
echo Examples:
echo   %~nx0 -p "document.pdf" -o "./images" -r
echo   %~nx0 --pdf "manual.pdf" --output "./output" --manual "DOC01"
echo.
echo Nomenclature:
echo   * CRL-[MANUALNAME]-[SECTION#].{ext}          (1 image)
echo   * CRL-[MANUALNAME]-[SECTION#] n_[POS].{ext}  (multiple images)
echo.
exit /b 0

:validate_args
if "%PDF_FILE%"=="" (
    echo [91mError: Source PDF file is required (-p/--pdf)[0m
    goto show_help
)

if "%OUTPUT_DIR%"=="" (
    echo [91mError: Output directory is required (-o/--output)[0m
    goto show_help
)

REM Si aucun argument, utiliser le mode interactif
if "%PDF_FILE%"=="" if "%OUTPUT_DIR%"=="" goto interactive_mode

goto start_extraction

:interactive_mode
echo.
echo ================================================
echo LENSCRL v1.0 - PDF IMAGE EXTRACTOR
echo ================================================
echo.

REM Demander le fichier PDF source
:ask_pdf
echo.
set /p "PDF_FILE=Path to PDF file: "
if "!PDF_FILE!"=="" goto ask_pdf

REM Supprimer les guillemets
set "PDF_FILE=!PDF_FILE:"=!"

if not exist "!PDF_FILE!" (
    echo [91mError: The specified PDF file does not exist.[0m
    echo Path: !PDF_FILE!
    goto ask_pdf
)

echo [92mPDF file: !PDF_FILE![0m

REM Demander le répertoire de sortie
echo.
set /p "OUTPUT_DIR=Output directory (default: .\images): "
if "!OUTPUT_DIR!"=="" set "OUTPUT_DIR=.\images"

echo [92mOutput directory: !OUTPUT_DIR![0m

REM Demander le nom du manuel (optionnel)
echo.
set /p "MANUAL_NAME=Manual name (optional): "

REM Demander si un rapport doit être généré
echo.
set /p "REPORT_CHOICE=Generate report? (y/N): "
if /i "!REPORT_CHOICE!"=="y" set "GENERATE_REPORT=true"

:start_extraction
echo.
echo ================================================
echo ENVIRONMENT CHECK
echo ================================================

REM Vérifier que le fichier PDF existe
if not exist "%PDF_FILE%" (
    echo [91mError: PDF file '%PDF_FILE%' does not exist[0m
    exit /b 1
)

REM Vérifier que le script Python existe
if not exist "%EXTRACTOR_SCRIPT%" (
    echo [91mError: Extractor script not found: %EXTRACTOR_SCRIPT%[0m
    exit /b 1
)

REM Détecter Python
set "PYTHON_CMD="

python --version >nul 2>&1
if %errorlevel%==0 (
    for /f "tokens=2" %%v in ('python --version 2^>^&1') do (
        for /f "tokens=1 delims=." %%a in ("%%v") do (
            if %%a geq 3 set "PYTHON_CMD=python"
        )
    )
)

if "%PYTHON_CMD%"=="" (
    python3 --version >nul 2>&1
    if !errorlevel!==0 set "PYTHON_CMD=python3"
)

if "%PYTHON_CMD%"=="" (
    py --version >nul 2>&1
    if !errorlevel!==0 set "PYTHON_CMD=py"
)

if "%PYTHON_CMD%"=="" (
    echo [91mError: Python 3 is not installed or accessible[0m
    echo.
    echo Install Python 3 from: https://www.python.org/downloads/
    echo Or use Microsoft Store: python3
    pause
    exit /b 1
)

for /f "tokens=*" %%v in ('%PYTHON_CMD% --version 2^>^&1') do echo [92mPython found: %%v[0m

REM Vérifier PyMuPDF
echo.
echo [94mChecking PyMuPDF...[0m
%PYTHON_CMD% -c "import fitz" >nul 2>&1
if %errorlevel% neq 0 (
    echo [93mPyMuPDF is not installed[0m
    echo [94mInstalling PyMuPDF...[0m
    
    %PYTHON_CMD% -m pip install PyMuPDF
    if !errorlevel! neq 0 (
        echo [91mFailed to install PyMuPDF[0m
        echo Try manually:
        echo   %PYTHON_CMD% -m pip install --user PyMuPDF
        pause
        exit /b 1
    )
    
    echo [92mPyMuPDF installed successfully[0m
) else (
    echo [92mPyMuPDF is available[0m
)

REM Construction de la commande
echo.
echo [94mPreparing extraction...[0m

set "CMD_ARGS=--pdf "%PDF_FILE%" --output "%OUTPUT_DIR%""

if not "%MANUAL_NAME%"=="" (
    set "CMD_ARGS=!CMD_ARGS! --manual "%MANUAL_NAME%""
)

if "%GENERATE_REPORT%"=="true" (
    set "CMD_ARGS=!CMD_ARGS! --report"
)

REM Affichage des informations
echo.
echo ================================================
echo STARTING EXTRACTION
echo ================================================
echo [94mPDF file: %PDF_FILE%[0m
echo [94mOutput directory: %OUTPUT_DIR%[0m
if not "%MANUAL_NAME%"=="" echo [94mManual name: %MANUAL_NAME%[0m
if "%GENERATE_REPORT%"=="true" (
    echo [94mReport: Yes[0m
) else (
    echo [94mReport: No[0m
)
echo.

REM Exécution de l'extraction
echo [94mRunning LensCRL...[0m
echo.

%PYTHON_CMD% "%EXTRACTOR_SCRIPT%" %CMD_ARGS%

if %errorlevel%==0 (
    echo.
    echo [92mExtraction completed![0m
    echo [94mImages have been saved to: %OUTPUT_DIR%[0m
    
    if "%GENERATE_REPORT%"=="true" (
        set "REPORT_FILE=%OUTPUT_DIR%\lenscrl_report.txt"
        if exist "!REPORT_FILE!" (
            echo [94mReport available: !REPORT_FILE![0m
        )
    )
    
    REM Compter les fichiers extraits
    if exist "%OUTPUT_DIR%" (
        set "NB_IMAGES=0"
        for %%f in ("%OUTPUT_DIR%\CRL-*.png" "%OUTPUT_DIR%\CRL-*.jpg" "%OUTPUT_DIR%\CRL-*.jpeg") do (
            if exist "%%f" set /a NB_IMAGES+=1
        )
        echo [92m!NB_IMAGES! image(s) extracted with CRL nomenclature[0m
    )
    
    echo.
    echo [92m🎉 Done![0m
    
    REM Demander si on veut ouvrir le répertoire
    echo.
    set /p "OPEN_FOLDER=Open output directory? (y/N): "
    if /i "!OPEN_FOLDER!"=="y" (
        explorer "%OUTPUT_DIR%"
    )
    
) else (
    echo.
    echo [91mExtraction failed[0m
    pause
    exit /b 1
)

echo.
pause
exit /b 0 