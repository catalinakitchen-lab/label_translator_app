@echo off
title Aplikasi Pemindai & Penerjemah Label Kemasan
echo ========================================================
echo    APLIKASI PEMINDAI & PENERJEMAH LABEL KEMASAN
echo           Image to PDF & Translate EN
echo ========================================================
echo.
echo Sedang membuka aplikasi di browser Anda...
echo.
cd /d "%~dp0"
python -m streamlit run app.py
pause
