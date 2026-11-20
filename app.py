import io
import os
import tempfile

import gradio as gr
import pandas as pd
import plotly.express as px
import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

DEFAULT_URL = "https://data.tainan.gov.tw/File/ResourceCsvDownload/6c16b2c8-92b6-49d9-98b5-02966462172c"
ENCODINGS = ["自動偵測", "utf-8-sig", "utf-8", "big5", "cp950"]
CLEAN_MODES = ["不清理", "刪除「任一欄」有缺值的列", "只刪除「整列皆空」的列"]
CHART_TYPES = ["長條圖（類別次數）", "圓餅圖（類別佔比）", "直方圖（數值分布）"]


# ---------- 資料處理 ----------
def fetch_csv(url, encoding, verify_ssl):
    resp = requests.get(
        url, verify=verify_ssl, timeout=30, headers={"User-Agent": "Mozilla/5.0"}
    )
    resp.raise_for_status()
    candidates = (
        ["utf-8-sig", "utf-8", "big5", "cp950"] if encoding == "自動偵測" else [encoding]
    )
    for enc in candidates:
        try:
            return pd.read_csv(io.BytesIO(resp.content), encoding=enc), enc
        except UnicodeDecodeError:
            continue
    raise gr.Error("編碼無法解析，請手動選擇 big5 或 cp950 試試。")


def stat_cards(rows_raw, rows_clean, cols, enc):
    def card(title, value):
        return (
            "<div style='flex:1;min-width:120px;padding:14px 18px;border-radius:14px;"
            "background:linear-gradient(135deg,#6366f1,#8b5cf6);color:white;'>"
            f"<div style='font-size:12px;opacity:.85'>{title}</div>"
            f"<div style='font-size:26px;font-weight:700'>{value}</div></div>"
        )

    return (
        "<div style='display:flex;gap:12px;flex-wrap:wrap;'>"
        + card("原始筆數", f"{rows_raw:,}")
        + card("清理後筆數", f"{rows_clean:,}")
        + card("欄位數", cols)
        + card("使用編碼", enc)
        + "</div>"
    )


def load_data(url, encoding, verify_ssl, clean_mode):
    if not url or not url.strip():
        raise gr.Error("請輸入 CSV 連結")
    try:
        df_raw, enc = fetch_csv(url.strip(), encoding, verify_ssl)
    except requests.exceptions.SSLError:
        raise gr.Error("SSL 憑證錯誤，請取消勾選「驗證 SSL 憑證」再試。")
    except requests.exceptions.RequestException as e:
        raise gr.Error(f"下載失敗：{e}")
    except pd.errors.ParserError as e:
        raise gr.Error(f"CSV 解析失敗，連結可能不是 CSV：{e}")

    if clean_mode == CLEAN_MODES[1]:
        df = df_raw.dropna()
    elif clean_mode == CLEAN_MODES[2]:
        df = df_raw.dropna(how="all")
    else:
        df = df_raw.copy()
    df = df.reset_index(drop=True)

    missing = pd.DataFrame(
        {
            "欄位": df_raw.columns,
            "缺值數": df_raw.isna().sum().values,
            "缺值率(%)": (df_raw.isna().mean() * 100).round(2).values,
        }
    ).sort_values("缺值數", ascending=False)

    desc = df.describe(include="all").T.reset_index().rename(columns={"index": "欄位"})

    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".csv", prefix="cleaned_")
    df.to_csv(tmp.name, index=False, encoding="utf-8-sig")

    cols = list(df.columns)
    return (
        stat_cards(len(df_raw), len(df), len(cols), enc),
        df,
        df.head(200),
        missing,
        desc,
        gr.update(choices=cols, value=cols[0] if cols else None),
        tmp.name,
    )


def search(df, keyword):
    if df is None:
        return pd.DataFrame()
    if not keyword:
        return df.head(200)
    mask = (
        df.astype(str)
        .apply(lambda c: c.str.contains(keyword, case=False, na=False, regex=False))
        .any(axis=1)
    )
    return df[mask].head(500)


def make_chart(df, col, kind, topn):
    if df is None or col is None:
        raise gr.Error("請先載入資料")
    topn = int(topn)
    if kind == CHART_TYPES[2]:
        s = pd.to_numeric(df[col], errors="coerce").dropna()
        if s.empty:
            raise gr.Error(f"「{col}」不是數值欄位，請改選長條圖或圓餅圖。")
        fig = px.histogram(
            s.to_frame(col), x=col, nbins=30, color_discrete_sequence=["#6366f1"]
        )
    else:
        vc = df[col].astype(str).value_counts().head(topn).reset_index()
        vc.columns = [col, "次數"]
        if kind == CHART_TYPES[0]:
            fig = px.bar(
                vc, x=col, y="次數", text="次數", color_discrete_sequence=["#6366f1"]
            )
        else:
            fig = px.pie(vc, names=col, values="次數", hole=0.4)
    fig.update_layout(
        title=f"{col}", template="plotly_white", margin=dict(l=20, r=20, t=50, b=20)
    )
    return fig


# ---------- 介面 ----------
theme = gr.themes.Soft(
    primary_hue="indigo",
    secondary_hue="violet",
    font=[gr.themes.GoogleFont("Noto Sans TC"), "sans-serif"],
)

with gr.Blocks(theme=theme, title="開放資料 CSV 探索器") as demo:
    gr.Markdown(
        "# 📊 開放資料 CSV 探索器\n"
        "貼上政府開放資料的 CSV 連結，一鍵完成下載、清理、搜尋與視覺化。"
    )
    state_df = gr.State(None)

    with gr.Row():
        with gr.Column(scale=1, min_width=320):
            gr.Markdown("### ⚙️ 資料來源設定")
            url_in = gr.Textbox(label="CSV 連結", value=DEFAULT_URL, lines=3)
            enc_in = gr.Dropdown(ENCODINGS, value="自動偵測", label="編碼")
            clean_in = gr.Radio(CLEAN_MODES, value=CLEAN_MODES[0], label="缺值處理")
            ssl_in = gr.Checkbox(
                value=False,
                label="驗證 SSL 憑證（政府網站憑證有問題時請取消勾選）",
            )
            load_btn = gr.Button("🚀 載入資料", variant="primary", size="lg")
            file_out = gr.File(label="⬇️ 下載清理後的 CSV")

        with gr.Column(scale=3):
            cards = gr.HTML(
                "<div style='padding:24px;text-align:center;color:#888'>"
                "尚未載入資料，請按左側「載入資料」</div>"
            )
            with gr.Tabs():
                with gr.Tab("📄 資料預覽"):
                    kw = gr.Textbox(
                        label="🔍 關鍵字搜尋（搜尋所有欄位）",
                        placeholder="輸入關鍵字後按 Enter",
                    )
                    table = gr.Dataframe(interactive=False, wrap=True, max_height=480)
                with gr.Tab("🧩 缺值分析"):
                    missing_out = gr.Dataframe(interactive=False)
                with gr.Tab("📐 統計摘要"):
                    desc_out = gr.Dataframe(interactive=False)
                with gr.Tab("📈 視覺化"):
                    with gr.Row():
                        col_in = gr.Dropdown(label="選擇欄位", choices=[])
                        kind_in = gr.Dropdown(
                            CHART_TYPES, value=CHART_TYPES[0], label="圖表類型"
                        )
                        topn_in = gr.Slider(5, 30, value=10, step=1, label="顯示前 N 名")
                    plot_btn = gr.Button("繪製圖表", variant="secondary")
                    plot_out = gr.Plot()

    load_btn.click(
        load_data,
        inputs=[url_in, enc_in, ssl_in, clean_in],
        outputs=[cards, state_df, table, missing_out, desc_out, col_in, file_out],
    )
    kw.submit(search, [state_df, kw], table)
    plot_btn.click(make_chart, [state_df, col_in, kind_in, topn_in], plot_out)


if __name__ == "__main__":
    # Render 會注入 PORT 環境變數，且必須綁定 0.0.0.0
    port = int(os.environ.get("PORT", 7860))
    demo.queue().launch(server_name="0.0.0.0", server_port=port)
