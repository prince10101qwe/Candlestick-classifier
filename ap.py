import streamlit as st
import pandas as pd
import re

st.set_page_config(page_title="Candlestick Classifier", layout="centered")
st.title("📊 Candlestick Type Classifier (Based on Your Rules)")

st.markdown("### Choose Input Mode")
mode = st.radio("Select Input Type:", ["Paste OHLC Text", "Enter Manually"])

def classify_candle(o, h, l, c):
    body = abs(c - o)
    total_range = h - l
    upper_wick = h - max(o, c)
    lower_wick = min(o, c) - l

    if total_range <= 0:
        return "Invalid", "High must be greater than Low."

    body_pct = (body / total_range) * 100
    upper_wick_pct = (upper_wick / total_range) * 100
    lower_wick_pct = (lower_wick / total_range) * 100

    candle_type = "Normal Candle"
    reason = ""

    # --- DOJI TYPES ---
    if body_pct <= 10:
        wick_diff = abs(upper_wick - lower_wick) / max(upper_wick, lower_wick, 1)
        if wick_diff <= 0.20:
            candle_type = "Doji"
            reason = "Tiny body (≤10%), wicks roughly equal (≤20% diff)."
        elif lower_wick >= 2 * body and upper_wick <= 0.1 * lower_wick:
            candle_type = "Bullish Doji (Dragonfly)"
            reason = "Tiny body, long lower wick ≥2× body, upper wick ≤10% of lower wick."
        elif upper_wick >= 2 * body and lower_wick <= 0.1 * upper_wick:
            candle_type = "Bearish Doji (Gravestone)"
            reason = "Tiny body, long upper wick ≥2× body, lower wick ≤10% of upper wick."

    # --- PIN BARS ---
    elif body_pct < 20:
        if lower_wick >= 2 * body and (upper_wick <= body):
            candle_type = "Bullish Pin Bar"
            reason = "Small body near top, long lower wick ≥2× body, upper wick small or none."
        elif upper_wick >= 2 * body and (lower_wick <= body):
            candle_type = "Bearish Pin Bar"
            reason = "Small body near bottom, long upper wick ≥2× body, lower wick small or none."

    # --- LONG WICK REJECTIONS ---
    elif body_pct <= 30:
        if lower_wick >= 2 * body and (upper_wick * 4 <= lower_wick):
            candle_type = "Bullish Long Wick Rejection"
            reason = "Body ≤30%, long lower wick ≥2× body, upper wick ≤¼ of lower wick."
        elif upper_wick >= 2 * body and (lower_wick * 4 <= upper_wick):
            candle_type = "Bearish Long Wick Rejection"
            reason = "Body ≤30%, long upper wick ≥2× body, lower wick ≤¼ of upper wick."

    # --- SPINNING TOP ---
    elif 10 < body_pct <= 30:
        wick_diff = abs(upper_wick - lower_wick) / max(upper_wick, lower_wick, 1)
        if wick_diff <= 0.40:
            candle_type = "Spinning Top"
            reason = "Body 10–30% of range, wicks roughly equal (≤40% diff)."

    return candle_type, reason


if mode == "Paste OHLC Text":
    st.markdown("### Paste OHLC Data (one per line)")
    st.text("Example format:\nO3721.670 H3724.995 L3719.530 C3722.610")
    text_data = st.text_area("Paste here:", height=200)

    if st.button("🔍 Classify All"):
        lines = text_data.strip().split("\n")
        results = []
        pattern = re.compile(r"O([\d.]+)\s*H([\d.]+)\s*L([\d.]+)\s*C([\d.]+)")

        for line in lines:
            match = pattern.search(line)
            if match:
                o, h, l, c = map(float, match.groups())
                t, r = classify_candle(o, h, l, c)
                results.append({"Open": o, "High": h, "Low": l, "Close": c, "Type": t, "Reason": r})
            else:
                results.append({"Open": None, "High": None, "Low": None, "Close": None, "Type": "Invalid Format", "Reason": "Use O,H,L,C format"})

        df = pd.DataFrame(results)
        st.dataframe(df)

else:
    st.markdown("### Enter Single Candle Manually")
    o = st.number_input("Open", value=0.0, format="%.3f")
    h = st.number_input("High", value=0.0, format="%.3f")
    l = st.number_input("Low", value=0.0, format="%.3f")
    c = st.number_input("Close", value=0.0, format="%.3f")

    if st.button("🔍 Classify Candle"):
        t, r = classify_candle(o, h, l, c)
        st.subheader(f"🕯 Type: {t}")
        st.write(f"Reason: {r}")
