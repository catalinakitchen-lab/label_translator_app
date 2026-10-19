@echo off
title Instalasi Dependensi Aplikasi Label Kemasan
echo ========================================================
echo    MENGINSTAL DEPENDENSI APLIKASI LABEL KEMASAN
echo ========================================================
echo.
echo Sedang menginstal library Python yang diperlukan...
echo.
cd /d "%~dp0"
python -m pip install -r requirements.txt
echo.
echo ========================================================
echo [OK] Instalasi selesai! 
echo Silakan klik ganda 'Jalankan_Aplikasi.bat' untuk memulai.
echo ========================================================
pause
