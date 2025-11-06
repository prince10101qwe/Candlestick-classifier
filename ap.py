import streamlit as st
import pandas as pd

st.title("Candlestick Analyzer")
st.write("Paste your OHLC data below (Open, High, Low, Close per line, comma or space separated).")

# Input box
ohlc_text = st.text_area("Paste OHLC data here", 
                         "1.2345 1.2450 1.2300 1.2400\n1.2400 1.2500 1.2380 1.2490")

if st.button("Analyze"):
    # Parse text
    data = []
    for line in ohlc_text.strip().split("\n"):
        parts = [float(x) for x in line.replace(",", " ").split()]
        if len(parts) == 4:
            data.append(parts)

    df = pd.DataFrame(data, columns=["Open", "High", "Low", "Close"])
    
    results = []

    for i, row in df.iterrows():
        o, h, l, c = row["Open"], row["High"], row["Low"], row["Close"]
        body = abs(c - o)
        candle_range = h - l
        upper_wick = h - max(o, c)
        lower_wick = min(o, c) - l
        body_pct = (body / candle_range) * 100 if candle_range else 0

        # Candle bias
        direction = "Bullish" if c > o else "Bearish"

        # --- Classification logic ---
        candle_type = "Unknown"
        reason = ""
        comparison = []

        # Doji
        if body_pct <= 10:
            candle_type = f"{direction} Doji"
            reason = f"Body very small ({body_pct:.1f}%), open≈close"
            comparison = [
                "- Not Pin Bar: wicks not 3× body",
                "- Not Spinning Top: wick ratio ≠ equal",
                "- Not Long Wick Rejection: wick imbalance < 3×"
            ]

        # Pin Bar (Hammer/Shooting Star)
        elif lower_wick > body * 3 and upper_wick < body:
            candle_type = "Bullish Pin Bar"
            reason = "Body small (<20%), long lower wick >3× body, upper wick < body"
            comparison = [
                "- Not Doji: body not ≈ close (body% >10%)",
                "- Not Long Wick Rejection: upper wick not 4× smaller than lower wick",
                "- Not Spinning Top: body near top, wick ratio not equal"
            ]
        elif upper_wick > body * 3 and lower_wick < body:
            candle_type = "Bearish Pin Bar"
            reason = "Body small (<20%), long upper wick >3× body, lower wick < body"
            comparison = [
                "- Not Doji: body not ≈ close (body% >10%)",
                "- Not Long Wick Rejection: lower wick not 4× smaller than upper wick",
                "- Not Spinning Top: body near bottom, wick ratio not equal"
            ]

        # Long Wick Rejection
        elif upper_wick >= lower_wick * 4 or lower_wick >= upper_wick * 4:
            candle_type = f"{direction} Long Wick Rejection"
            reason = "One wick ≥4× the opposite wick, showing rejection"
            comparison = [
                "- Not Pin Bar: both wicks not balanced for hammer pattern",
                "- Not Doji: body% >10%",
                "- Not Spinning Top: wick ratio highly uneven"
            ]

        # Spinning Top
        elif 20 <= body_pct <= 40 and abs(upper_wick - lower_wick) / candle_range < 0.2:
            candle_type = f"{direction} Spinning Top"
            reason = "Body medium (20–40%), wicks roughly equal"
            comparison = [
                "- Not Doji: body% >10%",
                "- Not Pin Bar: no long wick dominance",
                "- Not Long Wick Rejection: both wicks balanced"
            ]
        else:
            candle_type = f"{direction} Candle"
            reason = "No special pattern detected"
            comparison = [
                "- Not Doji: body% >10%",
                "- Not Pin Bar: wicks not 3× body",
                "- Not Spinning Top: wick ratio not equal"
            ]

        results.append({
            "Candle #": i + 1,
            "Candle Type": candle_type,
            "Reason": reason,
            "Comparison": "\n".join(comparison)
        })

# Display results
    for r in results:
        st.markdown(f"### Candle {r['Candle #']}")
        st.write(f"Candle Type: {r['Candle Type']}")
        st.write(f"Reason: {r['Reason']}")
        st.text(f"Comparison:\n{r['Comparison']}")
        st.divider()
