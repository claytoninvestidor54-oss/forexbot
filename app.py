import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import matplotlib.pyplot as plt
import datetime

st.set_page_config(page_title="RSI Forex Bot", layout="wide")

# -----------------------------
# Cabeçalho
# -----------------------------
st.title("💹 RSI Forex Bot - Backtest Educacional")
st.markdown("Este app demonstra uma estratégia simples de RSI para **Forex** usando dados do Yahoo Finance. "
            "Use apenas para fins educacionais — não utilize em conta real.")

# -----------------------------
# Parâmetros do usuário
# -----------------------------
st.sidebar.header("⚙️ Parâmetros da Estratégia")
symbol = st.sidebar.text_input("Par (ex: EURUSD=X)", "EURUSD=X")
start_date = st.sidebar.date_input("Data inicial", datetime.date(2020, 1, 1))
end_date = st.sidebar.date_input("Data final", datetime.date.today())
rsi_period = st.sidebar.slider("Período RSI", 5, 30, 14)
rsi_buy = st.sidebar.slider("RSI de Compra (<)", 10, 50, 30)
rsi_sell = st.sidebar.slider("RSI de Venda (>)", 50, 90, 70)
initial_capital = st.sidebar.number_input("Capital inicial (USD)", 1000, 100000, 10000)
risk_per_trade = st.sidebar.slider("Risco por trade (%)", 0.1, 5.0, 1.0)
fixed_stop_pips = st.sidebar.number_input("Stop fixo (em pips)", 10, 200, 20) / 10000

if st.sidebar.button("▶️ Rodar Backtest"):
    with st.spinner("Baixando dados e calculando RSI..."):

        def compute_rsi(close, period=14):
            delta = close.diff()
            up = delta.clip(lower=0)
            down = -1 * delta.clip(upper=0)
            roll_up = up.ewm(alpha=1/period, adjust=False).mean()
            roll_down = down.ewm(alpha=1/period, adjust=False).mean()
            rs = roll_up / roll_down
            rsi = 100 - (100 / (1 + rs))
            return rsi

        df = yf.download(symbol, start=start_date, end=end_date, interval="60m", progress=False)
        df = df[['Open', 'High', 'Low', 'Close', 'Volume']].dropna()
        df['RSI'] = compute_rsi(df['Close'], period=rsi_period)

        # -------------------------
        # Estratégia
        # -------------------------
        capital = initial_capital
        position = None
        positions = []
        equity_curve = []

        for i in range(len(df)):
            price = df['Close'].iloc[i]
            rsi = df['RSI'].iloc[i]
            equity_curve.append(capital)

            if position is None:
                if pd.notna(rsi) and rsi < rsi_buy:
                    stop_price = price - fixed_stop_pips
                    risk_per_unit = price - stop_price
                    if risk_per_unit <= 0:
                        continue
                    max_risk_amount = capital * (risk_per_trade / 100)
                    units = max_risk_amount / risk_per_unit
                    position = {'entry': price, 'units': units, 'stop': stop_price, 'entry_index': i}
                    positions.append({'type': 'buy', 'price': price, 'index': i})
            else:
                if pd.notna(rsi) and rsi > rsi_sell or df['Close'].iloc[i] <= position['stop']:
                    profit = (price - position['entry']) * position['units']
                    capital += profit
                    positions.append({'type': 'sell', 'price': price, 'index': i, 'profit': profit})
                    position = None

        total_return = (capital - initial_capital) / initial_capital
        df['Equity'] = equity_curve

        # -------------------------
        # Resultados
        # -------------------------
        st.success("✅ Backtest concluído com sucesso!")

        col1, col2, col3 = st.columns(3)
        col1.metric("💰 Capital Final", f"${capital:,.2f}")
        col2.metric("📈 Retorno Total", f"{total_return*100:.2f}%")
        col3.metric("📊 Nº de Trades", len([p for p in positions if p['type'] == 'buy']))

        # -------------------------
        # Gráficos
        # -------------------------
        st.subheader("📊 Gráficos de Resultados")

        fig, ax = plt.subplots(2, 1, figsize=(12, 8), sharex=True)
