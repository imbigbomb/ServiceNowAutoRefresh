@echo off
title 正在安装依赖库
echo ==================================================
echo   正在检查并安装 Python 依赖库，请稍候...
echo ==================================================
echo.

:: 升级 pip
python -m pip install --upgrade pip

:: 根据 requirements.txt 安装
pip install -r requirements.txt

echo.
echo ==================================================
echo                    安装完成
echo ==================================================
pause
