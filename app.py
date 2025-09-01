# finance_app.py
import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, date
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import io
import base64
from PIL import Image
import pytesseract
from pathlib import Path
import sqlite3
import hashlib
import json
import re
import tempfile
from fpdf import FPDF
import matplotlib.pyplot as plt

# Configuração da página
st.set_page_config(
    page_title="Sistema de Controle Financeiro",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Função para rerun (compatibilidade com versões do Streamlit)
def rerun():
    try:
        st.rerun()  # Para versões mais recentes
    except:
        try:
            st.experimental_rerun()  # Para versões mais antigas
        except:
            pass  # Se nada funcionar, pelo menos não quebra

# Funções de autenticação
def make_hashes(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def check_hashes(password, hashed_text):
    if make_hashes(password) == hashed_text:
        return hashed_text
    return False

def create_user():
    conn = sqlite3.connect('finance.db')
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS userstable(username TEXT, password TEXT)')
    
    # Verificar se o usuário admin já existe
    c.execute('SELECT * FROM userstable WHERE username = "admin"')
    if not c.fetchone():
        # Criar usuário admin padrão
        c.execute('INSERT INTO userstable(username, password) VALUES (?, ?)', 
                 ('admin', make_hashes('1234')))
    
    conn.commit()
    conn.close()

def add_user(username, password):
    conn = sqlite3.connect('finance.db')
    c = conn.cursor()
    c.execute('INSERT INTO userstable(username,password) VALUES (?,?)', (username, password))
    conn.commit()
    conn.close()

def login_user(username, password):
    conn = sqlite3.connect('finance.db')
    c = conn.cursor()
    c.execute('SELECT * FROM userstable WHERE username =? AND password = ?', (username, password))
    data = c.fetchall()
    conn.close()
    return data

def get_all_users():
    conn = sqlite3.connect('finance.db')
    c = conn.cursor()
    c.execute('SELECT username FROM userstable')
    users = [user[0] for user in c.fetchall()]
    conn.close()
    return users

def delete_user(username):
    conn = sqlite3.connect('finance.db')
    c = conn.cursor()
    c.execute('DELETE FROM userstable WHERE username = ?', (username,))
    conn.commit()
    conn.close()

def create_tables():
    conn = sqlite3.connect('finance.db')
    c = conn.cursor()
    
    # Tabela de despesas
    c.execute('''
        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT,
            origin TEXT,
            value REAL,
            category TEXT,
            user_id TEXT
        )
    ''')
    
    # Tabela de receitas
    c.execute('''
        CREATE TABLE IF NOT EXISTS incomes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT,
            type TEXT,
            description TEXT,
            value REAL,
            user_id TEXT
        )
    ''')
    
    conn.commit()
    conn.close()

# Inicializar tabelas
create_user()
create_tables()

# Funções para gerenciar dados
def add_expense(date, origin, value, category, user_id):
    conn = sqlite3.connect('finance.db')
    c = conn.cursor()
    c.execute('INSERT INTO expenses(date, origin, value, category, user_id) VALUES (?,?,?,?,?)', 
              (date, origin, value, category, user_id))
    conn.commit()
    conn.close()

def get_expenses(user_id):
    conn = sqlite3.connect('finance.db')
    c = conn.cursor()
    c.execute('SELECT * FROM expenses WHERE user_id = ?', (user_id,))
    data = c.fetchall()
    conn.close()
    return data

def delete_expense(id, user_id):
    conn = sqlite3.connect('finance.db')
    c = conn.cursor()
    c.execute('DELETE FROM expenses WHERE id = ? AND user_id = ?', (id, user_id))
    conn.commit()
    conn.close()

def add_income(date, type, description, value, user_id):
    conn = sqlite3.connect('finance.db')
    c = conn.cursor()
    c.execute('INSERT INTO incomes(date, type, description, value, user_id) VALUES (?,?,?,?,?)', 
              (date, type, description, value, user_id))
    conn.commit()
    conn.close()

def get_incomes(user_id):
    conn = sqlite3.connect('finance.db')
    c = conn.cursor()
    c.execute('SELECT * FROM incomes WHERE user_id = ?', (user_id,))
    data = c.fetchall()
    conn.close()
    return data

def delete_income(id, user_id):
    conn = sqlite3.connect('finance.db')
    c = conn.cursor()
    c.execute('DELETE FROM incomes WHERE id = ? AND user_id = ?', (id, user_id))
    conn.commit()
    conn.close()

# Função para processar OCR (requer Tesseract instalado)
def process_image_with_ocr(image):
    try:
        # Salvar imagem temporariamente
        image_path = "temp_image.png"
        image.save(image_path)
        
        # Processar com OCR
        text = pytesseract.image_to_string(Image.open(image_path), lang='por')
        return text
    except:
        return "Erro ao processar imagem. Certifique-se de que o Tesseract está instalado."

# Função para extrair valor do texto
def extract_value_from_text(text):
    patterns = [
        r'R\s*[\$\s]*\s*(\d+[\.,]\d{2})',
        r'valor\s*[\:\s]*\s*(\d+[\.,]\d{2})',
        r'total\s*[\:\s]*\s*(\d+[\.,]\d{2})',
        r'(\d+[\.,]\d{2})'
    ]
    
    max_value = 0
    
    for pattern in patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        if matches:
            for match in matches:
                if isinstance(match, tuple):
                    match = match[0]
                
                clean_value = re.sub(r'[^\d,.]', '', match)
                try:
                    numeric_value = float(clean_value.replace(',', '.'))
                    
                    if not np.isnan(numeric_value) and numeric_value > max_value and numeric_value < 10000:
                        max_value = numeric_value
                except:
                    continue
    
    return max_value

# Função para exportar dados para Excel
def export_to_excel(expenses, incomes):
    # Criar DataFrames
    expense_df = pd.DataFrame(expenses, columns=['ID', 'Data', 'Origem', 'Valor', 'Categoria', 'UserID']) if expenses else pd.DataFrame()
    income_df = pd.DataFrame(incomes, columns=['ID', 'Data', 'Tipo', 'Descrição', 'Valor', 'UserID']) if incomes else pd.DataFrame()
    
    # Formatar datas para o formato brasileiro
    if not expense_df.empty:
        expense_df['Data'] = pd.to_datetime(expense_df['Data']).dt.strftime("%d/%m/%Y")
    if not income_df.empty:
        income_df['Data'] = pd.to_datetime(income_df['Data']).dt.strftime("%d/%m/%Y")
    
    # Criar arquivo Excel em memória
    output = io.BytesIO()
    
    try:
        # Tentar usar xlsxwriter primeiro
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            if not expense_df.empty:
                expense_df.to_excel(writer, sheet_name='Despesas', index=False)
            if not income_df.empty:
                income_df.to_excel(writer, sheet_name='Receitas', index=False)
            
            # Adicionar resumo
            total_expenses = expense_df['Valor'].sum() if not expense_df.empty else 0
            total_income = income_df['Valor'].sum() if not income_df.empty else 0
            balance = total_income - total_expenses
            
            summary_data = {
                'Metrica': ['Total de Despesas', 'Total de Receitas', 'Saldo'],
                'Valor': [total_expenses, total_income, balance]
            }
            summary_df = pd.DataFrame(summary_data)
            summary_df.to_excel(writer, sheet_name='Resumo', index=False)
    except ImportError:
        # Se xlsxwriter não estiver disponível, tentar openpyxl
        try:
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                if not expense_df.empty:
                    expense_df.to_excel(writer, sheet_name='Despesas', index=False)
                if not income_df.empty:
                    income_df.to_excel(writer, sheet_name='Receitas', index=False)
                
                # Adicionar resumo
                total_expenses = expense_df['Valor'].sum() if not expense_df.empty else 0
                total_income = income_df['Valor'].sum() if not income_df.empty else 0
                balance = total_income - total_expenses
                
                summary_data = {
                    'Metrica': ['Total de Despesas', 'Total de Receitas', 'Saldo'],
                    'Valor': [total_expenses, total_income, balance]
                }
                summary_df = pd.DataFrame(summary_data)
                summary_df.to_excel(writer, sheet_name='Resumo', index=False)
        except ImportError:
            # Se nenhum engine do Excel estiver disponível, usar CSV
            st.warning("Bibliotecas Excel não disponíveis. Exportando como CSV.")
            
            # Combinar dados em um único DataFrame para CSV
            combined_data = []
            for expense in expenses:
                combined_data.append({
                    'Tipo': 'Despesa',
                    'Data': format_brazilian_date(expense[1]),
                    'Descrição': expense[2],
                    'Valor': -expense[3],  # Valores negativos para despesas
                    'Categoria': expense[4]
                })
            
            for income in incomes:
                combined_data.append({
                    'Tipo': 'Receita',
                    'Data': format_brazilian_date(income[1]),
                    'Descrição': income[3],
                    'Valor': income[4],
                    'Categoria': income[2]
                })
            
            if combined_data:
                combined_df = pd.DataFrame(combined_data)
                csv_output = combined_df.to_csv(index=False, sep=';')
                output = io.BytesIO(csv_output.encode())
            else:
                output = io.BytesIO(b"Nenhum dado para exportar")
    
    output.seek(0)
    return output

# Função para formatar data no formato brasileiro
def format_brazilian_date(date_str):
    try:
        # Converter de YYYY-MM-DD para DD/MM/YYYY
        if isinstance(date_str, str) and len(date_str) == 10 and date_str[4] == '-':
            parts = date_str.split('-')
            if len(parts) == 3:
                return f"{parts[2]}/{parts[1]}/{parts[0]}"
        return date_str
    except:
        return date_str

# Função para exportar relatório em PDF
def export_to_pdf(expenses, incomes, filters=None):
    # Criar DataFrames
    expense_df = pd.DataFrame(expenses, columns=['ID', 'Data', 'Origem', 'Valor', 'Categoria', 'UserID']) if expenses else pd.DataFrame()
    income_df = pd.DataFrame(incomes, columns=['ID', 'Data', 'Tipo', 'Descrição', 'Valor', 'UserID']) if incomes else pd.DataFrame()
    
    # Formatar datas para o formato brasileiro
    if not expense_df.empty:
        expense_df['Data'] = pd.to_datetime(expense_df['Data']).dt.strftime("%d/%m/%Y")
    if not income_df.empty:
        income_df['Data'] = pd.to_datetime(income_df['Data']).dt.strftime("%d/%m/%Y")
    
    # Calcular totais
    total_expenses = expense_df['Valor'].sum() if not expense_df.empty else 0
    total_income = income_df['Valor'].sum() if not income_df.empty else 0
    balance = total_income - total_expenses
    
    # Criar PDF
    pdf = FPDF()
    pdf.add_page()
    
    # Configurar fonte
    pdf.set_font("Arial", 'B', 16)
    
    # Título
    pdf.cell(0, 10, "Relatório Financeiro", 0, 1, 'C')
    pdf.ln(5)
    
    # Informações do relatório
    pdf.set_font("Arial", '', 12)
    pdf.cell(0, 10, f"Usuário: {st.session_state.username}", 0, 1)
    pdf.cell(0, 10, f"Data do relatório: {datetime.now().strftime('%d/%m/%Y %H:%M')}", 0, 1)
    
    if filters:
        pdf.cell(0, 10, f"Filtros aplicados: {filters}", 0, 1)
    
    pdf.ln(5)
    
    # Resumo financeiro
    pdf.set_font("Arial", 'B', 14)
    pdf.cell(0, 10, "Resumo Financeiro", 0, 1)
    pdf.set_font("Arial", '', 12)
    
    pdf.cell(0, 10, f"Total de Receitas: R$ {total_income:,.2f}", 0, 1)
    pdf.cell(0, 10, f"Total de Despesas: R$ {total_expenses:,.2f}", 0, 1)
    
    # Definir cor para o saldo (verde para positivo, vermelho para negativo)
    if balance >= 0:
        pdf.set_text_color(0, 128, 0)  # Verde
    else:
        pdf.set_text_color(255, 0, 0)  # Vermelho
    
    pdf.cell(0, 10, f"Saldo: R$ {balance:,.2f}", 0, 1)
    pdf.set_text_color(0, 0, 0)  # Voltar para preto
    
    pdf.ln(5)
    
    # Detalhes das despesas
    if not expense_df.empty:
        pdf.set_font("Arial", 'B', 14)
        pdf.cell(0, 10, "Despesas", 0, 1)
        pdf.set_font("Arial", '', 10)
        
        # Cabeçalho da tabela
        pdf.cell(40, 10, "Data", 1)
        pdf.cell(60, 10, "Origem", 1)
        pdf.cell(40, 10, "Categoria", 1)
        pdf.cell(40, 10, "Valor (R$)", 1)
        pdf.ln()
        
        # Dados das despesas
        for _, row in expense_df.iterrows():
            pdf.cell(40, 10, str(row['Data']), 1)
            pdf.cell(60, 10, str(row['Origem'])[:30], 1)  # Limitar tamanho
            pdf.cell(40, 10, str(row['Categoria']), 1)
            pdf.cell(40, 10, f"{row['Valor']:,.2f}", 1)
            pdf.ln()
        
        pdf.ln(5)
    
    # Detalhes das receitas
    if not income_df.empty:
        pdf.set_font("Arial", 'B', 14)
        pdf.cell(0, 10, "Receitas", 0, 1)
        pdf.set_font("Arial", '', 10)
        
        # Cabeçalho da tabela
        pdf.cell(40, 10, "Data", 1)
        pdf.cell(60, 10, "Tipo", 1)
        pdf.cell(60, 10, "Descrição", 1)
        pdf.cell(40, 10, "Valor (R$)", 1)
        pdf.ln()
        
        # Dados das receitas
        for _, row in income_df.iterrows():
            pdf.cell(40, 10, str(row['Data']), 1)
            pdf.cell(60, 10, str(row['Tipo']), 1)
            pdf.cell(60, 10, str(row['Descrição'])[:30], 1)  # Limitar tamanho
            pdf.cell(40, 10, f"{row['Valor']:,.2f}", 1)
            pdf.ln()
    
    # Adicionar página de gráficos se houver dados
    if not expense_df.empty or not income_df.empty:
        pdf.add_page()
        pdf.set_font("Arial", 'B', 14)
        pdf.cell(0, 10, "Gráficos e Estatísticas", 0, 1)
        
        # Criar gráficos simples (seriam melhores com matplotlib)
        pdf.set_font("Arial", '', 12)
        pdf.cell(0, 10, "Distribuição de Despesas por Categoria", 0, 1)
        
        if not expense_df.empty:
            expense_by_category = expense_df.groupby('Categoria')['Valor'].sum()
            for category, value in expense_by_category.items():
                pdf.cell(0, 10, f"{category}: R$ {value:,.2f} ({value/total_expenses*100:.1f}%)", 0, 1)
        
        pdf.ln(5)
        pdf.cell(0, 10, "Distribuição de Receitas por Tipo", 0, 1)
        
        if not income_df.empty:
            income_by_type = income_df.groupby('Tipo')['Valor'].sum()
            for type_, value in income_by_type.items():
                pdf.cell(0, 10, f"{type_}: R$ {value:,.2f} ({value/total_income*100:.1f}%)", 0, 1)
    
    # Salvar PDF em buffer
    pdf_output = io.BytesIO()
    pdf_output.write(pdf.output(dest='S').encode('latin1'))
    pdf_output.seek(0)
    
    return pdf_output

# Interface principal da aplicação
def main():
    st.title("💰 Sistema de Controle Financeiro Pessoal")
    
    # Inicializar estado da sessão
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False
    if 'username' not in st.session_state:
        st.session_state.username = ""
    if 'page' not in st.session_state:
        st.session_state.page = "Login"
    if 'is_admin' not in st.session_state:
        st.session_state.is_admin = False
    
    # Navegação
    if not st.session_state.logged_in:
        login_page()
    else:
        # Menu de navegação
        if st.session_state.is_admin:
            menu = ["Dashboard", "Despesas", "Receitas", "Relatórios", "Configurações", "Administração"]
        else:
            menu = ["Dashboard", "Despesas", "Receitas", "Relatórios", "Configurações"]
            
        choice = st.sidebar.selectbox("Navegação", menu)
        
        # Exibir página selecionada
        if choice == "Dashboard":
            dashboard_page()
        elif choice == "Despesas":
            expenses_page()
        elif choice == "Receitas":
            incomes_page()
        elif choice == "Relatórios":
            reports_page()
        elif choice == "Configurações":
            settings_page()
        elif choice == "Administração" and st.session_state.is_admin:
            admin_page()
        
        # Botão de logout
        st.sidebar.write("---")
        if st.sidebar.button("🚪 Sair"):
            st.session_state.logged_in = False
            st.session_state.username = ""
            st.session_state.is_admin = False
            rerun()

# Página de login
def login_page():
    st.header("Login")
    
    username = st.text_input("Usuário")
    password = st.text_input("Senha", type="password")
    
    if st.button("Entrar"):
        hashed_pswd = make_hashes(password)
        
        # Verificar credenciais corretamente
        conn = sqlite3.connect('finance.db')
        c = conn.cursor()
        c.execute('SELECT * FROM userstable WHERE username =? AND password = ?', (username, hashed_pswd))
        result = c.fetchall()
        conn.close()
        
        if result:
            st.session_state.logged_in = True
            st.session_state.username = username
            st.session_state.is_admin = (username == "admin")
            st.success("Login realizado com sucesso!")
            # Forçar rerun para atualizar a interface
            st.rerun()
        else:
            st.error("Usuário ou senha incorretos")
    
    # Informações de login padrão
    with st.expander("Credenciais padrão"):
        st.info("""
        **Usuário padrão para teste:**
        - Usuário: `admin`
        - Senha: `1234`
        """)

# Página de administração
def admin_page():
    st.header("👨‍💼 Painel de Administração")
    
    tab1, tab2 = st.tabs(["Gerenciar Usuários", "Estatísticas do Sistema"])
    
    with tab1:
        st.subheader("Gerenciar Usuários")
        
        # Adicionar novo usuário
        with st.form("add_user_form"):
            st.write("Adicionar Novo Usuário")
            new_username = st.text_input("Nome de usuário")
            new_password = st.text_input("Senha", type="password")
            confirm_password = st.text_input("Confirmar senha", type="password")
            
            if st.form_submit_button("Adicionar Usuário"):
                if new_username and new_password:
                    if new_password == confirm_password:
                        # Verificar if usuário já existe
                        existing_users = get_all_users()
                        if new_username in existing_users:
                            st.error("Usuário já existe")
                        else:
                            add_user(new_username, make_hashes(new_password))
                            st.success(f"Usuário '{new_username}' adicionado com sucesso!")
                            rerun()
                    else:
                        st.error("As senhas não coincidem")
                else:
                    st.error("Preencha todos os campos")
        
        # Lista de usuários
        st.subheader("Usuários Existentes")
        users = get_all_users()
        
        if users:
            for user in users:
                col1, col2, col3 = st.columns([3, 1, 1])
                with col1:
                    st.write(f"**{user}**")
                with col2:
                    if user != "admin":  # Não permitir excluir o admin
                        if st.button(f"Excluir", key=f"delete_{user}"):
                            # Excluir dados do usuário primeiro
                            conn = sqlite3.connect('finance.db')
                            c = conn.cursor()
                            c.execute('DELETE FROM expenses WHERE user_id = ?', (user,))
                            c.execute('DELETE FROM incomes WHERE user_id = ?', (user,))
                            conn.commit()
                            conn.close()
                            
                            # Excluir usuário
                            delete_user(user)
                            st.success(f"Usuário '{user}' excluído com sucesso!")
                            rerun()
                with col3:
                    if st.button(f"Redefinir Senha", key=f"reset_{user}"):
                        # Redefinir senha para padrão
                        conn = sqlite3.connect('finance.db')
                        c = conn.cursor()
                        c.execute('UPDATE userstable SET password = ? WHERE username = ?', 
                                 (make_hashes("1234"), user))
                        conn.commit()
                        conn.close()
                        st.success(f"Senha do usuário '{user}' redefinida para '1234'")
        else:
            st.info("Nenhum usuário cadastrado.")
    
    with tab2:
        st.subheader("Estatísticas do Sistema")
        
        # Estatísticas gerais
        conn = sqlite3.connect('finance.db')
        c = conn.cursor()
        
        # Total de usuários
        c.execute('SELECT COUNT(*) FROM userstable')
        total_users = c.fetchone()[0]
        
        # Total de despesas
        c.execute('SELECT COUNT(*) FROM expenses')
        total_expenses = c.fetchone()[0]
        
        # Total de receitas
        c.execute('SELECT COUNT(*) FROM incomes')
        total_incomes = c.fetchone()[0]
        
        # Valor total de despesas
        c.execute('SELECT SUM(value) FROM expenses')
        total_expenses_value = c.fetchone()[0] or 0
        
        # Valor total de receitas
        c.execute('SELECT SUM(value) FROM incomes')
        total_incomes_value = c.fetchone()[0] or 0
        
        conn.close()
        
        # Exibir métricas
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total de Usuários", total_users)
        with col2:
            st.metric("Total de Despesas", total_expenses)
        with col3:
            st.metric("Total de Receitas", total_incomes)
        
        col4, col5 = st.columns(2)
        with col4:
            st.metric("Valor Total de Despesas", f"R$ {total_expenses_value:,.2f}")
        with col5:
            st.metric("Valor Total de Receitas", f"R$ {total_incomes_value:,.2f}")

# Página principal (Dashboard)
def dashboard_page():
    st.header("📊 Dashboard Financeiro")
    
    # Carregar dados
    expenses = get_expenses(st.session_state.username)
    incomes = get_incomes(st.session_state.username)
    
    # Converter para DataFrames
    expense_df = pd.DataFrame(expenses, columns=['ID', 'Data', 'Origem', 'Valor', 'Categoria', 'UserID']) if expenses else pd.DataFrame()
    income_df = pd.DataFrame(incomes, columns=['ID', 'Data', 'Tipo', 'Descrição', 'Valor', 'UserID']) if incomes else pd.DataFrame()
    
    # Calcular totais
    total_expenses = expense_df['Valor'].sum() if not expense_df.empty else 0
    total_income = income_df['Valor'].sum() if not income_df.empty else 0
    balance = total_income - total_expenses
    
    # Exibir métricas
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total de Receitas", f"R$ {total_income:,.2f}")
    with col2:
        st.metric("Total de Despesas", f"R$ {total_expenses:,.2f}")
    with col3:
        st.metric("Saldo", f"R$ {balance:,.2f}", delta_color="inverse" if balance < 0 else "normal")
    
    # Gráficos
    if not expense_df.empty or not income_df.empty:
        col1, col2 = st.columns(2)
        
        with col1:
            # Gráfico de despesas por categoria
            if not expense_df.empty:
                expense_by_category = expense_df.groupby('Categoria')['Valor'].sum().reset_index()
                fig1 = px.pie(expense_by_category, values='Valor', names='Categoria', title='Despesas por Categoria')
                st.plotly_chart(fig1, use_container_width=True)
        
        with col2:
            # Gráfico de receitas por tipo
            if not income_df.empty:
                income_by_type = income_df.groupby('Tipo')['Valor'].sum().reset_index()
                fig2 = px.pie(income_by_type, values='Valor', names='Tipo', title='Receitas por Tipo')
                st.plotly_chart(fig2, use_container_width=True)
        
        # Gráfico de evolução mensal
        st.subheader("Evolução Mensal")
        
        # Preparar dados para o gráfico
        if not expense_df.empty:
            expense_df['Data'] = pd.to_datetime(expense_df['Data'])
            expense_df['Mês'] = expense_df['Data'].dt.to_period('M').astype(str)
            monthly_expenses = expense_df.groupby('Mês')['Valor'].sum().reset_index()
        else:
            monthly_expenses = pd.DataFrame(columns=['Mês', 'Valor'])
        
        if not income_df.empty:
            income_df['Data'] = pd.to_datetime(income_df['Data'])
            income_df['Mês'] = income_df['Data'].dt.to_period('M').astype(str)
            monthly_income = income_df.groupby('Mês')['Valor'].sum().reset_index()
        else:
            monthly_income = pd.DataFrame(columns=['Mês', 'Valor'])
        
        # Criar gráfico combinado
        fig3 = go.Figure()
        
        if not monthly_expenses.empty:
            fig3.add_trace(go.Scatter(
                x=monthly_expenses['Mês'], 
                y=monthly_expenses['Valor'],
                name='Despesas',
                line=dict(color='red')
            ))
        
        if not monthly_income.empty:
            fig3.add_trace(go.Scatter(
                x=monthly_income['Mês'], 
                y=monthly_income['Valor'],
                name='Receitas',
                line=dict(color='green')
            ))
        
        fig3.update_layout(
            title='Evolução Mensal de Receitas e Despesas',
            xaxis_title='Mês',
            yaxis_title='Valor (R$)',
            hovermode='x unified'
        )
        
        st.plotly_chart(fig3, use_container_width=True)
    else:
        st.info("Nenhum dado disponível. Adicione despesas e receitas para ver os gráficos.")

# Página de despesas
def expenses_page():
    st.header("💸 Gerenciar Despesas")
    
    # Formulário para adicionar despesa
    with st.expander("Adicionar Nova Despesa"):
        col1, col2 = st.columns(2)
        
        with col1:
            # Usando text_input para data no formato brasileiro
            expense_date_str = st.text_input("Data (DD/MM/AAAA)", value=date.today().strftime("%d/%m/%Y"))
            expense_origin = st.text_input("Origem")
            
            # Campo de valor com placeholder e valor inicial 0.00
            expense_value = st.number_input("Valor (R$)", min_value=0.0, step=0.01, value=0.0, format="%.2f")
        
        with col2:
            expense_category = st.selectbox(
                "Categoria",
                ["Alimentação", "Combustível", "Transporte", "Moradia", "Outros"]
            )
            
            # Upload de imagem para OCR
            uploaded_image = st.file_uploader("Upload de cupom fiscal (OCR)", type=['png', 'jpg', 'jpeg'])
            
            if uploaded_image is not None:
                image = Image.open(uploaded_image)
                st.image(image, caption="Imagem do cupom", use_column_width=True)
                
                if st.button("Extrair texto da imagem"):
                    with st.spinner("Processando imagem..."):
                        text = process_image_with_ocr(image)
                        st.text_area("Texto extraído", text, height=150)
                        
                        # Tentar extrair valor
                        value = extract_value_from_text(text)
                        if value > 0:
                            st.success(f"Valor extraído: R$ {value:.2f}")
                            # Atualizar o valor no campo usando session state
                            st.session_state.extracted_expense_value = value
        
        # Usar valor extraído se disponível
        if 'extracted_expense_value' in st.session_state:
            expense_value = st.session_state.extracted_expense_value
        
        if st.button("Adicionar Despesa"):
            # Validar e converter data
            try:
                # Converter data do formato brasileiro para o formato do banco
                date_obj = datetime.strptime(expense_date_str, "%d/%m/%Y")
                db_date = date_obj.strftime("%Y-%m-%d")
            except ValueError:
                st.error("Formato de data inválido. Use DD/MM/AAAA.")
                return
            
            if expense_origin and expense_value > 0:
                add_expense(
                    db_date,
                    expense_origin,
                    expense_value,
                    expense_category,
                    st.session_state.username
                )
                st.success("Despesa adicionada com sucesso!")
                # Limpar valor extraído da sessão
                if 'extracted_expense_value' in st.session_state:
                    del st.session_state.extracted_expense_value
                rerun()
            else:
                st.error("Preencha todos os campos obrigatórios")
    
    # Lista de despesas
    st.subheader("Despesas Registradas")
    expenses = get_expenses(st.session_state.username)
    
    if expenses:
        expense_df = pd.DataFrame(expenses, columns=['ID', 'Data', 'Origem', 'Valor', 'Categoria', 'UserID'])
        expense_df['Data'] = pd.to_datetime(expense_df['Data']).dt.date
        
        # Formatar datas para exibição no formato brasileiro
        expense_df['Data'] = expense_df['Data'].apply(lambda d: d.strftime("%d/%m/%Y"))
        
        # Filtrar por período
        col1, col2 = st.columns(2)
        with col1:
            # Converter para datas para filtro
            expense_dates = [datetime.strptime(d, "%d/%m/%Y") for d in expense_df['Data']]
            min_date = min(expense_dates) if expense_dates else date.today()
            max_date = max(expense_dates) if expense_dates else date.today()
            
            start_date = st.date_input("Data inicial", value=min_date, min_value=min_date, max_value=max_date)
        with col2:
            end_date = st.date_input("Data final", value=max_date, min_value=min_date, max_value=max_date)
        
        # Converter datas de filtro para o formato de exibição
        start_date_str = start_date.strftime("%d/%m/%Y")
        end_date_str = end_date.strftime("%d/%m/%Y")
        
        # Filtrar DataFrame
        filtered_df = expense_df.copy()
        filtered_df['Data_Comparavel'] = pd.to_datetime(filtered_df['Data'], format="%d/%m/%Y")
        filtered_df = filtered_df[
            (filtered_df['Data_Comparavel'] >= pd.to_datetime(start_date)) & 
            (filtered_df['Data_Comparavel'] <= pd.to_datetime(end_date))
        ]
        filtered_df = filtered_df.drop('Data_Comparavel', axis=1)
        
        # Exibir tabela
        st.dataframe(
            filtered_df[['Data', 'Origem', 'Valor', 'Categoria']],
            use_container_width=True
        )
        
        # Opção para excluir despesa
        st.subheader("Excluir Despesa")
        expense_ids = [f"{e[0]} - {e[2]} - R$ {e[3]:.2f} - {e[4]}" for e in expenses]
        selected_expense = st.selectbox("Selecione a despesa para excluir", expense_ids)
        
        if st.button("Excluir Despesa"):
            expense_id = int(selected_expense.split(" - ")[0])
            delete_expense(expense_id, st.session_state.username)
            st.success("Despesa excluída com sucesso!")
            rerun()
    else:
        st.info("Nenhuma despesa registrada.")

# Página de receitas
def incomes_page():
    st.header("💵 Gerenciar Receitas")
    
    # Formulário para adicionar receita
    with st.expander("Adicionar Nova Receita"):
        col1, col2 = st.columns(2)
        
        with col1:
            # Usando text_input para data no formato brasileiro
            income_date_str = st.text_input("Data (DD/MM/AAAA)", value=date.today().strftime("%d/%m/%Y"), key="income_date")
            income_type = st.selectbox("Tipo", ["Dízimo", "Oferta", "Outros"])
        
        with col2:
            income_description = st.text_input("Descrição")
            # Campo de valor com placeholder e valor inicial 0.00
            income_value = st.number_input("Valor (R$)", min_value=0.0, step=0.01, value=0.0, format="%.2f", key="income_value")
        
        if st.button("Adicionar Receita"):
            # Validar e converter data
            try:
                # Converter data do formato brasileiro para o formato do banco
                date_obj = datetime.strptime(income_date_str, "%d/%m/%Y")
                db_date = date_obj.strftime("%Y-%m-%d")
            except ValueError:
                st.error("Formato de data inválido. Use DD/MM/AAAA.")
                return
            
            if income_value > 0:
                add_income(
                    db_date,
                    income_type,
                    income_description,
                    income_value,
                    st.session_state.username
                )
                st.success("Receita adicionada com sucesso!")
                rerun()
            else:
                st.error("Preencha todos os campos obrigatórios")
    
    # Lista de receitas
    st.subheader("Receitas Registradas")
    incomes = get_incomes(st.session_state.username)
    
    if incomes:
        income_df = pd.DataFrame(incomes, columns=['ID', 'Data', 'Tipo', 'Descrição', 'Valor', 'UserID'])
        income_df['Data'] = pd.to_datetime(income_df['Data']).dt.date
        
        # Formatar datas para exibição no formato brasileiro
        income_df['Data'] = income_df['Data'].apply(lambda d: d.strftime("%d/%m/%Y"))
        
        # Filtrar por período
        col1, col2 = st.columns(2)
        with col1:
            # Converter para datas para filtro
            income_dates = [datetime.strptime(d, "%d/%m/%Y") for d in income_df['Data']]
            min_date = min(income_dates) if income_dates else date.today()
            max_date = max(income_dates) if income_dates else date.today()
            
            start_date = st.date_input("Data inicial", value=min_date, min_value=min_date, max_value=max_date, key="income_start")
        with col2:
            end_date = st.date_input("Data final", value=max_date, min_value=min_date, max_value=max_date, key="income_end")
        
        # Converter datas de filtro para o formato de exibição
        start_date_str = start_date.strftime("%d/%m/%Y")
        end_date_str = end_date.strftime("%d/%m/%Y")
        
        # Filtrar DataFrame
        filtered_df = income_df.copy()
        filtered_df['Data_Comparavel'] = pd.to_datetime(filtered_df['Data'], format="%d/%m/%Y")
        filtered_df = filtered_df[
            (filtered_df['Data_Comparavel'] >= pd.to_datetime(start_date)) & 
            (filtered_df['Data_Comparavel'] <= pd.to_datetime(end_date))
        ]
        filtered_df = filtered_df.drop('Data_Comparavel', axis=1)
        
        # Exibir tabela
        st.dataframe(
            filtered_df[['Data', 'Tipo', 'Descrição', 'Valor']],
            use_container_width=True
        )
        
        # Opção para excluir receita
        st.subheader("Excluir Receita")
        income_ids = [f"{i[0]} - {i[2]} - R$ {i[4]:.2f} - {i[3]}" for i in incomes]
        selected_income = st.selectbox("Selecione a receita para excluir", income_ids)
        
        if st.button("Excluir Receita"):
            income_id = int(selected_income.split(" - ")[0])
            delete_income(income_id, st.session_state.username)
            st.success("Receita excluída com sucesso!")
            rerun()
    else:
        st.info("Nenhuma receita registrada.")

# Página de relatórios
def reports_page():
    st.header("📈 Relatórios e Exportação")
    
    # Carregar dados
    expenses = get_expenses(st.session_state.username)
    incomes = get_incomes(st.session_state.username)
    
    if not expenses and not incomes:
        st.info("Nenhum dado disponível para gerar relatórios.")
        return
    
    # Converter para DataFrames
    expense_df = pd.DataFrame(expenses, columns=['ID', 'Data', 'Origem', 'Valor', 'Categoria', 'UserID']) if expenses else pd.DataFrame()
    income_df = pd.DataFrame(incomes, columns=['ID', 'Data', 'Tipo', 'Descrição', 'Valor', 'UserID']) if incomes else pd.DataFrame()
    
    # Formatar datas para exibição
    if not expense_df.empty:
        expense_df['Data'] = pd.to_datetime(expense_df['Data']).dt.strftime("%d/%m/%Y")
    if not income_df.empty:
        income_df['Data'] = pd.to_datetime(income_df['Data']).dt.strftime("%d/%m/%Y")
    
    # Filtros
    st.subheader("Filtros")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        year_options = ["Todos"] + list(range(2023, 2031))
        year = st.selectbox("Ano", options=year_options)
    with col2:
        month_options = ["Todos", "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", 
                       "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"]
        month = st.selectbox("Mês", options=month_options)
    with col3:
        if not expense_df.empty:
            category_options = ["Todas"] + list(expense_df['Categoria'].unique())
        else:
            category_options = ["Todas"]
        category = st.selectbox("Categoria", options=category_options)
    
    # Aplicar filtros
    if not expense_df.empty:
        expense_df['Data_Comparavel'] = pd.to_datetime(expense_df['Data'], format="%d/%m/%Y")
        expense_df['Ano'] = expense_df['Data_Comparavel'].dt.year
        expense_df['Mês'] = expense_df['Data_Comparavel'].dt.month
        
        if year != "Todos":
            expense_df = expense_df[expense_df['Ano'] == int(year)]
        if month != "Todos":
            month_num = month_options.index(month)
            expense_df = expense_df[expense_df['Mês'] == month_num]
        if category != "Todas":
            expense_df = expense_df[expense_df['Categoria'] == category]
        
        expense_df = expense_df.drop(['Data_Comparavel', 'Ano', 'Mês'], axis=1)
    
    if not income_df.empty:
        income_df['Data_Comparavel'] = pd.to_datetime(income_df['Data'], format="%d/%m/%Y")
        income_df['Ano'] = income_df['Data_Comparavel'].dt.year
        income_df['Mês'] = income_df['Data_Comparavel'].dt.month
        
        if year != "Todos":
            income_df = income_df[income_df['Ano'] == int(year)]
        if month != "Todos":
            month_num = month_options.index(month)
            income_df = income_df[income_df['Mês'] == month_num]
        
        income_df = income_df.drop(['Data_Comparavel', 'Ano', 'Mês'], axis=1)
    
    # Estatísticas
    st.subheader("Estatísticas")
    
    # Converter valores para numérico para cálculo
    if not expense_df.empty:
        expense_df['Valor'] = pd.to_numeric(expense_df['Valor'])
        total_expenses = expense_df['Valor'].sum()
    else:
        total_expenses = 0
        
    if not income_df.empty:
        income_df['Valor'] = pd.to_numeric(income_df['Valor'])
        total_income = income_df['Valor'].sum()
    else:
        total_income = 0
        
    balance = total_income - total_expenses
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total de Receitas", f"R$ {total_income:,.2f}")
    with col2:
        st.metric("Total de Despesas", f"R$ {total_expenses:,.2f}")
    with col3:
        st.metric("Saldo", f"R$ {balance:,.2f}", delta_color="inverse" if balance < 0 else "normal")
    
    # Exportação
    st.subheader("Exportar Dados")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("📊 Exportar para Excel"):
            excel_file = export_to_excel(expenses, incomes)
            st.download_button(
                label="⬇️ Baixar arquivo Excel",
                data=excel_file,
                file_name="relatorio_financeiro.xlsx",
                mime="application/vnd.ms-excel"
            )
    
    with col2:
        # Exportar para JSON
        if st.button("📋 Exportar para JSON"):
            data = {
                "despesas": expense_df.to_dict(orient='records') if not expense_df.empty else [],
                "receitas": income_df.to_dict(orient='records') if not income_df.empty else [],
                "resumo": {
                    "total_despesas": total_expenses,
                    "total_receitas": total_income,
                    "saldo": balance
                }
            }
            
            json_str = json.dumps(data, indent=4, default=str)
            st.download_button(
                label="⬇️ Baixar arquivo JSON",
                data=json_str,
                file_name="relatorio_financeiro.json",
                mime="application/json"
            )
    
    with col3:
        # Exportar para PDF
        if st.button("📄 Exportar para PDF"):
            # Criar descrição dos filtros aplicados
            filters_desc = []
            if year != "Todos":
                filters_desc.append(f"Ano: {year}")
            if month != "Todos":
                filters_desc.append(f"Mês: {month}")
            if category != "Todas":
                filters_desc.append(f"Categoria: {category}")
            
            filters_text = ", ".join(filters_desc) if filters_desc else "Todos os dados"
            
            pdf_file = export_to_pdf(expenses, incomes, filters_text)
            st.download_button(
                label="⬇️ Baixar arquivo PDF",
                data=pdf_file,
                file_name="relatorio_financeiro.pdf",
                mime="application/pdf"
            )

# Página de configurações
def settings_page():
    st.header("⚙️ Configurações")
    
    st.subheader("Informações da Conta")
    st.write(f"Usuário: {st.session_state.username}")
    
    st.subheader("Alterar Senha")
    current_password = st.text_input("Senha atual", type="password")
    new_password = st.text_input("Nova senha", type="password")
    confirm_password = st.text_input("Confirmar nova senha", type="password")
    
    if st.button("Alterar Senha"):
        if new_password == confirm_password:
            # Verificar senha atual
            conn = sqlite3.connect('finance.db')
            c = conn.cursor()
            c.execute('SELECT password FROM userstable WHERE username = ?', (st.session_state.username,))
            result = c.fetchone()
            conn.close()
            
            if result and check_hashes(current_password, result[0]):
                # Atualizar senha
                conn = sqlite3.connect('finance.db')
                c = conn.cursor()
                c.execute('UPDATE userstable SET password = ? WHERE username = ?', 
                         (make_hashes(new_password), st.session_state.username))
                conn.commit()
                conn.close()
                
                st.success("Senha alterada com sucesso!")
            else:
                st.error("Senha atual incorreta")
        else:
            st.error("As senhas não coincidem")
    
    st.subheader("Backup de Dados")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("💾 Fazer Backup"):
            expenses = get_expenses(st.session_state.username)
            incomes = get_incomes(st.session_state.username)
            
            backup_data = {
                "expenses": expenses,
                "incomes": incomes,
                "backup_date": datetime.now().isoformat()
            }
            
            json_str = json.dumps(backup_data, indent=4)
            st.download_button(
                label="⬇️ Baixar Backup",
                data=json_str,
                file_name=f"backup_financeiro_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                mime="application/json"
            )
    
    with col2:
        uploaded_backup = st.file_uploader("Restaurar Backup", type=['json'])
        if uploaded_backup is not None:
            if st.button("🔄 Restaurar Backup"):
                try:
                    backup_data = json.load(uploaded_backup)
                    
                    # Limpar dados atuais
                    conn = sqlite3.connect('finance.db')
                    c = conn.cursor()
                    c.execute('DELETE FROM expenses WHERE user_id = ?', (st.session_state.username,))
                    c.execute('DELETE FROM incomes WHERE user_id = ?', (st.session_state.username,))
                    
                    # Restaurar despesas
                    for expense in backup_data.get('expenses', []):
                        c.execute('INSERT INTO expenses (date, origin, value, category, user_id) VALUES (?, ?, ?, ?, ?)',
                                 (expense[1], expense[2], expense[3], expense[4], st.session_state.username))
                    
                    # Restaurar receitas
                    for income in backup_data.get('incomes', []):
                        c.execute('INSERT INTO incomes (date, type, description, value, user_id) VALUES (?, ?, ?, ?, ?)',
                                 (income[1], income[2], income[3], income[4], st.session_state.username))
                    
                    conn.commit()
                    conn.close()
                    
                    st.success("Backup restaurado com sucesso!")
                    rerun()
                except Exception as e:
                    st.error(f"Erro ao restaurar backup: {str(e)}")

# Executar aplicação
if __name__ == "__main__":
    main()