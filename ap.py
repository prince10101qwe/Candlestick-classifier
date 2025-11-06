
import streamlit as st

st.set_page_config(page_title="Candlestick Classifier", layout="centered")

st.title("📊 Real-Time Candlestick Classifier")

# --- User Inputs ---
open_price = st.number_input("Open Price", value=0.0, format="%.3f")
high_price = st.number_input("High Price", value=0.0, format="%.3f")
low_price = st.number_input("Low Price", value=0.0, format="%.3f")
close_price = st.number_input("Close Price", value=0.0, format="%.3f")

# --- Core Calculations ---
body = abs(close_price - open_price)
total_range = high_price - low_price
upper_wick = high_price - max(open_price, close_price)
lower_wick = min(open_price, close_price) - low_price

if total_range > 0:
    body_percent = (body / total_range) * 100
    upper_wick_percent = (upper_wick / total_range) * 100
    lower_wick_percent = (lower_wick / total_range) * 100
else:
    body_percent = upper_wick_percent = lower_wick_percent = 0

# --- Classification Logic (your rules) ---
if st.button("🔍 Classify Candle"):
    candle_type = "Normal Candle"
    reason = ""

    # Rule 1: Doji
    if 0 <= body_percent <= 10:
        candle_type = "Doji"
        reason = "Body 0–10% of total range."

    # Rule 2: Pin Bar
    elif body_percent < 20:
        candle_type = "Pin Bar"
        reason = "Body <20%, usually 5–15%."

    # Rule 3: Long Wick Rejection
    elif body_percent <= 30:
        if upper_wick_percent >= 60:
            candle_type = "Shooting Star (Bearish Rejection)"
            reason = "Upper wick >60% with small body."
        elif lower_wick_percent >= 60:
            candle_type = "Hammer (Bullish Rejection)"
            reason = "Lower wick >60% with small body."
        else:
            candle_type = "Long Wick Candle"
            reason = "Wicks longer than body."

    # Strong/Weak Classification
    if candle_type not in ["Doji", "Normal Candle"]:
        strength = "Strong" if body_percent > 50 else "Weak"
    else:
        strength = "Neutral"

    # --- Display Result ---
    st.subheader(f"🕯 Type: {candle_type}")
    st.write(f"Reason: {reason}")
    st.write(f"Strength: {strength}")
    st.write("---")
    st.metric("Body %", f"{body_percent:.1f}%")
    st.metric("Upper Wick %", f"{upper_wick_percent:.1f}%")
    st.metric("Lower Wick %", f"{lower_wick_percent:.1f}%")
