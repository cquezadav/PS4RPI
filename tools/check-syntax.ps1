# Checks the SYNTAX and TYPES of RPI/sandbird.c with the clang that comes with Visual Studio 2022.
# The real headers (OpenOrbis toolchain) are replaced by minimal stand-ins (tools/make_stubs.py), nothing is linked or run.
# This does NOT replace a build with the OpenOrbis toolchain and a test on the console.
#
#   powershell -File tools\check-syntax.ps1
#   (If script files are disabled on your PC, run the two commands below by hand in a terminal.
#    They were run that way for the first check, the result was 0 errors and the same 3 old warnings.)

$root  = Split-Path -Parent $PSScriptRoot
$stubs = Join-Path $env:TEMP 'rpi_stubs'
$vsdev = 'C:\Program Files\Microsoft Visual Studio\2022\Community\Common7\Tools\VsDevCmd.bat'

python -I (Join-Path $PSScriptRoot 'make_stubs.py') $stubs | Out-Null

$cmd = "`"$vsdev`" -arch=x64 -no_logo >nul 2>&1 && clang-cl /Zs /nologo /TC /W3 /clang:-Wall /clang:-Wextra " +
       "/clang:-Wno-unused-parameter /clang:-Wno-sign-compare /D_CRT_SECURE_NO_WARNINGS /D_CRT_NONSTDC_NO_DEPRECATE " +
       "/I `"$stubs`" /I `"$root\RPI`" `"$root\RPI\sandbird.c`" 2>&1"

$out = cmd /c $cmd
$errors = ($out | Select-String 'error:').Count
$out | Where-Object { $_ -match 'warning:|error:' }
"sandbird.c: $errors error(s), $(($out | Select-String 'warning:').Count) warning(s) (3 warnings were there before the changes)"
exit $(if ($errors) { 1 } else { 0 })
