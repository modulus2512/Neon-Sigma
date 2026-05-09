import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import yfinance as yf
from datetime import datetime
import plotly.express as px

# 1. 페이지 설정
st.set_page_config(page_title="NEON SIGMA: Asset & Milestone Tracker v5.14", layout="wide")

# --- [NEON PULSE] 커스텀 사이버펑크 CSS ---
st.markdown("""
<style>
    .neon-text { color: #00FFCC !important; font-weight: bold; }
    .neon-card {
        padding: 20px; border-radius: 8px; border: 1px solid rgba(0, 255, 204, 0.4); 
        background-color: rgba(0, 255, 204, 0.02); box-shadow: 0 0 15px rgba(0, 255, 204, 0.1);
        transition: all 0.3s ease;
    }
    .neon-card:hover { box-shadow: 0 0 25px rgba(0, 255, 204, 0.25); border: 1px solid rgba(0, 255, 204, 0.8); }
    .neon-title { margin: 0; font-size: 1rem; color: #8892B0; font-weight: bold; }
    .neon-value { margin: 0; font-size: 2.1rem; font-weight: bold; color: #E6F1FF; letter-spacing: -0.5px; }
    .pulse-panel { 
        border: 1px solid #FF007F; background-color: rgba(255, 0, 127, 0.03); 
        padding: 20px; border-radius: 8px; margin-top: 10px; margin-bottom: 20px;
    }
</style>
""", unsafe_allow_html=True)

# 0. 인증 정보 로드 및 SECURITY GATEKEEPER
if "connections" not in st.secrets:
    st.error("❌ '.streamlit/secrets.toml' 파일을 찾을 수 없거나 형식이 잘못되었습니다.")
    st.stop()

if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

if not st.session_state["authenticated"]:
    st.markdown("<br><br><br><h2 style='text-align: center; color: #00FFCC; font-weight: bold;'>⚡ NEON PULSE : SYSTEM LOCK</h2>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        pwd = st.text_input("Enter Access Key", type="password")
        if st.button("UNLOCK SYSTEM", use_container_width=True):
            if "ACCESS_KEY" in st.secrets and pwd == st.secrets["ACCESS_KEY"]:
                st.session_state["authenticated"] = True
                st.rerun()
            else:
                st.error("❌ ACCESS DENIED: 키가 일치하지 않습니다.")
    st.stop()

# 2. GSheets 연결 설정
SPREADSHEET_URL = "https://docs.google.com/spreadsheets/d/1V_3ImpmGbJr-I1S3mhdCSijjcWMeFQ6vb89yJJvLH-I"
SHEET_NAME = "Transactions"
conn = st.connection("gsheets", type=GSheetsConnection)

# 3. 데이터 불러오기 함수
@st.cache_data(ttl=60)
def load_data():
    try:
        df = conn.read(spreadsheet=SPREADSHEET_URL, worksheet=SHEET_NAME, ttl=0)
        if df.empty or "Name" not in df.columns:
            return pd.DataFrame(columns=["Date", "Account", "Name", "Ticker", "Category", "Type", "Price", "Qty", "Ex_Rate", "Note"])
        
        text_columns = ["Account", "Name", "Ticker", "Category", "Type", "Note"]
        for col in text_columns:
            if col in df.columns:
                df[col] = df[col].astype(str).str.strip().replace('nan', '')
        
        df['Price'] = pd.to_numeric(df['Price'], errors='coerce').fillna(0.0)
        df['Qty'] = pd.to_numeric(df['Qty'], errors='coerce').fillna(0.0)
        df['Ex_Rate'] = pd.to_numeric(df.get('Ex_Rate', 1.0), errors='coerce').fillna(1.0)
                
        return df
    except Exception as e:
        st.error(f"⚠️ 시트를 불러오는 중 오류가 발생했습니다: {e}")
        return pd.DataFrame(columns=["Date", "Account", "Name", "Ticker", "Category", "Type", "Price", "Qty", "Ex_Rate", "Note"])

df = load_data()

# --- yfinance 실시간 시장 변수 ---
@st.cache_data(ttl=300)
def get_current_prices(tickers):
    prices = {"USD": 1.0} 
    for ticker in tickers:
        if not ticker or ticker == "선택하세요" or ticker == "" or ticker == "USD":
            continue
        ticker_str = str(ticker).replace('.0', '')
        if ticker_str.isdigit() and len(ticker_str) == 6:
            try:
                ticker_data = yf.Ticker(f"{ticker_str}.KS")
                hist = ticker_data.history(period="1d")
                if not hist.empty:
                    prices[ticker] = float(hist['Close'].iloc[-1])
                    continue
                
                ticker_data_kq = yf.Ticker(f"{ticker_str}.KQ")
                hist_kq = ticker_data_kq.history(period="1d")
                if not hist_kq.empty:
                    prices[ticker] = float(hist_kq['Close'].iloc[-1])
                    continue
                    
                prices[ticker] = None
            except:
                prices[ticker] = None
        else:
            try:
                ticker_data = yf.Ticker(ticker_str)
                hist = ticker_data.history(period="1d")
                if not hist.empty:
                    prices[ticker] = float(hist['Close'].iloc[-1])
                else:
                    prices[ticker] = None
            except:
                prices[ticker] = None
    return prices

@st.cache_data(ttl=3600)
def get_realtime_usdkrw():
    try:
        return float(yf.Ticker("USDKRW=X").history(period="1d")['Close'].iloc[-1])
    except:
        return 1350.0 

unique_tickers = df['Ticker'].dropna().unique().tolist() if not df.empty else []
current_price_dict = get_current_prices(unique_tickers)
realtime_ex_rate = get_realtime_usdkrw()

# 4. 사이드바: 스마트 입력 폼
with st.sidebar:
    st.markdown("### 🔄 시스템 동기화")
    if st.button("최신 DB 불러오기", use_container_width=True):
        st.cache_data.clear()
        st.rerun()
        
    st.markdown("---")
    st.header("➕ 신규 거래 기록")
    
    existing_names = df['Name'].dropna().unique().tolist() if not df.empty else []
    existing_tickers = df['Ticker'].dropna().unique().tolist() if not df.empty else []
    existing_categories = df['Category'].dropna().unique().tolist() if not df.empty else ["모멘텀", "배당", "커버드 콜", "채권"]

    date = st.date_input("날짜", datetime.now())
    account = st.selectbox("계좌", ["해외직투", "ISA", "국내일반"])
    is_overseas = (account == "해외직투")

    st.markdown("---")
    
    if is_overseas:
        trans_type = st.selectbox("거래유형", ["정기매수", "추가매수", "매도", "배당금입금", "환전", "절세재매수", "배당재투자", "달러수수료보정"])
    else:
        trans_type = st.selectbox("거래유형", ["정기매수", "추가매수", "매도", "배당금입금", "배당재투자"])

    if trans_type == "환전":
        st.info("💡 외화 환전: '달러 예수금(USD)' 잔고가 증가합니다.")
        name, ticker, category = "달러 예수금", "USD", "기타"
        price = 1.0
        qty = st.number_input("환전 금액 (USD)", min_value=0.0, step=None)
        fee = 0.0
        transaction_ex_rate = st.number_input("적용 환율 (₩/$)", min_value=800.0, value=float(round(realtime_ex_rate, 2)), step=1.0)
        note = st.text_input("비고", placeholder="원화 가액 등 기록")
        div_amount = 0.0
    elif trans_type == "달러수수료보정":
        st.info("💡 세금/수수료 단차로 인한 어플과의 달러 잔고 차이를 맞춥니다.")
        name, ticker, category = "달러 예수금", "USD", "기타"
        price = 1.0
        qty = st.number_input("보정 수량 (USD) ※ 차감은 음수(-), 추가는 양수(+) 기입", value=0.0, step=None, help="예: 잔고에서 6.40 달러를 빼야 한다면 -6.40 을 입력하세요.")
        fee = 0.0
        transaction_ex_rate = st.number_input("적용 환율 (₩/$)", min_value=800.0, value=float(round(realtime_ex_rate, 2)), step=1.0)
        note = st.text_input("비고", placeholder="예: 세전 배당금 단차 보정")
        div_amount = 0.0
    else:
        name_option = st.selectbox("종목명", ["선택하세요", "[신규 직접 입력]"] + existing_names)
        if name_option == "[신규 직접 입력]":
            name = st.text_input("종목명 입력")
            auto_ticker, auto_category = "", ""
        else:
            name = name_option if name_option != "선택하세요" else ""
            auto_ticker = dict(zip(df['Name'], df['Ticker'])).get(name, "")
            auto_category = dict(zip(df['Name'], df['Category'])).get(name, "")

        ticker_options = ["선택하세요", "[신규 직접 입력]"] + existing_tickers
        ticker_default_idx = ticker_options.index(auto_ticker) if auto_ticker in ticker_options else 0
        ticker = st.selectbox("티커", ticker_options, index=ticker_default_idx)
        if ticker == "[신규 직접 입력]": ticker = st.text_input("티커 입력")
        elif ticker == "선택하세요": ticker = ""

        category_options = ["선택하세요", "[신규 직접 입력]"] + [c for c in existing_categories if c not in ["선택하세요", "[신규 직접 입력]"]]
        category_default_idx = category_options.index(auto_category) if auto_category in category_options else 0
        category = st.selectbox("카테고리", category_options, index=category_default_idx)
        if category == "[신규 직접 입력]": category = st.text_input("카테고리 입력")
        elif category == "선택하세요": category = ""

        if trans_type == "배당금입금":
            unit = "USD" if is_overseas else "KRW"
            div_amount = st.number_input(f"배당 금액 ({unit})", min_value=0.0, step=None)
            price, qty, fee = 0.0, 0.0, 0.0
            transaction_ex_rate = st.number_input("당일 적용 환율 (₩/$)", min_value=800.0, value=float(round(realtime_ex_rate, 2)), step=1.0) if is_overseas else 1.0
            note = st.text_input("비고", value=f"{name} 배당 입금")
        else:
            if is_overseas:
                price = st.number_input("체결 단가 ($ USD)", min_value=0.0, step=None)
                fee = st.number_input("제비용 ($ USD)", min_value=0.0, step=None)
                transaction_ex_rate = st.number_input("당시 적용 환율 (₩/$)", min_value=800.0, value=float(round(realtime_ex_rate, 2)), step=1.0, help="해당 거래일의 환율을 기입하세요. 카테고리별 대략적 성과 분석에 사용됩니다.")
                note_prefix = "[USD] "
            else:
                price = st.number_input("체결 단가 (₩ KRW)", min_value=0.0, step=None)
                fee = 0.0
                transaction_ex_rate = 1.0
                note_prefix = ""
            
            qty = st.number_input("체결 수량 (양수 입력)", min_value=0.0, step=None)
            raw_note = st.text_input("비고", placeholder="임의 내용 작성")
            note = note_prefix + raw_note
            div_amount = 0.0

    st.markdown("---")

    if st.button("DB에 기록하기", type="primary"):
        if not ticker or (trans_type not in ["환전", "달러수수료보정"] and not name):
            st.error("필수 항목을 입력하세요.")
        elif trans_type == "배당금입금" and div_amount <= 0:
            st.error("배당 금액은 0보다 커야 합니다.")
        elif trans_type in ["환전", "정기매수", "추가매수", "매도", "절세재매수", "배당재투자"] and qty <= 0:
            st.error("수량(금액)은 0보다 커야 합니다.")
        elif trans_type == "달러수수료보정" and qty == 0:
            st.error("보정할 달러 수량을 0이 아닌 값으로 입력하세요. (차감 시 음수, 추가 시 양수)")
        else:
            rows_to_add = []
            
            if trans_type == "환전":
                rows_to_add.append({"Date": date.strftime("%Y-%m-%d"), "Account": account, "Name": name, "Ticker": ticker, "Category": category, "Type": trans_type, "Price": price, "Qty": qty, "Ex_Rate": transaction_ex_rate, "Note": note})
            elif trans_type == "달러수수료보정":
                rows_to_add.append({"Date": date.strftime("%Y-%m-%d"), "Account": account, "Name": name, "Ticker": ticker, "Category": category, "Type": trans_type, "Price": price, "Qty": qty, "Ex_Rate": transaction_ex_rate, "Note": note})
            elif trans_type == "배당금입금":
                rows_to_add.append({"Date": date.strftime("%Y-%m-%d"), "Account": account, "Name": name, "Ticker": ticker, "Category": category, "Type": trans_type, "Price": price, "Qty": qty, "Ex_Rate": transaction_ex_rate, "Note": note})
                if is_overseas:
                    rows_to_add.append({"Date": date.strftime("%Y-%m-%d"), "Account": account, "Name": "달러 예수금", "Ticker": "USD", "Category": "기타", "Type": "배당금입금", "Price": 1.0, "Qty": div_amount, "Ex_Rate": transaction_ex_rate, "Note": f"[{ticker}] 배당 연동"})
            else:
                final_qty = -qty if trans_type == "매도" else qty
                rows_to_add.append({"Date": date.strftime("%Y-%m-%d"), "Account": account, "Name": name, "Ticker": ticker, "Category": category, "Type": trans_type, "Price": price, "Qty": final_qty, "Ex_Rate": transaction_ex_rate, "Note": note})
                
                if is_overseas:
                    if trans_type in ["정기매수", "추가매수", "절세재매수", "배당재투자"]:
                        usd_qty = -(price * qty + fee)
                        usd_type = "매수결제"
                    elif trans_type == "매도":
                        usd_qty = (price * qty - fee)
                        usd_type = "매도입금"
                    else:
                        usd_qty = 0
                        usd_type = "기타"
                        
                    if usd_qty != 0:
                        rows_to_add.append({"Date": date.strftime("%Y-%m-%d"), "Account": account, "Name": "달러 예수금", "Ticker": "USD", "Category": "기타", "Type": usd_type, "Price": 1.0, "Qty": usd_qty, "Ex_Rate": transaction_ex_rate, "Note": f"[{ticker}] 거래 연동"})

            updated_df = pd.concat([df, pd.DataFrame(rows_to_add)], ignore_index=True)
            try:
                conn.update(spreadsheet=SPREADSHEET_URL, worksheet=SHEET_NAME, data=updated_df)
                st.success("✅ 거래 내역이 완벽히 기록되었습니다.")
                st.cache_data.clear()
                st.rerun()
            except Exception as e:
                st.error(f"❌ 저장 중 오류 발생: {e}")

# 5. 계산 엔진
st.title("🛡️ NEON SIGMA: Asset & Milestone Tracker v5.14")
st.caption("⚙️ **System Update:** NULL 렌더링 버그 픽스 및 Swift 로직 안정화 (Build 260529)")

st.info("⚠️ **[데이터 평가액 오차 안내]** yfinance API는 실시간 FX 환율 및 시간외 거래 시세를 반영하므로, 증권사 어플의 '고정 고시 환율' 및 '공식 종가'와는 필연적인 평가액 오차가 발생할 수 있습니다 (대략적 성과 및 마일스톤 지표로 활용).")

def calculate_eval_krw(row, ex_rate):
    api_price = current_price_dict.get(row['Ticker'])
    final_price = api_price if api_price is not None else float(row['Price'])
    if str(row['Account']).strip() == '해외직투':
        return final_price * float(row['Qty']) * ex_rate
    else:
        return final_price * float(row['Qty'])

def calculate_total_invested_krw(row):
    # 시스템 총 원금: 보정액 등은 무시하고 '환전'과 '국내 매수'만 합산
    if row['Type'] == "환전":
        return float(row['Price']) * float(row['Qty']) * float(row['Ex_Rate'])
    elif str(row['Account']).strip() != '해외직투' and row['Type'] in ["정기매수", "추가매수"]:
        return float(row['Price']) * float(row['Qty'])
    return 0.0

def calculate_category_invested_krw(row):
    if row['Type'] in ['정기매수', '추가매수', '매도', '절세재매수', '배당재투자'] and row['Ticker'] != 'USD':
        return float(row['Price']) * float(row['Qty']) * (float(row['Ex_Rate']) if str(row['Account']).strip() == '해외직투' else 1.0)
    return 0.0

if not df.empty:
    df['Eval_Value_KRW'] = df.apply(lambda x: calculate_eval_krw(x, realtime_ex_rate), axis=1)
    df['Total_Invested_KRW'] = df.apply(calculate_total_invested_krw, axis=1)
    df['Cat_Invested_KRW'] = df.apply(calculate_category_invested_krw, axis=1)

tabs = st.tabs(["📊 거래 내역 확인", "⚖️ 리밸런싱 가이드", "🚀 마일스톤 2031"])

ordered_categories = ["모멘텀", "배당", "커버드 콜", "채권", "기타"]
def cat_sort_key(c):
    return ordered_categories.index(c) if c in ordered_categories else 99

def format_korean_currency(amount):
    if amount == 0:
        return "0 원"
    eok = amount // 100000000
    man = (amount % 100000000) // 10000
    result = ""
    if eok > 0:
        result += f"{int(eok):,.0f}억 "
    if man > 0:
        result += f"{int(man):,.0f}만 "
    return result.strip() + " 원"

# --- [ 탭 1: 거래 내역 확인 ] ---
with tabs[0]:
    st.subheader("Database Confirm")
    st.info("💡 **데이터 기록 원칙:** 외화 자산 거래 시 환율을 정확히 기입해 주시면 카테고리별 성과가 정확해집니다.")
    if df.empty:
        st.info("현재 기록된 데이터가 없습니다. 사이드바에서 첫 데이터를 입력해 주세요.")
    else:
        display_cols = ["Date", "Account", "Name", "Ticker", "Category", "Type", "Price", "Qty", "Ex_Rate", "Note"]
        edited_df = st.data_editor(
            df[display_cols], 
            num_rows="dynamic", 
            use_container_width=True,
            column_config={
                "Ticker": st.column_config.TextColumn("Ticker", help="yfinance 연동을 위한 티커"),
                "Price": st.column_config.NumberColumn("Price"),
                "Qty": st.column_config.NumberColumn("Qty"),
                "Ex_Rate": st.column_config.NumberColumn("Ex_Rate", help="해당 거래 당시의 환율")
            }
        )
        if st.button("수정사항 저장하기"):
            try:
                conn.update(spreadsheet=SPREADSHEET_URL, worksheet=SHEET_NAME, data=edited_df)
                st.success("✅ 수정사항이 DB에 반영되었습니다.")
                st.cache_data.clear()
                st.rerun()
            except Exception as e:
                st.error(f"❌ 수정 실패: {e}")

# --- [ 탭 2: 리밸런싱 가이드 ] ---
with tabs[1]:
    if df.empty:
        st.warning("데이터가 부족하여 리밸런싱을 계산할 수 없습니다. 거래 내역을 먼저 등록해 주세요.")
    else:
        st.markdown("#### 🌍 실시간 시장 변수: Indexes")
        current_ex_rate_ui = st.number_input("실시간 시장 환율 (원/$)", min_value=800.0, value=float(round(realtime_ex_rate, 2)), step=1.0)
        
        df['Eval_Value_KRW_UI'] = df.apply(lambda x: calculate_eval_krw(x, current_ex_rate_ui), axis=1)
        st.markdown("---")

        standard_categories = ["모멘텀", "배당", "커버드 콜", "채권"]
        df['Sim_Category'] = df['Category'].apply(lambda x: x if str(x).strip() in standard_categories else "기타")

        total_eval_krw_ui = df['Eval_Value_KRW_UI'].sum()
        current_category_assets = df.groupby('Sim_Category')['Eval_Value_KRW_UI'].sum().to_dict()
        
        for cat in standard_categories + ["기타"]:
            if cat not in current_category_assets:
                current_category_assets[cat] = 0.0

        other_val_krw = current_category_assets["기타"]
        core_eval_krw = total_eval_krw_ui - other_val_krw

        cat_grouped = df.copy()
        cat_grouped['Effective_Price'] = cat_grouped.apply(lambda x: current_price_dict.get(x['Ticker']) if current_price_dict.get(x['Ticker']) is not None else float(x['Price']), axis=1)
        cat_summary = cat_grouped.groupby(['Sim_Category', 'Ticker', 'Account', 'Name']).agg(
            Eval_Sum=('Eval_Value_KRW_UI', 'sum'), Price_Unit=('Effective_Price', 'first')
        ).reset_index()

        st.markdown("#### 🎯 목표 비중: Target Matrix")
        change_others = st.toggle("기타 자산(달러 예수금 포함) 비중 변경", value=False)
        base_for_weights = total_eval_krw_ui if change_others else core_eval_krw

        default_weights = {"모멘텀": 0.0, "배당": 0.0, "커버드 콜": 0.0, "채권": 0.0, "기타": 0.0}
        if base_for_weights > 0:
            if change_others:
                for cat in default_weights.keys(): default_weights[cat] = round((current_category_assets[cat] / base_for_weights) * 100, 2)
                weight_sum = round(sum(default_weights.values()), 2)
                if weight_sum > 0 and weight_sum != 100.00:
                    largest_cat = max(default_weights, key=default_weights.get)
                    default_weights[largest_cat] = round(default_weights[largest_cat] + (100.00 - weight_sum), 2)
            else:
                for cat in standard_categories: default_weights[cat] = round((current_category_assets[cat] / base_for_weights) * 100, 2)
                weight_sum = round(sum([default_weights[cat] for cat in standard_categories]), 2)
                if weight_sum > 0 and weight_sum != 100.00:
                    largest_cat = max(standard_categories, key=lambda c: default_weights[c])
                    default_weights[largest_cat] = round(default_weights[largest_cat] + (100.00 - weight_sum), 2)

        cols = st.columns(5)
        target_weights = {
            "모멘텀": cols[0].number_input("모멘텀 (%)", value=float(default_weights["모멘텀"]), step=0.01, format="%.2f"),
            "배당": cols[1].number_input("배당 (%)", value=float(default_weights["배당"]), step=0.01, format="%.2f"),
            "커버드 콜": cols[2].number_input("커버드 콜 (%)", value=float(default_weights["커버드 콜"]), step=0.01, format="%.2f"),
            "채권": cols[3].number_input("채권 (%)", value=float(default_weights["채권"]), step=0.01, format="%.2f"),
            "기타": cols[4].number_input("기타 (%)", value=float(default_weights["기타"]) if change_others else 0.00, step=0.01, format="%.2f", disabled=not change_others)
        }
        
        total_target = sum(target_weights.values())
        if abs(total_target - 100.0) > 0.015: 
            st.error(f"⚠️ 목표 비중의 합이 100%가 아닙니다! (현재 {total_target:.2f}%)")
        else:
            st.markdown("---")
            
            # --- [v5.14] NEON-PULSE Swift Portfolio (Sell to Buy) ---
            st.markdown("#### ⚡ NEON-PULSE: Swift Portfolio Control")
            use_pulse = st.toggle("QLD 정산 Swift 포트폴리오 연계 모드 활성화", value=False)
            
            if use_pulse:
                st.markdown("""
                <div class='pulse-panel'>
                    <span style='color:#FF007F; font-weight:bold;'>[SYSTEM]</span> 공격적 스위칭(Sell to Buy) 모드 활성화. 초과 보유한 자산을 깎아내어(Trim) 현금을 확보한 뒤, 신규 투자금과 합산하여 우선순위에 따라 폭포수(Waterfall)처럼 채워 넣습니다.
                </div>
                """, unsafe_allow_html=True)
                
                p_col1, p_col2 = st.columns(2)
                with p_col1:
                    guidance_level = st.selectbox("Leverage Guidance 레벨 선택", [
                        "[FULL-THROTTLE] 레버리지 100%", "[STEADY-CRUISE] 상승주 70%, 레버리지 30%",
                        "[WAVE BOARDING] 상승주 80%, 레버리지 20%", "[HOLD & PAUSE] 상승주 100%",
                        "[AGILE SWITCH] 상승주 100% (레버리지 전량 매도)", "[SPRING-LOAD] 상승주 30%, 레버리지 70%"
                    ], index=1)
                    
                    momentum_tickers = df[df['Sim_Category'] == '모멘텀']['Ticker'].dropna().unique().tolist()
                    lev_tickers = st.multiselect("레버리지(QLD 등) 자산 티커 지정", momentum_tickers, default=[t for t in momentum_tickers if "QLD" in str(t)], help="모멘텀 카테고리 중 레버리지 비율을 적용받을 자산을 선택하세요.")

                with p_col2:
                    st.write("🎯 적립 우선순위 설정 (계단식)")
                    p_opts = ["모멘텀", "채권", "배당", "커버드 콜", "기타"]
                    p1 = st.selectbox("1순위 (최우선)", p_opts, index=0)
                    p2 = st.selectbox("2순위", [o for o in p_opts if o != p1], index=0)
                    p3 = st.selectbox("3순위", [o for o in p_opts if o not in [p1, p2]], index=0)
                    p4 = st.selectbox("4순위", [o for o in p_opts if o not in [p1, p2, p3]], index=0)
                    p5 = st.selectbox("5순위 (최하위)", [o for o in p_opts if o not in [p1, p2, p3, p4]], index=0)
                    priorities = [p1, p2, p3, p4, p5]
                
                st.markdown("<br>", unsafe_allow_html=True)
                
                if "[FULL-THROTTLE]" in guidance_level: up_ratio, lev_ratio = 0.0, 1.0
                elif "[STEADY-CRUISE]" in guidance_level: up_ratio, lev_ratio = 0.7, 0.3
                elif "[WAVE BOARDING]" in guidance_level: up_ratio, lev_ratio = 0.8, 0.2
                elif "[HOLD & PAUSE]" in guidance_level: up_ratio, lev_ratio = 1.0, 0.0
                elif "[AGILE SWITCH]" in guidance_level: up_ratio, lev_ratio = 1.0, 0.0
                elif "[SPRING-LOAD]" in guidance_level: up_ratio, lev_ratio = 0.3, 0.7
                else: up_ratio, lev_ratio = 0.7, 0.3

            st.markdown("#### 💰 자산 현황 및 신규 투자: Sigma Simulation")
            new_investment = st.number_input("이달의 신규 투입 자금 (₩)", min_value=0, value=2000000, step=100000, format="%d")
            
            simulated_total_asset = total_eval_krw_ui + new_investment
            st.markdown(f"**현재 총 평가 자산:** 약 {total_eval_krw_ui:,.0f} 원 &nbsp;&nbsp;➔&nbsp;&nbsp; **투자 후 예상 총 자산:** 약 <span class='neon-text'>{simulated_total_asset:,.0f}</span> 원", unsafe_allow_html=True)
            
            rebal_pool_krw = simulated_total_asset if change_others else (simulated_total_asset - other_val_krw)
            
            rebalance_data = []
            gap_dict = {}

            if use_pulse:
                mom_df = df[df['Sim_Category'] == '모멘텀']
                cur_mom_lev = mom_df[mom_df['Ticker'].isin(lev_tickers)]['Eval_Value_KRW_UI'].sum()
                cur_mom_up = current_category_assets.get('모멘텀', 0.0) - cur_mom_lev

            for category in ordered_categories:
                current_val = current_category_assets.get(category, 0.0)
                
                if category == "기타" and not change_others:
                    target_w_str = "-"
                    ideal_val = current_val
                    gap = 0.0
                else:
                    target_w = target_weights[category]
                    ideal_val = rebal_pool_krw * (target_w / 100.0)
                    gap = ideal_val - current_val
                    target_w_str = f"{target_w:.2f}%"
                
                gap_dict[category] = gap

                if use_pulse and category == "모멘텀":
                    rebalance_data.append({
                        "카테고리": "모멘텀 (상승주)", "목표 비중 (%)": f"{target_weights['모멘텀'] * up_ratio:.2f}%", 
                        "현재 평가액": f"{cur_mom_up:,.0f} 원", "이상적 평가액": f"{ideal_val * up_ratio:,.0f} 원", 
                        "필요한 조치": (ideal_val * up_ratio) - cur_mom_up
                    })
                    rebalance_data.append({
                        "카테고리": "모멘텀 (레버리지)", "목표 비중 (%)": f"{target_weights['모멘텀'] * lev_ratio:.2f}%", 
                        "현재 평가액": f"{cur_mom_lev:,.0f} 원", "이상적 평가액": f"{ideal_val * lev_ratio:,.0f} 원", 
                        "필요한 조치": (ideal_val * lev_ratio) - cur_mom_lev
                    })
                else:
                    rebalance_data.append({
                        "카테고리": category, "목표 비중 (%)": target_w_str,
                        "현재 평가액": f"{current_val:,.0f} 원", "이상적 평가액": f"{ideal_val:,.0f} 원",
                        "필요한 조치": gap
                    })
            
            rebalance_df = pd.DataFrame(rebalance_data)
            
            def format_action(row):
                g = row["필요한 조치"]
                cat = row["카테고리"]
                if cat == "기타" and not change_others: return "➖ 현상 유지 (리밸런싱 제외)"
                if use_pulse and "AGILE SWITCH" in guidance_level and "레버리지" in cat: return "🚨 레버리지 전량 매도 요망"
                if g > 0: return f"🟢 {g:,.0f} 원 매수 요망"
                else: return f"🔴 {-g:,.0f} 원 초과"
                    
            rebalance_df["필요한 조치"] = rebalance_df.apply(format_action, axis=1)
            st.dataframe(rebalance_df, hide_index=True, use_container_width=True)
            
            st.markdown("#### 📌 최종 행동 지침: Action Plan")
            
            if new_investment == 0 and not use_pulse:
                st.caption("신규 투자 금액을 입력하면 구체적인 Action Plan이 도출됩니다.")
            elif not use_pulse:
                buy_instructions = []
                for category in ordered_categories:
                    if gap_dict[category] > 0 and (category != "기타" or change_others):
                        buy_instructions.append(f"✅ **[{category}]** 약 **{gap_dict[category]:,.0f} 원** 매수 요망")
                if not buy_instructions: st.success("현재 시스템 내 밸런스가 최적 상태입니다. 추가 매수가 필요하지 않습니다.")
                else: 
                    for inst in buy_instructions: st.write(inst)
            else:
                # [v5.14 Waterfall Engine with Sell-to-Buy]
                st.info("💡 **Swift Rebalancing (Sell to Buy):** 초과된 자산을 깎아내어(Trim) 확보한 현금과 신규 투자금을 합산해, 설정한 우선순위에 따라 순차적으로 채워 넣습니다.")
                if "[AGILE SWITCH]" in guidance_level:
                    st.error("🚨 **[긴급 시그널] AGILE SWITCH 발동:** 보유 중인 레버리지 자산을 전량 매도하여 현금을 확보하십시오.")
                
                sell_instructions = []
                total_proceeds = 0.0
                
                m_ideal = rebal_pool_krw * (target_weights["모멘텀"] / 100.0)
                gap_up = (m_ideal * up_ratio) - cur_mom_up
                gap_lev = -cur_mom_lev if "[AGILE SWITCH]" in guidance_level else (m_ideal * lev_ratio) - cur_mom_lev
                
                # Phase 1: Surplus Calculation (Sell)
                if gap_up < 0:
                    sell_instructions.append(f"🔴 **[모멘텀 상승주]** 목표 초과. 약 **{-gap_up:,.0f} 원** 매도 요망")
                    total_proceeds += -gap_up
                if gap_lev < 0:
                    sell_instructions.append(f"🔴 **[모멘텀 레버리지]** 목표 초과. 약 **{-gap_lev:,.0f} 원** 매도 요망")
                    total_proceeds += -gap_lev
                    
                for cat in ordered_categories:
                    if cat == "모멘텀": continue
                    if cat == "기타" and not change_others: continue
                    g = gap_dict.get(cat, 0)
                    if g < 0:
                        sell_instructions.append(f"🔴 **[{cat}]** 목표 초과. 약 **{-g:,.0f} 원** 매도 요망")
                        total_proceeds += -g
                
                st.write("##### 🔄 [Phase 1] 자산 매도 및 현금 확보 (Trim)")
                if not sell_instructions: st.write("⚪ 초과된 자산이 없어 매도 지침이 없습니다.")
                else:
                    for inst in sell_instructions: st.write(inst)
                    st.write(f"👉 **확보 예상 현금:** **{total_proceeds:,.0f} 원**")

                # Phase 2: Waterfall Allocation (Buy)
                rem_cash = new_investment + total_proceeds
                st.write("##### 🌊 [Phase 2] 폭포수 매수 배정 (Waterfall Allocation)")
                st.write(f"👉 **총 가용 자금 (신규 투자금 + 매도 대금):** **{rem_cash:,.0f} 원**")
                
                buy_instructions_pulse = []
                for prio in priorities:
                    if prio == "모멘텀":
                        for sub_name, sub_gap in [("모멘텀 상승주", gap_up), ("모멘텀 레버리지", gap_lev)]:
                            if sub_gap > 0:
                                alloc = min(rem_cash, sub_gap)
                                if alloc > 0:
                                    buy_instructions_pulse.append(f"🟢 **[1순위-{sub_name}]** **{alloc:,.0f} 원** 매수 배정")
                                    rem_cash -= alloc
                                else: buy_instructions_pulse.append(f"⚪ **[{sub_name}]** 자금 부족으로 매수 생략 (필요: {sub_gap:,.0f}원)")
                    elif prio != "기타" or change_others:
                        g_val = gap_dict.get(prio, 0)
                        if g_val > 0:
                            alloc = min(rem_cash, g_val)
                            if alloc > 0:
                                buy_instructions_pulse.append(f"✅ **[{prio}]** **{alloc:,.0f} 원** 매수 배정")
                                rem_cash -= alloc
                            else: buy_instructions_pulse.append(f"⚪ **[{prio}]** 자금 부족으로 매수 생략 (필요: {g_val:,.0f}원)")
                
                # [v5.14 버그 수정] 리스트 컴프리헨션(List Comprehension) 대신 for 반복문 사용
                if not buy_instructions_pulse: 
                    st.write("⚪ 부족한 자산이 없어 매수 지침이 없습니다.")
                else: 
                    for b in buy_instructions_pulse: 
                        st.write(b)
                
                if rem_cash > 0:
                    st.success(f"🎉 **모든 목표 비중 달성!** 남은 자금 **{rem_cash:,.0f} 원**은 예수금으로 보유하거나 임의 투자하십시오.")

# --- [ 탭 3: 마일스톤 2031 ] ---
with tabs[2]:
    if df.empty:
        st.warning("데이터가 부족합니다. 거래 내역을 등록해 주세요.")
    else:
        stock_eval_krw = df[df['Ticker'] != 'USD']['Eval_Value_KRW'].sum()
        cash_eval_krw = df[df['Ticker'] == 'USD']['Eval_Value_KRW'].sum()
        cash_usd_qty = df[df['Ticker'] == 'USD']['Qty'].sum()
        total_eval_krw = stock_eval_krw + cash_eval_krw
        
        total_invested_krw = df['Total_Invested_KRW'].sum()
        total_return_pct = ((total_eval_krw / total_invested_krw) - 1) * 100 if total_invested_krw > 0 else 0.0

        col_top_left, col_top_mid, col_top_right = st.columns(3)
        
        with col_top_left:
            st.markdown(f"""
            <div class="neon-card" style="margin-bottom: 20px;">
                <p class="neon-title">총 투입 원금</p>
                <p class="neon-value">₩ {total_invested_krw:,.0f}</p>
            </div>
            """, unsafe_allow_html=True)
            
        with col_top_mid:
            st.markdown(f"""
            <div class="neon-card" style="margin-bottom: 20px;">
                <p class="neon-title" style="color: #FFD700;">보유 주식 평가액 (달러 예수금 제외)</p>
                <p class="neon-value">₩ {stock_eval_krw:,.0f}</p>
            </div>
            """, unsafe_allow_html=True)
            
        with col_top_right:
            delta_color = "#FF007F" if total_return_pct < 0 else "#39FF14"
            delta_sign = "+" if total_return_pct > 0 else ""
            st.markdown(f"""
            <div class="neon-card">
                <p class="neon-title">총 자산 (주식 + 달러 예수금)</p>
                <p class="neon-value" style="font-size: 1.8rem;">
                    ₩ {total_eval_krw:,.0f} 
                    <span style="font-size: 1.2rem; color: {delta_color}; margin-left: 5px; text-shadow: 0 0 5px rgba(57, 255, 20, 0.4);">
                        ({delta_sign}{total_return_pct:.2f}%)
                    </span>
                </p>
                <p style="margin-top: 8px; font-size: 0.9rem; color: #8892B0;">💵 달러 예수금: <strong style="color:#00FFCC;">{cash_usd_qty:,.2f} USD</strong></p>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("---")

        st.markdown("##### 📊 ETF 카테고리별 대략적 성과")
        
        df_etf = df[df['Category'] != '기타']
        
        if not df_etf.empty:
            cat_perf = df_etf.groupby('Category').agg(
                Invested=('Cat_Invested_KRW', 'sum'),
                Eval=('Eval_Value_KRW', 'sum')
            ).reset_index()
            
            cat_perf['SortKey'] = cat_perf['Category'].apply(cat_sort_key)
            cat_perf = cat_perf.sort_values(['SortKey', 'Category']).drop(columns=['SortKey'])
            
            cat_perf['Return_Pct'] = ((cat_perf['Eval'] / cat_perf['Invested']) - 1) * 100
            cat_perf.fillna(0, inplace=True)
            
            cat_perf_table = cat_perf.copy()
            cat_perf_table['Invested'] = cat_perf_table['Invested'].apply(lambda x: f"₩ {x:,.0f}")
            cat_perf_table['Eval'] = cat_perf_table['Eval'].apply(lambda x: f"₩ {x:,.0f}")
            cat_perf_table['Return_Pct'] = cat_perf_table['Return_Pct'].apply(lambda x: f"{x:+.2f} %")
            cat_perf_table.columns = ['카테고리', '투입 원금', '현재 평가액', '수익률']
            
            st.dataframe(cat_perf_table, hide_index=True, use_container_width=True)
        else:
            st.info("표시할 ETF 자산 내역이 없습니다.")

        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("##### 📝 전체 카테고리별 거래 로그 (기타 자산 포함)")
        sorted_categories = sorted(df['Category'].unique(), key=cat_sort_key)
        
        for cat in sorted_categories:
            cat_data = df[df['Category'] == cat]
            with st.expander(f"📁 {cat} 내역 보기"):
                counts = cat_data['Type'].value_counts().to_dict()
                summary_text = " / ".join([f"{k}: {v}회" for k, v in counts.items()])
                
                st.markdown(f"**총 거래 요약:**<br><span style='color:gray'>{summary_text}</span>", unsafe_allow_html=True)
                st.dataframe(cat_data[['Date', 'Account', 'Name', 'Ticker', 'Type', 'Price', 'Qty', 'Ex_Rate', 'Note']], hide_index=True)

        st.markdown("---")
        
        st.subheader("🎯 주택자금 조달 계획 (2031년 2월 목표)")
        
        remaining_months = 57 
        st.info(f"⏳ **목표 시점까지 남은 기간:** {remaining_months}개월")
        
        st.markdown("##### 💰 성실한 투자")
        monthly_savings = st.number_input("매월 신규 저축액 (₩)", min_value=0, value=2500000, step=100000)
        
        st.markdown("##### 🌱 복리 증식 시뮬레이터")
        extend_milestone = st.toggle("마일스톤 연장 (현재 시스템 수익률 기준 반영)", value=False)
        
        if extend_milestone:
            assumed_annual_rate = total_return_pct if total_return_pct > 0 else 5.0
            annual_rate = st.number_input("예상 연평균 수익률 (%)", value=float(f"{assumed_annual_rate:.2f}"), disabled=True)
            st.warning(f"⚠️ **수익률 환산 주의:** 현재 포트폴리오의 단순 누적 수익률인 **{assumed_annual_rate:.2f}%**를 연평균 수익률로 강제 연장합니다. 투자 기간이 1년 미만인 경우, 단기 수익을 연 단위로 가정하는 것은 통계적 과대평가를 유발할 수 있습니다.")
        else:
            annual_rate = st.number_input("예상 연평균 수익률 (%)", value=7.0, step=0.1)
            st.caption(f"※ 참고: 현재 포트폴리오의 단순 누적 수익률은 {total_return_pct:.2f}% 입니다.")
                
        r_monthly = (annual_rate / 100) / 12
        n_months = remaining_months
        
        if r_monthly > 0:
            fv_current_assets = total_eval_krw * ((1 + r_monthly) ** n_months)
            fv_future_savings = monthly_savings * (((1 + r_monthly) ** n_months - 1) / r_monthly)
        else:
            fv_current_assets = total_eval_krw
            fv_future_savings = monthly_savings * n_months
            
        expected_total_asset_2031 = fv_current_assets + fv_future_savings
        
        st.markdown(f"**👉 2031년 2월 예상 총 자산:** 약 <span class='neon-text'>{expected_total_asset_2031:,.0f}</span> 원", unsafe_allow_html=True)
        
        st.markdown("---")
        
        company_loan = 50000000
        company_loan_rate = 2.0
        
        st.markdown("##### 🏢 고정 자금")
        st.info(f"💡 **지원 한도 (회사 주택자금 대출):** {company_loan:,.0f} 원 &nbsp;&nbsp;|&nbsp;&nbsp; **연 금리:** {company_loan_rate:.1f}% 고정")
        
        st.markdown("##### 🏦 변동 자금")
        col_g1, col_g2, col_g3 = st.columns(3)
        with col_g1:
            apt_price_m = st.number_input("예상 아파트 가액 (백만 원)", min_value=0, value=1150, step=10)
            apt_price = apt_price_m * 1000000
        with col_g2:
            jeonse_price_m = st.number_input("예상 전세 가액 (백만 원) - 실거주 시 0", min_value=0, value=0, step=10)
            jeonse_price = jeonse_price_m * 1000000
        with col_g3:
            mortgage_rate = st.number_input("예상 주담대 금리 (%)", min_value=0.0, value=4.0, step=0.1)
            
        st.markdown("##### ⚖️ 필요 자금 분석")
        
        apt_kr = format_korean_currency(apt_price)
        jeonse_kr = format_korean_currency(jeonse_price)
        st.write(f"👉 **설정 가액:** 아파트 **{apt_kr}** &nbsp;|&nbsp; 전세 **{jeonse_kr}**")
        
        required_mortgage = apt_price - jeonse_price - expected_total_asset_2031 - company_loan
        
        if required_mortgage <= 0:
            st.success("🎉 **목표 초과 달성!** 주택담보대출 없이 아파트 취득 및 입주가 가능합니다.")
            ltv = 0.0
            required_mortgage = 0
            monthly_mortgage_interest = 0
        else:
            ltv = (required_mortgage / apt_price) * 100
            st.warning(f"🏦 **필요 주택담보대출(LTV {ltv:.1f}%):** 약 **{required_mortgage:,.0f}** 원")
            monthly_mortgage_interest = required_mortgage * (mortgage_rate / 100) / 12
            
        monthly_company_interest = company_loan * (company_loan_rate / 100) / 12
        total_monthly_interest = monthly_mortgage_interest + monthly_company_interest
        
        st.markdown("##### 💸 2031년 3월 예상 월 이자 부담액")
        
        st.info(f"**약 {total_monthly_interest:,.0f} 원** &nbsp;&nbsp;(내역: 회사 대출 이자 {monthly_company_interest:,.0f}원 + 주담대 이자 {monthly_mortgage_interest:,.0f}원)")
        
        if total_monthly_interest > (monthly_savings * 0.7):
            st.error("🚨 **Cash Flow 경고:** 월 이자 부담액이 현재 저축 가능액의 70%를 초과하여 생활 자금 압박이 예상됩니다. '성실한 투자' 변수를 높이거나 전세를 껴서 LTV를 낮추는 전략을 고려해 보세요.")
        elif total_monthly_interest > 0:
            st.success("✅ **Cash Flow 안정권:** 이자 부담액이 관리 가능한 범위 내에 있습니다.")
