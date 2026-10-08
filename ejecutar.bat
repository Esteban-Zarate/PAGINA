@echo off
chcp 65001 >nul
title Calculadora Solar ☀
streamlit run solar_app.py --server.port 8501
