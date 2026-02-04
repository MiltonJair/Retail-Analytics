@echo off
REM Ejecuta el dashboard usando Python del sistema

cd /d "c:\Users\indie\Nueva carpeta"

REM Instala streamlit si no lo tiene
"C:\Program Files\WindowsApps\PythonSoftwareFoundation.Python.3.11_3.11.2544.0_x64__qbz5n2kfra8p0\python.exe" -m pip install streamlit plotly pandas --quiet

REM Ejecuta el dashboard
echo.
echo ========================================
echo  Iniciando Dashboard...
echo ========================================
echo.
echo Abre tu navegador en: http://localhost:8501
echo.
"C:\Program Files\WindowsApps\PythonSoftwareFoundation.Python.3.11_3.11.2544.0_x64__qbz5n2kfra8p0\python.exe" -m streamlit run src/analytics/dashboard.py
