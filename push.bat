@echo off
cd /d "%~dp0"
git add .
git commit -m "обновление"
git push
echo.
echo Готово! Сайт обновится через ~1 минуту.
pause
