import streamlit as st
import re

st.set_page_config(page_title="Candlestick Identifier — Strict Rules", layout="centered")
st.title("Candlestick Identifier — Strict Rules + Full Comparison")

# ---------- Input ----------
st.markdown("Paste OHLC, any format per line (e.g. `O3,743.520 H3,745.840 L3,739.345 C3,745.240`).")
raw = st.text_area("OHLC lines", height=200)

def parse_input(text):
    candles = []
    for line in text.splitlines():
        # extract 4 numbers in order, ignoring letters and commas
        nums = re.findall(r"[-+]?\d*\.?\d+", line.replace(",", ""))
        if len(nums) >= 4:
            o, h, l, c = map(float, nums[:4])
            candles.append((o, h, l, c, line.strip()))
    return candles

# ---------- Core checks (strict to your latest rules) ----------
def checks(o, h, l, c):
    eps = 1e-12
    total = max(h - l, eps)
    body = abs(c - o)
    upper = h - max(o, c)
    lower = min(o, c) - l

    body_pct = 100.0 * body / total
    wick_ratio_equal_doji = (max(upper, lower) / max(min(upper, lower), eps)) if (upper > 0 or lower > 0) else 1.0
    wick_ratio_equal_spin = wick_ratio_equal_doji

    res = {}

    # 1) Doji (0–10%, both wicks >= body, wicks within 20%)
    res["Doji"] = (
        body_pct <= 10.0 and upper >= body and lower >= body and wick_ratio_equal_doji <= 1.2,
        f"body {body_pct:.2f}% ≤ 10%, upper≥body({upper:.6g}≥{body:.6g}), lower≥body({lower:.6g}≥{body:.6g}), wick ratio ≤1.2 ({wick_ratio_equal_doji:.2f})"
        if body_pct <= 10.0 else f"body {body_pct:.2f}% > 10%"
    )

    # 2) Bullish Doji (Dragonfly): body ≤10%, long lower ≥2×body, upper ≤10% of lower (or 0)
    res["Bullish Doji (Dragonfly)"] = (
        body_pct <= 10.0 and lower >= 2.0*body and upper <= 0.1*lower,
        f"body {body_pct:.2f}% ≤10%, lower {lower:.6g} ≥ 2×body {2*body:.6g}, upper {upper:.6g} ≤ 10% of lower {0.1*lower:.6g}"
        if body_pct <= 10.0 else f"body {body_pct:.2f}% > 10%"
    )

    # 3) Bearish Doji (Gravestone): body ≤10%, long upper ≥2×body, lower ≤10% of upper (or 0)
    res["Bearish Doji (Gravestone)"] = (
        body_pct <= 10.0 and upper >= 2.0*body and lower <= 0.1*upper,
        f"body {body_pct:.2f}% ≤10%, upper {upper:.6g} ≥ 2×body {2*body:.6g}, lower {lower:.6g} ≤ 10% of upper {0.1*upper:.6g}"
        if body_pct <= 10.0 else f"body {body_pct:.2f}% > 10%"
    )

    # 4) Bullish Pin Bar: body <20%, lower ≥2×body, upper ≤ body
    res["Bullish Pin Bar"] = (
        body_pct < 20.0 and lower >= 2.0*body and upper <= body,
        f"body {body_pct:.2f}% <20%, lower {lower:.6g} ≥ 2×body {2*body:.6g}, upper {upper:.6g} ≤ body {body:.6g}"
    )

    # 5) Bearish Pin Bar: body <20%, upper ≥2×body, lower ≤ body
    res["Bearish Pin Bar"] = (
        body_pct < 20.0 and upper >= 2.0*body and lower <= body,
        f"body {body_pct:.2f}% <20%, upper {upper:.6g} ≥ 2×body {2*body:.6g}, lower {lower:.6g} ≤ body {body:.6g}"
    )

    # 6) Bullish Long Wick Rejection: body ≤30%, lower ≥2×body, upper ≤ 1/4 lower
    res["Bullish Long Wick Rejection"] = (
        body_pct <= 30.0 and lower >= 2.0*body and upper <= 0.25*lower,
        f"body {body_pct:.2f}% ≤30%, lower {lower:.6g} ≥ 2×body {2*body:.6g}, upper {upper:.6g} ≤ ¼ lower {0.25*lower:.6g}"
    )

    # 7) Bearish Long Wick Rejection: body ≤30%, upper ≥2×body, lower ≤ 1/4 upper
    res["Bearish Long Wick Rejection"] = (
        body_pct <= 30.0 and upper >= 2.0*body and lower <= 0.25*upper,
        f"body {body_pct:.2f}% ≤30%, upper {upper:.6g} ≥ 2×body {2*body:.6g}, lower {lower:.6g} ≤ ¼ upper {0.25*upper:.6g}"
    )

    # 8) Spinning Top: body 10–30%, both wicks ≥ body, wicks within 40%
    res["Spinning Top"] = (
        (10.0 <= body_pct <= 30.0) and (upper >= body) and (lower >= body) and (wick_ratio_equal_spin <= 1.4),
        f"body {body_pct:.2f}% in [10,30], upper≥body({upper:.6g}≥{body:.6g}), lower≥body({lower:.6g}≥{body:.6g}), wick ratio ≤1.4 ({wick_ratio_equal_spin:.2f})"
        if 10.0 <= body_pct <= 30.0 else f"body {body_pct:.2f}% not in [10,30]"
    )

    # Pin Bar → Long Wick Rejection conversion (only if LWR rules also hold)
    convert_from = None
    if res["Bullish Pin Bar"][0] and res["Bullish Long Wick Rejection"][0]:
        convert_from = "Bullish Pin Bar"
        res["Bullish Pin Bar"] = (False, "Converted to Bullish Long Wick Rejection (LWR rules also satisfied).")
    if res["Bearish Pin Bar"][0] and res["Bearish Long Wick Rejection"][0]:
        convert_from = "Bearish Pin Bar"
        res["Bearish Pin Bar"] = (False, "Converted to Bearish Long Wick Rejection (LWR rules also satisfied).")

    # Priority by strength (your order)
    priority = [
        "Bullish Doji (Dragonfly)",
        "Bearish Doji (Gravestone)",
        "Doji",
        "Bullish Pin Bar",
        "Bearish Pin Bar",
        "Bullish Long Wick Rejection",
        "Bearish Long Wick Rejection",
        "Spinning Top",
    ]

    # Choose final
    final_type, final_reason = "Normal Candle", f"body {body_pct:.2f}% — no rule matched"
    for name in priority:
        ok, why = res[name]
        if ok:
            final_type, final_reason = name, why
            break

    # Build comparison list: why not others
    comparison = []
    for name in priority:
        ok, why = res[name]
        if name == final_type:
            continue
        if ok:
            comparison.append(f"- {name}: matched, but lower priority than {final_type}")
        else:
            comparison.append(f"- Not {name}: {why}")

    # if truly nothing matched
    if final_type == "Normal Candle":
        for name in priority:
            ok, why = res[name]
            comparison.append(f"- Not {name}: {why}")

    return {
        "final": (final_type, final_reason),
        "comparison": comparison
    }

def format_output(idx, line, o, h, l, c, report):
    t, why = report["final"]
    st.subheader(f"Candle {idx}")
    st.caption(line)
    st.write(f"**Candle Type:** {t}")
    st.write(f"**Reason:** {why}")
    st.write("**Comparison:**")
    for row in report["comparison"]:
        st.write(row)
    st.divider()

candles = parse_input(raw)

if st.button("Analyze"):
    if not candles:
        st.error("No valid OHLC found. Paste one per line.")
    else:
        for i, (o, h, l, c, line) in enumerate(candles, start=1):
            rep = checks(o, h, l, c)
            format_output(i, line, o, h, l, c, rep)
