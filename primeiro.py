import streamlit as st
import pandas as pd
from supabase import create_client
import urllib.parse

st.set_page_config(page_title="Caronas Handebol", layout="wide")

# ==========================================
# 1. CONEXÃO COM O SUPABASE E ELENCO
# ==========================================
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)

# Volta a puxar as meninas do arquivo rápido e seguro!
MENINAS_DO_TIME = sorted(list(st.secrets["MENINAS_DO_TIME"]))

# Busca quem é isenta no secrets (se a lista não existir lá, ninguém é isenta)
try:
    isentas_list = list(st.secrets["ISENTAS"])
except:
    isentas_list = []

# ==========================================
# 2. INICIALIZAÇÃO DA SESSÃO
# ==========================================
if "autenticado" not in st.session_state:
    st.session_state.autenticado = False

# ==========================================
# 3. TELA DE LOGIN
# ==========================================
if not st.session_state.autenticado:
    col_esq, col_centro, col_dir = st.columns([1, 1.5, 1])
    with col_centro:
        st.write("") 
        with st.container(border=True):
            col_vazia_esq, col_img, col_vazia_dir = st.columns([1, 1.5, 1])
            with col_img:
                try: st.image("1.jpg", use_container_width=True)
                except Exception as e: st.warning("⚠️ Imagem não carregou.")
            
            st.markdown("<h2 style='text-align: center;'>Acesso Restrito</h2>", unsafe_allow_html=True)
            st.divider()
            senha_digitada = st.text_input("🔑 Senha do Time", type="password")
            
            if st.button("Entrar no Sistema 🚀", type="primary", use_container_width=True):
                if senha_digitada == st.secrets["SENHA_TIME"]:
                    st.session_state.autenticado = True
                    st.rerun()
                else: 
                    st.error("❌ Senha incorreta!")
    st.stop()

# ==========================================
# 4. O SISTEMA (LOGADO)
# ==========================================
st.sidebar.title("Configurações")
mes_ref = st.sidebar.selectbox("Mês de Referência", ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"])
ano_ref = st.sidebar.number_input("Ano", value=2026)

if st.sidebar.button("Log out / Sair"):
    st.session_state.autenticado = False
    st.rerun()

st.title("🤾‍♀️ Gestão Handebol Feminino")
st.write(f"Trabalhando no mês de **{mes_ref}/{ano_ref}**")

aba_carona, aba_lancamentos, aba_faturas, aba_resumo = st.tabs([
    "🚗 Registro de Caronas", "💸 Lançamentos", "🧾 Gerar Faturas", "📊 Balanço Geral"
])

# ---------------------------------------------------------
# ABA 1: CARONAS
# ---------------------------------------------------------
with aba_carona:
    col_input, col_conf = st.columns([1.2, 1])
    with col_input:
        st.header("Lançar Carona")
        data_carona = st.date_input("Data do Treino")
        tipo_v = st.radio("Viagem", ["Ida", "Volta"], horizontal=True)
        num_carros = st.number_input("Quantos carros?", 1, 6, value=2)
        
        lista_de_carros = []
        for i in range(1, num_carros + 1):
            with st.expander(f"🚙 Carro {i}", expanded=True):
                m = st.selectbox(f"Motorista", [""] + MENINAS_DO_TIME, key=f"m_{i}")
                p = st.multiselect(f"Passageiras", [n for n in MENINAS_DO_TIME if n != m], key=f"p_{i}")
                if m:
                    lista_de_carros.append({"motorista": m, "passageiras": p})

    with col_conf:
        st.header("Conferência")
        if lista_de_carros:
            num_mots = len(lista_de_carros)
            bolo = 0.0
            for c in lista_de_carros:
                n = len(c['passageiras'])
                custo = 3.50 / (n + 1) if n > 0 else 0
                bolo += (custo * n)
                c['custo'] = custo
            ganho = bolo / num_mots
            st.metric("Bolo Total", f"R$ {bolo:.2f}")
            if st.button("💾 Salvar Carona", type="primary"):
                for c in lista_de_carros:
                    supabase.table("caixa_mensal").insert({"data": str(data_carona), "tipo_viagem": tipo_v, "nome": c['motorista'], "papel": "Motorista", "valor_a_pagar": 0, "valor_a_receber": ganho, "mes": mes_ref, "ano": ano_ref}).execute()
                    for p in c['passageiras']:
                        supabase.table("caixa_mensal").insert({"data": str(data_carona), "tipo_viagem": tipo_v, "nome": p, "papel": "Passageira", "valor_a_pagar": c['custo'], "valor_a_receber": 0, "mes": mes_ref, "ano": ano_ref}).execute()
                st.success("Salvo!")
        
        st.divider()
        st.subheader("🗑️ Apagar Viagens (Dia/Trajeto Completo)")
        st.write("Ao clicar em excluir, você apagará todos os carros e passageiras daquele trajeto específico.")
        
        res_caronas = supabase.table("caixa_mensal").select("*").eq("mes", mes_ref).eq("ano", ano_ref).execute()
        if res_caronas.data:
            df_hist_carona = pd.DataFrame(res_caronas.data)
            viagens_agrupadas = df_hist_carona.groupby(['data', 'tipo_viagem']).size().reset_index(name='qtd_pessoas')
            viagens_agrupadas = viagens_agrupadas.sort_values(by="data", ascending=False)
            
            for _, viagem in viagens_agrupadas.iterrows():
                data_v = viagem['data']
                tipo_v = viagem['tipo_viagem']
                qtd = viagem['qtd_pessoas']
                col_txt, col_btn = st.columns([4, 1])
                col_txt.write(f"🚗 **Data:** {data_v} | **Trajeto:** {tipo_v} *(Envolve {qtd} pessoas)*")
                
                if col_btn.button("Excluir Viagem", key=f"del_v_{data_v}_{tipo_v}", type="secondary"):
                    supabase.table("caixa_mensal").delete().eq("data", data_v).eq("tipo_viagem", tipo_v).eq("mes", mes_ref).eq("ano", ano_ref).execute()
                    st.rerun()
        else:
            st.info("Nenhuma carona registrada para este mês.")               

# ---------------------------------------------------------
# ABA 2: LANÇAMENTOS (AGORA COM 8 ABAS)
# ---------------------------------------------------------
with aba_lancamentos:
    st.header("💸 Lançamentos do Mês")
    t_ndu, t_academia, t_alfajor, t_bolo, t_gastos, t_outros, t_dividas, t_historico = st.tabs([
        "🏆 NDU", "🏋️ Academia", "🍫 Alfajor", "🎂 Bolo", "👥 Gastos Mensais", "⚙️ Outros", "⏳ Dívidas", "🗑️ Apagar Erros"
    ])

    with t_ndu:
        with st.form("form_ndu", clear_on_submit=True):
            c1, c2, c3 = st.columns(3)
            atleta = c1.selectbox("Atleta", MENINAS_DO_TIME, index=None, key="n1")
            desc = c2.text_input("Competição (Ex: Jogo contra USP)")
            valor = c3.number_input("Valor", min_value=0.0, step=0.50, key="v1")
            if st.form_submit_button("Lançar NDU") and atleta and valor > 0:
                supabase.table("lancamentos_extras").insert({"nome": atleta, "tipo": "NDU", "valor": valor, "mes": mes_ref, "ano": ano_ref, "obs": desc}).execute()
                st.rerun()

    with t_academia:
        st.subheader("🏋️ Lançamento de Faltas")
        preco_falta = st.number_input("💰 Valor da multa por falta (R$)", min_value=0.0, value=2.0, step=0.50)
        st.divider()
        with st.form("form_aca", clear_on_submit=True):
            c1, c2 = st.columns(2)
            atleta = c1.selectbox("Atleta", MENINAS_DO_TIME, index=None, key="a1")
            faltas = c2.number_input("Quantas faltas?", min_value=0, step=1)
            if st.form_submit_button("Lançar Academia") and atleta and faltas > 0:
                valor_calc = faltas * preco_falta
                supabase.table("lancamentos_extras").insert({"nome": atleta, "tipo": "Academia", "valor": valor_calc, "mes": mes_ref, "ano": ano_ref, "obs": f"{faltas} faltas (R$ {preco_falta:.2f} cada)"}).execute()
                st.success(f"R$ {valor_calc:.2f} lançado para {atleta}!")
                st.rerun()

    with t_alfajor:
        with st.form("form_alf", clear_on_submit=True):
            c1, c2 = st.columns(2)
            atleta = c1.selectbox("Atleta", MENINAS_DO_TIME, index=None, key="al1")
            valor = c2.number_input("Valor Total (R$)", min_value=0.0, key="va1", step=0.50)
            if st.form_submit_button("Lançar Alfajor") and atleta and valor > 0:
                supabase.table("lancamentos_extras").insert({"nome": atleta, "tipo": "Alfajor", "valor": valor, "mes": mes_ref, "ano": ano_ref}).execute()
                st.rerun()

    with t_bolo:
        st.subheader("🎂 Divisão de Bolo")
        with st.form("form_bolo", clear_on_submit=True):
            c1, c2 = st.columns(2)
            niver = c1.selectbox("Quem é a Aniversariante?", MENINAS_DO_TIME, index=None)
            v_bolo = c2.number_input("Valor Total do Bolo", min_value=0.0, step=0.50)
            if st.form_submit_button("Distribuir Bolo") and niver and v_bolo > 0:
                v_c = v_bolo / (len(MENINAS_DO_TIME) - 1)
                for m in MENINAS_DO_TIME:
                    supabase.table("lancamentos_extras").insert({"nome": m, "tipo": "Bolo", "valor": 0 if m==niver else v_c, "mes": mes_ref, "ano": ano_ref, "obs": f"Niver: {niver}"}).execute()
                st.rerun()

    with t_gastos:
        st.subheader("👥 Gastos Mensais da Equipe")
        with st.form("form_gastos", clear_on_submit=True):
            c1, c2 = st.columns([2, 1])
            desc_g = c1.text_input("Com o que foi gasto? (Ex: Aluguel de Quadra, Água)")
            v_gastos = c2.number_input("Valor Total do Gasto", min_value=0.0, step=0.50)
            if st.form_submit_button("Dividir Gastos") and v_gastos > 0 and desc_g:
                v_c = v_gastos / len(MENINAS_DO_TIME)
                for m in MENINAS_DO_TIME:
                    supabase.table("lancamentos_extras").insert({"nome": m, "tipo": "Gastos mensais", "valor": v_c, "mes": mes_ref, "ano": ano_ref, "obs": desc_g}).execute()
                st.rerun()

    # --- NOVA ABA SEPARADA: APENAS OUTROS ---
    with t_outros:
        st.subheader("⚙️ Outros Gastos Manuais")
        st.write("Ex: Compra de uniforme, garrafinha, etc.")
        with st.form("form_outros", clear_on_submit=True):
            c1, c2, c3 = st.columns(3)
            atleta = c1.selectbox("Atleta", MENINAS_DO_TIME, index=None, key="o1")
            tipo_outro = c2.text_input("Gasto (Ex: Uniforme)")
            valor = c3.number_input("Valor (R$)", min_value=0.0, key="vo1",step=0.50)
            if st.form_submit_button("Lançar Gasto") and atleta and valor > 0 and tipo_outro:
                supabase.table("lancamentos_extras").insert({"nome": atleta, "tipo": tipo_outro, "valor": valor, "mes": mes_ref, "ano": ano_ref}).execute()
                st.rerun()

    # --- NOVA ABA SEPARADA: APENAS DÍVIDAS E AJUSTES ---
    with t_dividas:
        st.subheader("🔄 Sincronizar Dívidas do Mês Passado")
        if st.button("Puxar Dívidas Acumuladas ⚠️", type="primary"):
            meses = ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"]
            idx_atual = meses.index(mes_ref)
            mes_passado = meses[idx_atual - 1] if idx_atual > 0 else "Dezembro"
            ano_passado = ano_ref if idx_atual > 0 else ano_ref - 1
            
            with st.spinner(f"Calculando quem ficou devendo em {mes_passado}..."):
                df_ext_p = pd.DataFrame(supabase.table("lancamentos_extras").select("*").eq("mes", mes_passado).eq("ano", ano_passado).execute().data)
                df_car_p = pd.DataFrame(supabase.table("caixa_mensal").select("*").eq("mes", mes_passado).eq("ano", ano_passado).execute().data)
                df_pagos_p = pd.DataFrame(supabase.table("mensalidades_hand").select("*").eq("mes", mes_passado).eq("ano", ano_passado).execute().data)

                for m in MENINAS_DO_TIME:
                    fixo = 0.0 if m in isentas_list else 80.0
                    
                    ext = df_ext_p[df_ext_p['nome'] == m]['valor'].sum() if not df_ext_p.empty else 0
                    car_d = df_car_p[df_car_p['nome'] == m]['valor_a_pagar'].sum() if not df_car_p.empty else 0
                    car_r = df_car_p[df_car_p['nome'] == m]['valor_a_receber'].sum() if not df_car_p.empty else 0
                    devia = fixo + ext + (car_d - car_r)
                    
                    pagou = df_pagos_p[df_pagos_p['nome'] == m]['valor'].sum() if not df_pagos_p.empty else 0
                    pendencia = devia - pagou
                    
                    if pendencia > 0.01:
                        ja_lancou = supabase.table("lancamentos_extras").select("*").eq("nome", m).eq("tipo", "Dívida Acumulativa").eq("mes", mes_ref).eq("ano", ano_ref).execute().data
                        if not ja_lancou:
                            supabase.table("lancamentos_extras").insert({"nome": m, "tipo": "Dívida Acumulativa", "valor": pendencia, "mes": mes_ref, "ano": ano_ref, "obs": f"Saldo de {mes_passado}"}).execute()
            st.success("Pronto! Dívidas roladas para este mês.")
            st.rerun()

        st.divider()
        st.subheader("✏️ Ajustar Dívidas do Mês")
        st.write("Se o sistema puxou algum valor errado, você pode corrigir manualmente abaixo:")
        
        # Busca todas as dívidas geradas neste mês para permitir edição
        dividas_atuais = supabase.table("lancamentos_extras").select("*").eq("tipo", "Dívida Acumulativa").eq("mes", mes_ref).eq("ano", ano_ref).execute().data
        
        if dividas_atuais:
            for div in dividas_atuais:
                c_nome, c_val, c_btn = st.columns([2, 1.5, 1])
                c_nome.write(f"**{div['nome'].capitalize()}**")
                
                # Caixinha que já vem preenchida com o valor atual da dívida
                novo_valor = c_val.number_input("Valor Correto (R$)", value=float(div['valor']), min_value=0.0, step=0.50, key=f"edit_div_{div['id']}")
                
                if c_btn.button("Atualizar", key=f"btn_edit_{div['id']}"):
                    supabase.table("lancamentos_extras").update({"valor": novo_valor}).eq("id", div['id']).execute()
                    st.success("Valor corrigido!")
                    st.rerun()
        else:
            st.info("Nenhuma Dívida Acumulativa registrada neste mês ainda.")
            
    with t_historico:
        st.info("Todos os lançamentos do mês atual ficam aqui. Clique em 'Excluir' se digitou algo errado.")
        res_rec = supabase.table("lancamentos_extras").select("*").eq("mes", mes_ref).eq("ano", ano_ref).execute()
        if res_rec.data:
            for _, item in pd.DataFrame(res_rec.data).iterrows():
                c_i, c_b = st.columns([4,1])
                obs_txt = f" - ({item['obs']})" if item.get('obs') else ""
                c_i.write(f"**{item['nome']}**: {item['tipo']} - R$ {item['valor']:.2f}{obs_txt}")
                if c_b.button("Excluir", key=f"del_{item['id']}"):
                    supabase.table("lancamentos_extras").delete().eq("id", item['id']).execute()
                    st.rerun()

# ---------------------------------------------------------
# ABA 3: FATURAS
# ---------------------------------------------------------
with aba_faturas:
    st.header("🧾 Fechamento e Faturas")
    c_p1, c_p2 = st.columns(2)
    prazo_pagamento = c_p1.text_input("📅 Prazo de Pagamento", "Dia 08")
    chave_pix = c_p2.text_input("🔑 Chave PIX", "maju.maziero02@gmail.com")
    st.divider()

    df_ext = pd.DataFrame(supabase.table("lancamentos_extras").select("*").eq("mes", mes_ref).eq("ano", ano_ref).execute().data)
    df_car = pd.DataFrame(supabase.table("caixa_mensal").select("*").eq("mes", mes_ref).eq("ano", ano_ref).execute().data)
    df_pagos = pd.DataFrame(supabase.table("mensalidades_hand").select("*").eq("mes", mes_ref).eq("ano", ano_ref).execute().data)

    for menina in MENINAS_DO_TIME:
        with st.expander(f"📋 Fatura: {menina.capitalize()}"):
            gastos_menina = df_ext[df_ext['nome'] == menina] if not df_ext.empty else pd.DataFrame()
            
            # Cálculo com isenção
            fixo = 0.0 if menina in isentas_list else 80.0
            
            total_extras = gastos_menina['valor'].sum() if not gastos_menina.empty else 0
            car_d = df_car[df_car['nome'] == menina]['valor_a_pagar'].sum() if not df_car.empty else 0
            car_r = df_car[df_car['nome'] == menina]['valor_a_receber'].sum() if not df_car.empty else 0
            v_car = car_d - car_r

            total_mes = fixo + total_extras + v_car
            ja_pagou = df_pagos[df_pagos['nome'] == menina]['valor'].sum() if not df_pagos.empty else 0
            falta_pagar = total_mes - ja_pagou

            # Mensagem do WhatsApp
            msg = f"Bom diaa,\nPassando para te mandar a sua 💰Mensalidade💰 de {mes_ref.lower()}\n\nPrazo: {prazo_pagamento}\n\n"
            if fixo > 0: msg += f"Mensalidade- R$ {fixo:.2f}\n"
            if v_car != 0: msg += f"Caronas - R$ {v_car:.2f}\n"
            
            if not gastos_menina.empty:
                gastos_agrupados = gastos_menina.groupby('tipo')['valor'].sum()
                for tipo, val in gastos_agrupados.items():
                    if val > 0: msg += f"{tipo} - R$ {val:.2f}\n"
            
            msg += f"\nTotal do Mês: R$ {total_mes:.2f}\n"
            if ja_pagou > 0 and falta_pagar > 0:
                msg += f"Já recebido: R$ {ja_pagou:.2f}\n"
                msg += f"*FALTA PAGAR: R$ {falta_pagar:.2f}*\n"
            
            msg += f"\nPix: {chave_pix}\nQualquer dúvida me avisa!!"

            # Visual no Site
            st.markdown("#### 🔍 Detalhamento:")
            if fixo == 0.0:
                st.caption("*(Atleta Isenta da Mensalidade Fixa)*")
            if not gastos_menina.empty:
                for _, linha in gastos_menina.iterrows():
                    obs = f" - {linha.get('obs', '')}" if linha.get('obs') else ""
                    st.write(f"• {linha['tipo']}: R$ {linha['valor']:.2f}{obs}")
            if car_d > 0 or car_r > 0:
                st.write(f"• Caronas: Usou R$ {car_d:.2f} | Recebeu R$ {car_r:.2f}")
            
            st.divider()
            st.write(f"### Total da Fatura: R$ {total_mes:.2f}")

            # Lógica Anti-Bug de Número Negativo e Crédito
            if total_mes < -0.01:
                st.success(f"🎉 CRÉDITO! Ela tem R$ {abs(total_mes):.2f} de crédito neste mês (Carro/Acerto).")
            elif falta_pagar <= 0.01 and total_mes > 0:
                st.success("✅ FATURA QUITADA! Tudo certo este mês.")
                if st.button("Estornar Pagamentos (Erro)", key=f"estorno_{menina}"):
                    supabase.table("mensalidades_hand").delete().eq("nome", menina).eq("mes", mes_ref).eq("ano", ano_ref).execute()
                    st.rerun()
            elif total_mes >= -0.01 and total_mes <= 0.01:
                st.info("Nenhum custo neste mês (Fatura Zerada).")
            else:
                if ja_pagou > 0:
                    st.warning(f"⚠️ Atenção: Ela já pagou R$ {ja_pagou:.2f}. Ainda falta R$ {falta_pagar:.2f}.")
                
                c_val, c_btn = st.columns([1.5, 1])
                # Garante que o input nunca tente iniciar com número menor que 0
                valor_seguro = max(0.0, float(falta_pagar))
                v_recebido = c_val.number_input("Pix Recebido (R$)", min_value=0.0, value=valor_seguro, key=f"rec_{menina}")
                
                if c_btn.button("Dar Baixa 💸", key=f"btn_{menina}", type="primary"):
                    if v_recebido > 0:
                        supabase.table("mensalidades_hand").insert({"nome": menina, "mes": mes_ref, "ano": ano_ref, "valor": v_recebido}).execute()
                        st.success("Pagamento registrado!")
                        st.rerun()

                st.link_button(f"Enviar Cobrança 🟢", f"https://api.whatsapp.com/send?text={urllib.parse.quote(msg)}")

# ---------------------------------------------------------
# ABA 4: BALANÇO GERAL
# ---------------------------------------------------------
with aba_resumo:
    st.header(f"📊 Resumo Financeiro - {mes_ref}/{ano_ref}")
    st.write("Acompanhe o saldo consolidado de cada atleta neste mês.")

    res_car = supabase.table("caixa_mensal").select("*").eq("mes", mes_ref).eq("ano", ano_ref).execute()
    df_car = pd.DataFrame(res_car.data)
    
    res_ext = supabase.table("lancamentos_extras").select("*").eq("mes", mes_ref).eq("ano", ano_ref).execute()
    df_ext = pd.DataFrame(res_ext.data)

    res_pagos = supabase.table("mensalidades_hand").select("*").eq("mes", mes_ref).eq("ano", ano_ref).execute()
    df_pagos = pd.DataFrame(res_pagos.data)

    balanco = []
    total_esperado = 0
    total_caixa = 0

    for m in MENINAS_DO_TIME:
        p_c = df_car[df_car['nome'] == m]['valor_a_pagar'].sum() if not df_car.empty else 0
        r_c = df_car[df_car['nome'] == m]['valor_a_receber'].sum() if not df_car.empty else 0
        saldo_carona = r_c - p_c
        
        ext = df_ext[df_ext['nome'] == m]['valor'].sum() if not df_ext.empty else 0
        
        fixo = 0.0 if m in isentas_list else 80.0
        pago = df_pagos[df_pagos['nome'] == m]['valor'].sum() if not df_pagos.empty else 0
        
        devido = fixo + ext - saldo_carona
        pendente = devido - pago
        
        total_esperado += devido
        total_caixa += pago

        balanco.append({
            "Atleta": m.capitalize(), 
            "Saldo Caronas": f"R$ {saldo_carona:.2f}",
            "Lançamentos Extras": f"R$ {ext:.2f}",
            "Fixo/Mensalidade": f"R$ {fixo:.2f}",
            "Total Devido": f"R$ {devido:.2f}",
            "Já Pagou": f"R$ {pago:.2f}",
            "Falta Pagar": f"R$ {pendente:.2f}"
        })
    
    c1, c2, c3 = st.columns(3)
    c1.metric("Expectativa de Arrecadação", f"R$ {total_esperado:.2f}")
    c2.metric("Dinheiro em Caixa (PIX Recebido)", f"R$ {total_caixa:.2f}")
    c3.metric("Falta Receber (Na Rua)", f"R$ {total_esperado - total_caixa:.2f}")

    st.divider()
    st.dataframe(pd.DataFrame(balanco), use_container_width=True, hide_index=True)