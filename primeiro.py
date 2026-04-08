import streamlit as st
import sqlite3
import pandas as pd

# ==========================================
# 1. CONFIGURAÇÃO DO BANCO DE DADOS
# ==========================================
def conectar_banco():
    conexao = sqlite3.connect('caronas.db')
    cursor = conexao.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS caixa_mensal (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            data TEXT,
            tipo_viagem TEXT,
            nome TEXT,
            papel TEXT,
            valor_a_pagar REAL,
            valor_a_receber REAL
        )
    ''')
    conexao.commit()
    return conexao

MENINAS_DO_TIME = [
    "arritmia", "buh", "carreta", "clt", "curupira", "jenga", 
    "lela", "maju", "maritaca", "md", "mestica", "nicolle", 
    "parca", "prikita", "proerd", "sauva", "sofia", "solda"
]
MENINAS_DO_TIME.sort()

# ==========================================
# INTERFACE DO SITE
# ==========================================
st.set_page_config(page_title="Caronas Handebol", layout="wide")
st.title("🚗 Sistema de Caronas Handebol")
st.write("olá mocita, amo vc ❤️")
st.divider()

aba_lancamento, aba_resumo = st.tabs(["📝 Lançamentos do Dia", "📊 Resumo Mensal"])

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

        for i in range(1, 6):
            with st.expander(f"🚙 Carro {i} - {tipo_viagem}"):
                motorista = st.selectbox("Motorista", options=[""] + MENINAS_DO_TIME, key=f"mot_{i}")
                opcoes_passageiras = [nome for nome in MENINAS_DO_TIME if nome != motorista]
                passageiras = st.multiselect("Passageiras", options=opcoes_passageiras, max_selections=5, key=f"pass_{i}")
                
                if motorista != "":
                    lista_de_carros.append({"motorista": motorista, "passageiras": passageiras})
                    todas_as_pessoas.append(motorista)
                    todas_as_pessoas.extend(passageiras)

    with col2:
        st.header("Conferência")
        pessoas_repetidas = [p for p in set(todas_as_pessoas) if todas_as_pessoas.count(p) > 1]

        if len(pessoas_repetidas) > 0:
            st.error(f"⚠️ ERRO: Nomes duplicados: **{', '.join(pessoas_repetidas)}**")
        
        # SÓ CALCULA SE TIVER PELO MENOS 1 CARRO E NENHUM ERRO
        elif len(lista_de_carros) > 0:
            
            num_motoristas = len(lista_de_carros)
            bolo_total = 0.0
            
            # MATEMÁTICA DA PLANILHA (Motorista conta na divisão do carro)
            for carro in lista_de_carros:
                num_passageiras = len(carro['passageiras'])
                
                if num_passageiras > 0:
                    pessoas_no_carro = num_passageiras + 1 # +1 da motorista
                    custo_da_divisao = 3.50 / pessoas_no_carro
                    
                    arrecadado_neste_carro = custo_da_divisao * num_passageiras
                    bolo_total += arrecadado_neste_carro
                    
                    carro['custo_individual'] = custo_da_divisao
                else:
                    carro['custo_individual'] = 0.0

            ganho_por_motorista = bolo_total / num_motoristas

            st.info(f"Resumo da **{tipo_viagem}** do dia {data_carona.strftime('%d/%m')}")
            st.metric("Bolo Total da Viagem", f"R$ {bolo_total:.2f}")
            st.write(f"Cada passageira paga a sua parte da divisão do carro.")
            st.write(f"Cada motorista recebe a divisão da caixinha: **R$ {ganho_por_motorista:.2f}**")

            # SALVAR NO BANCO
            if st.button("💾 Salvar no Banco de Dados", type="primary"):
                conexao = conectar_banco()
                cursor = conexao.cursor()
                data_texto = str(data_carona)

                for carro in lista_de_carros:
                    mot = carro['motorista']
                    passags = carro['passageiras']
                    custo_passageira = carro['custo_individual'] 

                    # Salva a Motorista
                    cursor.execute(
                        "INSERT INTO caixa_mensal (data, tipo_viagem, nome, papel, valor_a_pagar, valor_a_receber) VALUES (?, ?, ?, ?, ?, ?)", 
                        (data_texto, tipo_viagem, mot, "Motorista", 0.0, ganho_por_motorista)
                    )

                    # Salva as Passageiras
                    if len(passags) > 0:
                        for p in passags:
                            cursor.execute(
                                "INSERT INTO caixa_mensal (data, tipo_viagem, nome, papel, valor_a_pagar, valor_a_receber) VALUES (?, ?, ?, ?, ?, ?)", 
                                (data_texto, tipo_viagem, p, "Passageira", custo_passageira, 0.0)
                            )
                
                conexao.commit()
                conexao.close()
                st.success("✅ Viagem salva! Vá para a aba 'Resumo Mensal' para ver o balanço.")
                st.balloons()

# ==========================================
# ABA 2: RESUMO MENSAL E CÁLCULO FINAL
# ==========================================
with aba_resumo:
    st.header("Fechamento do Caixa")
    st.write("Veja quem deve pagar e quem deve receber baseado em todas as caronas salvas.")
    
    conexao = conectar_banco()
    query = '''
        SELECT 
            nome AS Nome, 
            SUM(valor_a_pagar) AS "Total a Pagar", 
            SUM(valor_a_receber) AS "Total a Receber" 
        FROM caixa_mensal 
        GROUP BY nome
    '''
    
    tabela_resumo = pd.read_sql_query(query, conexao)
    conexao.close()
    
    if not tabela_resumo.empty:
        tabela_resumo["Saldo Final"] = tabela_resumo["Total a Receber"] - tabela_resumo["Total a Pagar"]
        
        st.dataframe(
            tabela_resumo, 
            use_container_width=True, 
            hide_index=True,          
            column_config={           
                "Total a Pagar": st.column_config.NumberColumn(format="R$ %.2f"),
                "Total a Receber": st.column_config.NumberColumn(format="R$ %.2f"),
                "Saldo Final": st.column_config.NumberColumn(format="R$ %.2f")
            }
        )
    else:
        st.info("Nenhuma carona foi registrada no banco de dados ainda.")

    # ==========================================
    # BOTÃO DE ZERAR O BANCO DE DADOS
    # ==========================================
    st.divider() # Cria uma linha separadora
    st.subheader("⚠️ Zona de Perigo")
    
    # st.button devolve "Verdadeiro" quando é clicado
    if st.button("🗑️ Apagar Todos os Dados", type="secondary"):
        conexao = conectar_banco()
        cursor = conexao.cursor()
        
        # Comando SQL que deleta todas as linhas da tabela
        cursor.execute("DELETE FROM caixa_mensal") 
        
        conexao.commit()
        conexao.close()
        
        st.success("Tudo apagado com sucesso! Atualize a página (F5) para zerar a tabela.")