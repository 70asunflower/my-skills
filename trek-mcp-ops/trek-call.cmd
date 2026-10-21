@echo off
REM ==========================================================================
REM  TREK MCP tool caller - resolves node.exe by itself.
REM    trek-call.cmd --list                 list all 135 tools
REM    trek-call.cmd --list budget          list tools matching a keyword
REM    trek-call.cmd --schema create_trip   print a tool's exact input schema
REM    trek-call.cmd create_trip @args.json call a tool, arguments from a file
REM
REM  ALWAYS pass arguments via an @file.json. Inline JSON survives poorly through
REM  cmd.exe (double quotes get eaten); an @file has no quoting problems and also
REM  handles long or Chinese text safely.
REM  NOTE for maintainers: never put the characters pipe, less-than, greater-than
REM  or ampersand inside a REM line - cmd.exe still parses them as operators.
REM ==========================================================================
setlocal
set "SELF=%~dp0"
set "NODEEXE="
for /f "delims=" %%I in ('where node 2^>nul') do if not defined NODEEXE set "NODEEXE=%%I"
if not defined NODEEXE (
  for /f "delims=" %%V in ('dir /b /ad /o-n "%USERPROFILE%\.workbuddy\binaries\node\versions" 2^>nul') do (
    if not defined NODEEXE if exist "%USERPROFILE%\.workbuddy\binaries\node\versions\%%V\node.exe" (
      set "NODEEXE=%USERPROFILE%\.workbuddy\binaries\node\versions\%%V\node.exe"
    )
  )
)
if not defined NODEEXE (
  echo [!] node.exe not found on PATH nor under %USERPROFILE%\.workbuddy\binaries\node\versions
  exit /b 1
)
"%NODEEXE%" "%SELF%scripts\mcp-call.mjs" %*
