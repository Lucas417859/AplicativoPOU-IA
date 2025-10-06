# === CONFIGURAÇÕES PARA HOSPEDAGEM ===
import os
from dotenv import load_dotenv

load_dotenv()  # Carrega variáveis de ambiente

# Busca API Key de variáveis de ambiente (mais seguro)
API_KEY = os.getenv('GROQ_API_KEY', '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')
import streamlit as st
import pandas as pd
import sqlite3
import time
import os
from datetime import datetime
from groq import Groq

# ========= CONFIGURAÇÕES INICIAIS E TEMA ==========
st.set_page_config(
    page_title="Apicativo POU- Soluções Tecnológicas para Almoxarifados.", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# Estilo Customizado (Tema Industrial Clean)
st.markdown("""
<style>
    /* Cor principal (Azul Industrial) */
    :root {
        --primary-color: #0072BB;
        --secondary-color: #F0F2F6; 
        --success-color: #28a745;
        --warning-color: #ffc107;
        --danger-color: #dc3545;
    }
    
    h1 { color: var(--primary-color); font-weight: 700; }
    
    /* Estilo dos Botões */
    .stButton>button {
        background-color: var(--primary-color); 
        color: white;
        border-radius: 8px;
        padding: 10px 20px;
        transition: all 0.2s;
        border: none;
    }
    .stButton>button:hover {
        background-color: #00508C; 
        transform: scale(1.02);
    }
    
    /* Estilo para cards/containers e métricas */
    .stAlert { border-radius: 8px; }
    div[data-testid="stMetric"] > div[data-testid="stRealValue"] {
        font-size: 2.5rem;
        color: var(--primary-color);
        font-weight: 600;
    }
</style>
""", unsafe_allow_html=True)

# Dados do usuário
API_KEY = "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"
MODEL = "llama-3.3-70b-versatile"

# Inicialização do cliente Groq com tratamento de erro
try:
    groq_client = Groq(api_key=API_KEY)
    groq_available = True
except Exception as e:
    groq_client = None
    groq_available = False

# Constantes de Arquivo e Colunas
FILE_NAME = "poweapp.2.xlsx" 

# --- Estrutura de Colunas ---
COLUNAS_DB = [
    "kardex", "descricao", "classe", "codigo_global", 
    "almoxarifado", "compartimento", "fornecedor_principal", 
    "min_level", "max_level"
]

# --- Mapeamento para Leitura do Arquivo ---
RENAME_DICT = {
    "Coluna1": "kardex", 
    "Descricao": "descricao",
    "Classe": "classe",
    "Descricao do Codigo Global": "codigo_global", 
    "Almoxarifado": "almoxarifado", 
    "Compartimento": "compartimento", 
    "Fornecedor Principal": "fornecedor_principal",
    "Min Level": "min_level", 
    "Max Level": "max_level"
}

# Opções para tipos de requisição
TIPOS_REQUISICAO = ["POU Manutenção", "POU Manutenção Central", "POU Oficina"]

# ========= FUNÇÕES DE BANCO DE DADOS (SQLite) ==========

def init_db():
    """Inicializa a conexão e cria as tabelas 'itens' e 'requisicoes'."""
    conn = sqlite3.connect("pou_platinum.db")
    c = conn.cursor()
    
    # Criação da tabela itens
    c.execute("""
        CREATE TABLE IF NOT EXISTS itens (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            kardex TEXT,
            descricao TEXT,
            classe TEXT,
            codigo_global TEXT,
            almoxarifado TEXT,
            compartimento TEXT,
            fornecedor_principal TEXT,
            min_level REAL,
            max_level REAL
        )
    """)
    
    # Criação da tabela requisições (ESTRUTURA SIMPLIFICADA E CORRETA)
    c.execute("""
        CREATE TABLE IF NOT EXISTS requisicoes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            item_id INTEGER,
            tipo_requisicao TEXT,
            setor TEXT,
            quantidade INTEGER,
            motivo TEXT,
            material_novo BOOLEAN DEFAULT 0,
            descricao_material_novo TEXT,
            especificacao_material_novo TEXT,
            status TEXT DEFAULT 'Pendente',
            solicitante TEXT,
            data TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (item_id) REFERENCES itens (id)
        )
    """)
    conn.commit()
    conn.close()

def resetar_banco_completo():
    """Reseta completamente o banco de dados para corrigir erros."""
    conn = sqlite3.connect("pou_platinum.db")
    c = conn.cursor()
    
    # Remove as tabelas
    c.execute("DROP TABLE IF EXISTS requisicoes")
    c.execute("DROP TABLE IF EXISTS itens")
    
    # Recria as tabelas
    c.execute("""
        CREATE TABLE itens (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            kardex TEXT,
            descricao TEXT,
            classe TEXT,
            codigo_global TEXT,
            almoxarifado TEXT,
            compartimento TEXT,
            fornecedor_principal TEXT,
            min_level REAL,
            max_level REAL
        )
    """)
    
    c.execute("""
        CREATE TABLE requisicoes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            item_id INTEGER,
            tipo_requisicao TEXT,
            setor TEXT,
            quantidade INTEGER,
            motivo TEXT,
            material_novo BOOLEAN DEFAULT 0,
            descricao_material_novo TEXT,
            especificacao_material_novo TEXT,
            status TEXT DEFAULT 'Pendente',
            solicitante TEXT,
            data TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (item_id) REFERENCES itens (id)
        )
    """)
    conn.commit()
    conn.close()

@st.cache_data
def carregar_itens_df():
    """Lê o arquivo de dados (cacheado para performance)."""
    try:
        if not os.path.exists(FILE_NAME):
            st.error(f"❌ Arquivo '{FILE_NAME}' não encontrado no diretório atual.")
            return pd.DataFrame()
            
        if FILE_NAME.endswith('.xlsx'):
            df = pd.read_excel(FILE_NAME)
        else:
            df = pd.read_csv(FILE_NAME, encoding='latin1', on_bad_lines='skip')
            
    except Exception as e:
        st.error(f"❌ Erro ao ler arquivo: {e}")
        return pd.DataFrame()

    try:
        # Verifica e ajusta colunas
        num_cols = df.shape[1]
        expected_cols = len(RENAME_DICT)
        
        if num_cols != expected_cols:
            st.warning(f"⚠️ Arquivo tem {num_cols} colunas, esperávamos {expected_cols}. Ajustando...")
        
        # Atribui nomes às colunas
        if num_cols <= expected_cols:
            df.columns = list(RENAME_DICT.keys())[:num_cols]
        else:
            df = df.iloc[:, :expected_cols]
            df.columns = list(RENAME_DICT.keys())
        
        # Renomeia as colunas
        df.rename(columns=RENAME_DICT, inplace=True)
        
        # Filtra colunas que existem
        colunas_existentes = [c for c in COLUNAS_DB if c in df.columns]
        df_final = df[colunas_existentes].copy()
        
        # Limpa valores nulos
        for col in ['min_level', 'max_level']:
            if col in df_final.columns:
                df_final[col] = pd.to_numeric(df_final[col], errors='coerce').fillna(0)
                
        return df_final
        
    except Exception as e:
        st.error(f"❌ Erro ao processar colunas: {e}")
        return pd.DataFrame()

def popular_banco(df):
    """Insere os dados do DataFrame na tabela 'itens'."""
    if df.empty:
        st.error("❌ DataFrame vazio. Nada para inserir.")
        return 0
        
    conn = sqlite3.connect("pou_platinum.db")
    c = conn.cursor()
    
    # Limpa a tabela antes de popular
    c.execute("DELETE FROM itens") 
    
    inserted_count = 0
    for _, row in df.iterrows():
        try:
            # Prepara valores para inserção
            valores = []
            colunas = []
            
            for col in COLUNAS_DB:
                if col in df.columns:
                    colunas.append(col)
                    valores.append(row[col])
            
            placeholders = ', '.join(['?'] * len(colunas))
            colunas_str = ', '.join(colunas)
            
            c.execute(f"INSERT INTO itens ({colunas_str}) VALUES ({placeholders})", valores)
            inserted_count += 1
        except Exception:
            continue
        
    conn.commit()
    conn.close()
    return inserted_count

def get_itens(filtro=None):
    """Busca itens no DB, aplicando filtro opcional."""
    conn = sqlite3.connect("pou_platinum.db")
    
    query = """
        SELECT id, kardex, descricao, classe, codigo_global, 
               almoxarifado, compartimento, fornecedor_principal,
               min_level, max_level 
        FROM itens
    """
    
    if filtro:
        query += f"""
            WHERE descricao LIKE '%{filtro}%'
            OR classe LIKE '%{filtro}%'
            OR almoxarifado LIKE '%{filtro}%'
            OR codigo_global LIKE '%{filtro}%'
            OR kardex LIKE '%{filtro}%'
        """
    
    try:
        df = pd.read_sql_query(query, conn)
    except Exception as e:
        st.error(f"Erro na consulta: {e}")
        df = pd.DataFrame()
        
    conn.close()
    return df

def criar_requisicao(item_id, tipo_requisicao, setor, quantidade, motivo, solicitante, 
                    material_novo=False, descricao_material_novo="", especificacao_material_novo=""):
    """Cria uma nova requisição de material."""
    conn = sqlite3.connect("pou_platinum.db")
    c = conn.cursor()
    
    # Converte boolean para inteiro (SQLite não tem boolean nativo)
    material_novo_int = 1 if material_novo else 0
    
    c.execute("""
        INSERT INTO requisicoes 
        (item_id, tipo_requisicao, setor, quantidade, motivo, solicitante, 
         material_novo, descricao_material_novo, especificacao_material_novo)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (item_id, tipo_requisicao, setor, quantidade, motivo, solicitante,
          material_novo_int, descricao_material_novo, especificacao_material_novo))
    
    conn.commit()
    conn.close()

def get_requisicoes():
    """Busca todas as requisições."""
    conn = sqlite3.connect("pou_platinum.db")
    
    try:
        # Query corrigida - sem LEFT JOIN complexo
        df = pd.read_sql_query("""
            SELECT r.id, 
                   CASE 
                     WHEN r.material_novo = 1 THEN r.descricao_material_novo 
                     ELSE i.descricao 
                   END as descricao,
                   CASE 
                     WHEN r.material_novo = 1 THEN 'NOVO ITEM' 
                     ELSE i.kardex 
                   END as kardex,
                   r.tipo_requisicao, 
                   r.setor, 
                   r.quantidade, 
                   r.motivo, 
                   r.status, 
                   r.solicitante, 
                   r.data,
                   r.material_novo
            FROM requisicoes r
            LEFT JOIN itens i ON r.item_id = i.id
            ORDER BY r.id DESC
        """, conn)
    except Exception as e:
        st.error(f"Erro ao buscar requisições: {e}")
        # Tenta uma query mais simples
        try:
            df = pd.read_sql_query("SELECT * FROM requisicoes ORDER BY id DESC", conn)
        except:
            df = pd.DataFrame()
        
    conn.close()
    return df

def atualizar_status_requisicao(req_id, status):
    """Atualiza o status de uma requisição."""
    conn = sqlite3.connect("pou_platinum.db")
    c = conn.cursor()
    c.execute("UPDATE requisicoes SET status = ? WHERE id = ?", (status, req_id))
    conn.commit()
    conn.close()

# Inicializa o DB
init_db()

# ========= CABEÇALHO DO APLICATIVO ==========
col_logo, col_title = st.columns([1, 4])
with col_logo:
    st.markdown('<div style="background-color: #0072BB; color: white; padding: 10px; border-radius: 5px; text-align: center; font-weight: bold;">GM POU</div>', unsafe_allow_html=True) 
with col_title:
    st.title("POU Platinum - Almoxarifado Inteligente")
    st.markdown("---")

# Menu lateral
menu = st.sidebar.radio(
    "Escolha a Seção", 
    ["1️⃣ Carregar Dados", "2️⃣ Consultar Estoque", "3️⃣ Solicitar Item", "4️⃣ Aprovar Requisições", "5️⃣ Chat IA"],
    index=1 
)

# ========= 1️⃣ CARREGAR DADOS ==========
if menu == "1️⃣ Carregar Dados":
    st.header("⚙️ Carregamento e Manutenção de Dados")
    
    # Ferramentas de correção
    with st.expander("🔧 CORREÇÃO DE ERROS (Usar se houver problemas)"):
        st.warning("⚠️ Esta ação apaga TODOS os dados e recria as tabelas.")
        if st.button("🔄 RESETAR BANCO DE DADOS COMPLETO"):
            resetar_banco_completo()
            st.success("✅ Banco de dados resetado com sucesso!")
            time.sleep(2)
            st.rerun()
    
    uploaded_file = st.file_uploader("Ou faça upload de um novo arquivo", type=['xlsx', 'csv'])
    
    if uploaded_file is not None:
        with open(FILE_NAME, "wb") as f:
            f.write(uploaded_file.getbuffer())
        st.success(f"✅ Arquivo '{uploaded_file.name}' salvo como {FILE_NAME}")
    
    df = carregar_itens_df()
    
    if not df.empty:
        st.markdown(f"**Arquivo lido:** `{FILE_NAME}` com **{len(df)}** linhas.")
        
        with st.expander("Visualizar Dados Carregados"):
            st.dataframe(df.head(10), use_container_width=True)
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total de Itens", len(df))
            with col2:
                st.metric("Colunas", df.shape[1])
            with col3:
                kardex_unicos = df['kardex'].nunique() if 'kardex' in df.columns else 0
                st.metric("Kardex Únicos", kardex_unicos)
        
        if st.button("🚀 Inserir/Atualizar Banco de Dados POU", type="primary"):
            with st.spinner("Processando e populando o banco..."):
                inserted_count = popular_banco(df)
                
            if inserted_count > 0:
                st.success(f"✅ **Banco de dados atualizado! {inserted_count} itens inseridos.**")
                st.cache_data.clear()
            else:
                st.error("❌ Nenhum item foi inserido no banco.")
    else:
        st.error(f"❌ Não foi possível carregar os dados do arquivo '{FILE_NAME}'.")

# ========= 2️⃣ CONSULTAR ESTOQUE ==========
elif menu == "2️⃣ Consultar Estoque":
    st.header("🔍 Consulta Detalhada de Itens")
    
    df_all = get_itens()
    
    if not df_all.empty:
        col_kpi1, col_kpi2, col_kpi3 = st.columns(3)
        col_kpi1.metric("Total de Itens", len(df_all))
        
        if 'fornecedor_principal' in df_all.columns:
            col_kpi2.metric("Fornecedores", df_all['fornecedor_principal'].nunique())
        else:
            col_kpi2.metric("Fornecedores", "N/D")
            
        col_kpi3.metric("Itens Únicos", df_all['kardex'].nunique())

        st.markdown("---")
        
        filtro_principal = st.text_input("🔍 Buscar Item por: Descrição, Kardex ou Localização", 
                                       placeholder="Digite termos de busca...")
        
        df_filtrado = get_itens(filtro_principal) if filtro_principal else df_all
        
        st.markdown(f"**{len(df_filtrado)} itens encontrados**")
        
        st.dataframe(
            df_filtrado, 
            use_container_width=True,
            hide_index=True,
            column_config={
                "id": st.column_config.NumberColumn("ID", format="%d"),
                "kardex": "Kardex",
                "descricao": "Descrição",
                "almoxarifado": "Almox.",
                "compartimento": "Localização",
                "fornecedor_principal": "Fornecedor"
            }
        )
    else:
        st.info("📝 Nenhum item cadastrado. Vá para 'Carregar Dados' para importar.")

# ========= 3️⃣ SOLICITAR ITEM ==========
elif menu == "3️⃣ Solicitar Item":
    st.header("🛒 Criar Nova Requisição de Material")
    
    df_all = get_itens()
    
    tab1, tab2 = st.tabs(["📦 Material do Estoque", "🆕 Novo Material"])
    
    with tab1:
        st.subheader("Requisitar Material Existente")
        
        if df_all.empty:
            st.warning("📝 Nenhum item disponível. Carregue os dados primeiro.")
        else:
            col_main, col_form = st.columns([1, 1.5])

            with col_main:
                st.markdown("### 1. Encontre o Item")
                filtro_solic = st.text_input("Busca Rápida (Nome, Kardex, Local)", key='filtro_solic')
                df_busca = get_itens(filtro_solic) if filtro_solic else df_all
                
                st.dataframe(
                    df_busca[['id', 'kardex', 'descricao']], 
                    height=300, 
                    use_container_width=True
                )

            with col_form:
                st.markdown("### 2. Preencha a Requisição")
                with st.container(border=True):
                    item_id = st.number_input("ID do Item *", min_value=1, step=1, key='req_item_id')
                    
                    # Valida se o ID existe
                    id_valido = item_id in df_all['id'].values
                    
                    if item_id > 0 and not id_valido:
                        st.warning("⚠️ ID não encontrado")
                    
                    tipo_requisicao = st.selectbox("Tipo de Requisição *", TIPOS_REQUISICAO)
                    
                    setor = st.text_input("Setor/Solicitante *", placeholder="Ex: Manutenção - Lucas")
                    
                    qtd = st.number_input("Quantidade Necessária *", min_value=1, step=1, key='req_qtd')
                    
                    motivo = st.text_area("Motivo da Requisição *", height=80, placeholder="Ex: PMC Pintura")
                    
                    if st.button("📩 Enviar Requisição", use_container_width=True, type="primary"):
                        if not all([setor.strip(), motivo.strip()]):
                            st.error("❌ Preencha todos os campos obrigatórios (*)")
                        elif item_id <= 0:
                            st.error("❌ ID do item deve ser maior que zero")
                        elif not id_valido:
                            st.error("❌ ID do item não encontrado")
                        else:
                            try:
                                criar_requisicao(
                                    item_id=item_id,
                                    tipo_requisicao=tipo_requisicao,
                                    setor=setor.strip(),
                                    quantidade=qtd,
                                    motivo=motivo.strip(),
                                    solicitante=setor.strip(),
                                    material_novo=False
                                )
                                st.success("✅ Requisição enviada para aprovação!")
                                time.sleep(2)
                                st.rerun()
                            except Exception as e:
                                st.error(f"❌ Erro: {e}")
    
    with tab2:
        st.subheader("Solicitar Material Novo")
        st.info("💡 Para materiais que não estão no estoque")
        
        with st.container(border=True):
            tipo_requisicao_novo = st.selectbox("Tipo de Requisição *", TIPOS_REQUISICAO, key="tipo_novo")
            
            setor_novo = st.text_input("Setor/Solicitante *", key="setor_novo", placeholder="Ex: Oficina - João")
            
            descricao_material = st.text_input("Descrição do Material *", placeholder="Ex: Parafuso M8x50 INOX")
            
            especificacao = st.text_area("Especificações Técnicas *", height=80, placeholder="Ex: M8 x 60mm, INOX A2")
            
            qtd_novo = st.number_input("Quantidade *", min_value=1, step=1, key='req_qtd_novo')
            
            motivo_novo = st.text_area("Motivo *", height=80, key="motivo_novo", placeholder="Ex: PMC Ferramentaria")
            
            if st.button("🆕 Enviar Requisição de Material Novo", use_container_width=True, type="primary"):
                if not all([setor_novo.strip(), descricao_material.strip(), especificacao.strip(), motivo_novo.strip()]):
                    st.error("❌ Preencha todos os campos obrigatórios (*)")
                else:
                    try:
                        criar_requisicao(
                            item_id=None,
                            tipo_requisicao=tipo_requisicao_novo,
                            setor=setor_novo.strip(),
                            quantidade=qtd_novo,
                            motivo=motivo_novo.strip(),
                            solicitante=setor_novo.strip(),
                            material_novo=True,
                            descricao_material_novo=descricao_material.strip(),
                            especificacao_material_novo=especificacao.strip()
                        )
                        st.success("🎉 Requisição de material novo enviada!")
                        time.sleep(2)
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ Erro: {e}")

# ========= 4️⃣ APROVAR REQUISIÇÕES ==========
elif menu == "4️⃣ Aprovar Requisições":
    st.header("✅ Gerenciamento e Aprovação de Requisições")
    
    reqs = get_requisicoes()
    
    if not reqs.empty:
        reqs_pendentes = reqs[reqs['status'] == 'Pendente']
        
        col_kpi1, col_kpi2 = st.columns(2)
        col_kpi1.metric("Total de Requisições", len(reqs))
        col_kpi2.metric("Pendentes", len(reqs_pendentes))
        
        st.markdown("---")
        st.markdown("### Histórico de Requisições")
        
        st.dataframe(reqs, use_container_width=True, hide_index=True)
        
        if not reqs_pendentes.empty:
            st.markdown("---")
            st.markdown("### 🎯 Aprovar / Rejeitar")
            with st.container(border=True):
                req_id_list = reqs_pendentes['id'].tolist()
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    req_id_selecionada = st.selectbox("ID da Requisição", req_id_list)
                    
                    if req_id_selecionada:
                        req_detalhes = reqs_pendentes[reqs_pendentes['id'] == req_id_selecionada].iloc[0]
                        st.markdown(f"**Item:** {req_detalhes['descricao']}")
                        st.markdown(f"**Solicitante:** {req_detalhes['solicitante']}")
                        st.markdown(f"**Quantidade:** {req_detalhes['quantidade']}")
                
                with col2:
                    status = st.radio("Status", ["Aprovado", "Rejeitado"])
                
                with col3:
                    st.markdown("<br>", unsafe_allow_html=True)
                    if st.button("🔄 Atualizar Status", use_container_width=True):
                        atualizar_status_requisicao(req_id_selecionada, status)
                        st.success(f"✅ Requisição {req_id_selecionada} {status.lower()}!")
                        time.sleep(1)
                        st.rerun()
        else:
            st.info("🎉 Não há requisições pendentes.")
    else:
        st.info("📝 Nenhuma requisição registrada.")

# ========= 5️⃣ CHAT IA (FINAL) ==========
# ========= 5️⃣ CHAT IA (VERSÃO MELHORADA) ==========
# ========= 5️⃣ CHAT IA (VERSÃO SUPER INTELIGENTE) ==========
# ========= 5️⃣ CHAT IA (VERSÃO MELHORADA) ==========
elif menu == "5️⃣ Chat IA":
    st.header("🤖 POU-IA — Seu Especialista em Almoxarifado")
    
    if not groq_available:
        st.error("🚫 Serviço de IA indisponível.")
        st.info("💡 As outras funcionalidades continuam disponíveis!")
    else:
        st.info("""
        💡 **Exemplos:** 
        - *Onde fica o item 'MOLA GAS'?*
        - *Qual o fornecedor do Kardex 2122?*
        - *Mostre itens da classe 'PARAFUSO'*
        - *Quantos itens tem no estoque?*
        - *Quais os principais fornecedores?*
        """)

        # Inicializa o histórico do chat
        if "messages" not in st.session_state:
            st.session_state.messages = []
            
        # Exibe histórico do chat
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

        user_input = st.chat_input("Pergunte sobre estoque...")
        
        if user_input:
            # Adiciona mensagem do usuário
            st.session_state.messages.append({"role": "user", "content": user_input})
            with st.chat_message("user"):
                st.markdown(user_input)
                
            try:
                with st.chat_message("assistant"):
                    with st.spinner("🔍 Analisando estoque..."):
                        # Busca dados do estoque
                        df_estoque = get_itens()
                        
                        if not df_estoque.empty:
                            # ANÁLISE COMPLETA DOS DADOS PARA O CHAT
                            total_itens = len(df_estoque)
                            
                            # Análise de fornecedores
                            if 'fornecedor_principal' in df_estoque.columns:
                                fornecedores = df_estoque['fornecedor_principal'].dropna().unique()
                                top_fornecedores = df_estoque['fornecedor_principal'].value_counts().head(5)
                            else:
                                fornecedores = []
                                top_fornecedores = pd.Series()
                            
                            # Análise de classes
                            if 'classe' in df_estoque.columns:
                                classes = df_estoque['classe'].dropna().unique()
                                top_classes = df_estoque['classe'].value_counts().head(5)
                            else:
                                classes = []
                                top_classes = pd.Series()
                            
                            # Análise de almoxarifados
                            if 'almoxarifado' in df_estoque.columns:
                                almoxarifados = df_estoque['almoxarifado'].dropna().unique()
                            else:
                                almoxarifados = []
                            
                            # Prepara dados para busca específica
                            user_lower = user_input.lower()
                            
                            # BUSCAS INTELIGENTES
                            if 'quantos itens' in user_lower or 'total de itens' in user_lower:
                                resposta = f"📊 **Resumo do Estoque:**\n\n• **Total de itens cadastrados:** {total_itens}\n"
                                if len(fornecedores) > 0:
                                    resposta += f"• **Fornecedores cadastrados:** {len(fornecedores)}\n"
                                if len(classes) > 0:
                                    resposta += f"• **Classes de produtos:** {len(classes)}\n"
                                if len(almoxarifados) > 0:
                                    resposta += f"• **Almoxarifados:** {len(almoxarifados)}"
                                
                            elif 'fornecedor' in user_lower or 'fornecedores' in user_lower:
                                if len(fornecedores) > 0:
                                    resposta = f"🏭 **Fornecedores no Sistema:**\n\n"
                                    resposta += f"**Total:** {len(fornecedores)} fornecedores\n\n"
                                    resposta += "**Principais fornecedores:**\n"
                                    for fornecedor, count in top_fornecedores.items():
                                        resposta += f"• {fornecedor}: {count} itens\n"
                                else:
                                    resposta = "📝 Não encontrei informações sobre fornecedores na base de dados."
                            
                            elif 'classe' in user_lower:
                                termo_busca = user_lower.replace('classe', '').replace('"', '').replace("'", "").strip()
                                if termo_busca:
                                    # Busca específica por classe
                                    itens_classe = df_estoque[df_estoque['classe'].str.contains(termo_busca, case=False, na=False)]
                                    if len(itens_classe) > 0:
                                        resposta = f"📦 **Itens da classe '{termo_busca.upper()}':**\n\n"
                                        resposta += f"**Total encontrado:** {len(itens_classe)} itens\n\n"
                                        for _, item in itens_classe.head(10).iterrows():
                                            localizacao = f" - {item['almoxarifado']}" if 'almoxarifado' in item and pd.notna(item['almoxarifado']) else ""
                                            resposta += f"• **{item['descricao']}**{localizacao}\n"
                                        if len(itens_classe) > 10:
                                            resposta += f"\n... e mais {len(itens_classe) - 10} itens"
                                    else:
                                        resposta = f"❌ Não encontrei itens da classe '{termo_busca}'. Tente outra classe."
                                else:
                                    # Lista todas as classes
                                    if len(classes) > 0:
                                        resposta = "📋 **Classes de Produtos Disponíveis:**\n\n"
                                        for classe, count in top_classes.items():
                                            resposta += f"• **{classe}**: {count} itens\n"
                                        if len(classes) > 5:
                                            resposta += f"\n**Total de classes:** {len(classes)}"
                                    else:
                                        resposta = "📝 Não encontrei informações sobre classes na base de dados."
                            
                            elif 'onde' in user_lower or 'local' in user_lower or 'prateleira' in user_lower:
                                # Busca por localização
                                termos = user_lower.replace('onde', '').replace('fica', '').replace('local', '').replace('prateleira', '').strip()
                                if termos:
                                    itens_encontrados = df_estoque[
                                        df_estoque['descricao'].str.contains(termos, case=False, na=False) |
                                        df_estoque['kardex'].str.contains(termos, case=False, na=False)
                                    ]
                                    if len(itens_encontrados) > 0:
                                        resposta = f"📍 **Localização dos itens com '{termos}':**\n\n"
                                        for _, item in itens_encontrados.head(10).iterrows():
                                            almox = item['almoxarifado'] if 'almoxarifado' in item and pd.notna(item['almoxarifado']) else "Não informado"
                                            comp = item['compartimento'] if 'compartimento' in item and pd.notna(item['compartimento']) else "Não informado"
                                            resposta += f"• **{item['descricao']}**\n  🏢 {almox} | 📦 {comp} | 🔢 Kardex: {item['kardex']}\n\n"
                                    else:
                                        resposta = f"❌ Não encontrei itens com '{termos}'. Tente outros termos de busca."
                                else:
                                    resposta = "🔍 Diga qual item você quer encontrar. Ex: 'Onde fica parafuso M8?'"
                            
                            elif any(palavra in user_lower for palavra in ['oi', 'olá', 'tudo bem', 'bom dia', 'boa tarde']):
                                resposta = f"👋 Olá! Sou o POU-IA, seu assistente de almoxarifado! \n\n📊 No momento tenso **{total_itens} itens** cadastrados no sistema. \n\nComo posso ajudar você com o estoque hoje?"
                            
                            elif 'ajuda' in user_lower or 'help' in user_lower:
                                resposta = """🤖 **Como usar o POU-IA:**\n
• **Buscar itens:** "Onde fica parafuso M8?"\n
• **Consultar classes:** "Mostre itens da classe PARAFUSO"\n  
• **Fornecedores:** "Quais fornecedores temos?"\n
• **Estoque geral:** "Quantos itens tem no estoque?"\n
• **Localização:** "Itens no almoxarifado PRINCIPAL"\n\n💡 **Dica:** Seja específico nas buscas!"""
                            
                            else:
                                # Busca geral inteligente
                                itens_encontrados = df_estoque[
                                    df_estoque['descricao'].str.contains(user_lower, case=False, na=False) |
                                    df_estoque['classe'].str.contains(user_lower, case=False, na=False) |
                                    df_estoque['almoxarifado'].str.contains(user_lower, case=False, na=False) |
                                    df_estoque['kardex'].str.contains(user_lower, case=False, na=False)
                                ]
                                
                                if len(itens_encontrados) > 0:
                                    resposta = f"🔍 **Encontrei {len(itens_encontrados)} itens relacionados a '{user_input}':**\n\n"
                                    for _, item in itens_encontrados.head(8).iterrows():
                                        almox = item['almoxarifado'] if 'almoxarifado' in item and pd.notna(item['almoxarifado']) else "Não informado"
                                        comp = item['compartimento'] if 'compartimento' in item and pd.notna(item['compartimento']) else "Não informado"
                                        resposta += f"• **{item['descricao']}**\n  🏢 {almox} | 📦 {comp} | 🔢 {item['kardex']}\n\n"
                                    
                                    if len(itens_encontrados) > 8:
                                        resposta += f"📋 *Mostrando 8 de {len(itens_encontrados)} itens. Seja mais específico para ver mais resultados.*"
                                else:
                                    # Se não encontrou, usa IA generativa para resposta contextual
                                    contexto_geral = f"""
                                    Estoque GM - Resumo:
                                    - Total de itens: {total_itens}
                                    - Fornecedores: {len(fornecedores)} 
                                    - Classes: {len(classes)}
                                    - Almoxarifados: {len(almoxarifados)}
                                    
                                    Pergunta do usuário: {user_input}
                                    
                                    Baseado no contexto do almoxarifado, responda de forma útil mesmo sem encontrar dados específicos.
                                    """
                                    
                                    response = groq_client.chat.completions.create(
                                        model=MODEL,
                                        messages=[{"role": "user", "content": contexto_geral}],
                                        temperature=0.3,
                                        max_tokens=300
                                    )
                                    resposta = response.choices[0].message.content
                        else:
                            resposta = "📝 A base de dados está vazia. Vá em 'Carregar Dados' para importar seu arquivo Excel/CSV."
                    
                    st.markdown(resposta)
                    
                # Adiciona resposta ao histórico
                st.session_state.messages.append({"role": "assistant", "content": resposta})
                
            except Exception as e:
                error_msg = f"❌ Erro: {str(e)}"
                st.error(error_msg)
                st.session_state.messages.append({"role": "assistant", "content": "Desculpe, tive um problema. Tente novamente!"})

        # Botão para limpar o histórico
        if st.button("🧹 Limpar Conversa", use_container_width=True):
            st.session_state.messages = []

            st.rerun()
