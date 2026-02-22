#!/bin/bash
# Script di avvio per Travel & Expense Approval Management
# Usa python3 con i pacchetti utente aggiornati

echo "🚀 Avvio Travel & Expense Approval Management..."
echo "📍 Directory: $(pwd)"
echo "🐍 Python: $(which python3)"
echo "📦 Streamlit version: $(python3 -c 'import streamlit; print(streamlit.__version__)')"
echo ""
echo "🌐 Server sarà disponibile su: http://localhost:8501"
echo ""

# Avvia Streamlit
python3 -m streamlit run app.py
