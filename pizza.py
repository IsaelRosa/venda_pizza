import streamlit as st
import sqlite3
import pandas as pd
import datetime
import base64
import os
import warnings
from PIL import Image
from streamlit.runtime.scriptrunner import ScriptRunContext

warnings.filterwarnings("ignore", category=UserWarning, message="missing ScriptRunContext")

# Criar contexto fake se necessário
try:
    from streamlit.runtime.scriptrunner import get_script_run_ctx
    if not get_script_run_ctx():
        ctx = ScriptRunContext()
        ctx.script_requests = []
except:
    pass

# Configuração inicial da página
st.set_page_config(page_title="Sistema de Vendas de Pizzas", layout="wide")

# Configurações de autenticação
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "pizza123"

# Função para verificar login
def check_login(username, password):
    return username == ADMIN_USERNAME and password == ADMIN_PASSWORD

# Tela de Login
def login_screen():
    st.title("🍕 Sistema de Vendas de Pizzas")
    
    col1, col2, col3 = st.columns([1, 3, 1])
    with col2:
        with st.container(border=True):
            st.markdown("""
            <style>
                .login-title {
                    text-align: center;
                    color: #FF5733;
                    font-size: 28px;
                    margin-bottom: 30px;
                }
                .stButton>button {
                    width: 100%;
                    background-color: #FF5733;
                    color: white;
                }
            </style>
            <div class='login-title'>Acesso Administrativo</div>
            """, unsafe_allow_html=True)
            
            username = st.text_input("Usuário", key="username")
            password = st.text_input("Senha", type="password", key="password")
            
            if st.button("Entrar"):
                if check_login(username, password):
                    st.session_state.logged_in = True
                    st.rerun()
                else:
                    st.error("Credenciais inválidas. Tente novamente.")

# Tela inicial bonita
def welcome_screen():
    st.title("🍕 Bem-vindo ao Sistema de Vendas de Pizzas!")
    
    st.markdown("""
    <style>
        .welcome-container {
            background-color: #FFF5F0;
            border-radius: 10px;
            padding: 20px;
            margin-bottom: 20px;
        }
        .welcome-title {
            color: #FF5733;
            text-align: center;
            font-size: 32px;
        }
        .welcome-text {
            font-size: 18px;
            text-align: center;
        }
    </style>
    """, unsafe_allow_html=True)
    
    with st.container():
        st.markdown('<div class="welcome-title">Sistema de Gerenciamento de Vendas</div>', unsafe_allow_html=True)
        st.markdown("""
        <div class="welcome-text">
        <p>Gerencie seus pedidos, acompanhe vendas e controle estoque de forma eficiente.</p>
        <p>Para acessar o sistema, faça login como administrador.</p>
        </div>
        """, unsafe_allow_html=True)
        
        if st.button("Acessar Painel Administrativo"):
            st.session_state.show_login = True
            st.rerun()

# Funções de banco de dados
def init_db():
    conn = sqlite3.connect('pizza.db')
    c = conn.cursor()
    
    # Tabela principal de pedidos
    c.execute('''CREATE TABLE IF NOT EXISTS orders
                 (id TEXT PRIMARY KEY,
              timestamp TEXT,
              sellerName TEXT,
              frangoComCebola INTEGER,
              frangoSemCebola INTEGER,
              calabresaComCebola INTEGER,
              calabresaSemCebola INTEGER,
              pickupTime TEXT,
              observations TEXT,
              paymentProof TEXT,
              paymentChecked INTEGER,
              deliveredToSeller INTEGER,
              deliveredToCustomer INTEGER,
              valor_total REAL,
                  forma_pagamento TEXT)''')
    
    # Tabela de comprovantes
    c.execute('''CREATE TABLE IF NOT EXISTS comprovantes
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  order_id TEXT,
                  file_path TEXT,
                  upload_time TEXT,
                  FOREIGN KEY(order_id) REFERENCES orders(id))''')
    
    conn.commit()
    conn.close()

def save_comprovante(uploaded_file, order_id):
    if not os.path.exists('comprovantes'):
        os.makedirs('comprovantes')
    
    file_path = f"comprovantes/{order_id}_{uploaded_file.name}"
    with open(file_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    
    conn = sqlite3.connect('pizza.db')
    c = conn.cursor()
    c.execute('''INSERT INTO comprovantes 
                 (order_id, file_path, upload_time)
                 VALUES (?, ?, ?)''',
              (order_id, file_path, datetime.datetime.now().isoformat()))
    conn.commit()
    conn.close()
    
    return file_path

def get_comprovantes(order_id):
    conn = sqlite3.connect('pizza.db')
    c = conn.cursor()
    c.execute("SELECT file_path FROM comprovantes WHERE order_id=?", (order_id,))
    result = c.fetchall()
    conn.close()
    return [r[0] for r in result]

def get_all_orders():
    conn = sqlite3.connect('pizza.db')
    df = pd.read_sql_query("SELECT * FROM orders", conn)
    conn.close()
    return df

def save_order(order_id, order_data):
    conn = sqlite3.connect('pizza.db')
    c = conn.cursor()
    
    order_data['paymentChecked'] = int(order_data.get('paymentChecked', False))
    order_data['deliveredToSeller'] = int(order_data.get('deliveredToSeller', False))
    order_data['deliveredToCustomer'] = int(order_data.get('deliveredToCustomer', False))
    
    # Calcular valor total
    precos = {
        'frangoComCebola': 30.0,
        'frangoSemCebola': 30.0,
        'calabresaComCebola': 35.0,
        'calabresaSemCebola': 35.0
    }
    
    valor_total = (
        order_data['frangoComCebola'] * precos['frangoComCebola'] +
        order_data['frangoSemCebola'] * precos['frangoSemCebola'] +
        order_data['calabresaComCebola'] * precos['calabresaComCebola'] +
        order_data['calabresaSemCebola'] * precos['calabresaSemCebola']
    )
    
    c.execute("SELECT id FROM orders WHERE id=?", (order_id,))
    exists = c.fetchone()
    
    if exists:
        query = '''UPDATE orders SET
                   timestamp=?,
                   sellerName=?,
                   frangoComCebola=?,
                   frangoSemCebola=?,
                   calabresaComCebola=?,
                   calabresaSemCebola=?,
                   pickupTime=?,
                   observations=?,
                   paymentProof=?,
                   paymentChecked=?,
                   deliveredToSeller=?,
                   deliveredToCustomer=?,
                   valor_total=?,
                   forma_pagamento=?
                   WHERE id=?'''
        params = (
            order_data['timestamp'],
            order_data['sellerName'],
            order_data['frangoComCebola'],
            order_data['frangoSemCebola'],
            order_data['calabresaComCebola'],
            order_data['calabresaSemCebola'],
            order_data['pickupTime'],
            order_data.get('observations', ''),
            order_data.get('paymentProof', ''),
            order_data['paymentChecked'],
            order_data['deliveredToSeller'],
            order_data['deliveredToCustomer'],
            valor_total,
            order_data.get('forma_pagamento', 'Dinheiro'),
            order_id
        )
    else:
        query = '''INSERT INTO orders VALUES
                   (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)'''
        params = (
            order_id,
            order_data['timestamp'],
            order_data['sellerName'],
            order_data['frangoComCebola'],
            order_data['frangoSemCebola'],
            order_data['calabresaComCebola'],
            order_data['calabresaSemCebola'],
            order_data['pickupTime'],
            order_data.get('observations', ''),
            order_data.get('paymentProof', ''),
            order_data['paymentChecked'],
            order_data['deliveredToSeller'],
            order_data['deliveredToCustomer'],
            valor_total,
            order_data.get('forma_pagamento', 'Dinheiro')
        )
    
    c.execute(query, params)
    conn.commit()
    conn.close()

def delete_order(order_id):
    conn = sqlite3.connect('pizza.db')
    c = conn.cursor()
    
    # Primeiro deletar comprovantes
    comprovantes = get_comprovantes(order_id)
    for comprovante in comprovantes:
        if os.path.exists(comprovante):
            os.remove(comprovante)
    
    c.execute("DELETE FROM comprovantes WHERE order_id=?", (order_id,))
    c.execute("DELETE FROM orders WHERE id=?", (order_id,))
    
    conn.commit()
    conn.close()

def calculate_totals(orders_df):
    totals = {}
    totals['frangoComCebola'] = orders_df['frangoComCebola'].sum()
    totals['frangoSemCebola'] = orders_df['frangoSemCebola'].sum()
    totals['calabresaComCebola'] = orders_df['calabresaComCebola'].sum()
    totals['calabresaSemCebola'] = orders_df['calabresaSemCebola'].sum()
    totals['totalPizzas'] = totals['frangoComCebola'] + totals['frangoSemCebola'] + totals['calabresaComCebola'] + totals['calabresaSemCebola']
    totals['retiradas9'] = len(orders_df[orders_df['pickupTime'] == 'entre 9 e 10'])
    totals['retiradas10'] = len(orders_df[orders_df['pickupTime'] == 'entre 10 e 11'])
    totals['retiradas11'] = len(orders_df[orders_df['pickupTime'] == 'entre 11 e 12'])
    totals['retiradas12'] = len(orders_df[orders_df['pickupTime'] == 'entre 12 e 13'])
    totals['pagamentosCorretos'] = orders_df['paymentChecked'].sum()
    totals['pagamentosIncorretos'] = (~orders_df['paymentChecked'].astype(bool)).sum()
    totals['pagamentosNaoConferidos'] = orders_df['paymentChecked'].isna().sum()
    totals['entreguesVendedor'] = orders_df['deliveredToSeller'].sum()
    totals['naoEntreguesVendedor'] = (~orders_df['deliveredToSeller'].astype(bool)).sum()
    totals['entreguesCliente'] = orders_df['deliveredToCustomer'].sum()
    totals['naoEntreguesCliente'] = (~orders_df['deliveredToCustomer'].astype(bool)).sum()
    totals['totalCebolas'] = totals['frangoComCebola'] + totals['calabresaComCebola']
    totals['totalMussarela'] = 0.3 * totals['totalPizzas']
    totals['totalMassaTomate'] = 0.4 * totals['totalPizzas']
    totals['totalFrango'] = 0.4 * (totals['frangoComCebola'] + totals['frangoSemCebola'])
    totals['totalCalabresa'] = 0.2 * (totals['calabresaComCebola'] + totals['calabresaSemCebola'])
    
    # Totais financeiros
    totals['valorTotalVendas'] = orders_df['valor_total'].sum()
    totals['valorMedioVenda'] = orders_df['valor_total'].mean() if len(orders_df) > 0 else 0
    
    return totals

def gerar_fluxo_caixa():
    conn = sqlite3.connect('pizza.db')
    df = pd.read_sql_query("""
        SELECT 
            date(timestamp) as data,
            forma_pagamento,
            SUM(valor_total) as total,
            COUNT(*) as quantidade_vendas
        FROM orders
        GROUP BY date(timestamp), forma_pagamento
        ORDER BY date(timestamp) DESC
    """, conn)
    conn.close()
    return df

# Página principal do sistema
def main_app():
    init_db()
    
    # Barra de logout no topo
    col1, col2 = st.columns([4, 1])
    with col1:
        st.title("🍕 Sistema de Vendas de Pizzas")
    with col2:
        if st.button("Sair"):
            st.session_state.logged_in = False
            st.session_state.show_login = False
            st.rerun()
    
    # Menu de navegação
    menu = st.sidebar.radio("Menu", ["Registrar Pedido", "Visualizar Pedidos", "Fluxo de Caixa", "Comprovantes"])
    
    if menu == "Registrar Pedido":
        registrar_pedido()
    elif menu == "Visualizar Pedidos":
        visualizar_pedidos()
    elif menu == "Fluxo de Caixa":
        mostrar_fluxo_caixa()
    elif menu == "Comprovantes":
        gerenciar_comprovantes()

def registrar_pedido():
    st.header("📝 Novo Pedido")
    
    # Inicializar estado do formulário
    if 'form_data' not in st.session_state:
        st.session_state.form_data = {
            'seller_name': "",
            'pickup_time': "entre 9 e 10",
            'observations': "",
            'payment_proof': "",
            'frango_com': 0,
            'frango_sem': 0,
            'calabresa_com': 0,
            'calabresa_sem': 0,
            'payment_checked': False,
            'delivered_seller': False,
            'delivered_customer': False,
            'forma_pagamento': "Dinheiro",
            'comprovante': None
        }

    if 'editing_order_id' not in st.session_state:
        st.session_state.editing_order_id = None

    with st.form("order_form"):
        col1, col2 = st.columns(2)
        with col1:
            seller_name = st.text_input("Vendedor", value=st.session_state.form_data['seller_name'])
            forma_pagamento = st.selectbox(
                "Forma de Pagamento",
                ["Dinheiro", "Cartão de Crédito", "Cartão de Débito", "PIX", "Transferência"],
                index=["Dinheiro", "Cartão de Crédito", "Cartão de Débito", "PIX", "Transferência"].index(
                    st.session_state.form_data['forma_pagamento'])
            )
        with col2:
            observations = st.text_input("Observações", value=st.session_state.form_data['observations'])
            comprovante = st.file_uploader("Comprovante (opcional)", type=['png', 'jpg', 'jpeg', 'pdf'])
        
        col3, col4 = st.columns(2)
        with col3:
            pickup_time = st.selectbox(
                "Horário de Retirada",
                ["entre 9 e 10", "entre 10 e 11", "entre 11 e 12", "entre 12 e 13"],
                index=["entre 9 e 10", "entre 10 e 11", "entre 11 e 12", "entre 12 e 13"].index(
                    st.session_state.form_data['pickup_time'])
            )
        
        st.subheader("Quantidade de Pizzas")
        col5, col6, col7, col8 = st.columns(4)
        with col5:
            frango_com = st.number_input("Frango COM cebola", min_value=0, value=st.session_state.form_data['frango_com'])
        with col6:
            frango_sem = st.number_input("Frango SEM cebola", min_value=0, value=st.session_state.form_data['frango_sem'])
        with col7:
            calabresa_com = st.number_input("Calabresa COM cebola", min_value=0, value=st.session_state.form_data['calabresa_com'])
        with col8:
            calabresa_sem = st.number_input("Calabresa SEM cebola", min_value=0, value=st.session_state.form_data['calabresa_sem'])
        
        # Cálculo do valor total
        precos = {
            'frangoComCebola': 30.0,
            'frangoSemCebola': 30.0,
            'calabresaComCebola': 35.0,
            'calabresaSemCebola': 35.0
        }
        
        valor_total = (
            frango_com * precos['frangoComCebola'] +
            frango_sem * precos['frangoSemCebola'] +
            calabresa_com * precos['calabresaComCebola'] +
            calabresa_sem * precos['calabresaSemCebola']
        )
        
        st.metric("Valor Total", f"R$ {valor_total:.2f}")
        
        st.subheader("Status do Pedido")
        col9, col10, col11 = st.columns(3)
        with col9:
            payment_checked = st.checkbox("Pagamento Conferido", value=st.session_state.form_data['payment_checked'])
        with col10:
            delivered_seller = st.checkbox("Entregue ao Vendedor", value=st.session_state.form_data['delivered_seller'])
        with col11:
            delivered_customer = st.checkbox("Entregue ao Cliente", value=st.session_state.form_data['delivered_customer'])
        
        submitted = st.form_submit_button("Salvar Pedido")
        if submitted:
            if not seller_name:
                st.error("Nome do vendedor é obrigatório!")
            else:
                order_data = {
                    'timestamp': datetime.datetime.now().isoformat(),
                    'sellerName': seller_name,
                    'frangoComCebola': frango_com,
                    'frangoSemCebola': frango_sem,
                    'calabresaComCebola': calabresa_com,
                    'calabresaSemCebola': calabresa_sem,
                    'pickupTime': pickup_time,
                    'observations': observations,
                    'paymentProof': "",
                    'paymentChecked': payment_checked,
                    'deliveredToSeller': delivered_seller,
                    'deliveredToCustomer': delivered_customer,
                    'forma_pagamento': forma_pagamento
                }
                
                order_id = st.session_state.editing_order_id or str(datetime.datetime.now().timestamp())
                save_order(order_id, order_data)
                
                # Salvar comprovante se existir
                if comprovante:
                    save_comprovante(comprovante, order_id)
                
                # Resetar o formulário
                st.session_state.form_data = {
                    'seller_name': "",
                    'pickup_time': "entre 9 e 10",
                    'observations': "",
                    'payment_proof': "",
                    'frango_com': 0,
                    'frango_sem': 0,
                    'calabresa_com': 0,
                    'calabresa_sem': 0,
                    'payment_checked': False,
                    'delivered_seller': False,
                    'delivered_customer': False,
                    'forma_pagamento': "Dinheiro",
                    'comprovante': None
                }
                
                if st.session_state.editing_order_id:
                    st.session_state.editing_order_id = None
                    st.success("Pedido atualizado com sucesso!")
                else:
                    st.success("Pedido adicionado com sucesso!")
                
                st.rerun()

def visualizar_pedidos():
    st.header("📋 Pedidos Registrados")
    
    orders_df = get_all_orders()
    
    if not orders_df.empty:
        # Filtros
        st.subheader("Filtros")
        col1, col2 = st.columns(2)
        with col1:
            filtro_vendedor = st.selectbox(
                "Filtrar por vendedor",
                ["Todos"] + list(orders_df['sellerName'].unique()))
        with col2:
            filtro_status = st.selectbox(
                "Filtrar por status",
                ["Todos", "Pago", "Não Pago", "Entregue ao Vendedor", "Entregue ao Cliente"])
        
        # Aplicar filtros
        if filtro_vendedor != "Todos":
            orders_df = orders_df[orders_df['sellerName'] == filtro_vendedor]
        
        if filtro_status == "Pago":
            orders_df = orders_df[orders_df['paymentChecked'] == 1]
        elif filtro_status == "Não Pago":
            orders_df = orders_df[orders_df['paymentChecked'] == 0]
        elif filtro_status == "Entregue ao Vendedor":
            orders_df = orders_df[orders_df['deliveredToSeller'] == 1]
        elif filtro_status == "Entregue ao Cliente":
            orders_df = orders_df[orders_df['deliveredToCustomer'] == 1]
        
        # Ordenação
        sort_option = st.selectbox(
            "Ordenar por",
            ["Data (Mais Recente)", "Data (Mais Antigo)", "Vendedor (A-Z)", "Vendedor (Z-A)", "Valor (Maior)", "Valor (Menor)"]
        )
        
        if sort_option == "Data (Mais Recente)":
            orders_df = orders_df.sort_values('timestamp', ascending=False)
        elif sort_option == "Data (Mais Antigo)":
            orders_df = orders_df.sort_values('timestamp', ascending=True)
        elif sort_option == "Vendedor (A-Z)":
            orders_df = orders_df.sort_values('sellerName', ascending=True)
        elif sort_option == "Vendedor (Z-A)":
            orders_df = orders_df.sort_values('sellerName', ascending=False)
        elif sort_option == "Valor (Maior)":
            orders_df = orders_df.sort_values('valor_total', ascending=False)
        elif sort_option == "Valor (Menor)":
            orders_df = orders_df.sort_values('valor_total', ascending=True)
        
        # Exibir pedidos
        for _, row in orders_df.iterrows():
            with st.container(border=True):
                col1, col2 = st.columns([4, 1])
                with col1:
                    st.markdown(f"**Vendedor:** {row['sellerName']} | **Data:** {pd.to_datetime(row['timestamp']).strftime('%d/%m/%Y %H:%M')}")
                    st.markdown(f"**Frango C/Cebola:** {row['frangoComCebola']} | **Frango S/Cebola:** {row['frangoSemCebola']}")
                    st.markdown(f"**Calabresa C/Cebola:** {row['calabresaComCebola']} | **Calabresa S/Cebola:** {row['calabresaSemCebola']}")
                    st.markdown(f"**Retirada:** {row['pickupTime']} | **Valor Total:** R$ {row['valor_total']:.2f}")
                    st.markdown(f"**Forma de Pagamento:** {row['forma_pagamento']}")
                    
                    if pd.notna(row['observations']) and row['observations'] != '':
                        st.markdown(f"**Observações:** {row['observations']}")
                    
                    # Status
                    status = []
                    if row['paymentChecked']:
                        status.append("✅ Pago")
                    if row['deliveredToSeller']:
                        status.append("🚚 Vendedor")
                    if row['deliveredToCustomer']:
                        status.append("🏠 Cliente")
                    if status:
                        st.markdown("**Status:** " + " | ".join(status))
                
                with col2:
                    # Botões de ação
                    if st.button("✏️ Editar", key=f"edit_{row['id']}"):
                        st.session_state.editing_order_id = row['id']
                        st.session_state.form_data = {
                            'seller_name': row['sellerName'],
                            'pickup_time': row['pickupTime'],
                            'observations': row['observations'] if pd.notna(row['observations']) else "",
                            'payment_proof': row['paymentProof'] if pd.notna(row['paymentProof']) else "",
                            'frango_com': row['frangoComCebola'],
                            'frango_sem': row['frangoSemCebola'],
                            'calabresa_com': row['calabresaComCebola'],
                            'calabresa_sem': row['calabresaSemCebola'],
                            'payment_checked': bool(row['paymentChecked']),
                            'delivered_seller': bool(row['deliveredToSeller']),
                            'delivered_customer': bool(row['deliveredToCustomer']),
                            'forma_pagamento': row['forma_pagamento']
                        }
                        st.session_state.menu = "Registrar Pedido"
                        st.rerun()
                    
                    if st.button("🗑️ Excluir", key=f"delete_{row['id']}"):
                        delete_order(row['id'])
                        st.success("Pedido excluído com sucesso!")
                        st.rerun()
        
        # Totais
        st.subheader("Totais")
        col3, col4, col5 = st.columns(3)
        with col3:
            st.metric("Total de Vendas", f"R$ {orders_df['valor_total'].sum():.2f}")
        with col4:
            st.metric("Número de Pedidos", len(orders_df))
        with col5:
            st.metric("Média por Pedido", f"R$ {orders_df['valor_total'].mean():.2f}")
    else:
        st.info("Nenhum pedido cadastrado ainda.")

def mostrar_fluxo_caixa():
    st.header("💰 Fluxo de Caixa")
    
    df_fluxo = gerar_fluxo_caixa()
    
    if not df_fluxo.empty:
        # Filtro por período
        st.subheader("Filtrar por Período")
        col1, col2 = st.columns(2)
        with col1:
            data_inicio = st.date_input("Data Início", pd.to_datetime(df_fluxo['data']).min())
        with col2:
            data_fim = st.date_input("Data Fim", pd.to_datetime(df_fluxo['data']).max())
        
        df_fluxo['data'] = pd.to_datetime(df_fluxo['data'])
        df_filtrado = df_fluxo[
            (df_fluxo['data'].dt.date >= data_inicio) &
            (df_fluxo['data'].dt.date <= data_fim)
        ]
        
        # Resumo financeiro
        st.subheader("Resumo Financeiro")
        total_periodo = df_filtrado['total'].sum()
        media_diaria = df_filtrado.groupby('data')['total'].sum().mean()
        
        col3, col4 = st.columns(2)
        with col3:
            st.metric("Total no Período", f"R$ {total_periodo:.2f}")
        with col4:
            st.metric("Média Diária", f"R$ {media_diaria:.2f}")
        
        # Gráficos
        st.subheader("Visualizações")
        
        tab1, tab2, tab3 = st.tabs(["Evolução Diária", "Formas de Pagamento", "Dados Detalhados"])
        
        with tab1:
            st.line_chart(df_filtrado.groupby('data')['total'].sum())
        
        with tab2:
            st.bar_chart(df_filtrado.groupby('forma_pagamento')['total'].sum())
        
        with tab3:
            st.dataframe(df_filtrado)
        
        # Exportar dados
        st.subheader("Exportar Dados")
        csv = df_filtrado.to_csv(index=False).encode('utf-8')
        st.download_button(
            "Baixar como CSV",
            csv,
            "fluxo_caixa.csv",
            "text/csv"
        )
    else:
        st.warning("Nenhum dado de venda disponível para gerar o fluxo de caixa.")

def gerenciar_comprovantes():
    st.header("🧾 Comprovantes de Venda")
    
    orders_df = get_all_orders()
    
    if not orders_df.empty:
        # Selecionar pedido
        order_id = st.selectbox(
            "Selecione um pedido para ver os comprovantes",
            orders_df['id'],
            format_func=lambda x: f"{orders_df[orders_df['id'] == x]['sellerName'].iloc[0]} - {pd.to_datetime(orders_df[orders_df['id'] == x]['timestamp'].iloc[0]).strftime('%d/%m/%Y %H:%M')}"
        )
        
        # Mostrar detalhes do pedido
        pedido = orders_df[orders_df['id'] == order_id].iloc[0]
        
        with st.expander("Detalhes do Pedido"):
            st.markdown(f"**Vendedor:** {pedido['sellerName']}")
            st.markdown(f"**Data:** {pd.to_datetime(pedido['timestamp']).strftime('%d/%m/%Y %H:%M')}")
            st.markdown(f"**Valor Total:** R$ {pedido['valor_total']:.2f}")
            st.markdown(f"**Forma de Pagamento:** {pedido['forma_pagamento']}")
        
        # Comprovantes existentes
        comprovantes = get_comprovantes(order_id)
        
        if comprovantes:
            st.subheader("Comprovantes Associados")
            
            for comprovante in comprovantes:
                with st.container(border=True):
                    if comprovante.lower().endswith(('.png', '.jpg', '.jpeg')):
                        st.image(comprovante, caption=os.path.basename(comprovante), width=300)
                    elif comprovante.lower().endswith('.pdf'):
                        st.warning("Visualização de PDF não suportada diretamente. Faça download para visualizar.")
                    
                    with open(comprovante, "rb") as f:
                        st.download_button(
                            f"Download {os.path.basename(comprovante)}",
                            f.read(),
                            os.path.basename(comprovante)
                        )
                    
                    if st.button(f"Excluir {os.path.basename(comprovante)}", key=f"del_{comprovante}"):
                        conn = sqlite3.connect('pizza.db')
                        c = conn.cursor()
                        c.execute("DELETE FROM comprovantes WHERE file_path=?", (comprovante,))
                        conn.commit()
                        conn.close()
                        
                        if os.path.exists(comprovante):
                            os.remove(comprovante)
                        
                        st.success("Comprovante excluído com sucesso!")
                        st.rerun()
        else:
            st.info("Nenhum comprovante associado a este pedido.")
        
        # Adicionar novo comprovante
        st.subheader("Adicionar Comprovante")
        novo_comprovante = st.file_uploader("Carregar novo comprovante", type=['png', 'jpg', 'jpeg', 'pdf'])
        
        if novo_comprovante:
            if st.button("Salvar Comprovante"):
                save_comprovante(novo_comprovante, order_id)
                st.success("Comprovante adicionado com sucesso!")
                st.rerun()
    else:
        st.info("Nenhum pedido cadastrado para visualizar comprovantes.")

# Fluxo principal do aplicativo
def main():
    # Inicializar estados da sessão
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False
    if 'show_login' not in st.session_state:
        st.session_state.show_login = False
    if 'menu' not in st.session_state:
        st.session_state.menu = "Registrar Pedido"
    
    # Mostrar a tela apropriada
    if st.session_state.logged_in:
        main_app()
    elif st.session_state.show_login:
        login_screen()
    else:
        welcome_screen()

if __name__ == "__main__":
    main()