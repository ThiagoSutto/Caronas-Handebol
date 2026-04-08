import streamlit as st
import pandas as pd
from supabase import create_client

# ==========================================
# 1. CONEXÃO SEGURA COM O SUPABASE
# ==========================================
# O Streamlit busca estas chaves lá na aba "Secrets" que você preencheu
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)

# O Python agora pega a lista direto dos Secrets e já organiza por ordem alfabética
MENINAS_DO_TIME = list(st.secrets["MENINAS_DO_TIME"])

# ==========================================
# 2. INTERFACE E SEGURANÇA
# ==========================================
st.set_page_config(page_title="Caronas Handebol", layout="wide")
st.title("🚗 Sistema de Caronas Handebol")

st.sidebar.header("🔐 Acesso Restrito")
senha_digitada = st.sidebar.text_input("Digite a senha do time", type="password")

# Verifica a senha usando o cofre (Secrets)
if senha_digitada == st.secrets["SENHA_TIME"]:
    st.sidebar.success("Acesso liberado!")
    st.write("olá mocita, amo vc ❤️")
    st.divider()
    
    aba_lancamento, aba_resumo, aba_detalhes = st.tabs(["📝 Lançamentos do Dia", "📊 Resumo Mensal","🔍 Detalhes"])
else:
    if senha_digitada != "":
        st.error("Senha incorreta!")
    st.warning("Aguardando senha na barra lateral para liberar o sistema...")
    st.stop()

# ==========================================
# ABA 1: LANÇAMENTOS
# ==========================================
with aba_lancamento:
    col1, col2 = st.columns(2)

    with col1:
        st.header("Entrada de Dados")
        data_carona = st.date_input("Data da Carona")
        tipo_viagem = st.radio("Tipo de Viagem", ["Ida", "Volta"], horizontal=True)
        
        lista_de_carros = []
        todas_as_pessoas = []
        num_carros = st.number_input("Quantos carros foram nessa viagem?", 1, 6, value=2)

        for i in range(1, num_carros + 1):
            with st.expander(f"🚙 Carro {i}", expanded=True):
                motorista = st.selectbox("Motorista", options=[""] + MENINAS_DO_TIME, key=f"mot_{i}")
                opcoes_passageiras = [nome for nome in MENINAS_DO_TIME if nome != motorista]
                passageiras = st.multiselect("Passageiras", options=opcoes_passageiras, max_selections=5, key=f"pass_{i}")
                
                if motorista != "":
                    lista_de_carros.append({"motorista": motorista, "passageiras": passageiras})
                    todas_as_pessoas.extend([motorista] + passageiras)

    with col2:
        st.header("Conferência")
        pessoas_repetidas = [p for p in set(todas_as_pessoas) if todas_as_pessoas.count(p) > 1]

        if len(pessoas_repetidas) > 0:
            st.error(f"⚠️ ERRO: Nomes duplicados: **{', '.join(pessoas_repetidas)}**")
        
        elif len(lista_de_carros) > 0:
            num_motoristas = len(lista_de_carros)
            bolo_total = 0.0
            
            # MATEMÁTICA DA PLANILHA
            for carro in lista_de_carros:
                num_passageiras = len(carro['passageiras'])
                if num_passageiras > 0:
                    pessoas_no_carro = num_passageiras + 1
                    custo_da_divisao = 3.50 / pessoas_no_carro
                    arrecadado_neste_carro = custo_da_divisao * num_passageiras
                    bolo_total += arrecadado_neste_carro
                    carro['custo_individual'] = custo_da_divisao
                else:
                    carro['custo_individual'] = 0.0

            ganho_por_motorista = bolo_total / num_motoristas

            st.info(f"Resumo da **{tipo_viagem}**")
            st.metric("Bolo Total da Viagem", f"R$ {bolo_total:.2f}")
            st.write(f"Ganho por motorista: **R$ {ganho_por_motorista:.2f}**")

            if st.button("💾 Salvar no Banco de Dados (Nuvem)", type="primary"):
                data_texto = str(data_carona)

                for carro in lista_de_carros:
                    # Salva Motorista no Supabase
                    supabase.table("caixa_mensal").insert({
                        "data": data_texto, "tipo_viagem": tipo_viagem,
                        "nome": carro['motorista'], "papel": "Motorista",
                        "valor_a_pagar": 0.0, "valor_a_receber": ganho_por_motorista
                    }).execute()

                    # Salva Passageiras no Supabase
                    for p in carro['passageiras']:
                        supabase.table("caixa_mensal").insert({
                            "data": data_texto, "tipo_viagem": tipo_viagem,
                            "nome": p, "papel": "Passageira",
                            "valor_a_pagar": carro['custo_individual'], "valor_a_receber": 0.0
                        }).execute()
                
                st.success("✅ Dados salvos com sucesso no Supabase!")
                st.balloons()

# ==========================================
# ABA 2: RESUMO MENSAL (Lendo da Nuvem)
# ==========================================
with aba_resumo:
    st.header("Fechamento do Caixa")
    
    # Busca todos os dados do Supabase
    response = supabase.table("caixa_mensal").select("*").execute()
    df = pd.DataFrame(response.data)
    
    if not df.empty:
        df["nome"] = pd.Categorical(df["nome"], categories=MENINAS_DO_TIME, ordered=True)
        # Agrupa os valores por nome
        resumo = df.groupby("nome").agg({
            "valor_a_pagar": "sum",
            "valor_a_receber": "sum"
        }).reset_index()
        
        resumo["Saldo Final"] = resumo["valor_a_receber"] - resumo["valor_a_pagar"]
        
        st.dataframe(
            resumo, 
            use_container_width=True, 
            hide_index=True,
            column_config={
                "valor_a_pagar": st.column_config.NumberColumn("Total a Pagar", format="R$ %.2f"),
                "valor_a_receber": st.column_config.NumberColumn("Total a Receber", format="R$ %.2f"),
                "Saldo Final": st.column_config.NumberColumn(format="R$ %.2f")
            }
        )
    else:
        st.info("Nenhuma carona registrada no banco de dados em nuvem.")

    st.divider()
    if st.button("🗑️ Zerar Banco de Dados"):
        # Deleta todas as linhas onde o ID não é zero (ou seja, tudo)
        supabase.table("caixa_mensal").delete().neq("id", 0).execute()
        st.success("Banco de dados zerado!")
        st.rerun()

        # ==========================================
# ABA 3: DETALHES (HISTÓRICO COMPLETO)
# ==========================================
with aba_detalhes:
    st.header("🔍 Detalhamento dos Lançamentos")
    st.write("Confira aqui cada linha salva no banco de dados para auditoria.")

    # Busca os dados novamente para garantir que está atualizado
    response_detalhes = supabase.table("caixa_mensal").select("*").execute()
    df_detalhes = pd.DataFrame(response_detalhes.data)

    if not df_detalhes.empty:
        # 1. Organizar para que os lançamentos mais recentes apareçam no topo
        # (Usamos o ID ou a Data para isso)
        df_detalhes = df_detalhes.sort_values(by=["data", "id"], ascending=[False, False])

        # 2. Deixar os nomes na ordem da sua planilha também aqui (opcional)
        df_detalhes["nome"] = pd.Categorical(df_detalhes["nome"], categories=MENINAS_DO_TIME, ordered=True)

        # 3. Exibir a tabela formatada
        st.dataframe(
            df_detalhes,
            use_container_width=True,
            hide_index=True,
            column_config={
                "id": None, # Esconde o ID que é só controle do banco
                "data": st.column_config.TextColumn("Data"),
                "tipo_viagem": "Viagem",
                "nome": "Nome",
                "papel": "Papel",
                "valor_a_pagar": st.column_config.NumberColumn("A Pagar", format="R$ %.2f"),
                "valor_a_receber": st.column_config.NumberColumn("A Receber", format="R$ %.2f"),
            }
        )
        
        # Botão extra para baixar os dados caso você queira abrir no Excel depois
        csv = df_detalhes.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Baixar tudo em CSV (Excel)",
            data=csv,
            file_name='detalhes_caronas_handebol.csv',
            mime='text/csv',
        )
    else:
        st.info("Nenhum dado encontrado para detalhamento.")