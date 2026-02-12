@echo off
setlocal

call "%~dp0.buildtools.bat"

set "CMAKE_BINARY_DIR=cmake-build-release-x64"
if NOT "%1"=="" set "CMAKE_BINARY_DIR=%1"
set "DUMPBIN_DIR=%CMAKE_BINARY_DIR:build=dump%"

pushd %~dp0
mkdir %DUMPBIN_DIR%

pushd %DUMPBIN_DIR%

    dumpbin /headers ..\%CMAKE_BINARY_DIR%\lfs.dll > lfs.dll.headers.txt
    dumpbin /exports ..\%CMAKE_BINARY_DIR%\lfs.dll > lfs.dll.exports.txt
    dumpbin /dependents ..\%CMAKE_BINARY_DIR%\lfs.dll > lfs.dll.dependents.txt
    dumpbin /imports ..\%CMAKE_BINARY_DIR%\lfs.dll > lfs.dll.imports.txt

popd
popd

endlocal
