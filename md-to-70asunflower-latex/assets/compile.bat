@echo off
REM ============================================================
REM  Windows / MiKTeX compile helper.
REM  The table of contents needs TWO passes:
REM    pass 1 writes the .toc file, pass 2 renders the entries.
REM  A single pass => blank TOC (normal LaTeX behaviour).
REM  NOTE: MiKTeX Portable is usually NOT on PATH. Run this from
REM  the MiKTeX Portable console, or use TeXworks (XeLaTeX, typeset x2).
REM ============================================================
setlocal
set MAIN=
for %%f in (*.tex) do if not defined MAIN set MAIN=%%f
if "%MAIN%"=="" ( echo No .tex file found. & pause & exit /b 1 )
echo [compile] main file: %MAIN%
where texify >nul 2>nul
if %errorlevel%==0 (
  echo [compile] using texify (auto multi-pass, XeLaTeX)...
  texify --pdf --engine=xetex "%MAIN%"
) else (
  echo [compile] texify not found, running xelatex twice...
  xelatex -interaction=nonstopmode "%MAIN%"
  xelatex -interaction=nonstopmode "%MAIN%"
)
echo [compile] done. Verify the TOC page is no longer blank.
pause
