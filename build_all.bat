@echo off
echo Building 1C Help MCP Server...

call venv\Scripts\activate.bat
echo.
echo [1/2] Building Admin Tool...
pyinstaller --onedir --windowed --name "1C-Help-Admin" --noconfirm ^
    --hidden-import=sqlite3 ^
    --hidden-import=json ^
    --add-data "admin_tool;admin_tool" ^
    --add-data "shared;shared" ^
    admin_tool/gui.py

echo.
echo [2/2] Building MCP Server...
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
echo Creating 1c_help_mcp_server_Portable in parent folder...
set "PORTABLE=%~dp0..\1c_help_mcp_server_Portable"
if exist "%PORTABLE%" rmdir /s /q "%PORTABLE%"
mkdir "%PORTABLE%"
mkdir "%PORTABLE%\databases"

echo Copying Admin...
xcopy /E /I /Y dist\1C-Help-Admin "%PORTABLE%\Admin"

echo Copying Server...
xcopy /E /I /Y dist\1c-help-server "%PORTABLE%\Server"

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
