import streamlit as st
import pandas as pd
from datetime import datetime
from supabase import create_client

# -------------------------------
# 🔐 Passwörter
# -------------------------------
USER_PASSWORD = "welovekb"
ADMIN_PASSWORD = "sebaforceo"

# -------------------------------
# 🧠 Supabase-Client
# -------------------------------
supabase = create_client(
    st.secrets["SUPABASE_URL"],
    st.secrets["SUPABASE_KEY"]
)

def log_login(role, success):
    """Loginversuch in Supabase speichern"""
    supabase.table("login_events").insert({
        "role": role,
        "success": success,
        "created_at": datetime.utcnow().isoformat()
    }).execute()

# -------------------------------
# 🧠 Session State Initialisierung
# -------------------------------
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "is_admin" not in st.session_state:
    st.session_state.is_admin = False
if "USER_PASSWORD" not in st.session_state:
    st.session_state["USER_PASSWORD"] = USER_PASSWORD

# -------------------------------
# 🔐 Login
# -------------------------------
def login(password):
    user_pw = st.session_state.get("USER_PASSWORD", USER_PASSWORD)
        
    if password == user_pw:
        st.session_state.logged_in = True
        st.session_state.is_admin = False
        log_login("User", True)
        st.rerun()
    elif password == ADMIN_PASSWORD:
        st.session_state.logged_in = True
        st.session_state.is_admin = True
        log_login("Admin", True)
        st.rerun()
    else:
        log_login("Unknown", False)
        st.error("❌ Falsches Passwort")

if not st.session_state.logged_in:
    st.title("🔐 Login erforderlich")
    pw = st.text_input("Passwort", type="password")
    if st.button("Login"):
        login(pw)
    st.stop()

# -------------------------------
# 👑 Admin Backend
# -------------------------------
if st.session_state.is_admin:
    st.header("👑 Admin Dashboard")

    # Login-Historie
    data = supabase.table("login_events").select("*").order("created_at", desc=True).execute()
    df = pd.DataFrame(data.data)
    if not df.empty:
        df["Datum"] = pd.to_datetime(df["created_at"]).dt.date

        st.subheader("📄 Login-Historie")
        st.dataframe(df, use_container_width=True)

        st.subheader("📊 Logins pro Tag")
        logins_per_day = (
            df[df["success"]==True]
            .groupby("Datum")
            .size()
            .reset_index(name="Logins")
        )
        st.dataframe(logins_per_day, use_container_width=True)
        st.bar_chart(logins_per_day.set_index("Datum"))

        csv = df.to_csv(index=False).encode("utf-8")
        st.download_button("CSV Export", csv, "login_history.csv", "text/csv")
    else:
        st.info("Noch keine Login-Daten vorhanden.")

    # Passwortänderung für normalen User
    st.subheader("🔑 User Passwort ändern")
    new_password = st.text_input("Neues User-Passwort", type="password")
    if st.button("Update User Passwort"):
        if new_password:
            st.session_state['USER_PASSWORD'] = new_password
            st.success("✅ Passwort erfolgreich geändert!")
        else:
            st.warning("Bitte ein gültiges Passwort eingeben.")

    st.stop()

# -------------------------------
# 🔧 App Konfiguration
# -------------------------------
st.set_page_config(page_title="Kalkulations-App", layout="wide")
st.title("📊 Kalkulations-App")

# -------------------------------
# 📋 Seitenmenü
# -------------------------------
page = st.sidebar.radio("Wähle eine Kalkulation:", ["Platform", "Cardpayment", "Pricing"])

# -------------------------------
# 🏁 Platform
# -------------------------------
if page == "Platform":
    st.header("🏁 Platform Kalkulation")
    col1, col2 = st.columns([2, 1.5])

    init_keys = ["revenue","commission_pct","avg_order_value","service_fee","OTF","MRR","contract_length"]
    defaults = [0.0,14.0,25.0,0.69,0.0,0.0,24]
    for k, v in zip(init_keys, defaults):
        if k not in st.session_state:
            st.session_state[k] = v

    with col1:
        st.subheader("Eingaben")
        st.number_input("Revenue on platform (€)", step=250.0, key="revenue")
        st.number_input("Commission (%)", step=1.0, key="commission_pct")
        st.number_input("Average order value (€)", step=5.0, key="avg_order_value")
        st.number_input("Service Fee (€)", step=0.1, key="service_fee")

        total_cost = st.session_state.revenue*(st.session_state.commission_pct/100) + \
                     (0.7*st.session_state.revenue/st.session_state.avg_order_value if st.session_state.avg_order_value else 0)*st.session_state.service_fee

        st.markdown("### 💶 Cost on Platform")
        st.markdown(f"<div style='color:red; font-size:28px;'>{total_cost:,.2f} €</div>", unsafe_allow_html=True)

        st.markdown("---")
        st.subheader("Vertragsdetails")
        st.number_input("One Time Fee (OTF) (€)", step=100.0, key="OTF")
        st.number_input("Monthly Recurring Revenue (MRR) (€)", step=10.0, key="MRR")
        st.number_input("Contract length (Monate)", step=12, key="contract_length")

    transaction = 0.7*st.session_state.revenue/5*0.35
    cost_monthly = st.session_state.MRR + transaction
    saving_monthly = total_cost - cost_monthly
    saving_over_contract = saving_monthly*st.session_state.contract_length

    st.subheader("📊 Kennzahlen")
    st.info(
        f"- Cost monthly: {cost_monthly:,.2f} €\n"
        f"- Saving monthly: {saving_monthly:,.2f} €\n"
        f"- Saving over contract length: {saving_over_contract:,.2f} €"
    )

# -------------------------------
# 💳 Cardpayment
# -------------------------------
elif page == "Cardpayment":
    st.header("💳 Cardpayment Vergleich")
    col1, col2 = st.columns(2)

    init_keys = ["rev_a","sum_a","mrr_a","comm_a","auth_a","rev_o","sum_o","mrr_o","comm_o","auth_o"]
    defaults = [0.0,0.0,0.0,1.39,0.0,0.0,0.0,0.0,1.19,0.06]
    for k, v in zip(init_keys, defaults):
        if k not in st.session_state:
            st.session_state[k] = v

    with col1:
        st.subheader("Actual")
        st.number_input("Revenue (€)", step=250.0, key="rev_a")
        st.number_input("Sum of payments", step=20, key="sum_a")
        st.number_input("Monthly Fee (€)", step=5.0, key="mrr_a")
        st.number_input("Commission (%)", step=0.01, key="comm_a")
        st.number_input("Authentification Fee (€)", key="auth_a")

    with col2:
        st.subheader("Offer")
        st.session_state.rev_o = st.session_state.rev_a
        st.session_state.sum_o = st.session_state.sum_a

        st.number_input("Revenue (€)", step=250.0, key="rev_o")
        st.number_input("Sum of payments", step=20, key="sum_o")
        st.number_input("Monthly Fee (€)", step=5.0, key="mrr_o")
        st.number_input("Commission (%)", step=0.01, key="comm_o")
        st.number_input("Authentification Fee (€)", key="auth_o")

    total_actual = st.session_state.rev_a*(st.session_state.comm_a/100) + st.session_state.sum_a*st.session_state.auth_a + st.session_state.mrr_a
    total_offer  = st.session_state.rev_o*(st.session_state.comm_o/100) + st.session_state.sum_o*st.session_state.auth_o + st.session_state.mrr_o
    saving = total_offer - total_actual

    st.markdown("---")
    col3, col4, col5 = st.columns(3)
    col3.markdown(f"<div style='color:red; font-size:28px;'>💳 {total_actual:,.2f} €</div>", unsafe_allow_html=True)
    col3.caption("Total Actual")
    col4.markdown(f"<div style='color:blue; font-size:28px;'>💳 {total_offer:,.2f} €</div>", unsafe_allow_html=True)
    col4.caption("Total Offer")
    col5.markdown(f"<div style='color:green; font-size:28px;'>💰 {saving:,.2f} €</div>", unsafe_allow_html=True)
    col5.caption("Ersparnis (Offer - Actual)")

# -------------------------------
# 💰 Pricing
# -------------------------------
elif page == "Pricing":
    st.header("💰 Pricing Kalkulation")

    software_data = {
        "Produkt": ["Shop","App","POS","Pay","GAW"],
        "Min_OTF": [365,15,365,35,50],
        "List_OTF": [999,49,999,49,100],
        "Min_MRR": [50,15,49,5,100],
        "List_MRR": [119,49,89,25,100]
    }

    hardware_data = {
        "Produkt":["Ordermanager","POS inkl 1 Printer","Cash Drawer","Extra Printer","Additional Display","PAX"],
        "Min_OTF":[135,350,50,99,100,225],
        "List_OTF":[299,1699,149,199,100,299],
        "Min_MRR":[0,0,0,0,0,0],
        "List_MRR":[0,0,0,0,0,0]
    }

    df_sw = pd.DataFrame(software_data)
    df_hw = pd.DataFrame(hardware_data)

    # Session State initialisieren
    for i in range(len(df_sw)):
        if f"sw_{i}" not in st.session_state:
            st.session_state[f"sw_{i}"]=0
    for i in range(len(df_hw)):
        if f"hw_{i}" not in st.session_state:
            st.session_state[f"hw_{i}"]=0

    if "gaw_value" not in st.session_state: st.session_state["gaw_value"]=50.0
    if "gaw_qty" not in st.session_state: st.session_state["gaw_qty"]=1

    col_sw, col_hw = st.columns(2)

    # --- Software Eingaben ---
    with col_sw:
        st.subheader("🧩 Software")
        for i in range(len(df_sw)):
            if df_sw["Produkt"][i] != "GAW":
                st.number_input(df_sw["Produkt"][i], min_value=0, step=1, key=f"sw_{i}")
        st.number_input("GAW Menge", step=1, key="gaw_qty")
        st.number_input("GAW Betrag (€)", min_value=0.0, step=25.0, key="gaw_value")
        df_sw["Menge"] = [st.session_state[f"sw_{i}"] for i in range(len(df_sw))]

    # --- Hardware Eingaben ---
    with col_hw:
        st.subheader("🖥️ Hardware")
        for i in range(len(df_hw)):
            st.number_input(df_hw["Produkt"][i], min_value=0, step=1, key=f"hw_{i}")
        df_hw["Menge"] = [st.session_state[f"hw_{i}"] for i in range(len(df_hw))]

    # --- Berechnung List Prices & GAW ---
    list_mrr = (df_sw[df_sw["Produkt"]!="GAW"]["Menge"]*df_sw[df_sw["Produkt"]!="GAW"]["List_MRR"]).sum()
    list_otf = (df_hw["Menge"]*df_hw["List_OTF"]).sum()
    gaw_total = st.session_state["gaw_qty"]*st.session_state["gaw_value"]

    # --- Anzeige List Prices ---
    col_list1, col_list2 = st.columns(2)
    col_list1.markdown(f"### 🧩 Software MRR List: {list_mrr:,.2f} €", unsafe_allow_html=True)
    col_list2.markdown(f"### 🖥️ Hardware OTF List: {list_otf:,.2f} €", unsafe_allow_html=True)

    # --- GAW Gesamt ---
    st.markdown(f"### 💰 GAW Gesamt: {gaw_total:,.2f} €", unsafe_allow_html=True)

    # --- Min Prices unten ---
    min_mrr = (df_sw[df_sw["Produkt"]!="GAW"]["Menge"]*df_sw[df_sw["Produkt"]!="GAW"]["Min_MRR"]).sum()
    min_otf = (df_hw["Menge"]*df_hw["Min_OTF"]).sum()
    st.markdown("---")
    st.markdown(f"### 🔻 MRR Min: {min_mrr:,.2f} €")
    st.markdown(f"### 🔻 OTF Min: {min_otf:,.2f} €")

    # --- Tabelle ---
    with st.expander("Preisdetails anzeigen"):
        df_show = pd.concat([df_sw, df_hw])[["Produkt","Min_OTF","List_OTF","Min_MRR","List_MRR"]]
        st.dataframe(
            df_show.style.format({
                "Min_OTF":"{:,.0f} €",
                "List_OTF":"{:,.0f} €",
                "Min_MRR":"{:,.0f} €",
                "List_MRR":"{:,.0f} €",
            }),
            hide_index=True,
            use_container_width=True
        )

# -------------------------------
# Footer
# -------------------------------
st.markdown("""
<hr style="margin:20px 0;">
<p style='text-align:center; font-size:0.8rem; color:gray;'>
😉 Traue niemals Zahlen, die du nicht selbst gefälscht hast 😉
</p>
""", unsafe_allow_html=True)
