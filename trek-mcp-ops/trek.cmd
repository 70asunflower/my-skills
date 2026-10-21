@echo off
REM ==========================================================================
REM  TREK lifecycle launcher - resolves node.exe by itself.
REM    trek.cmd doctor    verify all paths and dependencies, change nothing
REM    trek.cmd status    what is currently running
REM    trek.cmd start     Docker + TREK + auth-proxy + end-to-end self-test
REM    trek.cmd stop      shut everything down and quit Docker Desktop
REM
REM  Why this wrapper: node is usually NOT on PATH on this machine. WorkBuddy
REM  ships its own Node under the user profile binaries dir. Hardcoding a version
REM  breaks on every WorkBuddy upgrade, so we discover it at runtime.
REM  NOTE: never put pipe, less-than, greater-than, ampersand, or parentheses
REM  inside a REM line or inside a parenthesized IF block - cmd parses them.
REM
REM  start runs HIDDEN by default - no black console window appears. Output goes
REM  to trek-start.log and trek-start.err next to this file. Use --show to run in
REM  a visible window if you want live progress on screen.
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
  echo [!] node.exe not found on PATH nor under the user profile binaries node versions dir
  exit /b 1
)

REM ---- start: hidden by default, no black window ----
if /i "%1"=="start" (
  if /i "%2"=="--show" (
    "%NODEEXE%" "%SELF%scripts\trek-control.mjs" start
    exit /b %errorlevel%
  )
  echo TREK starting in the background - no window will appear.
  echo   progress log : %SELF%trek-start.log
  echo   error log    : %SELF%trek-start.err
  echo   when ready   : trek.cmd status   - or: type %SELF%trek-start.log
  powershell -NoProfile -WindowStyle Hidden -Command "Start-Process -WindowStyle Hidden -FilePath '%NODEEXE%' -ArgumentList '%SELF%scripts\trek-control.mjs start' -RedirectStandardOutput '%SELF%trek-start.log' -RedirectStandardError '%SELF%trek-start.err'"
  exit /b 0
)

REM ---- everything else: run inline, visible, short-lived ----
"%NODEEXE%" "%SELF%scripts\trek-control.mjs" %*
