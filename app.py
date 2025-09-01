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
    try:
        st.rerun()
    except:
        try:
            st.rerun()
        except:
            pass

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
    c.execute('SELECT username, nome_completo, cpf_cnpj, tipo_pessoa FROM userstable')
    users = c.fetchall()
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
    
    # Tabela de despesas
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
    
    # Tabela de receitas
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

# Função para exportar dados para Excel
def export_to_excel(expenses, incomes):
    # Criar DataFrames
    expense_df = pd.DataFrame(expenses, columns=['ID', 'Data', 'Origem', 'Valor', 'Categoria', 'UserID', 'CPF_CNPJ', 'Tipo_Pessoa']) if expenses else pd.DataFrame()
    income_df = pd.DataFrame(incomes, columns=['ID', 'Data', 'Tipo', 'Descrição', 'Valor', 'UserID', 'CPF_CNPJ', 'Tipo_Pessoa']) if incomes else pd.DataFrame()
    
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
                    'Data': expense[1],
                    'Descrição': expense[2],
                    'Valor': -expense[3],
                    'Categoria': expense[4],
                    'CPF/CNPJ': expense[6],
                    'Tipo Pessoa': expense[7]
                })
            
            for income in incomes:
                combined_data.append({
                    'Tipo': 'Receita',
                    'Data': income[1],
                    'Descrição': income[3],
                    'Valor': income[4],
                    'Categoria': income[2],
                    'CPF/CNPJ': income[6],
                    'Tipo Pessoa': income[7]
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

# Função para exportar relatório em HTML com logo
def export_to_html_with_logo(expenses, incomes, filters=None):
    # Criar DataFrames
    expense_df = pd.DataFrame(expenses, columns=['ID', 'Data', 'Origem', 'Valor', 'Categoria', 'UserID', 'CPF_CNPJ', 'Tipo_Pessoa']) if expenses else pd.DataFrame()
    income_df = pd.DataFrame(incomes, columns=['ID', 'Data', 'Tipo', 'Descrição', 'Valor', 'UserID', 'CPF_CNPJ', 'Tipo_Pessoa']) if incomes else pd.DataFrame()
    
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
            html_content += f"""
            <tr>
                <td>{row['Data']}</td>
                <td>{row['Origem']}</td>
                <td>{row['Categoria']}</td>
                <td>{row['CPF_CNPJ'] if pd.notna(row['CPF_CNPJ']) else 'N/A'}</td>
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
            html_content += f"""
            <tr>
                <td>{row['Data']}</td>
                <td>{row['Tipo']}</td>
                <td>{row['Descrição']}</td>
                <td>{row['CPF_CNPJ'] if pd.notna(row['CPF_CNPJ']) else 'N/A'}</td>
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
    
    # Navegação principal
    if not st.session_state.logged_in:
        # Se não está logado, mostrar login
        st.title("💰 Sistema de Controle Financeiro - Igreja Batista Ágape")
        login_page()
    else:
        # VERIFICAR SE PRECISA COMPLETAR CADASTRO
        if st.session_state.user_info is None:
            st.session_state.user_info = get_user_info(st.session_state.username)
        
        if st.session_state.user_info and (st.session_state.user_info[0] is None or st.session_state.user_info[0] == ''):
            complete_registration_page()
            return
        
        # MOSTRAR MENU E PÁGINAS (SEM TÍTULO AQUI, CADA PÁGINA TEM SEU PRÓPRIO)
        if st.session_state.is_admin:
            menu = ["Dashboard", "Despesas", "Receitas", "Relatórios", "Configurações", "Administração", "Importar Dados"]
        else:
            menu = ["Dashboard", "Despesas", "Receitas", "Relatórios", "Configurações", "Importar Dados"]
            
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
        elif choice == "Importar Dados":
            import_data_page()
        
        # Botão de logout
        st.sidebar.write("---")
        if st.sidebar.button("🚪 Sair"):
            st.session_state.logged_in = False
            st.session_state.username = ""
            st.session_state.is_admin = False
            st.session_state.user_info = None
            rerun()

# Página de login
def login_page():
    st.header("Login")
    
    username = st.text_input("Usuário")
    password = st.text_input("Senha", type="password")
    
    if st.button("Entrar"):
        hashed_pswd = make_hashes(password)
        
        # Verificar credenciais
        conn = sqlite3.connect('finance.db')
        c = conn.cursor()
        try:
            c.execute('SELECT * FROM userstable WHERE username =? AND password = ?', (username, hashed_pswd))
            result = c.fetchall()
            conn.close()
            
            if result:
                st.session_state.logged_in = True
                st.session_state.username = username
                st.session_state.is_admin = (username == "admin")
                st.session_state.user_info = get_user_info(username)
                st.success("Login realizado com sucesso!")
                
                # Forçar redirecionamento manual
                st.markdown("<script>window.location.reload()</script>", unsafe_allow_html=True)
                time.sleep(0.5)
                rerun()
                
            else:
                st.error("Usuário ou senha incorretos")
                
        except sqlite3.OperationalError:
            conn.close()
            st.error("Erro no banco de dados. Tente novamente.")

# Página de completar cadastro
def complete_registration_page():
    st.header("📝 Completar Cadastro")
    
    with st.form("complete_registration"):
        nome_completo = st.text_input("Nome Completo*", placeholder="Digite seu nome completo")
        tipo_pessoa = st.radio("Tipo de Pessoa*", ["Física", "Jurídica"])
        
        if tipo_pessoa == "Física":
            cpf = st.text_input("CPF*", placeholder="000.000.000-00")
            cpf_cnpj = cpf
        else:
            cnpj = st.text_input("CNPJ*", placeholder="00.000.000/0000-00")
            cpf_cnpj = cnpj
        
        if st.form_submit_button("Completar Cadastro"):
            if nome_completo and cpf_cnpj:
                # Validar CPF/CNPJ
                cpf_cnpj_clean = re.sub(r'[^0-9]', '', cpf_cnpj)
                
                if tipo_pessoa == "Física":
                    if not validate_cpf(cpf_cnpj_clean):
                        st.error("CPF inválido. Por favor, verifique o número.")
                        return
                else:
                    if not validate_cnpj(cpf_cnpj_clean):
                        st.error("CNPJ inválido. Por favor, verifique o número.")
                        return
                
                # Atualizar informações do usuário
                update_user_info(st.session_state.username, nome_completo, cpf_cnpj_clean, tipo_pessoa)
                st.session_state.user_info = (nome_completo, cpf_cnpj_clean, tipo_pessoa)
                st.success("Cadastro completado com sucesso!")
                rerun()
            else:
                st.error("Por favor, preencha todos os campos obrigatórios.")

# Página de importação de dados
def import_data_page():
    st.header("📤 Importar Dados de Planilha")
    
    st.info("""
    **Instruções para importação:**
    - Para **despesas**: a planilha deve conter colunas: Data, Origem, Valor, Categoria
    - Para **receitas**: a planilha deve conter colunas: Data, Tipo, Descrição, Valor
    - Colunas opcionais: CPF, CNPJ, CPF_CNPJ
    - Formato de data: DD/MM/AAAA ou YYYY-MM-DD
    - Formatos suportados: Excel (.xlsx, .xls) e CSV
    """)
    
    tab1, tab2 = st.tabs(["Importar Despesas", "Importar Receitas"])
    
    with tab1:
        st.subheader("Importar Despesas")
        uploaded_file = st.file_uploader("Selecione a planilha de despesas", 
                                       type=['xlsx', 'xls', 'csv'],
                                       key="expense_import")
        
        if uploaded_file is not None:
            if st.button("Importar Despesas", key="import_expenses_btn"):
                success, message = import_from_spreadsheet(uploaded_file, st.session_state.username, is_income=False)
                if success:
                    st.success(message)
                else:
                    st.error(message)
    
    with tab2:
        st.subheader("Importar Receitas")
        uploaded_file = st.file_uploader("Selecione a planilha de receitas", 
                                       type=['xlsx', 'xls', 'csv'],
                                       key="income_import")
        
        if uploaded_file is not None:
            if st.button("Importar Receitas", key="import_incomes_btn"):
                success, message = import_from_spreadsheet(uploaded_file, st.session_state.username, is_income=True)
                if success:
                    st.success(message)
                else:
                    st.error(message)

# Página de administração
def admin_page():
    st.header("👨‍💼 Painel de Administração")
    
    tab1, tab2 = st.tabs(["Gerenciar Usuários", "Estatísticas do Sistema"])
    
    with tab1:
        st.subheader("Gerenciar Usuários")
        
        # Adicionar novo usuário
        with st.form("add_user_form"):
            st.write("Adicionar Novo Usuário")
            new_username = st.text_input("Nome de usuário*")
            new_password = st.text_input("Senha*", type="password")
            confirm_password = st.text_input("Confirmar senha*", type="password")
            nome_completo = st.text_input("Nome Completo*")
            tipo_pessoa = st.radio("Tipo de Pessoa*", ["Física", "Jurídica"])
            
            if tipo_pessoa == "Física":
                cpf = st.text_input("CPF*", placeholder="000.000.000-00")
                cpf_cnpj = cpf
            else:
                cnpj = st.text_input("CNPJ*", placeholder="00.000.000/0000-00")
                cpf_cnpj = cnpj
            
            if st.form_submit_button("Adicionar Usuário"):
                if not new_username or not new_password or not nome_completo or not cpf_cnpj:
                    st.error("Por favor, preencha todos os campos obrigatórios.")
                elif new_password != confirm_password:
                    st.error("As senhas não coincidem.")
                else:
                    # Verificar se usuário já existe
                    conn = sqlite3.connect('finance.db')
                    c = conn.cursor()
                    c.execute('SELECT * FROM userstable WHERE username = ?', (new_username,))
                    if c.fetchone():
                        st.error("Nome de usuário já existe.")
                    else:
                        # Validar CPF/CNPJ
                        cpf_cnpj_clean = re.sub(r'[^0-9]', '', cpf_cnpj)
                        
                        if tipo_pessoa == "Física":
                            if not validate_cpf(cpf_cnpj_clean):
                                st.error("CPF inválido.")
                                return
                        else:
                            if not validate_cnpj(cpf_cnpj_clean):
                                st.error("CNPJ inválido.")
                                return
                        
                        hashed_password = make_hashes(new_password)
                        add_user(new_username, hashed_password, nome_completo, cpf_cnpj_clean, tipo_pessoa)
                        st.success(f"Usuário '{new_username}' adicionado com sucesso!")
        
        # Listar usuários
        st.subheader("Usuários Cadastrados")
        users = get_all_users()
        
        if users:
            user_data = []
            for user in users:
                user_data.append({
                    "Usuário": user[0],
                    "Nome": user[1],
                    "CPF/CNPJ": format_cpf(user[2]) if user[3] == "Física" else format_cnpj(user[2]) if user[2] else "N/A",
                    "Tipo": user[3]
                })
            
            user_df = pd.DataFrame(user_data)
            st.dataframe(user_df, use_container_width=True)
            
            # Opção para remover usuário
            user_to_delete = st.selectbox("Selecionar usuário para remover", 
                                        [user[0] for user in users if user[0] != "admin"])
            
            if st.button("Remover Usuário", type="secondary"):
                if user_to_delete:
                    delete_user(user_to_delete)
                    st.success(f"Usuário '{user_to_delete}' removido com sucesso!")
                    rerun()
        else:
            st.info("Nenhum usuário cadastrado.")
    
    with tab2:
        st.subheader("Estatísticas do Sistema")
        
        # Obter estatísticas gerais
        conn = sqlite3.connect('finance.db')
        c = conn.cursor()
        
        # Total de usuários
        c.execute('SELECT COUNT(*) FROM userstable')
        total_users = c.fetchone()[0]
        
        # Total de transações
        c.execute('SELECT COUNT(*) FROM expenses')
        total_expenses = c.fetchone()[0]
        
        c.execute('SELECT COUNT(*) FROM incomes')
        total_incomes = c.fetchone()[0]
        
        # Valores totais
        c.execute('SELECT SUM(value) FROM expenses')
        total_expense_value = c.fetchone()[0] or 0
        
        c.execute('SELECT SUM(value) FROM incomes')
        total_income_value = c.fetchone()[0] or 0
        
        conn.close()
        
        # Exibir estatísticas
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Total de Usuários", total_users)
            st.metric("Total de Despesas", total_expenses)
        
        with col2:
            st.metric("Total de Receitas", total_incomes)
            st.metric("Valor Total Despesas", f"R$ {total_expense_value:,.2f}")
        
        with col3:
            st.metric("Saldo do Sistema", f"R$ {(total_income_value - total_expense_value):,.2f}")
            st.metric("Valor Total Receitas", f"R$ {total_income_value:,.2f}")

# Página de configurações
def settings_page():
    st.header("⚙️ Configurações")
    
    # Obter informações atuais do usuário
    user_info = get_user_info(st.session_state.username)
    
    if user_info:
        nome_completo, cpf_cnpj, tipo_pessoa = user_info
        
        with st.form("update_profile"):
            st.subheader("Atualizar Perfil")
            
            new_nome = st.text_input("Nome Completo", value=nome_completo or "")
            new_tipo_pessoa = st.radio("Tipo de Pessoa", ["Física", "Jurídica"], 
                                     index=0 if tipo_pessoa == "Física" else 1)
            
            if new_tipo_pessoa == "Física":
                new_cpf = st.text_input("CPF", 
                                      value=format_cpf(cpf_cnpj) if cpf_cnpj else "",
                                      placeholder="000.000.000-00")
                new_cpf_cnpj = new_cpf
            else:
                new_cnpj = st.text_input("CNPJ", 
                                       value=format_cnpj(cpf_cnpj) if cpf_cnpj else "",
                                       placeholder="00.000.000/0000-00")
                new_cpf_cnpj = new_cnpj
            
            if st.form_submit_button("Atualizar Perfil"):
                if new_nome and new_cpf_cnpj:
                    # Validar CPF/CNPJ
                    new_cpf_cnpj_clean = re.sub(r'[^0-9]', '', new_cpf_cnpj)
                    
                    if new_tipo_pessoa == "Física":
                        if not validate_cpf(new_cpf_cnpj_clean):
                            st.error("CPF inválido.")
                            return
                    else:
                        if not validate_cnpj(new_cpf_cnpj_clean):
                            st.error("CNPJ inválido.")
                            return
                    
                    update_user_info(st.session_state.username, new_nome, new_cpf_cnpj_clean, new_tipo_pessoa)
                    st.session_state.user_info = (new_nome, new_cpf_cnpj_clean, new_tipo_pessoa)
                    st.success("Perfil atualizado com sucesso!")
                else:
                    st.error("Por favor, preencha todos os campos.")
    
    # Alterar senha
    with st.form("change_password"):
        st.subheader("Alterar Senha")
        
        current_password = st.text_input("Senha Atual", type="password")
        new_password = st.text_input("Nova Senha", type="password")
        confirm_password = st.text_input("Confirmar Nova Senha", type="password")
        
        if st.form_submit_button("Alterar Senha"):
            if current_password and new_password and confirm_password:
                # Verificar senha atual
                hashed_current = make_hashes(current_password)
                conn = sqlite3.connect('finance.db')
                c = conn.cursor()
                c.execute('SELECT * FROM userstable WHERE username = ? AND password = ?', 
                         (st.session_state.username, hashed_current))
                
                if not c.fetchone():
                    st.error("Senha atual incorreta.")
                elif new_password != confirm_password:
                    st.error("As novas senhas não coincidem.")
                else:
                    # Atualizar senha
                    hashed_new = make_hashes(new_password)
                    c.execute('UPDATE userstable SET password = ? WHERE username = ?', 
                             (hashed_new, st.session_state.username))
                    conn.commit()
                    conn.close()
                    st.success("Senha alterada com sucesso!")
            else:
                st.error("Por favor, preencha todos os campos.")

# Página de relatórios
def reports_page():
    st.header("📊 Relatórios Financeiros")
    
    # Obter dados
    expenses = get_expenses(st.session_state.username)
    incomes = get_incomes(st.session_state.username)
    
    if not expenses and not incomes:
        st.info("Nenhum dado financeiro disponível para gerar relatórios.")
        return
    
    # Filtros
    col1, col2, col3 = st.columns(3)
    
    with col1:
        start_date = st.date_input("Data Inicial", 
                                 value=date.today().replace(day=1),
                                 max_value=date.today())
    
    with col2:
        end_date = st.date_input("Data Final", 
                               value=date.today(),
                               max_value=date.today())
    
    with col3:
        report_type = st.selectbox("Tipo de Relatório", 
                                 ["Completo", "Apenas Despesas", "Apenas Receitas"])
    
    # Filtrar dados
    filtered_expenses = []
    filtered_incomes = []
    
    if expenses:
        for expense in expenses:
            expense_date = datetime.strptime(expense[1], "%Y-%m-%d").date()
            if start_date <= expense_date <= end_date:
                filtered_expenses.append(expense)
    
    if incomes:
        for income in incomes:
            income_date = datetime.strptime(income[1], "%Y-%m-%d").date()
            if start_date <= income_date <= end_date:
                filtered_incomes.append(income)
    
    # Calcular totais
    total_expenses = sum(expense[3] for expense in filtered_expenses) if filtered_expenses else 0
    total_income = sum(income[4] for income in filtered_incomes) if filtered_incomes else 0
    balance = total_income - total_expenses
    
    # Exibir resumo
    st.subheader("📈 Resumo Financeiro")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Total de Receitas", f"R$ {total_income:,.2f}")
    
    with col2:
        st.metric("Total de Despesas", f"R$ {total_expenses:,.2f}")
    
    with col3:
        st.metric("Saldo", f"R$ {balance:,.2f}", 
                 delta=f"{'Superavit' if balance >= 0 else 'Deficit'}")
    
    # Gráficos
    if filtered_expenses or filtered_incomes:
        tab1, tab2, tab3 = st.tabs(["📋 Detalhado", "📈 Gráficos", "💾 Exportar"])
        
        with tab1:
            # Dados detalhados
            if report_type in ["Completo", "Apenas Despesas"] and filtered_expenses:
                st.subheader("Despesas Detalhadas")
                expense_data = []
                for expense in filtered_expenses:
                    expense_data.append({
                        "Data": format_brazilian_date(expense[1]),
                        "Origem": expense[2],
                        "Valor": expense[3],
                        "Categoria": expense[4],
                        "CPF/CNPJ": format_cpf(expense[6]) if expense[7] == "Física" else format_cnpj(expense[6]) if expense[6] else "N/A",
                        "Tipo Pessoa": expense[7] or "N/A"
                    })
                
                expense_df = pd.DataFrame(expense_data)
                st.dataframe(expense_df, use_container_width=True, hide_index=True)
            
            if report_type in ["Completo", "Apenas Receitas"] and filtered_incomes:
                st.subheader("Receitas Detalhadas")
                income_data = []
                for income in filtered_incomes:
                    income_data.append({
                        "Data": format_brazilian_date(income[1]),
                        "Tipo": income[2],
                        "Descrição": income[3],
                        "Valor": income[4],
                        "CPF/CNPJ": format_cpf(income[6]) if income[7] == "Física" else format_cnpj(income[6]) if income[6] else "N/A",
                        "Tipo Pessoa": income[7] or "N/A"
                    })
                
                income_df = pd.DataFrame(income_data)
                st.dataframe(income_df, use_container_width=True, hide_index=True)
        
        with tab2:
            # Gráficos
            if filtered_expenses:
                st.subheader("Análise de Despesas")
                
                # Gráfico de pizza por categoria
                if len(filtered_expenses) > 0:
                    expense_categories = {}
                    for expense in filtered_expenses:
                        category = expense[4]
                        expense_categories[category] = expense_categories.get(category, 0) + expense[3]
                    
                    if expense_categories:
                        fig1 = px.pie(
                            values=list(expense_categories.values()),
                            names=list(expense_categories.keys()),
                            title="Distribuição de Despesas por Categoria"
                        )
                        st.plotly_chart(fig1, use_container_width=True)
            
            if filtered_incomes:
                st.subheader("Análise de Receitas")
                
                # Gráfico de pizza por tipo
                if len(filtered_incomes) > 0:
                    income_types = {}
                    for income in filtered_incomes:
                        income_type = income[2]
                        income_types[income_type] = income_types.get(income_type, 0) + income[4]
                    
                    if income_types:
                        fig2 = px.pie(
                            values=list(income_types.values()),
                            names=list(income_types.keys()),
                            title="Distribuição de Receitas por Tipo"
                        )
                        st.plotly_chart(fig2, use_container_width=True)
            
            # Gráfico de linha temporal
            if filtered_expenses or filtered_incomes:
                st.subheader("Evolução Temporal")
                
                # Preparar dados temporais
                time_data = {}
                for expense in filtered_expenses:
                    date_str = expense[1]
                    time_data[date_str] = time_data.get(date_str, {'receitas': 0, 'despesas': 0})
                    time_data[date_str]['despesas'] += expense[3]
                
                for income in filtered_incomes:
                    date_str = income[1]
                    time_data[date_str] = time_data.get(date_str, {'receitas': 0, 'despesas': 0})
                    time_data[date_str]['receitas'] += income[4]
                
                # Criar DataFrame para o gráfico
                dates = sorted(time_data.keys())
                receitas = [time_data[date]['receitas'] for date in dates]
                despesas = [time_data[date]['despesas'] for date in dates]
                saldos = [receitas[i] - despesas[i] for i in range(len(dates))]
                
                # Formatar datas para exibição
                display_dates = [format_brazilian_date(date) for date in dates]
                
                fig3 = go.Figure()
                fig3.add_trace(go.Scatter(x=display_dates, y=receitas, mode='lines+markers', name='Receitas', line=dict(color='green')))
                fig3.add_trace(go.Scatter(x=display_dates, y=despesas, mode='lines+markers', name='Despesas', line=dict(color='red')))
                fig3.add_trace(go.Scatter(x=display_dates, y=saldos, mode='lines+markers', name='Saldo', line=dict(color='blue')))
                
                fig3.update_layout(
                    title="Evolução Financeira ao Longo do Tempo",
                    xaxis_title="Data",
                    yaxis_title="Valor (R$)",
                    hovermode='x unified'
                )
                
                st.plotly_chart(fig3, use_container_width=True)
        
        with tab3:
            # Exportar dados
            st.subheader("Exportar Relatório")
            
            export_format = st.radio("Formato de Exportação", 
                                   ["Excel", "HTML com Logo", "CSV"])
            
            if st.button("📥 Exportar Relatório"):
                if export_format == "Excel":
                    excel_data = export_to_excel(filtered_expenses, filtered_incomes)
                    st.download_button(
                        label="⬇️ Baixar Excel",
                        data=excel_data,
                        file_name=f"relatorio_financeiro_{date.today()}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
                
                elif export_format == "HTML com Logo":
                    html_content = export_to_html_with_logo(filtered_expenses, filtered_incomes)
                    st.download_button(
                        label="⬇️ Baixar HTML",
                        data=html_content,
                        file_name=f"relatorio_financeiro_{date.today()}.html",
                        mime="text/html"
                    )
                
                elif export_format == "CSV":
                    # Combinar dados
                    all_data = []
                    for expense in filtered_expenses:
                        all_data.append({
                            'Tipo': 'Despesa',
                            'Data': format_brazilian_date(expense[1]),
                            'Descrição': expense[2],
                            'Valor': -expense[3],
                            'Categoria': expense[4],
                            'CPF/CNPJ': format_cpf(expense[6]) if expense[7] == "Física" else format_cnpj(expense[6]) if expense[6] else "N/A",
                            'Tipo Pessoa': expense[7] or "N/A"
                        })
                    
                    for income in filtered_incomes:
                        all_data.append({
                            'Tipo': 'Receita',
                            'Data': format_brazilian_date(income[1]),
                            'Descrição': income[3],
                            'Valor': income[4],
                            'Categoria': income[2],
                            'CPF/CNPJ': format_cpf(income[6]) if income[7] == "Física" else format_cnpj(income[6]) if income[6] else "N/A",
                            'Tipo Pessoa': income[7] or "N/A"
                        })
                    
                    if all_data:
                        df = pd.DataFrame(all_data)
                        csv = df.to_csv(index=False, sep=';')
                        st.download_button(
                            label="⬇️ Baixar CSV",
                            data=csv,
                            file_name=f"relatorio_financeiro_{date.today()}.csv",
                            mime="text/csv"
                        )
    else:
        st.warning("Nenhum dado encontrado para o período selecionado.")

# Página de receitas
def incomes_page():
    st.header("💵 Gestão de Receitas")
    
    # Formulário para adicionar receita
    with st.form("add_income_form"):
        st.subheader("➕ Adicionar Nova Receita")
        
        col1, col2 = st.columns(2)
        
        with col1:
            income_date = st.date_input("Data da Receita", value=date.today())
            income_type = st.selectbox("Tipo de Receita*", 
                                     ["Dízimo", "Oferta", "Doação", "Evento", "Outros"])
        
        with col2:
            income_value = st.number_input("Valor (R$)*", min_value=0.01, step=0.01, format="%.2f")
            income_description = st.text_input("Descrição*", placeholder="Ex: Oferta do culto de domingo")
        
        # Informações do contribuinte (opcional)
        st.subheader("Informações do Contribuinte (Opcional)")
        contrib_tipo = st.radio("Tipo de Contribuinte", ["Física", "Jurídica", "Não informar"], index=2)
        
        if contrib_tipo != "Não informar":
            col3, col4 = st.columns(2)
            with col3:
                if contrib_tipo == "Física":
                    contrib_cpf = st.text_input("CPF do Contribuinte", placeholder="000.000.000-00")
                    contrib_identifier = contrib_cpf
                else:
                    contrib_cnpj = st.text_input("CNPJ do Contribuinte", placeholder="00.000.000/0000-00")
                    contrib_identifier = contrib_cnpj
            
            with col4:
                contrib_name = st.text_input("Nome do Contribuinte", placeholder="Nome completo ou razão social")
        
        if st.form_submit_button("Adicionar Receita"):
            if income_value and income_description:
                # Validar CPF/CNPJ se fornecido
                cpf_cnpj = None
                tipo_pessoa = None
                
                if contrib_tipo != "Não informar" and contrib_identifier:
                    cpf_cnpj_clean = re.sub(r'[^0-9]', '', contrib_identifier)
                    
                    if contrib_tipo == "Física":
                        if validate_cpf(cpf_cnpj_clean):
                            cpf_cnpj = cpf_cnpj_clean
                            tipo_pessoa = "Física"
                        else:
                            st.error("CPF inválido. A receita será cadastrada sem informações do contribuinte.")
                    else:
                        if validate_cnpj(cpf_cnpj_clean):
                            cpf_cnpj = cpf_cnpj_clean
                            tipo_pessoa = "Jurídica"
                        else:
                            st.error("CNPJ inválido. A receita será cadastrada sem informações do contribuinte.")
                
                add_income(
                    income_date.strftime("%Y-%m-%d"),
                    income_type,
                    income_description,
                    income_value,
                    st.session_state.username,
                    cpf_cnpj,
                    tipo_pessoa
                )
                st.success("Receita adicionada com sucesso!")
                rerun()
            else:
                st.error("Por favor, preencha todos os campos obrigatórios.")
    
    # Lista de receitas
    st.subheader("📋 Receitas Cadastradas")
    incomes = get_incomes(st.session_state.username)
    
    if incomes:
        income_data = []
        for income in incomes:
            income_data.append({
                "ID": income[0],
                "Data": format_brazilian_date(income[1]),
                "Tipo": income[2],
                "Descrição": income[3],
                "Valor": income[4],
                "CPF/CNPJ": format_cpf(income[6]) if income[7] == "Física" else format_cnpj(income[6]) if income[6] else "N/A",
                "Tipo Pessoa": income[7] or "N/A"
            })
        
        income_df = pd.DataFrame(income_data)
        
        # Exibir tabela com opção de remover
        edited_df = st.dataframe(income_df, use_container_width=True, hide_index=True)
        
        # Opção para remover receita
        income_to_delete = st.selectbox("Selecionar receita para remover", 
                                      [f"{income[0]} - {format_brazilian_date(income[1])} - {income[2]} - R$ {income[4]:.2f}" 
                                       for income in incomes],
                                      key="delete_income_select")
        
        if st.button("🗑️ Remover Receita Selecionada", type="secondary"):
            if income_to_delete:
                income_id = int(income_to_delete.split(" - ")[0])
                delete_income(income_id, st.session_state.username)
                st.success("Receita removida com sucesso!")
                rerun()
    else:
        st.info("Nenhuma receita cadastrada.")

# Página de despesas
def expenses_page():
    st.header("💸 Gestão de Despesas")
    
    # Formulário para adicionar despesa
    with st.form("add_expense_form"):
        st.subheader("➕ Adicionar Nova Despesa")
        
        col1, col2 = st.columns(2)
        
        with col1:
            expense_date = st.date_input("Data da Despesa", value=date.today())
            expense_origin = st.text_input("Origem/Fornecedor*", placeholder="Ex: Mercado XYZ")
        
        with col2:
            expense_value = st.number_input("Valor (R$)*", min_value=0.01, step=0.01, format="%.2f")
            expense_category = st.selectbox("Categoria*", 
                                          ["Alimentação", "Transporte", "Utilidades", "Manutenção", 
                                           "Eventos", "Equipamentos", "Outros"])
        
        # Informações do fornecedor (opcional)
        st.subheader("Informações do Fornecedor (Opcional)")
        supplier_tipo = st.radio("Tipo de Fornecedor", ["Física", "Jurídica", "Não informar"], index=2)
        
        if supplier_tipo != "Não informar":
            col3, col4 = st.columns(2)
            with col3:
                if supplier_tipo == "Física":
                    supplier_cpf = st.text_input("CPF do Fornecedor", placeholder="000.000.000-00")
                    supplier_identifier = supplier_cpf
                else:
                    supplier_cnpj = st.text_input("CNPJ do Fornecedor", placeholder="00.000.000/0000-00")
                    supplier_identifier = supplier_cnpj
            
            with col4:
                supplier_name = st.text_input("Nome do Fornecedor", placeholder="Nome completo ou razão social")
        
        if st.form_submit_button("Adicionar Despesa"):
            if expense_value and expense_origin:
                # Validar CPF/CNPJ se fornecido
                cpf_cnpj = None
                tipo_pessoa = None
                
                if supplier_tipo != "Não informar" and supplier_identifier:
                    cpf_cnpj_clean = re.sub(r'[^0-9]', '', supplier_identifier)
                    
                    if supplier_tipo == "Física":
                        if validate_cpf(cpf_cnpj_clean):
                            cpf_cnpj = cpf_cnpj_clean
                            tipo_pessoa = "Física"
                        else:
                            st.error("CPF inválido. A despesa será cadastrada sem informações do fornecedor.")
                    else:
                        if validate_cnpj(cpf_cnpj_clean):
                            cpf_cnpj = cpf_cnpj_clean
                            tipo_pessoa = "Jurídica"
                        else:
                            st.error("CNPJ inválido. A despesa será cadastrada sem informações do fornecedor.")
                
                add_expense(
                    expense_date.strftime("%Y-%m-%d"),
                    expense_origin,
                    expense_value,
                    expense_category,
                    st.session_state.username,
                    cpf_cnpj,
                    tipo_pessoa
                )
                st.success("Despesa adicionada com sucesso!")
                rerun()
            else:
                st.error("Por favor, preencha todos os campos obrigatórios.")
    
    # Lista de despesas
    st.subheader("📋 Despesas Cadastradas")
    expenses = get_expenses(st.session_state.username)
    
    if expenses:
        expense_data = []
        for expense in expenses:
            expense_data.append({
                "ID": expense[0],
                "Data": format_brazilian_date(expense[1]),
                "Origem": expense[2],
                "Valor": expense[3],
                "Categoria": expense[4],
                "CPF/CNPJ": format_cpf(expense[6]) if expense[7] == "Física" else format_cnpj(expense[6]) if expense[6] else "N/A",
                "Tipo Pessoa": expense[7] or "N/A"
            })
        
        expense_df = pd.DataFrame(expense_data)
        
        # Exibir tabela com opção de remover
        edited_df = st.dataframe(expense_df, use_container_width=True, hide_index=True)
        
        # Opção para remover despesa
        expense_to_delete = st.selectbox("Selecionar despesa para remover", 
                                       [f"{expense[0]} - {format_brazilian_date(expense[1])} - {expense[2]} - R$ {expense[3]:.2f}" 
                                        for expense in expenses],
                                       key="delete_expense_select")
        
        if st.button("🗑️ Remover Despesa Selecionada", type="secondary"):
            if expense_to_delete:
                expense_id = int(expense_to_delete.split(" - ")[0])
                delete_expense(expense_id, st.session_state.username)
                st.success("Despesa removida com sucesso!")
                rerun()
    else:
        st.info("Nenhuma despesa cadastrada.")

# Página de dashboard
def dashboard_page():
    st.header("📊 Dashboard Financeiro")
    
    # Obter dados
    expenses = get_expenses(st.session_state.username)
    incomes = get_incomes(st.session_state.username)
    
    if not expenses and not incomes:
        st.info("Bem-vindo ao Sistema de Controle Financeiro! Comece adicionando suas primeiras receitas e despesas.")
        return
    
    # Calcular totais
    total_expenses = sum(expense[3] for expense in expenses) if expenses else 0
    total_income = sum(income[4] for income in incomes) if incomes else 0
    balance = total_income - total_expenses
    
    # Métricas principais
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("💰 Total de Receitas", f"R$ {total_income:,.2f}")
    
    with col2:
        st.metric("💸 Total de Despesas", f"R$ {total_expenses:,.2f}")
    
    with col3:
        st.metric("📈 Saldo Atual", f"R$ {balance:,.2f}", 
                 delta=f"{'Superavit' if balance >= 0 else 'Deficit'}")
    
    # Gráficos
    if expenses or incomes:
        col1, col2 = st.columns(2)
        
        with col1:
            # Gráfico de pizza - Distribuição de despesas
            if expenses:
                expense_categories = {}
                for expense in expenses:
                    category = expense[4]
                    expense_categories[category] = expense_categories.get(category, 0) + expense[3]
                
                if expense_categories:
                    fig1 = px.pie(
                        values=list(expense_categories.values()),
                        names=list(expense_categories.keys()),
                        title="Distribuição de Despesas por Categoria"
                    )
                    st.plotly_chart(fig1, use_container_width=True)
        
        with col2:
            # Gráfico de pizza - Distribuição de receitas
            if incomes:
                income_types = {}
                for income in incomes:
                    income_type = income[2]
                    income_types[income_type] = income_types.get(income_type, 0) + income[4]
                
                if income_types:
                    fig2 = px.pie(
                        values=list(income_types.values()),
                        names=list(income_types.keys()),
                        title="Distribuição de Receitas por Tipo"
                    )
                    st.plotly_chart(fig2, use_container_width=True)
        
        # Últimas transações
        st.subheader("🔄 Últimas Transações")
        
        # Combinar e ordenar transações
        all_transactions = []
        
        for expense in expenses[-5:]:  # Últimas 5 despesas
            all_transactions.append({
                "Tipo": "Despesa",
                "Data": expense[1],
                "Descrição": expense[2],
                "Valor": -expense[3],
                "Categoria": expense[4]
            })
        
        for income in incomes[-5:]:  # Últimas 5 receitas
            all_transactions.append({
                "Tipo": "Receita",
                "Data": income[1],
                "Descrição": income[3],
                "Valor": income[4],
                "Categoria": income[2]
            })
        
        # Ordenar por data (mais recente primeiro)
        all_transactions.sort(key=lambda x: x["Data"], reverse=True)
        
        if all_transactions:
            for transaction in all_transactions[:10]:  # Mostrar até 10 transações
                color = "red" if transaction["Tipo"] == "Despesa" else "green"
                icon = "⬇️" if transaction["Tipo"] == "Despesa" else "⬆️"
                
                st.markdown(f"""
                <div style='background-color: #f8f9fa; padding: 10px; border-radius: 5px; margin: 5px 0; border-left: 4px solid {color}'>
                    <strong>{icon} {transaction['Tipo']}</strong><br>
                    <small>Data: {format_brazilian_date(transaction['Data'])} | {transaction['Categoria']}</small><br>
                    {transaction['Descrição']}<br>
                    <strong style='color: {color}'>R$ {transaction['Valor']:,.2f}</strong>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("Nenhuma transação recente.")
    else:
        st.info("Adicione algumas transações para ver estatísticas detalhadas.")

# Executar aplicação
if __name__ == "__main__":
    main()