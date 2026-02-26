@echo off
echo CVRP Optimizer - Стартиране...
echo.

REM Проверяваме дали има входен файл
if exist "data\input.xlsx" (
    echo Намерен входен файл: data\input.xlsx
    CVRP_Optimizer.exe data\input.xlsx
) else (
    echo ВАЖНО: Не е намерен входен файл в data\input.xlsx
    echo Моля, поставете входния файл в директорията data\input.xlsx
    echo или директно в текущата директория като input.xlsx
    echo.
    echo Програмата ще се опита да стартира с наличните файлове...
    CVRP_Optimizer.exe
)

REM Програмата сама ще пита за повторно стартиране
