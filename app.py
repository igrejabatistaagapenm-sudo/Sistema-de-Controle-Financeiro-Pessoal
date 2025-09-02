# finance_app.py
import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, date as dt_date
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import io
import base64
from PIL import Image
import sqlite3
import hashlib
import json
import re
import tempfile
import csv
import os
import time

# Configuração da página
st.set_page_config(
    page_title="Sistema de Controle Financeiro - Igreja Batista Ágape",
    page_icon="✝️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Função para rerun (compatibilidade com versões do Streamlit)
def rerun():
    # Apenas recarrega a página via JavaScript
    st.markdown("""
        <script>
            window.location.reload(true);
        </script>
    """, unsafe_allow_html=True)

# Funções de validação de CPF/CNPJ
def validate_cpf(cpf):
    """Valida CPF"""
    cpf = re.sub(r'[^0-9]', '', cpf)
    
    if len(cpf) != 11:
        return False
    
    if cpf == cpf[0] * 11:
        return False
    
    # Cálculo do primeiro dígito verificador
    sum = 0
    for i in range(9):
        sum += int(cpf[i]) * (10 - i)
    remainder = sum % 11
    digit1 = 0 if remainder < 2 else 11 - remainder
    
    # Cálculo do segundo dígito verificador
    sum = 0
    for i in range(10):
        sum += int(cpf[i]) * (11 - i)
    remainder = sum % 11
    digit2 = 0 if remainder < 2 else 11 - remainder
    
    return int(cpf[9]) == digit1 and int(cpf[10]) == digit2

def validate_cnpj(cnpj):
    """Valida CNPJ"""
    cnpj = re.sub(r'[^0-9]', '', cnpj)
    
    if len(cnpj) != 14:
        return False
    
    if cnpj == cnpj[0] * 14:
        return False
    
    # Cálculo do primeiro dígito verificador
    weights1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    sum1 = 0
    for i in range(12):
        sum1 += int(cnpj[i]) * weights1[i]
    digit1 = 11 - (sum1 % 11)
    if digit1 >= 10:
        digit1 = 0
    
    # Cálculo do segundo dígito verificador
    weights2 = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    sum2 = 0
    for i in range(13):
        sum2 += int(cnpj[i]) * weights2[i]
    digit2 = 11 - (sum2 % 11)
    if digit2 >= 10:
        digit2 = 0
    
    return int(cnpj[12]) == digit1 and int(cnpj[13]) == digit2

def format_cpf(cpf):
    """Formata CPF"""
    cpf = re.sub(r'[^0-9]', '', cpf)
    if len(cpf) == 11:
        return f"{cpf[:3]}.{cpf[3:6]}.{cpf[6:9]}-{cpf[9:]}"
    return cpf

def format_cnpj(cnpj):
    """Formata CNPJ"""
    cnpj = re.sub(r'[^0-9]', '', cnpj)
    if len(cnpj) == 14:
        return f"{cnpj[:2]}.{cnpj[2:5]}.{cnpj[5:8]}/{cnpj[8:12]}-{cnpj[12:]}"
    return cnpj

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
    
    # APENAS verificar/criar usuário admin
    c.execute('SELECT * FROM userstable WHERE username = "admin"')
    if not c.fetchone():
        # Criar usuário admin padrão
        c.execute('INSERT INTO userstable(username, password, nome_completo, data_cadastro) VALUES (?, ?, ?, ?)', 
                 ('admin', make_hashes('1234'), 'Administrador', datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    
    conn.commit()
    conn.close()

def add_user(username, password, nome_completo, cpf_cnpj, tipo_pessoa):
    conn = sqlite3.connect('finance.db')
    c = conn.cursor()
    c.execute('INSERT INTO userstable(username, password, nome_completo, cpf_cnpj, tipo_pessoa, data_cadastro) VALUES (?,?,?,?,?,?)', 
              (username, password, nome_completo, cpf_cnpj, tipo_pessoa, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    conn.commit()
    conn.close()

def login_user(username, password):
    conn = sqlite3.connect('finance.db')
    c = conn.cursor()
    c.execute('SELECT * FROM userstable WHERE username =? AND password = ?', (username, password))
    data = c.fetchall()
    conn.close()
    return data

def get_user_info(username):
    conn = sqlite3.connect('finance.db')
    c = conn.cursor()
    try:
        c.execute('SELECT nome_completo, cpf_cnpj, tipo_pessoa FROM userstable WHERE username = ?', (username,))
        data = c.fetchone()
        conn.close()
        return data
    except sqlite3.OperationalError as e:
        # Se a tabela não existir, retorna None
        conn.close()
        return None

def update_user_info(username, nome_completo, cpf_cnpj, tipo_pessoa):
    conn = sqlite3.connect('finance.db')
    c = conn.cursor()
    c.execute('UPDATE userstable SET nome_completo = ?, cpf_cnpj = ?, tipo_pessoa = ? WHERE username = ?', 
              (nome_completo, cpf_cnpj, tipo_pessoa, username))
    conn.commit()
    conn.close()

def get_all_users():
    conn = sqlite3.connect('finance.db')
    c = conn.cursor()
    
    # Verificar se as colunas existem na tabela
    try:
        c.execute('PRAGMA table_info(userstable)')
        columns = [column[1] for column in c.fetchall()]
        
        # Construir a query baseada nas colunas existentes
        if 'cpf_cnpj' in columns and 'tipo_pessoa' in columns:
            c.execute('SELECT username, nome_completo, cpf_cnpj, tipo_pessoa FROM userstable')
        elif 'nome_completo' in columns:
            c.execute('SELECT username, nome_completo FROM userstable')
        else:
            c.execute('SELECT username FROM userstable')
            
        users = c.fetchall()
    except sqlite3.OperationalError:
        users = []
    
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
    
    # Tabela de usuários (se não existir)
    c.execute('''
        CREATE TABLE IF NOT EXISTS userstable (
            username TEXT PRIMARY KEY, 
            password TEXT,
            nome_completo TEXT,
            cpf_cnpj TEXT,
            tipo_pessoa TEXT,
            data_cadastro TEXT
        )
    ''')
    
    # Tabela de despesas - CORRIGIDA (adicionando colunas cpf_cnpj e tipo_pessoa)
    c.execute('''
        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT,
            origin TEXT,
            value REAL,
            category TEXT,
            user_id TEXT,
            cpf_cnpj TEXT,
            tipo_pessoa TEXT
        )
    ''')
    
    # Tabela de receitas - CORRIGIDA (adicionando colunas cpf_cnpj e tipo_pessoa)
    c.execute('''
        CREATE TABLE IF NOT EXISTS incomes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT,
            type TEXT,
            description TEXT,
            value REAL,
            user_id TEXT,
            cpf_cnpj TEXT,
            tipo_pessoa TEXT
        )
    ''')
    
    # VERIFICAR E CRIAR USUÁRIO ADMIN SE NÃO EXISTIR
    c.execute('SELECT * FROM userstable WHERE username = "admin"')
    if not c.fetchone():
        # Criar usuário admin padrão
        c.execute('INSERT INTO userstable(username, password, nome_completo, data_cadastro) VALUES (?, ?, ?, ?)', 
                 ('admin', make_hashes('1234'), 'Administrador', datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    
    conn.commit()
    conn.close()

# Função para verificar e atualizar a estrutura das tabelas se necessário
def check_and_update_tables():
    """Verifica e atualiza a estrutura das tabelas se necessário"""
    conn = sqlite3.connect('finance.db')
    c = conn.cursor()
    
    try:
        # Verificar se a coluna cpf_cnpj existe na tabela expenses
        c.execute("PRAGMA table_info(expenses)")
        columns = [column[1] for column in c.fetchall()]
        
        if 'cpf_cnpj' not in columns:
            # Adicionar colunas faltantes
            c.execute("ALTER TABLE expenses ADD COLUMN cpf_cnpj TEXT")
            c.execute("ALTER TABLE expenses ADD COLUMN tipo_pessoa TEXT")
            st.info("Estrutura da tabela expenses atualizada com sucesso!")
        
        # Verificar se a coluna cpf_cnpj existe na tabela incomes
        c.execute("PRAGMA table_info(incomes)")
        columns = [column[1] for column in c.fetchall()]
        
        if 'cpf_cnpj' not in columns:
            # Adicionar colunas faltantes
            c.execute("ALTER TABLE incomes ADD COLUMN cpf_cnpj TEXT")
            c.execute("ALTER TABLE incomes ADD COLUMN tipo_pessoa TEXT")
            st.info("Estrutura da tabela incomes atualizada com sucesso!")
            
    except Exception as e:
        st.error(f"Erro ao verificar/atualizar tabelas: {str(e)}")
    finally:
        conn.commit()
        conn.close()

# Inicializar tabelas
create_user()
create_tables()

# Funções para gerenciar dados
def add_expense(date, origin, value, category, user_id, cpf_cnpj=None, tipo_pessoa=None):
    conn = sqlite3.connect('finance.db')
    c = conn.cursor()
    c.execute('INSERT INTO expenses(date, origin, value, category, user_id, cpf_cnpj, tipo_pessoa) VALUES (?,?,?,?,?,?,?)', 
              (date, origin, value, category, user_id, cpf_cnpj, tipo_pessoa))
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

def add_income(date, type, description, value, user_id, cpf_cnpj=None, tipo_pessoa=None):
    conn = sqlite3.connect('finance.db')
    c = conn.cursor()
    c.execute('INSERT INTO incomes(date, type, description, value, user_id, cpf_cnpj, tipo_pessoa) VALUES (?,?,?,?,?,?,?)', 
              (date, type, description, value, user_id, cpf_cnpj, tipo_pessoa))
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

# Função para buscar CPF/CNPJ cadastrados
def get_all_cpf_cnpj():
    """Retorna todos os CPF/CNPJ cadastrados no sistema com nomes"""
    conn = sqlite3.connect('finance.db')
    c = conn.cursor()
    
    all_data = {}
    
    try:
        # Buscar CPF/CNPJ de usuários
        c.execute('SELECT cpf_cnpj, nome_completo FROM userstable WHERE cpf_cnpj IS NOT NULL AND cpf_cnpj != ""')
        users_data = c.fetchall()
        
        for cpf_cnpj, nome in users_data:
            if cpf_cnpj:
                all_data[cpf_cnpj] = nome
    except:
        pass
    
    try:
        # Buscar CPF/CNPJ de despesas
        c.execute('SELECT cpf_cnpj, origin FROM expenses WHERE cpf_cnpj IS NOT NULL AND cpf_cnpj != ""')
        expenses_data = c.fetchall()
        
        for cpf_cnpj, origem in expenses_data:
            if cpf_cnpj:
                all_data[cpf_cnpj] = origem
    except:
        pass
    
    try:
        # Buscar CPF/CNPJ de receitas
        c.execute('SELECT cpf_cnpj, description FROM incomes WHERE cpf_cnpj IS NOT NULL AND cpf_cnpj != ""')
        incomes_data = c.fetchall()
        
        for cpf_cnpj, descricao in incomes_data:
            if cpf_cnpj:
                all_data[cpf_cnpj] = descricao
    except:
        pass
    
    conn.close()
    
    # Combinar todos os dados
    all_data = {}
    for cpf_cnpj, nome in users_data:
        if cpf_cnpj:
            all_data[cpf_cnpj] = nome
    
    for cpf_cnpj, origem in expenses_data:
        if cpf_cnpj:
            all_data[cpf_cnpj] = origem
    
    for cpf_cnpj, descricao in incomes_data:
        if cpf_cnpj:
            all_data[cpf_cnpj] = descricao
    
    return all_data

# Funções para manipulação da logo
def get_base64_image(image_path):
    """Converte imagem para base64 (para HTML)"""
    try:
        with open(image_path, "rb") as img_file:
            return base64.b64encode(img_file.read()).decode()
    except:
        return ""

def add_logo_to_excel(df, logo_path, output):
    """Adiciona logo ao Excel usando xlsxwriter"""
    try:
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, sheet_name='Relatório Financeiro', index=False, startrow=3)
            
            workbook = writer.book
            worksheet = writer.sheets['Relatório Financeiro']
            
            # Adicionar cabeçalho com logo
            header_format = workbook.add_format({
                'bold': True,
                'font_size': 16,
                'align': 'center',
                'valign': 'vcenter'
            })
            
            # Mesclar células para o título
            worksheet.merge_range('A1:D1', 'RELATÓRIO FINANCEIRO - IGREJA BATISTA ÁGAPE', header_format)
            worksheet.merge_range('A2:D2', 'Sistema de Gestão Financeira', workbook.add_format({'align': 'center'}))
            
            # Inserir logo se disponível
            if os.path.exists(logo_path):
                try:
                    worksheet.insert_image('A1', logo_path, {'x_offset': 15, 'y_offset': 10, 'x_scale': 0.5, 'y_scale': 0.5})
                except:
                    st.warning("Não foi possível adicionar a logo ao Excel.")
            
            # Ajustar largura das colunas
            worksheet.set_column('A:A', 15)
            worksheet.set_column('B:B', 25)
            worksheet.set_column('C:C', 15)
            worksheet.set_column('D:D', 15)
            
        return True
    except Exception as e:
        st.error(f"Erro ao gerar Excel: {str(e)}")
        return False

# Função para exportar dados para Excel - CORRIGIDA
def export_to_excel(expenses, incomes):
    # Criar DataFrames com verificação de colunas
    expense_data = []
    for expense in expenses:
        # Verificar se os índices existen antes de acessá-los
        cpf_cnpj = expense[6] if len(expense) > 6 else None
        tipo_pessoa = expense[7] if len(expense) > 7 else None
        
        expense_data.append({
            'ID': expense[0],
            'Data': expense[1],
            'Origem': expense[2],
            'Valor': expense[3],
            'Categoria': expense[4],
            'UserID': expense[5],
            'CPF_CNPJ': cpf_cnpj,
            'Tipo_Pessoa': tipo_pessoa
        })
    
    expense_df = pd.DataFrame(expense_data) if expense_data else pd.DataFrame()
    
    income_data = []
    for income in incomes:
        # Verificar se os índices existen antes de acessá-los
        cpf_cnpj = income[6] if len(income) > 6 else None
        tipo_pessoa = income[7] if len(income) > 7 else None
        
        income_data.append({
            'ID': income[0],
            'Data': income[1],
            'Tipo': income[2],
            'Descrição': income[3],
            'Valor': income[4],
            'UserID': income[5],
            'CPF_CNPJ': cpf_cnpj,
            'Tipo_Pessoa': tipo_pessoa
        })
    
    income_df = pd.DataFrame(income_data) if income_data else pd.DataFrame()
    
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
                # Verificar se os índices existen antes de acessá-los
                cpf_cnpj = expense[6] if len(expense) > 6 else None
                tipo_pessoa = expense[7] if len(expense) > 7 else None
                
                combined_data.append({
                    'Tipo': 'Despesa',
                    'Data': expense[1],
                    'Descrição': expense[2],
                    'Valor': -expense[3],
                    'Categoria': expense[4],
                    'CPF/CNPJ': cpf_cnpj,
                    'Tipo Pessoa': tipo_pessoa
                })
            
            for income in incomes:
                # Verificar se os índices existen antes de acessá-los
                cpf_cnpj = income[6] if len(income) > 6 else None
                tipo_pessoa = income[7] if len(income) > 7 else None
                
                combined_data.append({
                    'Tipo': 'Receita',
                    'Data': income[1],
                    'Descrição': income[3],
                    'Valor': income[4],
                    'Categoria': income[2],
                    'CPF/CNPJ': cpf_cnpj,
                    'Tipo Pessoa': tipo_pessoa
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

# Função para exportar relatório em HTML com logo - CORRIGIDA
def export_to_html_with_logo(expenses, incomes, filters=None):
    # Criar DataFrames com verificação de colunas
    expense_data = []
    for expense in expenses:
        # Verificar se os índices existen antes de acessá-los
        cpf_cnpj = expense[6] if len(expense) > 6 else None
        tipo_pessoa = expense[7] if len(expense) > 7 else None
        
        expense_data.append({
            'ID': expense[0],
            'Data': expense[1],
            'Origem': expense[2],
            'Valor': expense[3],
            'Categoria': expense[4],
            'UserID': expense[5],
            'CPF_CNPJ': cpf_cnpj,
            'Tipo_Pessoa': tipo_pessoa
        })
    
    expense_df = pd.DataFrame(expense_data) if expense_data else pd.DataFrame()
    
    income_data = []
    for income in incomes:
        # Verificar se os índices existen antes de acessá-los
        cpf_cnpj = income[6] if len(income) > 6 else None
        tipo_pessoa = income[7] if len(income) > 7 else None
        
        income_data.append({
            'ID': income[0],
            'Data': income[1],
            'Tipo': income[2],
            'Descrição': income[3],
            'Valor': income[4],
            'UserID': income[5],
            'CPF_CNPJ': cpf_cnpj,
            'Tipo_Pessoa': tipo_pessoa
        })
    
    income_df = pd.DataFrame(income_data) if income_data else pd.DataFrame()
    
    # Formatar datas para o formato brasileiro
    if not expense_df.empty:
        expense_df['Data'] = pd.to_datetime(expense_df['Data']).dt.strftime("%d/%m/%Y")
    if not income_df.empty:
        income_df['Data'] = pd.to_datetime(income_df['Data']).dt.strftime("%d/%m/%Y")
    
    # Calcular totais
    total_expenses = expense_df['Valor'].sum() if not expense_df.empty else 0
    total_income = income_df['Valor'].sum() if not income_df.empty else 0
    balance = total_income - total_expenses
    
    # Verificar se a logo existe e converter para base64
    logo_base64 = ""
    logo_path = "logo_igreja.png"
    if os.path.exists(logo_path):
        logo_base64 = get_base64_image(logo_path)
    
    # Criar conteúdo HTML para o relatório
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>Relatório Financeiro - Igreja Batista Ágape</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 40px; color: #333; }}
            .header {{
                display: flex;
                align-items: center;
                margin-bottom: 30px;
                border-bottom: 2px solid #4CAF50;
                padding-bottom: 20px;
            }}
            .logo {{
                margin-right: 20px;
            }}
            .title {{
                color: #2E7D32;
            }}
            table {{
                border-collapse: collapse;
                width: 100%;
                margin-top: 20px;
            }}
            th, td {{
                border: 1px solid #ddd;
                padding: 12px;
                text-align: left;
            }}
            th {{
                background-color: #4CAF50;
                color: white;
            }}
            tr:nth-child(even) {{
                background-color: #f2f2f2;
            }}
            .summary {{
                margin-top: 30px;
                padding: 20px;
                background-color: #E8F5E9;
                border-radius: 5px;
            }}
            .footer {{
                margin-top: 50px;
                text-align: center;
                font-size: 0.8em;
                color: #777;
            }}
        </style>
    </head>
    <body>
        <div class="header">
            {"<img class='logo' src='data:image/png;base64,{}' alt='Logo Igreja' width='100'>".format(logo_base64) if logo_base64 else ""}
            <div>
                <h1 class="title">Relatório Financeiro</h1>
                <h2>Igreja Batista Ágape</h2>
                <p>Usuário: {st.session_state.username}</p>
                <p>Data do relatório: {datetime.now().strftime('%d/%m/%Y às %H:%M')}</p>
            </div>
        </div>
        
        <div class="summary">
            <h3>Resumo Financeiro</h3>
            <p><strong>Total de Receitas:</strong> R$ {total_income:,.2f}</p>
            <p><strong>Total de Despesas:</strong> R$ {total_expenses:,.2f}</p>
            <p><strong>Saldo:</strong> R$ {balance:,.2f}</p>
        </div>
    """
    
    # Adicionar despesas
    if not expense_df.empty:
        html_content += """
        <h2>Despesas</h2>
        <table>
            <tr>
                <th>Data</th>
                <th>Origem</th>
                <th>Categoria</th>
                <th>CPF/CNPJ</th>
                <th>Tipo Pessoa</th>
                <th>Valor (R$)</th>
            </tr>
        """
        for _, row in expense_df.iterrows():
            cpf_cnpj_formatado = format_cpf(row['CPF_CNPJ']) if row['Tipo_Pessoa'] == "Física" else format_cnpj(row['CPF_CNPJ']) if row['CPF_CNPJ'] else "N/A"
            html_content += f"""
            <tr>
                <td>{row['Data']}</td>
                <td>{row['Origem']}</td>
                <td>{row['Categoria']}</td>
                <td>{cpf_cnpj_formatado}</td>
                <td>{row['Tipo_Pessoa'] if pd.notna(row['Tipo_Pessoa']) else 'N/A'}</td>
                <td>{row['Valor']:,.2f}</td>
            </tr>
            """
        html_content += "</table>"
    
    # Adicionar receitas
    if not income_df.empty:
        html_content += """
        <h2>Receitas</h2>
        <table>
            <tr>
                <th>Data</th>
                <th>Tipo</th>
                <th>Descrição</th>
                <th>CPF/CNPJ</th>
                <th>Tipo Pessoa</th>
                <th>Valor (R$)</th>
            </tr>
        """
        for _, row in income_df.iterrows():
            cpf_cnpj_formatado = format_cpf(row['CPF_CNPJ']) if row['Tipo_Pessoa'] == "Física" else format_cnpj(row['CPF_CNPJ']) if row['CPF_CNPJ'] else "N/A"
            html_content += f"""
            <tr>
                <td>{row['Data']}</td>
                <td>{row['Tipo']}</td>
                <td>{row['Descrição']}</td>
                <td>{cpf_cnpj_formatado}</td>
                <td>{row['Tipo_Pessoa'] if pd.notna(row['Tipo_Pessoa']) else 'N/A'}</td>
                <td>{row['Valor']:,.2f}</td>
            </tr>
            """
        html_content += "</table>"
    
    html_content += """
        <div class="footer">
            Relatório gerado em """ + datetime.now().strftime('%d/%m/%Y %H:%M') + """ | Sistema de Controle Financeiro - Igreja Batista Ágape
        </div>
    </body>
    </html>
    """
    
    # Retornar o conteúdo HTML para download
    return html_content

# Função para importar dados de planilha
def import_from_spreadsheet(file, user_id, is_income=False):
    try:
        # Ler a planilha
        if file.name.endswith('.csv'):
            df = pd.read_csv(file, sep=';')
        else:
            df = pd.read_excel(file)
        
        # Verificar colunas necessárias
        required_columns = ['Data', 'Valor']
        if is_income:
            required_columns.extend(['Tipo', 'Descrição'])
        else:
            required_columns.extend(['Origem', 'Categoria'])
        
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            return False, f"Colunas faltantes: {', '.join(missing_columns)}"
        
        # Processar cada linha
        success_count = 0
        error_count = 0
        errors = []
        
        for _, row in df.iterrows():
            try:
                # Converter data
                if isinstance(row['Data'], str):
                    try:
                        date_obj = datetime.strptime(row['Data'], "%d/%m/%Y")
                    except:
                        date_obj = datetime.strptime(row['Data'], "%Y-%m-%d")
                else:
                    date_obj = row['Data']
                
                db_date = date_obj.strftime("%Y-%m-%d")
                
                # Extrair CPF/CNPJ se disponível
                cpf_cnpj = None
                tipo_pessoa = None
                
                if 'CPF' in df.columns and pd.notna(row.get('CPF')):
                    cpf_cnpj = re.sub(r'[^0-9]', '', str(row['CPF']))
                    if len(cpf_cnpj) == 11:
                        tipo_pessoa = 'Física'
                    elif len(cpf_cnpj) == 14:
                        tipo_pessoa = 'Jurídica'
                
                if 'CNPJ' in df.columns and pd.notna(row.get('CNPJ')):
                    cpf_cnpj = re.sub(r'[^0-9]', '', str(row['CNPJ']))
                    tipo_pessoa = 'Jurídica'
                
                if 'CPF_CNPJ' in df.columns and pd.notna(row.get('CPF_CNPJ')):
                    cpf_cnpj = re.sub(r'[^0-9]', '', str(row['CPF_CNPJ']))
                    if len(cpf_cnpj) == 11:
                        tipo_pessoa = 'Física'
                    elif len(cpf_cnpj) == 14:
                        tipo_pessoa = 'Jurídica'
                
                # Inserir no banco de dados
                if is_income:
                    add_income(
                        db_date,
                        row['Tipo'],
                        row['Descrição'],
                        float(row['Valor']),
                        user_id,
                        cpf_cnpj,
                        tipo_pessoa
                    )
                else:
                    add_expense(
                        db_date,
                        row['Origem'],
                        float(row['Valor']),
                        row['Categoria'],
                        user_id,
                        cpf_cnpj,
                        tipo_pessoa
                    )
                
                success_count += 1
                
            except Exception as e:
                error_count += 1
                errors.append(f"Linha {_ + 2}: {str(e)}")
        
        return True, f"Importação concluída: {success_count} registros importados, {error_count} erros."
    
    except Exception as e:
        return False, f"Erro ao processar planilha: {str(e)}"

# Interface principal da aplicação
def main():
    # Inicializar banco
    create_user()
    create_tables()
    check_and_update_tables()  # Verificar e atualizar estrutura das tabelas
    
    
    # Inicializar estado da sessão
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False
    if 'username' not in st.session_state:
        st.session_state.username = ""
    if 'page' not in st.session_state:
        st.session_state.page = "Login"
    if 'is_admin' not in st.session_state:
        st.session_state.is_admin = False
    if 'user_info' not in st.session_state:
        st.session_state.user_info = None
    
    # Navegação principal baseada no estado de login
    if not st.session_state.logged_in:
        # Mostrar APENAS a página de login
        show_login_page()
    else:
        # VERIFICAR SE PRECISA COMPLETAR CADASTRO
        if st.session_state.user_info is None:
            st.session_state.user_info = get_user_info(st.session_state.username)
        
        if st.session_state.user_info and (st.session_state.user_info[0] is None or st.session_state.user_info[0] == ''):
            show_complete_registration_page()
        else:
            show_main_app()
            show_expense_form()

# Página de login
def show_login_page():
    # Limpar qualquer conteúdo anterior
    st.empty()
    
    # Centralizar o formulário de login
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.title("✝️ Igreja Batista Ágape")
        st.subheader("Sistema de Controle Financeiro")
        
        # Adicionar logo se disponível
        logo_path = "logo_igreja.png"
        if os.path.exists(logo_path):
            st.image(logo_path, width=150)
        
        # Formulário de login
        with st.form("login_form"):
            username = st.text_input("Usuário")
            password = st.text_input("Senha", type="password")
            submitted = st.form_submit_button("Entrar")
            
            if submitted:
                if username and password:
                    hashed_password = make_hashes(password)
                    result = login_user(username, hashed_password)
                    
                    if result:
                        st.session_state.logged_in = True
                        st.session_state.username = username
                        st.session_state.user_info = get_user_info(username)
                        st.session_state.is_admin = (username == "admin")
                        st.success(f"Bem-vindo(a), {username}!")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error("Usuário ou senha incorretos")
                else:
                    st.warning("Por favor, preencha todos os campos")
        
        # Link para criar conta
        st.markdown("---")
        if st.button("Criar nova conta"):
            st.session_state.page = "Criar Conta"
            st.rerun()
        
        # Informações de acesso de demonstração
        st.info("""
        **Acesso de demonstração:**
        - Usuário: admin
        - Senha: 1234
        """)

# Página de registro
def show_complete_registration_page():
    st.title("✝️ Complete seu Cadastro")
    st.write("Para continuar usando o sistema, precisamos de algumas informações adicionais:")
    
    with st.form("complete_registration"):
        nome_completo = st.text_input("Nome Completo*")
        
        tipo_pessoa = st.radio("Tipo de Pessoa*", ["Física", "Jurídica"])
        
        if tipo_pessoa == "Física":
            cpf_cnpj = st.text_input("CPF*", placeholder="000.000.000-00")
            if cpf_cnpj:
                if not validate_cpf(cpf_cnpj):
                    st.error("CPF inválido. Por favor, verifique o número.")
        else:
            cpf_cnpj = st.text_input("CNPJ*", placeholder="00.000.000/0000-00")
            if cpf_cnpj:
                if not validate_cnpj(cpf_cnpj):
                    st.error("CNPJ inválido. Por favor, verifique o número.")
        
        submitted = st.form_submit_button("Salvar e Continuar")
        
        if submitted:
            if nome_completo and cpf_cnpj:
                if (tipo_pessoa == "Física" and validate_cpf(cpf_cnpj)) or (tipo_pessoa == "Jurídica" and validate_cnpj(cpf_cnpj)):
                    # Salvar informações no banco de dados
                    update_user_info(st.session_state.username, nome_completo, cpf_cnpj, tipo_pessoa)
                    st.session_state.user_info = (nome_completo, cpf_cnpj, tipo_pessoa)
                    st.success("Cadastro completado com sucesso!")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("Por favor, insira um CPF ou CNPJ válido.")
            else:
                st.error("Por favor, preencha todos os campos obrigatórios.")

# Página principal da aplicação
def show_main_app():
    # Menu lateral
    with st.sidebar:
        st.title(f"✝️ Bem-vindo(a), {st.session_state.username}")
        
        # Exibir informações do usuário se disponíveis
        if st.session_state.user_info:
            nome_completo, cpf_cnpj, tipo_pessoa = st.session_state.user_info
            st.write(f"**Nome:** {nome_completo}")
            if cpf_cnpj:
                if tipo_pessoa == "Física":
                    st.write(f"**CPF:** {format_cpf(cpf_cnpj)}")
                else:
                    st.write(f"**CNPJ:** {format_cnpj(cpf_cnpj)}")
        
        st.markdown("---")
        
        # Menu de navegação
        menu_options = ["📊 Dashboard", "💸 Registrar Despesa", "💰 Registrar Receita", 
                       "📋 Visualizar Relatórios", "⚙️ Configurações"]
        
        if st.session_state.is_admin:
            menu_options.append("👥 Gerenciar Usuários")
        
        selected_option = st.radio("Navegação", menu_options)
        
        st.markdown("---")
        
        # Botão de logout
        if st.button("🚪 Sair"):
            st.session_state.logged_in = False
            st.session_state.username = ""
            st.session_state.user_info = None
            st.session_state.is_admin = False
            st.rerun()
    
    # Conteúdo principal baseado na seleção do menu
    if selected_option == "📊 Dashboard":
        show_dashboard()
    elif selected_option == "💸 Registrar Despesa":
        show_expense_form()
    elif selected_option == "💰 Registrar Receita":
        show_income_form()
    elif selected_option == "📋 Visualizar Relatórios":
        show_reports()
    elif selected_option == "⚙️ Configurações":
        show_settings()
    elif selected_option == "👥 Gerenciar Usuários" and st.session_state.is_admin:
        show_user_management()

# Dashboard
def show_dashboard():
    st.title("📊 Dashboard Financeiro")
    
    # Obter dados
    expenses = get_expenses(st.session_state.username)
    incomes = get_incomes(st.session_state.username)
    
    # Converter para DataFrame
    expense_data = []
    for expense in expenses:
        expense_data.append({
            'Data': expense[1],
            'Origem': expense[2],
            'Valor': expense[3],
            'Categoria': expense[4]
        })
    
    income_data = []
    for income in incomes:
        income_data.append({
            'Data': income[1],
            'Tipo': income[2],
            'Descrição': income[3],
            'Valor': income[4]
        })
    
    expense_df = pd.DataFrame(expense_data) if expense_data else pd.DataFrame(columns=['Data', 'Origem', 'Valor', 'Categoria'])
    income_df = pd.DataFrame(income_data) if income_data else pd.DataFrame(columns=['Data', 'Tipo', 'Descrição', 'Valor'])
    
    # Calcular métricas
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
        st.metric("Saldo", f"R$ {balance:,.2f}", delta=f"{balance:,.2f}")
    
    # Filtros de data
    st.subheader("Filtros")
    col1, col2 = st.columns(2)
    
    with col1:
        start_date = st.date_input("Data inicial", value=dt_date.today().replace(day=1))  # Corrigido para dt_date
    with col2:
        end_date = st.date_input("Data final", value=dt_date.today())  # Corrigido para dt_date
    
    # Aplicar filtros
    if not expense_df.empty:
        expense_df['Data'] = pd.to_datetime(expense_df['Data'])
        filtered_expenses = expense_df[(expense_df['Data'] >= pd.to_datetime(start_date)) & 
                                      (expense_df['Data'] <= pd.to_datetime(end_date))]
    else:
        filtered_expenses = expense_df
    
    if not income_df.empty:
        income_df['Data'] = pd.to_datetime(income_df['Data'])
        filtered_incomes = income_df[(income_df['Data'] >= pd.to_datetime(start_date)) & 
                                    (income_df['Data'] <= pd.to_datetime(end_date))]
    else:
        filtered_incomes = income_df
    
    # Gráficos
    col1, col2 = st.columns(2)
    
    with col1:
        if not filtered_expenses.empty:
            st.subheader("Despesas por Categoria")
            expenses_by_category = filtered_expenses.groupby('Categoria')['Valor'].sum().reset_index()
            fig = px.pie(expenses_by_category, values='Valor', names='Categoria')
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Nenhuma despesa registrada no período selecionado.")
    
    with col2:
        if not filtered_incomes.empty:
            st.subheader("Receitas por Tipo")
            incomes_by_type = filtered_incomes.groupby('Tipo')['Valor'].sum().reset_index()
            fig = px.pie(incomes_by_type, values='Valor', names='Tipo')
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Nenhuma receita registrada no período selecionado.")
    
    # Tabela de últimas transações
    st.subheader("Últimas Transações")
    
    # Combinar despesas e receitas
    all_transactions = []
    
    for expense in expenses[-10:]:  # Últimas 10 despesas
        all_transactions.append({
            'Data': format_brazilian_date(expense[1]),
            'Tipo': 'Despesa',
            'Descrição': expense[2],
            'Categoria': expense[4],
            'Valor': -expense[3]
        })
    
    for income in incomes[-10:]:  # Últimas 10 receitas
        all_transactions.append({
            'Data': format_brazilian_date(income[1]),
            'Tipo': 'Receita',
            'Descrição': income[3],
            'Categoria': income[2],
            'Valor': income[4]
        })
    
    # Ordenar por data (mais recente primeiro)
    if all_transactions:
        all_transactions.sort(key=lambda x: datetime.strptime(x['Data'], '%d/%m/%Y'), reverse=True)
        transactions_df = pd.DataFrame(all_transactions[:10])  # Mostrar apenas as 10 mais recentes
        st.dataframe(transactions_df, use_container_width=True)
    else:
        st.info("Nenhuma transação registrada.")

# Formulário de despesa
def show_income_form():
    show_expense_form()
    st.title("💰 Registrar Receita")
    
    with st.form("income_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            income_date = st.date_input("Data*", value=dt_date.today())
            type_income = st.selectbox("Tipo de Receita*", 
                                     ["Dízimo", "Oferta", "Doação", "Evento", "Outros"])
            value = st.number_input("Valor (R$)*", min_value=0.01, step=0.01, format="%.2f")
        
        with col2:
            description = st.text_input("Descrição*")
            
            # Opções para CPF/CNPJ
            tipo_pessoa = st.radio("Tipo de Pessoa", ["Física", "Jurídica", "Não informar"])
            
            if tipo_pessoa != "Não informar":
                if tipo_pessoa == "Física":
                    cpf_cnpj = st.text_input("CPF do Doador", placeholder="000.000.000-00")
                    if cpf_cnpj and not validate_cpf(cpf_cnpj):
                        st.error("CPF inválido. Por favor, verifique o número.")
                else:
                    cpf_cnpj = st.text_input("CNPJ do Doador", placeholder="00.000.000/0000-00")
                    if cpf_cnpj and not validate_cnpj(cpf_cnpj):
                        st.error("CNPJ inválido. Por favor, verifique o número.")
            else:
                cpf_cnpj = None
        
        submitted = st.form_submit_button("Registrar Receita")
        
        if submitted:
            if description and value > 0:
                try:
                    # Se CPF/CNPJ foi fornecido, usar tipo_pessoa correspondente
                    if tipo_pessoa == "Não informar":
                        add_income(
                            income_date.strftime("%Y-%m-%d"),
                            type_income,
                            description,
                            value,
                            st.session_state.username
                        )
                    else:
                        # Validar CPF/CNPJ antes de inserir
                        cpf_cnpj_clean = re.sub(r'[^0-9]', '', cpf_cnpj) if cpf_cnpj else None
                        
                        if (tipo_pessoa == "Física" and validate_cpf(cpf_cnpj_clean)) or \
                           (tipo_pessoa == "Jurídica" and validate_cnpj(cpf_cnpj_clean)):
                            add_income(
                                income_date.strftime("%Y-%m-%d"),
                                type_income,
                                description,
                                value,
                                st.session_state.username,
                                cpf_cnpj_clean,
                                tipo_pessoa
                            )
                        else:
                            st.error("CPF/CNPJ inválido. A receita será cadastrada sem informações do doador.")
                            add_income(
                                income_date.strftime("%Y-%m-%d"),
                                type_income,
                                description,
                                value,
                                st.session_state.username
                            )
                    
                    st.success("Receita registrada com sucesso!")
                    time.sleep(1)
                    st.rerun()
                except sqlite3.OperationalError as e:
                    if "no such column" in str(e):
                        st.error("Erro na estrutura do banco de dados. Atualizando tabelas...")
                        check_and_update_tables()
                        st.rerun()
                    else:
                        st.error(f"Erro ao registrar receita: {str(e)}")
                except Exception as e:
                    st.error(f"Erro ao registrar receita: {str(e)}")
            else:
                st.error("Por favor, preencha todos os campos obrigatórios.")

# Relatórios
def show_reports():
    st.title("📋 Relatórios Financeiros")
    
    # Obter dados
    expenses = get_expenses(st.session_state.username)
    incomes = get_incomes(st.session_state.username)
    
    # Filtros
    st.subheader("Filtros")
    col1, col2 = st.columns(2)
    
    with col1:
        start_date = st.date_input("Data inicial", value=dt_date.today().replace(day=1))  # Corrigido para dt_date
    with col2:
        end_date = st.date_input("Data final", value=dt_date.today())  # Corrigido para dt_date
    
    # Filtrar dados
    filtered_expenses = []
    for expense in expenses:
        expense_date = datetime.strptime(expense[1], "%Y-%m-%d").date()
        if start_date <= expense_date <= end_date:
            filtered_expenses.append(expense)
    
    filtered_incomes = []
    for income in incomes:
        income_date = datetime.strptime(income[1], "%Y-%m-%d").date()
        if start_date <= income_date <= end_date:
            filtered_incomes.append(income)
    
    # Calcular totais
    total_expenses = sum(expense[3] for expense in filtered_expenses)
    total_income = sum(income[4] for income in filtered_incomes)
    balance = total_income - total_expenses
    
    # Exibir resumo
    st.subheader("Resumo do Período")
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Receitas", f"R$ {total_income:,.2f}")
    col2.metric("Total Despesas", f"R$ {total_expenses:,.2f}")
    col3.metric("Saldo", f"R$ {balance:,.2f}", delta=f"{balance:,.2f}")
    
    # Tabela de despesas
    st.subheader("Despesas Detalhadas")
    if filtered_expenses:
        expense_data = []
        for expense in filtered_expenses:
            # Verificar se os índices existen antes de acessá-los
            cpf_cnpj = expense[6] if len(expense) > 6 else None
            tipo_pessoa = expense[7] if len(expense) > 7 else None
            
            expense_data.append({
                'ID': expense[0],
                'Data': format_brazilian_date(expense[1]),
                'Origem': expense[2],
                'Valor': expense[3],
                'Categoria': expense[4],
                'CPF/CNPJ': cpf_cnpj,
                'Tipo Pessoa': tipo_pessoa
            })
        
        expense_df = pd.DataFrame(expense_data)
        st.dataframe(expense_df, use_container_width=True, hide_index=True)
    else:
        st.info("Nenhuma despesa no período selecionado.")
    
    # Tabela de receitas
    st.subheader("Receitas Detalhadas")
    if filtered_incomes:
        income_data = []
        for income in filtered_incomes:
            # Verificar se os índices existen antes de acessá-los
            cpf_cnpj = income[6] if len(income) > 6 else None
            tipo_pessoa = income[7] if len(income) > 7 else None
            
            income_data.append({
                'ID': income[0],
                'Data': format_brazilian_date(income[1]),
                'Tipo': income[2],
                'Descrição': income[3],
                'Valor': income[4],
                'CPF/CNPJ': cpf_cnpj,
                'Tipo Pessoa': tipo_pessoa
            })
        
        income_df = pd.DataFrame(income_data)
        st.dataframe(income_df, use_container_width=True, hide_index=True)
    else:
        st.info("Nenhuma receita no período selecionado.")
    
    # Opções de exportação
    st.subheader("Exportar Relatório")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("📄 Exportar para Excel"):
            excel_data = export_to_excel(filtered_expenses, filtered_incomes)
            st.download_button(
                label="⬇️ Baixar Arquivo Excel",
                data=excel_data,
                file_name=f"relatorio_financeiro_{date.today().strftime('%Y%m%d')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
    
    with col2:
        if st.button("🌐 Exportar para HTML"):
            html_content = export_to_html_with_logo(filtered_expenses, filtered_incomes)
            st.download_button(
                label="⬇️ Baixar Relatório HTML",
                data=html_content,
                file_name=f"relatorio_financeiro_{date.today().strftime('%Y%m%d')}.html",
                mime="text/html"
            )
    
    with col3:
        if st.button("📊 Gerar Gráficos"):
            show_charts(filtered_expenses, filtered_incomes)

# Função para mostrar gráficos
def show_charts(expenses, incomes):
    st.title("📊 Análise Gráfica")
    
    # Converter para DataFrame
    expense_data = []
    for expense in expenses:
        expense_data.append({
            'Data': expense[1],
            'Origem': expense[2],
            'Valor': expense[3],
            'Categoria': expense[4]
        })
    
    income_data = []
    for income in incomes:
        income_data.append({
            'Data': income[1],
            'Tipo': income[2],
            'Descrição': income[3],
            'Valor': income[4]
        })
    
    expense_df = pd.DataFrame(expense_data) if expense_data else pd.DataFrame()
    income_df = pd.DataFrame(income_data) if income_data else pd.DataFrame()
    
    # Gráfico de evolução temporal
    if not expense_df.empty or not income_df.empty:
        st.subheader("Evolução Temporal")
        
        # Preparar dados para o gráfico de linha
        timeline_data = []
        
        if not expense_df.empty:
            expense_df['Data'] = pd.to_datetime(expense_df['Data'])
            daily_expenses = expense_df.groupby('Data')['Valor'].sum().reset_index()
            daily_expenses['Tipo'] = 'Despesa'
            timeline_data.append(daily_expenses)
        
        if not income_df.empty:
            income_df['Data'] = pd.to_datetime(income_df['Data'])
            daily_incomes = income_df.groupby('Data')['Valor'].sum().reset_index()
            daily_incomes['Tipo'] = 'Receita'
            timeline_data.append(daily_incomes)
        
        if timeline_data:
            timeline_df = pd.concat(timeline_data)
            fig = px.line(timeline_df, x='Data', y='Valor', color='Tipo', 
                         title='Evolução de Receitas e Despesas ao Longo do Tempo')
            st.plotly_chart(fig, use_container_width=True)
    
    # Gráficos de pizza
    col1, col2 = st.columns(2)
    
    with col1:
        if not expense_df.empty:
            st.subheader("Distribuição de Despesas por Categoria")
            expenses_by_category = expense_df.groupby('Categoria')['Valor'].sum().reset_index()
            fig = px.pie(expenses_by_category, values='Valor', names='Categoria')
            st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        if not income_df.empty:
            st.subheader("Distribuição de Receitas por Tipo")
            incomes_by_type = income_df.groupby('Tipo')['Valor'].sum().reset_index()
            fig = px.pie(incomes_by_type, values='Valor', names='Tipo')
            st.plotly_chart(fig, use_container_width=True)
    
    # Comparativo mensal
    if not expense_df.empty or not income_df.empty:
        st.subheader("Comparativo Mensal")
        
        # Preparar dados mensais
        monthly_data = []
        
        if not expense_df.empty:
            expense_df['Mês'] = expense_df['Data'].dt.to_period('M')
            monthly_expenses = expense_df.groupby('Mês')['Valor'].sum().reset_index()
            monthly_expenses['Tipo'] = 'Despesa'
            monthly_data.append(monthly_expenses)
        
        if not income_df.empty:
            income_df['Mês'] = income_df['Data'].dt.to_period('M')
            monthly_incomes = income_df.groupby('Mês')['Valor'].sum().reset_index()
            monthly_incomes['Tipo'] = 'Receita'
            monthly_data.append(monthly_incomes)
        
        if monthly_data:
            monthly_df = pd.concat(monthly_data)
            monthly_df['Mês'] = monthly_df['Mês'].astype(str)
            
            fig = px.bar(monthly_df, x='Mês', y='Valor', color='Tipo', barmode='group',
                        title='Comparativo Mensal de Receitas e Despesas')
            st.plotly_chart(fig, use_container_width=True)

# Configurações
def show_settings():
    st.title("⚙️ Configurações")
    
    # Informações do usuário
    st.subheader("Informações do Usuário")
    
    user_info = get_user_info(st.session_state.username)
    if user_info:
        nome_completo, cpf_cnpj, tipo_pessoa = user_info
        
        with st.form("user_settings"):
            new_nome = st.text_input("Nome Completo", value=nome_completo if nome_completo else "")
            
            if tipo_pessoa:
                st.write(f"Tipo de Pessoa: {tipo_pessoa}")
                if tipo_pessoa == "Física":
                    st.write(f"CPF: {format_cpf(cpf_cnpj) if cpf_cnpj else 'Não informado'}")
                else:
                    st.write(f"CNPJ: {format_cnpj(cpf_cnpj) if cpf_cnpj else 'Não informado'}")
            
            submitted = st.form_submit_button("Atualizar Informações")
            
            if submitted:
                if new_nome:
                    update_user_info(st.session_state.username, new_nome, cpf_cnpj, tipo_pessoa)
                    st.success("Informações atualizadas com sucesso!")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("O nome completo é obrigatório.")
    
    # Importação/Exportação de dados
    st.subheader("Importar/Exportar Dados")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("**Importar Dados**")
        
        import_option = st.radio("Tipo de Dados", ["Despesas", "Receitas"])
        
        uploaded_file = st.file_uploader("Selecionar arquivo", type=["xlsx", "xls", "csv"])
        
        if uploaded_file:
            if st.button("Importar Dados"):
                with st.spinner("Importando dados..."):
                    success, message = import_from_spreadsheet(
                        uploaded_file, 
                        st.session_state.username, 
                        is_income=(import_option == "Receitas")
                    )
                    
                    if success:
                        st.success(message)
                        time.sleep(2)
                        st.rerun()
                    else:
                        st.error(message)
    
    with col2:
        st.write("**Exportar Dados**")
        
        # Obter todos os dados
        all_expenses = get_expenses(st.session_state.username)
        all_incomes = get_incomes(st.session_state.username)
        
        if st.button("Exportar Todos os Dados"):
            excel_data = export_to_excel(all_expenses, all_incomes)
            st.download_button(
                label="⬇️ Baixar Arquivo Excel",
                data=excel_data,
                file_name=f"dados_completos_{date.today().strftime('%Y%m%d')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
    
    # Limpar dados
    st.subheader("Limpar Dados")
    st.warning("⚠️ Esta ação não pode ser desfeita!")
    
    if st.button("❌ Limpar Todos os Dados"):
        # Implementar lógica para limpar dados do usuário atual
        st.error("Funcionalidade ainda não implementada.")

# Gerenciamento de usuários (apenas admin)
def show_user_management():
    st.title("👥 Gerenciamento de Usuários")
    
    # Listar usuários
    st.subheader("Usuários Cadastrados")
    
    users = get_all_users()
    if users:
        user_data = []
        for user in users:
            # Verificar estrutura dos dados retornados
            if len(user) >= 4:
                username, nome_completo, cpf_cnpj, tipo_pessoa = user[0], user[1], user[2], user[3]
                user_data.append({
                    'Usuário': username,
                    'Nome': nome_completo,
                    'CPF/CNPJ': cpf_cnpj,
                    'Tipo': tipo_pessoa
                })
            elif len(user) >= 2:
                username, nome_completo = user[0], user[1]
                user_data.append({
                    'Usuário': username,
                    'Nome': nome_completo,
                    'CPF/CNPJ': 'N/A',
                    'Tipo': 'N/A'
                })
            else:
                username = user[0]
                user_data.append({
                    'Usuário': username,
                    'Nome': 'N/A',
                    'CPF/CNPJ': 'N/A',
                    'Tipo': 'N/A'
                })
        
        users_df = pd.DataFrame(user_data)
        st.dataframe(users_df, use_container_width=True, hide_index=True)
    else:
        st.info("Nenhum usuário cadastrado.")
    
    # Adicionar novo usuário
    st.subheader("Adicionar Novo Usuário")
    
    with st.form("add_user_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            new_username = st.text_input("Nome de usuário*")
            new_password = st.text_input("Senha*", type="password")
            confirm_password = st.text_input("Confirmar Senha*", type="password")
        
        with col2:
            nome_completo = st.text_input("Nome Completo*")
            tipo_pessoa = st.radio("Tipo de Pessoa*", ["Física", "Jurídica"])
            
            if tipo_pessoa == "Física":
                cpf_cnpj = st.text_input("CPF*", placeholder="000.000.000-00")
                if cpf_cnpj and not validate_cpf(cpf_cnpj):
                    st.error("CPF inválido. Por favor, verifique o número.")
            else:
                cpf_cnpj = st.text_input("CNPJ*", placeholder="00.000.000/0000-00")
                if cpf_cnpj and not validate_cnpj(cpf_cnpj):
                    st.error("CNPJ inválido. Por favor, verifique o número.")
        
        submitted = st.form_submit_button("Adicionar Usuário")
        
        if submitted:
            if new_username and new_password and confirm_password and nome_completo and cpf_cnpj:
                if new_password == confirm_password:
                    if (tipo_pessoa == "Física" and validate_cpf(cpf_cnpj)) or (tipo_pessoa == "Jurídica" and validate_cnpj(cpf_cnpj)):
                        try:
                            add_user(
                                new_username, 
                                make_hashes(new_password), 
                                nome_completo, 
                                re.sub(r'[^0-9]', '', cpf_cnpj), 
                                tipo_pessoa
                            )
                            st.success(f"Usuário {new_username} adicionado com sucesso!")
                            time.sleep(1)
                            st.rerun()
                        except sqlite3.IntegrityError:
                            st.error("Nome de usuário já existe. Escolha outro.")
                    else:
                        st.error("Por favor, insira um CPF ou CNPJ válido.")
                else:
                    st.error("As senhas não coincidem.")
            else:
                st.error("Por favor, preencha todos os campos obrigatórios.")
    
    # Remover usuário
    st.subheader("Remover Usuário")
    
    if users:
        user_to_delete = st.selectbox("Selecionar usuário para remover", [user[0] for user in users if user[0] != "admin"])
        
        if st.button("🗑️ Remover Usuário"):
            if user_to_delete != "admin":
                delete_user(user_to_delete)
                st.success(f"Usuário {user_to_delete} removido com sucesso!")
                time.sleep(1)
                st.rerun()
            else:
                st.error("Não é possível remover o usuário administrador.")
    else:
        st.info("Nenhum usuário para remover.")

# Executar a aplicação
if __name__ == "__main__":
    main()