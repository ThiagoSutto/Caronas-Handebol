import streamlit as st
import pandas as pd
from supabase import create_client

# ==========================================
# 1. SETUP E CONEXÃO
# ==========================================
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)

# Puxa a lista de nomes do Secrets (escondido do GitHub)
MENINAS_DO_TIME = sorted(list(st.secrets["MENINAS_DO_TIME"]))

# Inicializa a memória do site (Session State)
if "dados_ida" not in st.session_state:
    st.session_state["dados_ida"] = []

# ==========================================
# 2. INTERFACE E SEGURANÇA
# ==========================================
st.set_page_config(page_title="Caronas Handebol", layout="wide")
st.title("🚗 Sistema de Caronas Handebol")

st.sidebar.header("🔐 Acesso Restrito")
senha_digitada = st.sidebar.text_input("Digite a senha do time", type="password")

if senha_digitada == st.secrets["SENHA_TIME"]:
    st.sidebar.success("Acesso liberado!")
    aba_lancamento, aba_resumo, aba_detalhes = st.tabs(["📝 Lançamentos", "📊 Resumo Mensal", "🔍 Detalhes"])
else:
    st.warning("Aguardando senha...")
    st.stop()

# ==========================================
# ABA 1: LANÇAMENTOS (Onde a mágica acontece)
# ==========================================
with aba_lancamento:
    col_input, col_conf = st.columns([1.2, 1])
    
    with col_input:
        st.header("Entrada de Dados")
        
        c1, c2 = st.columns(2)
        with c1:
            data_carona = st.date_input("Data da Carona")
        with c2:
            tipo_viagem = st.radio("Viagem", ["Ida", "Volta"], horizontal=True)

        # BOTÃO INTELIGENTE: Copiar da Ida para a Volta
        if tipo_viagem == "Volta" and st.session_state["dados_ida"]:
            if st.button("🔄 Repetir Carros da Ida"):
                st.info("Configuração da Ida copiada! Ajuste se necessário.")
        
        st.divider()
        
        # IDEIA 1: Quantidade dinâmica de carros
        num_carros = st.number_input("Quantos carros foram?", 1, 6, value=2)
        
        lista_de_carros = []
        todas_as_pessoas = []

        for i in range(1, num_carros + 1):
            with st.expander(f"🚙 Carro {i}", expanded=True):
                # IDEIA 2: Layout em Grid (Lado a lado)
                col_mot, col_pass = st.columns([1, 2])
                
                with col_mot:
                    motorista = st.selectbox(f"Motorista", [""] + MENINAS_DO_TIME, key=f"mot_{i}")
                with col_pass:
                    passageiras = st.multiselect(f"Passageiras", [n for n in MENINAS_DO_TIME if n != motorista], key=f"pass_{i}")
                
                if motorista:
                    lista_de_carros.append({"motorista": motorista, "passageiras": passageiras})
                    todas_as_pessoas.extend([motorista] + passageiras)

    with col_conf:
        st.header("Conferência")
        reps = [p for p in set(todas_as_pessoas) if todas_as_pessoas.count(p) > 1]
        
        if reps:
            st.error(f"⚠️ Nomes duplicados: {', '.join(reps)}")
        elif lista_de_carros:
            num_mots = len(lista_de_carros)
            bolo_total = 0.0
            
            for carro in lista_de_carros:
                n_pas = len(carro['passageiras'])
                custo_p = 3.50 / (n_pas + 1) if n_pas > 0 else 0
                bolo_total += (custo_p * n_pas)
                carro['custo'] = custo_p

            ganho_m = bolo_total / num_mots
            st.metric("Bolo Total", f"R$ {bolo_total:.2f}")
            st.write(f"Cada motorista recebe: **R$ {ganho_m:.2f}**")

            if st.button("💾 Salvar Lançamento", type="primary"):
                # Salva na memória para o botão "Repetir"
                if tipo_viagem == "Ida":
                    st.session_state["dados_ida"] = lista_de_carros
                
                # Salva no Supabase
                for c in lista_de_carros:
                    supabase.table("caixa_mensal").insert({
                        "data": str(data_carona), "tipo_viagem": tipo_viagem,
                        "nome": c['motorista'], "papel": "Motorista",
                        "valor_a_pagar": 0, "valor_a_receber": ganho_m
                    }).execute()
                    
                    for p in c['passageiras']:
                        supabase.table("caixa_mensal").insert({
                            "data": str(data_carona), "tipo_viagem": tipo_viagem,
                            "nome": p, "papel": "Passageira",
                            "valor_a_pagar": c['custo'], "valor_a_receber": 0
                        }).execute()
                
                st.success("✅ Salvo com sucesso!")
                st.balloons()

# ==========================================
# ABA 2: RESUMO MENSAL
# ==========================================
with aba_resumo:
    st.header("📊 Balanço do Time")
    res = supabase.table("caixa_mensal").select("*").execute()
    df = pd.DataFrame(res.data)
    
    if not df.empty:
        # Força a ordem da sua planilha
        df["nome"] = pd.Categorical(df["nome"], categories=MENINAS_DO_TIME, ordered=True)
        resumo = df.groupby("nome", observed=False).agg({
            "valor_a_pagar": "sum", "valor_a_receber": "sum"
        }).reset_index()
        resumo["Saldo Final"] = resumo["valor_a_receber"] - resumo["valor_a_pagar"]
        
        st.dataframe(resumo, use_container_width=True, hide_index=True,
                    column_config={
                        "valor_a_pagar": st.column_config.NumberColumn("A Pagar", format="R$ %.2f"),
                        "valor_a_receber": st.column_config.NumberColumn("A Receber", format="R$ %.2f"),
                        "Saldo Final": st.column_config.NumberColumn("Saldo", format="R$ %.2f")
                    })
    else:
        st.info("Sem dados.")

# ==========================================
# ABA 3: DETALHES
# ==========================================
with aba_detalhes:
    st.header("🔍 Histórico de Lançamentos")
    res_det = supabase.table("caixa_mensal").select("*").execute()
    df_det = pd.DataFrame(res_det.data)
    
    if not df_det.empty:
        df_det = df_det.sort_values(by=["data", "id"], ascending=False)
        st.dataframe(df_det.drop(columns=["id"]), use_container_width=True, hide_index=True)
        
        if st.button("🗑️ Zerar Banco de Dados"):
            supabase.table("caixa_mensal").delete().neq("id", 0).execute()
            st.rerun()
    else:
        st.info("Nada para mostrar.")