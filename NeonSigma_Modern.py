import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import yfinance as yf
from datetime import datetime
import plotly.express as px

# 0. 인증 정보 로드 확인
if "connections" not in st.secrets:
    st.error("❌ '.streamlit/secrets.toml' 파일을 찾을 수 없거나 형식이 잘못되었습니다.")
    st.stop()

# 1. 페이지 설정
st.set_page_config(page_title="NEON SIGMA: Asset & Milestone Tracker v3.4", layout="wide")

# --- [NEON PULSE] 커스텀 사이버펑크 CSS ---
st.markdown("""
<style>
    .neon-text {
        color: #00FFCC !important;
        font-weight: bold;
    }
    .neon-card {
        padding: 20px; 
        border-radius: 8px; 
        border: 1px solid rgba(0, 255, 204, 0.4); 
        background-color: rgba(0, 255, 204, 0.02); 
        box-shadow: 0 0 15px rgba(0, 255, 204, 0.1);
        transition: all 0.3s ease;
    }
    .neon-card:hover {
        box-shadow: 0 0 25px rgba(0, 255, 204, 0.25);
        border: 1px solid rgba(0, 255, 204, 0.8); 
    }
    .neon-title {
        margin: 0; 
        font-size: 1.1rem; 
        color: #8892B0; 
        font-weight: bold; /* 작은 제목도 볼드 처리 */
        /* font-family 삭제하여 Streamlit 기본 폰트와 완벽 동기화 */
    }
    .neon-value {
        margin: 0; 
        font-size: 2.2rem; 
        font-weight: bold; /* 800 오류 수정, 확실한 볼드 적용 */
        color: #E6F1FF;
        letter-spacing: -0.5px;
    }
</style>
""", unsafe_allow_html=True)

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
            return pd.DataFrame(columns=["Date", "Account", "Name", "Ticker", "Category", "Type", "Price", "Qty", "Note"])
        
        text_columns = ["Account", "Name", "Ticker", "Category", "Type", "Note"]
        for col in text_columns:
            if col in df.columns:
                df[col] = df[col].astype(str).str.strip().replace('nan', '')
        
        df['Price'] = pd.to_numeric(df['Price'], errors='coerce').fillna(0.0)
        df['Qty'] = pd.to_numeric(df['Qty'], errors='coerce').fillna(0.0)
                
        return df
    except Exception as e:
        st.error(f"⚠️ 시트를 불러오는 중 오류가 발생했습니다: {e}")
        return pd.DataFrame(columns=["Date", "Account", "Name", "Ticker", "Category", "Type", "Price", "Qty", "Note"])

df = load_data()

# --- yfinance 실시간 현재가 불러오기 ---
@st.cache_data(ttl=300)
def get_current_prices(tickers):
    prices = {}
    for ticker in tickers:
        if not ticker or ticker == "선택하세요" or ticker == "":
            continue
            
        ticker_str = str(ticker).replace('.0', '')
        formatted_ticker = f"{ticker_str}.KS" if ticker_str.isdigit() and len(ticker_str) == 6 else ticker_str
        
        try:
            ticker_data = yf.Ticker(formatted_ticker)
            hist = ticker_data.history(period="1d")
            if not hist.empty:
                prices[ticker] = float(hist['Close'].iloc[-1])
            else:
                prices[ticker] = None
        except:
            prices[ticker] = None
    return prices

unique_tickers = df['Ticker'].dropna().unique().tolist() if not df.empty else []
current_price_dict = get_current_prices(unique_tickers)

# 4. 사이드바: 스마트 입력 폼 및 동기화
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

    name_option = st.selectbox("종목명", ["선택하세요", "[신규 종목 직접 입력]"] + existing_names)
    if name_option == "[신규 종목 직접 입력]":
        name = st.text_input("새로운 종목명 입력", placeholder="예: Invesco QQQ")
        auto_ticker = ""
        auto_category = ""
    else:
        name = name_option if name_option != "선택하세요" else ""
        auto_ticker = dict(zip(df['Name'], df['Ticker'])).get(name, "")
        auto_category = dict(zip(df['Name'], df['Category'])).get(name, "")

    ticker_options = ["선택하세요", "[신규 티커 직접 입력]"] + existing_tickers
    ticker_default_idx = ticker_options.index(auto_ticker) if auto_ticker in ticker_options else 0
    ticker_option = st.selectbox("티커", ticker_options, index=ticker_default_idx)
    if ticker_option == "[신규 티커 직접 입력]":
        ticker = st.text_input("새로운 티커 입력", placeholder="예: QQQ / 409820")
    else:
        ticker = ticker_option if ticker_option != "선택하세요" else ""

    category_options = ["선택하세요", "[신규 카테고리 입력]"] + [c for c in existing_categories if c not in ["선택하세요", "[신규 카테고리 입력]"]]
    category_default_idx = category_options.index(auto_category) if auto_category in category_options else 0
    category_option = st.selectbox("카테고리", category_options, index=category_default_idx)
    if category_option == "[신규 카테고리 입력]":
        category = st.text_input("새로운 카테고리 입력")
    else:
        category = category_option if category_option != "선택하세요" else ""

    trans_type = st.selectbox("거래유형", ["정기매수", "추가매수", "절세재매수", "배당재투자"])

    st.markdown("---")

    if is_overseas:
        price = st.number_input("단가 ($ USD)", min_value=0.0, step=None)
        note_prefix = "[USD] "
    else:
        price = st.number_input("단가 (₩ KRW)", min_value=0.0, step=None)
        note_prefix = ""

    qty = st.number_input("수량", min_value=0.0, step=None)
    raw_note = st.text_input("비고", placeholder="임의 내용 작성")
    note = note_prefix + raw_note
    
    st.markdown("---")

    if st.button("DB에 기록하기", type="primary"):
        if not name or name == "선택하세요":
            st.error("종목명을 입력/선택해 주세요.")
        elif not ticker or ticker == "선택하세요":
            st.error("티커를 입력/선택해 주세요.")
        elif not category or category == "선택하세요":
            st.error("카테고리를 입력/선택해 주세요.")
        elif qty <= 0:
            st.error("수량은 0보다 커야 합니다.")
        else:
            new_row = {
                "Date": date.strftime("%Y-%m-%d"),
                "Account": account,
                "Name": name,
                "Ticker": ticker,
                "Category": category,
                "Type": trans_type,
                "Price": price,
                "Qty": qty,
                "Note": note
            }
            updated_df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
            try:
                conn.update(spreadsheet=SPREADSHEET_URL, worksheet=SHEET_NAME, data=updated_df)
                st.success("✅ 거래 내역이 기록되었습니다.")
                st.cache_data.clear()
                st.rerun()
            except Exception as e:
                st.error(f"❌ 저장 중 오류 발생: {e}")

# 5. 메인 화면
st.title("🛡️ NEON SIGMA: Asset & Milestone Tracker v3.4")
st.caption("⚙️ **System Update:** 메트릭 카드 폰트 상속화 및 볼드체(Font-Weight) 렌더링 버그 수정 완료 (Build 260511)")

tabs = st.tabs(["📊 거래 내역 확인", "⚖️ 리밸런싱 가이드", "🚀 마일스톤 2031"])

# --- 전역 변수 사전 계산 ---
current_ex_rate_global = 1350.0 

def calculate_eval_krw(row, ex_rate):
    api_price = current_price_dict.get(row['Ticker'])
    final_price = api_price if api_price is not None else float(row['Price'])
    if str(row['Account']).strip() == '해외직투':
        return final_price * float(row['Qty']) * ex_rate
    else:
        return final_price * float(row['Qty'])

def calculate_invested_krw(row, ex_rate):
    if str(row['Account']).strip() == '해외직투':
        return float(row['Price']) * float(row['Qty']) * ex_rate
    else:
        return float(row['Price']) * float(row['Qty'])

if not df.empty:
    df['Eval_Value_KRW'] = df.apply(lambda x: calculate_eval_krw(x, current_ex_rate_global), axis=1)
    df['Invested_KRW'] = df.apply(lambda x: calculate_invested_krw(x, current_ex_rate_global), axis=1)

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
    if df.empty:
        st.info("현재 기록된 데이터가 없습니다. 사이드바에서 첫 데이터를 입력해 주세요.")
    else:
        display_cols = ["Date", "Account", "Name", "Ticker", "Category", "Type", "Price", "Qty", "Note"]
        edited_df = st.data_editor(
            df[display_cols], 
            num_rows="dynamic", 
            use_container_width=True,
            column_config={
                "Ticker": st.column_config.TextColumn("Ticker", help="yfinance 연동을 위한 티커"),
                "Price": st.column_config.NumberColumn("Price"),
                "Qty": st.column_config.NumberColumn("Qty")
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
        current_ex_rate_ui = st.number_input("실시간 시장 환율 (원/$)", min_value=800.0, value=1350.0, step=1.0)
        
        df['Eval_Value_KRW'] = df.apply(lambda x: calculate_eval_krw(x, current_ex_rate_ui), axis=1)
        st.markdown("---")

        standard_categories = ["모멘텀", "배당", "커버드 콜", "채권"]
        df['Sim_Category'] = df['Category'].apply(lambda x: x if str(x).strip() in standard_categories else "기타")

        total_eval_krw = df['Eval_Value_KRW'].sum()
        current_category_assets = df.groupby('Sim_Category')['Eval_Value_KRW'].sum().to_dict()
        
        for cat in standard_categories + ["기타"]:
            if cat not in current_category_assets:
                current_category_assets[cat] = 0.0

        other_val_krw = current_category_assets["기타"]

        cat_grouped = df.copy()
        cat_grouped['Effective_Price'] = cat_grouped.apply(lambda x: current_price_dict.get(x['Ticker']) if current_price_dict.get(x['Ticker']) is not None else float(x['Price']), axis=1)
        
        cat_summary = cat_grouped.groupby(['Sim_Category', 'Ticker', 'Account', 'Name']).agg(
            Eval_Sum=('Eval_Value_KRW', 'sum'),
            Price_Unit=('Effective_Price', 'first')
        ).reset_index()

        st.markdown("#### 🎯 목표 비중: Target Matrix")
        change_others = st.toggle("기타 자산 비중 변경 (선택 시 기타 항목도 리밸런싱 모수에 포함됩니다)", value=False)
        
        core_eval_krw = total_eval_krw - other_val_krw
        base_for_weights = total_eval_krw if change_others else core_eval_krw

        default_weights = {"모멘텀": 0.0, "배당": 0.0, "커버드 콜": 0.0, "채권": 0.0, "기타": 0.0}
        
        if base_for_weights > 0:
            if change_others:
                for cat in default_weights.keys():
                    default_weights[cat] = round((current_category_assets[cat] / base_for_weights) * 100, 2)
                weight_sum = round(sum(default_weights.values()), 2)
                if weight_sum > 0 and weight_sum != 100.00:
                    largest_cat = max(default_weights, key=default_weights.get)
                    default_weights[largest_cat] = round(default_weights[largest_cat] + (100.00 - weight_sum), 2)
            else:
                for cat in standard_categories:
                    default_weights[cat] = round((current_category_assets[cat] / base_for_weights) * 100, 2)
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
            
            st.markdown("#### 💰 자산 현황 및 신규 투자: Sigma Simulation")
            new_investment = st.number_input("이달의 신규 투입 자금 (₩)", min_value=0, value=2000000, step=100000, format="%d")
            
            simulated_total_asset = total_eval_krw + new_investment
            st.markdown(f"**현재 총 평가 자산:** 약 {total_eval_krw:,.0f} 원 &nbsp;&nbsp;➔&nbsp;&nbsp; **투자 후 예상 총 자산:** 약 <span class='neon-text'>{simulated_total_asset:,.0f}</span> 원", unsafe_allow_html=True)
            
            rebal_pool_krw = simulated_total_asset if change_others else (simulated_total_asset - other_val_krw)
            
            rebalance_data = []
            buy_instructions = []
            
            for category in ordered_categories:
                current_val = current_category_assets.get(category, 0.0)
                
                if category == "기타" and not change_others:
                    target_w_str = "-"
                    current_w_str = "-"
                    ideal_val = current_val
                    gap = 0.0
                else:
                    target_w = target_weights[category]
                    current_w = (current_val / base_for_weights * 100) if base_for_weights > 0 else 0.0
                    ideal_val = rebal_pool_krw * (target_w / 100.0)
                    gap = ideal_val - current_val
                    target_w_str = f"{target_w:.2f}%"
                    current_w_str = f"{current_w:.2f}%"
                    
                rebalance_data.append({
                    "카테고리": category,
                    "목표 비중 (%)": target_w_str,
                    "현재 비중 (%)": current_w_str,
                    "현재 평가액": f"{current_val:,.0f} 원",
                    "이상적 평가액": f"{ideal_val:,.0f} 원",
                    "필요한 조치": gap
                })
                
                if gap > 0:
                    cat_summary_df = cat_summary[cat_summary['Sim_Category'] == category]
                    if not cat_summary_df.empty:
                        max_row = cat_summary_df.loc[cat_summary_df['Eval_Sum'].idxmax()]
                        top_ticker = max_row['Ticker']
                        top_name = max_row['Name']
                        top_account = str(max_row['Account']).strip()
                        display_asset = top_ticker if top_account == '해외직투' else top_name
                        
                        top_price_krw = float(max_row['Price_Unit']) * current_ex_rate_ui if top_account == '해외직투' else float(max_row['Price_Unit'])
                        
                        if top_price_krw > 0:
                            est_shares = gap / top_price_krw
                            share_text = f" (대표 종목 **{display_asset}** 기준 약 **{est_shares:.2f} 주**)"
                        else:
                            share_text = ""
                    else:
                        share_text = " (보유 종목 없음 - 신규 종목 발굴)"

                    if category != "기타":
                        buy_instructions.append(f"✅ **[{category}]** 약 **{gap:,.0f} 원** 매수 요망 {share_text}")
                    elif category == "기타" and change_others:
                        buy_instructions.append(f"💡 **[기타 자산]** 약 **{gap:,.0f} 원** 추가 투자 고려 {share_text}")

            rebalance_df = pd.DataFrame(rebalance_data)
            
            def format_action(row):
                gap = row["필요한 조치"]
                cat = row["카테고리"]
                if cat == "기타" and not change_others:
                    return "➖ 현상 유지 (리밸런싱 제외)"
                if gap > 0:
                    return f"🟢 {gap:,.0f} 원 매수 요망"
                else:
                    return f"🔴 {-gap:,.0f} 원 초과"
                    
            rebalance_df["필요한 조치"] = rebalance_df.apply(format_action, axis=1)
            st.dataframe(rebalance_df, hide_index=True, use_container_width=True)
            
            st.markdown("#### 📌 최종 행동 지침: Action Plan")
            st.info("💡 **거래 수수료 등 오차:** 이상적 평가액 전부 매수시 소량의 미수금 발생 가능")
            
            if new_investment == 0:
                st.caption("신규 투자 금액을 입력하면 구체적인 Action Plan이 도출됩니다.")
            elif not buy_instructions:
                st.success("현재 시스템 내 밸런스가 최적 상태입니다. 추가 매수가 필요하지 않습니다.")
            else:
                for inst in buy_instructions:
                    st.write(inst)

# --- [ 탭 3: 마일스톤 2031 ] ---
with tabs[2]:
    if df.empty:
        st.warning("데이터가 부족합니다. 거래 내역을 등록해 주세요.")
    else:
        current_ex_rate_milestone = current_ex_rate_ui if 'current_ex_rate_ui' in locals() else 1350.0
        
        df['Eval_Value_KRW'] = df.apply(lambda x: calculate_eval_krw(x, current_ex_rate_milestone), axis=1)
        df['Invested_KRW'] = df.apply(lambda x: calculate_invested_krw(x, current_ex_rate_milestone), axis=1)

        total_invested_krw = df['Invested_KRW'].sum()
        total_eval_krw = df['Eval_Value_KRW'].sum()
        total_return_pct = ((total_eval_krw / total_invested_krw) - 1) * 100 if total_invested_krw > 0 else 0.0

        col_top_left, col_top_right = st.columns([1, 2])
        
        with col_top_left:
            st.markdown("##### 📈 총 자산 수익률 모니터링")
            st.markdown(f"""
            <div class="neon-card" style="margin-bottom: 20px;">
                <p class="neon-title">총 투입 원금</p>
                <p class="neon-value">₩ {total_invested_krw:,.0f}</p>
            </div>
            """, unsafe_allow_html=True)
            
            delta_color = "#FF007F" if total_return_pct < 0 else "#39FF14"
            delta_sign = "+" if total_return_pct > 0 else ""
            st.markdown(f"""
            <div class="neon-card">
                <p class="neon-title">현재 평가 자산</p>
                <p class="neon-value" style="font-size: 1.8rem;">
                    ₩ {total_eval_krw:,.0f} 
                    <span style="font-size: 1.2rem; color: {delta_color}; margin-left: 5px; text-shadow: 0 0 5px rgba(57, 255, 20, 0.4);">
                        ({delta_sign}{total_return_pct:.2f}%)
                    </span>
                </p>
            </div>
            """, unsafe_allow_html=True)
            
        with col_top_right:
            st.markdown("##### 📉 월별 신규 투입 자산 트렌드 (최근 12개월)")
            
            current_date_mock = datetime(2026, 5, 1)
            df['Date_dt'] = pd.to_datetime(df['Date'], errors='coerce')
            df_trend = df.copy()
            
            last_12_months = pd.period_range(start=current_date_mock - pd.DateOffset(months=11), end=current_date_mock, freq='M')
            month_labels = last_12_months.strftime('%Y년 %m월').tolist()
            
            df_trend['Month_str'] = df_trend['Date_dt'].dt.strftime('%Y년 %m월')
            recent_df = df_trend[df_trend['Month_str'].isin(month_labels)]
            
            monthly_invest = recent_df.groupby('Month_str')['Invested_KRW'].sum().reset_index()
            trend_df = pd.DataFrame({'Month': month_labels})
            trend_df = trend_df.merge(monthly_invest, left_on='Month', right_on='Month_str', how='left').fillna(0)
            
            trend_df['Invested_Man'] = trend_df['Invested_KRW'] / 10000
            trend_df['Invested_Man_Text'] = trend_df['Invested_Man'].apply(lambda x: f"{x:,.0f}" if x > 0 else "")
            
            fig_bar = px.bar(trend_df, x='Month', y='Invested_Man', text='Invested_Man_Text')
            fig_bar.update_layout(
                template="plotly_dark",
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
                xaxis_title=None,
                yaxis_title=None,
                height=320,
                margin=dict(l=0, r=0, t=10, b=0),
                yaxis=dict(ticksuffix="만", showgrid=False),
                xaxis=dict(tickangle=-45, showgrid=False)
            )
            fig_bar.update_traces(
                textposition='outside',
                marker_color='#00FFCC',
                hovertemplate='%{x}<br>투입 금액: %{y:,.0f}만 원<extra></extra>'
            )
            st.plotly_chart(fig_bar, use_container_width=True)

        st.markdown("---")

        st.markdown("##### 📊 카테고리별 성과")
        cat_perf = df.groupby('Category').agg(
            Invested=('Invested_KRW', 'sum'),
            Eval=('Eval_Value_KRW', 'sum')
        ).reset_index()
        
        cat_perf['SortKey'] = cat_perf['Category'].apply(cat_sort_key)
        cat_perf = cat_perf.sort_values(['SortKey', 'Category']).drop(columns=['SortKey'])
        
        cat_perf['Return_Pct'] = ((cat_perf['Eval'] / cat_perf['Invested']) - 1) * 100
        cat_perf.fillna(0, inplace=True)
        
        cat_perf_table = cat_perf.copy()
        cat_perf_table['Invested'] = cat_perf_table['Invested'].apply(lambda x: f"₩ {x:,.0f}")
        cat_perf_table['Eval'] = cat_perf_table['Eval'].apply(lambda x: f"₩ {x:,.0f}")
        cat_perf_table['Return_Pct'] = cat_perf_table['Return_Pct'].apply(lambda x: f"{x:.2f} %")
        cat_perf_table.columns = ['카테고리', '투입 원금', '현재 평가액', '수익률']
        
        st.dataframe(cat_perf_table, hide_index=True, use_container_width=True)

        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("##### 📝 카테고리별 거래 로그")
        sorted_categories = sorted(df['Category'].unique(), key=cat_sort_key)
        
        for cat in sorted_categories:
            cat_data = df[df['Category'] == cat]
            with st.expander(f"📁 {cat} 내역 보기"):
                counts = cat_data['Type'].value_counts().to_dict()
                summary_text = " / ".join([f"{k}: {v}회" for k, v in counts.items()])
                
                st.markdown(f"**총 거래 요약:**<br><span style='color:gray'>{summary_text}</span>", unsafe_allow_html=True)
                st.dataframe(cat_data[['Date', 'Account', 'Name', 'Ticker', 'Type', 'Price', 'Qty', 'Note']], hide_index=True)

        st.markdown("---")
        
        st.subheader("🎯 주택자금 조달 계획")
        
        remaining_months = 57 
        st.info(f"⏳ **목표 시점(2031년 2월)까지 남은 기간:** {remaining_months}개월")
        
        st.markdown("##### 💰 성실한 투자")
        monthly_savings = st.number_input("매월 신규 저축액 (₩)", min_value=0, value=2500000, step=100000)
        
        st.markdown("##### 🌱 복리 증식 시뮬레이터")
        extend_milestone = st.toggle("마일스톤 연장 (현재 시스템 수익률 그대로 반영)", value=True)
        
        if extend_milestone:
            assumed_annual_rate = total_return_pct if total_return_pct > 0 else 5.0
            annual_rate = st.number_input("예상 연평균 수익률 (%)", value=float(f"{assumed_annual_rate:.2f}"), disabled=True)
            st.success(f"✅ **시스템 자동 연동:** 현재 포트폴리오의 누적 수익률인 **+{assumed_annual_rate:.2f}%**가 2031년까지 그대로 적용됩니다.")
        else:
            annual_rate = st.number_input("예상 연평균 수익률 (%)", value=7.0, step=0.1)
                
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