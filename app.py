import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from pathlib import Path

css_file = Path(__file__).parent / "style.css"

if css_file.exists():
    st.markdown(
        f"<style>{css_file.read_text(encoding='utf-8')}</style>",
        unsafe_allow_html=True
    )

st.set_page_config(
    page_title="Pocket Analyzer",
    page_icon="📈",
    layout="wide"
)

st.markdown("""
<div style="
    padding: 22px 24px;
    border-radius: 14px;
    background: linear-gradient(120deg, #111c30, #172554);
    border: 1px solid #26364f;
    margin-bottom: 24px;
">
    <div style="font-size: 13px; color: #38bdf8; letter-spacing: 2px;">
        POCKET ANALYZER · MARKET INTELLIGENCE
    </div>
    <h1 style="margin: 8px 0; color: #f8fafc;">
        📈 Pocket Analyzer
    </h1>
    <div style="color: #94a3b8;">
        Forex & Cryptocurrency Technical Analysis
    </div>
    <div style="margin-top: 16px; font-size: 12px; color: #34d399;">
        ● ANALYSIS SYSTEM READY
    </div>
</div>
""", unsafe_allow_html=True)

st.sidebar.header("Market Settings")

market = st.sidebar.selectbox(
    "Choose your market",
    [
        "EUR/USD",
        "GBP/USD",
        "USD/JPY",
        "Bitcoin (BTC/USD)",
        "Ethereum (ETH/USD)"
    ]
)

timeframe = st.sidebar.selectbox(
    "Trading Timeframe",
    ["1 minute", "5 minutes", "15 minutes", "30 minutes", "1 hour", "1 day"],
    index=2
)

timeframe_settings = {
    "1 minute": ("1m", "7d"),
    "5 minutes": ("5m", "60d"),
    "15 minutes": ("15m", "60d"),
    "30 minutes": ("30m", "60d"),
    "1 hour": ("60m", "730d"),
    "1 day": ("1d", "1y")
}

interval, period = timeframe_settings[timeframe]

markets = {
    "EUR/USD": "EURUSD=X",
    "GBP/USD": "GBPUSD=X",
    "USD/JPY": "JPY=X",
    "Bitcoin (BTC/USD)": "BTC-USD",
    "Ethereum (ETH/USD)": "ETH-USD"
}

if st.button("Analyze Market", type="primary"):
    with st.spinner("Downloading market data..."):
        try:
            data = yf.download(
                markets[market],
                period=period,
                interval=interval,
                progress=False,
                auto_adjust=True
            )

            if isinstance(data.columns, pd.MultiIndex):
                data.columns = data.columns.get_level_values(0)

            if data.empty or "Close" not in data.columns:
                st.error("No market data received. Please try again.")
            else:
                data = data[~data.index.duplicated(keep="last")].copy()
                data["SMA_20"] = data["Close"].rolling(20).mean()
                data["SMA_50"] = data["Close"].rolling(50).mean()

                change = data["Close"].diff()
                gain = change.clip(lower=0)
                loss = -change.clip(upper=0)

                avg_gain = gain.rolling(14).mean()
                avg_loss = loss.rolling(14).mean()
                rs = avg_gain / avg_loss.replace(0, np.nan)

                data["RSI_14"] = 100 - (100 / (1 + rs))
                data.loc[(avg_loss == 0) & (avg_gain > 0), "RSI_14"] = 100
                data.loc[(avg_loss == 0) & (avg_gain == 0), "RSI_14"] = 50
                # Calculate MACD indicator
                data["EMA_12"] = data["Close"].ewm(
                    span=12, adjust=False
                ).mean()

                data["EMA_26"] = data["Close"].ewm(
                    span=26, adjust=False
                ).mean()

                data["MACD"] = data["EMA_12"] - data["EMA_26"]

                data["MACD_Signal"] = data["MACD"].ewm(
                    span=9, adjust=False
                ).mean()

                data["MACD_Histogram"] = (
                    data["MACD"] - data["MACD_Signal"]
                )

                latest = data.iloc[-1]
                # Generate MACD trading signal
                if latest["MACD"] > latest["MACD_Signal"]:
                    macd_signal = "BUY"
                elif latest["MACD"] < latest["MACD_Signal"]:
                    macd_signal = "SELL"
                else:
                    macd_signal = "NEUTRAL"
                price = float(latest["Close"])
                rsi = latest["RSI_14"]

                st.subheader(f"{market} Dashboard — {timeframe}")
                st.caption(
                    f"Selected timeframe: {timeframe} | Latest candle: {data.index[-1]}"
                )

                col1, col2, col3 = st.columns(3)

                col1.metric("Latest Closing Price", f"{price:,.5f}")
                col2.metric(
                    "20-Day Moving Average",
                    f"{latest['SMA_20']:,.5f}"
                    if pd.notna(latest["SMA_20"]) else "Not available"
                )
                col3.metric(
                    "RSI (14)",
                    f"{rsi:.2f}" if pd.notna(rsi) else "Not available"
                )

                st.subheader("Price Chart")
                import plotly.graph_objects as go
                # Detect swing highs and swing lows
                recent_data = data.tail(100).copy()

                recent_data["Swing_Low"] = (
                    (recent_data["Low"] < recent_data["Low"].shift(1)) &
                    (recent_data["Low"] < recent_data["Low"].shift(-1))
                )

                recent_data["Swing_High"] = (
                    (recent_data["High"] > recent_data["High"].shift(1)) &
                    (recent_data["High"] > recent_data["High"].shift(-1))
                )

                swing_lows = recent_data.loc[
                    recent_data["Swing_Low"], "Low"
                ]

                swing_highs = recent_data.loc[
                    recent_data["Swing_High"], "High"
                ]

                support_level = (
                    swing_lows.iloc[-1]
                    if not swing_lows.empty
                    else recent_data["Low"].min()
                )

                resistance_level = (
                    swing_highs.iloc[-1]
                    if not swing_highs.empty
                    else recent_data["High"].max()
                )

                fig = go.Figure()
                fig.add_hline(
                    y=support_level,
                    line_dash="dash",
                    line_color="#22c55e",
                    line_width=2,
                    annotation_text=f"Support: {support_level:.5f}",
                    annotation_position="bottom right"
                )

                fig.add_hline(
                    y=resistance_level,
                    line_dash="dash",
                    line_color="#ef4444",
                    line_width=2,
                    annotation_text=f"Resistance: {resistance_level:.5f}",
                    annotation_position="top right"
                )

                fig.add_trace(go.Candlestick(
                    x=data.index,
                    open=data["Open"],
                    high=data["High"],
                    low=data["Low"],
                    close=data["Close"],
                    name="Price"
                ))

                fig.add_trace(go.Scatter(
                    x=data.index,
                    y=data["SMA_20"],
                    name="SMA 20",
                    line=dict(color="#22c55e", width=1.5)
                ))

                fig.add_trace(go.Scatter(
                    x=data.index,
                    y=data["SMA_50"],
                    name="SMA 50",
                    line=dict(color="#f59e0b", width=1.5)
                ))

                fig.update_layout(
                    title=f"{market} Candlestick Chart",
                    template="plotly_dark",
                    height=600,
                    xaxis_title="Time",
                    yaxis_title="Price",
                    xaxis_rangeslider_visible=False,
                    legend=dict(orientation="h", y=1.02, x=0)
                )
                col1, col2 = st.columns(2)

                col1.metric(
                    "🟢 Support Level",
                    f"{support_level:.5f}"
                )

                col2.metric(
                    "🔴 Resistance Level",
                    f"{resistance_level:.5f}"
                )

                st.plotly_chart(fig, use_container_width=True)
                st.subheader("📉 MACD Indicator")

                macd_fig = go.Figure()

                macd_fig.add_trace(go.Bar(
                    x=data.index,
                    y=data["MACD_Histogram"],
                    name="MACD Histogram"
                ))

                macd_fig.add_trace(go.Scatter(
                    x=data.index,
                    y=data["MACD"],
                    name="MACD",
                    line=dict(color="#38bdf8", width=2)
                ))

                macd_fig.add_trace(go.Scatter(
                    x=data.index,
                    y=data["MACD_Signal"],
                    name="Signal Line",
                    line=dict(color="#f59e0b", width=2)
                ))

                macd_fig.add_hline(
                    y=0,
                    line_dash="dash",
                    line_color="#94a3b8"
                )

                macd_fig.update_layout(
                    title="MACD (12, 26, 9)",
                    template="plotly_dark",
                    height=350,
                    xaxis_title="Time",
                    yaxis_title="MACD Value",
                    legend=dict(orientation="h", y=1.02, x=0)
                )

                st.plotly_chart(
                    macd_fig,
                    use_container_width=True
                )
                st.subheader("📉 MACD Trading Signal")

                if macd_signal == "BUY":
                    st.success("MACD: BUY — Bullish momentum")
                elif macd_signal == "SELL":
                    st.error("MACD: SELL — Bearish momentum")
                else:
                    st.warning("MACD: NEUTRAL — No clear direction")

                st.subheader("📊 Market Signal Dashboard")

                if pd.isna(latest["SMA_20"]) or pd.isna(latest["SMA_50"]):
                    st.info("🟡 NEUTRAL — Not enough data to determine the trend.")
                elif latest["SMA_20"] > latest["SMA_50"]:
                    st.success("🟢 BULLISH — The 20-day average is above the 50-day average.")
                elif latest["SMA_20"] < latest["SMA_50"]:
                    st.error("🔴 BEARISH — The 20-day average is below the 50-day average.")
                else:
                    st.warning("🟡 NEUTRAL — Both moving averages are equal.")

                if pd.isna(rsi):
                    st.info("RSI signal: Not enough data.")
                elif rsi < 30:
                    st.success("🟢 RSI: OVERSOLD — A possible rebound zone.")
                elif rsi > 70:
                    st.error("🔴 RSI: OVERBOUGHT — A possible pullback zone.")
                else:
                    st.info("🟡 RSI: NEUTRAL — RSI is between 30 and 70.")
                    

                if pd.isna(latest["SMA_20"]) or pd.isna(latest["SMA_50"]) or pd.isna(rsi):
                    recommendation = "HOLD"
                    rec_color = "#f59e0b"
                    rec_reason = "Not enough indicator data."

                elif latest["SMA_20"] > latest["SMA_50"] and 30 <= rsi <= 70:
                    recommendation = "BUY"
                    rec_color = "#22c55e"
                    rec_reason = "Bullish trend with RSI in a moderate range."

                elif latest["SMA_20"] < latest["SMA_50"] and 30 <= rsi <= 70:
                    recommendation = "SELL"
                    rec_color = "#ef4444"
                    rec_reason = "Bearish trend with RSI in a moderate range."

                else:
                    recommendation = "HOLD"
                    rec_color = "#f59e0b"
                    rec_reason = "Indicators are mixed or RSI is at an extreme."

                st.markdown(f"""
                <div style="background:#111827;border:1px solid {rec_color};
                    border-left:6px solid {rec_color};border-radius:12px;
                    padding:24px;margin:12px 0;">
                    <div style="color:#94a3b8;font-size:13px;">
                        TRADING SIGNAL · {timeframe.upper()}
                    </div>
                    <div style="color:{rec_color};font-size:34px;font-weight:800;
                        margin:8px 0;">{recommendation}</div>
                    <div style="color:#e2e8f0;">{rec_reason}</div>
                </div>
                """, unsafe_allow_html=True)
                st.subheader("🤝 Signal Confirmation")

                
                st.subheader("🔎 Multi-Timeframe Confirmation")
                higher_trend = "UNAVAILABLE"

                if interval == "60m":
                    confirmation_data = data
                else:
                    with st.spinner("Checking the 1-hour trend..."):
                        confirmation_data = yf.download(
                            markets[market],
                            period="60d",
                            interval="60m",
                            progress=False,
                            auto_adjust=True
                        )

                if isinstance(confirmation_data.columns, pd.MultiIndex):
                    confirmation_data.columns = confirmation_data.columns.get_level_values(0)

                if not confirmation_data.empty and "Close" in confirmation_data.columns:
                    confirmation_data = confirmation_data.copy()
                    confirmation_data["SMA_20"] = confirmation_data["Close"].rolling(20).mean()
                    confirmation_data["SMA_50"] = confirmation_data["Close"].rolling(50).mean()

                    if len(confirmation_data) < 50:
                        st.warning("Not enough hourly data to confirm the trend.")
                    else:
                        confirm_latest = confirmation_data.iloc[-1]

                        if pd.isna(confirm_latest["SMA_20"]) or pd.isna(confirm_latest["SMA_50"]):
                            higher_trend = "UNAVAILABLE"
                        elif confirm_latest["SMA_20"] > confirm_latest["SMA_50"]:
                            higher_trend = "BULLISH"
                        elif confirm_latest["SMA_20"] < confirm_latest["SMA_50"]:
                            higher_trend = "BEARISH"
                        else:
                            higher_trend = "NEUTRAL"

                        st.write(f"Selected timeframe: **{timeframe}**")
                        st.write(f"1-hour trend: **{higher_trend}**")

                        if higher_trend == "UNAVAILABLE":
                            st.warning("Not enough data to confirm the trend.")
                        elif (
                            (recommendation == "BUY" and higher_trend == "BULLISH")
                            or (recommendation == "SELL" and higher_trend == "BEARISH")
                        ):
                            st.success("✅ The selected timeframe agrees with the 1-hour trend.")
                        elif recommendation in ["BUY", "SELL"] and higher_trend in ["BULLISH", "BEARISH"]:
                            st.warning("⚠️ The timeframes conflict. Consider waiting for clearer confirmation.")
                        else:
                            st.info("No clear multi-timeframe confirmation.")
                else:
                    st.warning("Could not retrieve hourly data. Try again later.")
                

                st.subheader("🤝 Three-Signal Confirmation")

                if higher_trend == "UNAVAILABLE":
                    st.warning("Hourly trend unavailable. Full confirmation is not possible.")
                elif (
                    recommendation == "BUY"
                    and macd_signal == "BUY"
                    and higher_trend == "BULLISH"
                ):
                    st.success("🟢 BUY CONFIRMED — All three signals agree.")
                elif (
                    recommendation == "SELL"
                    and macd_signal == "SELL"
                    and higher_trend == "BEARISH"
                ):
                    st.error("🔴 SELL CONFIRMED — All three signals agree.")
                else:
                    st.warning("🟡 NO FULL CONFIRMATION — Signals disagree or are neutral.")
                st.caption(
                    "Educational analysis only. Signals do not guarantee "
                    "future price movements or profitable trades."
                )

            

                with st.expander("View recent market data"):
                    st.dataframe(
                        data[["Close", "SMA_20", "SMA_50", "RSI_14"]].tail(10),
                        use_container_width=True
                    )

                st.caption(
                    "Educational analysis only. Indicators do not guarantee "
                    "future price movements or confirm a profitable trade."
                )

        except Exception as error:
            st.error(f"Could not analyze this market: {error}")

else:
    st.info("Choose a market on the left, then click Analyze Market.")