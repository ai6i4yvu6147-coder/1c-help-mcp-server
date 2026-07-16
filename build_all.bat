@echo off
echo Building 1C Help MCP Server...

call venv\Scripts\activate.bat
if errorlevel 1 (
    echo ERROR: venv not found. Create it and run: pip install -r requirements.txt
    exit /b 1
)

echo.
echo Resolving 1c-metadata-schema...
set "METADATA_SCHEMA="
if exist "C:\repo\1c-metadata-schema\pyproject.toml" set "METADATA_SCHEMA=C:\repo\1c-metadata-schema"
if not defined METADATA_SCHEMA if exist "C:\projects\1c-metadata-schema\pyproject.toml" set "METADATA_SCHEMA=C:\projects\1c-metadata-schema"
if not defined METADATA_SCHEMA (
    echo ERROR: 1c-metadata-schema not found. Checked:
    echo   C:\repo\1c-metadata-schema
    echo   C:\projects\1c-metadata-schema
    exit /b 1
)
echo Using: %METADATA_SCHEMA%
pip install -e "%METADATA_SCHEMA%"
if errorlevel 1 (
    echo ERROR: pip install -e failed for %METADATA_SCHEMA%
    exit /b 1
)

echo.
echo [1/3] Building Admin Tool...
pyinstaller --onedir --windowed --name "1C-Help-Admin" --noconfirm ^
    --hidden-import=sqlite3 ^
    --hidden-import=json ^
    --add-data "admin_tool;admin_tool" ^
    --add-data "shared;shared" ^
    admin_tool/gui.py

echo.
echo [2/3] Building MCP Server...
pyinstaller --onedir --name "1c-help-server" --noconfirm ^
    --hidden-import=sqlite3 ^
    --hidden-import=json ^
    --hidden-import=asyncio ^
    --hidden-import=onec_metadata_schema ^
    --hidden-import=onec_metadata_schema.builder ^
    --collect-submodules onec_metadata_schema ^
    --add-data "server;server" ^
    --add-data "shared;shared" ^
    server/server.py

echo.
echo [3/3] Building Admin Hub CLI...
pyinstaller --onefile --name "1c-help-cli" --noconfirm ^
    --hidden-import=sqlite3 ^
    --hidden-import=json ^
    --add-data "shared;shared" ^
    admin_tool/cli.py

echo.
echo Creating 1c_help_mcp_server_Portable in parent folder...
set "PORTABLE=%~dp0..\1c_help_mcp_server_Portable"
if exist "%PORTABLE%" rmdir /s /q "%PORTABLE%"
mkdir "%PORTABLE%"
mkdir "%PORTABLE%\databases"
mkdir "%PORTABLE%\Tools"
mkdir "%PORTABLE%\logs"

echo Copying Admin...
xcopy /E /I /Y dist\1C-Help-Admin "%PORTABLE%\Admin"

echo Copying Server...
xcopy /E /I /Y dist\1c-help-server "%PORTABLE%\Server"

echo Copying Admin Hub CLI...
copy /Y dist\1c-help-cli.exe "%PORTABLE%\Tools\1c-help-cli.exe"

echo Copying module manifest...
copy /Y module.manifest.example.json "%PORTABLE%\module.manifest.json"

echo Creating launchers...
echo @echo off > "%PORTABLE%\Admin.bat"
echo start "" "%%~dp0Admin\1C-Help-Admin.exe" >> "%PORTABLE%\Admin.bat"

echo @echo off > "%PORTABLE%\Server.bat"
echo "%%~dp0Server\1c-help-server.exe" >> "%PORTABLE%\Server.bat"

echo Creating config.json...
echo {"databases_dir": "..\\databases", "default_version": null} > "%PORTABLE%\Server\config.json"
echo {"databases_dir": "..\\databases", "default_version": null} > "%PORTABLE%\Admin\config.json"

echo.
echo Done. Portable: %PORTABLE%
echo Build completed.
