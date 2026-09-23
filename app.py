import streamlit as st
import pandas as pd
import io
from supabase import create_client

st.set_page_config(page_title="ΚΕΔΙΒΙΜ Diagnostic Hub", page_icon="📊", layout="wide")
ADMIN_EMAIL = "dpatsioura@gmail.com"

# ---------- Supabase ----------
@st.cache_resource
def get_supabase():
    cfg = st.secrets["supabase"]
    return create_client(cfg["url"], cfg["secret_key"])

db = get_supabase()

TABLES = {
    "cash": "cash_bridge",
    "programs": "programs",
    "costs": "cost_base",
    "workload": "admin_workload",
    "findings": "findings_actions",
    "requests": "data_requests",
}

def fetch(table, order=None):
    q = db.table(table).select("*")
    if order:
        q = q.order(order)
    r = q.execute()
    return pd.DataFrame(r.data or [])

def clean(v):
    if pd.isna(v): return None
    if hasattr(v, "item"): return v.item()
    return v

def upsert_rows(table, df):
    if df.empty: return
    rows = [{k: clean(v) for k,v in row.items()} for row in df.to_dict("records")]
    db.table(table).upsert(rows).execute()

def delete_ids(table, ids):
    for x in ids:
        db.table(table).delete().eq("id", x).execute()

def euro(x):
    try: return f"{float(x):,.0f} €".replace(",", ".")
    except: return "0 €"

def n(series):
    return pd.to_numeric(series, errors="coerce").fillna(0)

def editor_sync(table, original, columns, key):
    view = original.copy()
    for c in columns:
        if c not in view.columns: view[c] = None
    display = view[["id"] + columns] if "id" in view.columns else view[columns]
    edited = st.data_editor(
        display, use_container_width=True, hide_index=True,
        num_rows="dynamic", disabled=["id"] if "id" in display.columns else False,
        key=key
    )
    if st.button("Αποθήκευση αλλαγών", type="primary", key="save_"+key):
        before_ids = set(original["id"].dropna().astype(str)) if "id" in original else set()
        after_ids = set(edited["id"].dropna().astype(str)) if "id" in edited else set()
        deleted = before_ids - after_ids
        if deleted: delete_ids(table, deleted)
        payload = edited.copy()
        if "id" in payload.columns:
            payload.loc[payload["id"].astype(str).isin(["", "None", "nan"]), "id"] = None
        # Let DB generate UUID for brand new rows.
        existing = payload[payload["id"].notna()].copy() if "id" in payload else pd.DataFrame()
        new = payload[payload["id"].isna()].drop(columns=["id"], errors="ignore").copy() if "id" in payload else payload.copy()
        if len(existing): upsert_rows(table, existing)
        if len(new):
            rows=[{k:clean(v) for k,v in r.items()} for r in new.to_dict("records")]
            db.table(table).insert(rows).execute()
        st.success("Οι αλλαγές αποθηκεύτηκαν στη βάση.")
        st.cache_data.clear()
        st.rerun()
    return edited

# ---------- Login ----------
if "is_admin" not in st.session_state:
    st.session_state.is_admin = False

with st.sidebar:
    st.markdown("## ΚΕΔΙΒΙΜ ΠΘ")
    st.caption("Diagnostic Hub · 2026")
    st.divider()
    if st.session_state.is_admin:
        st.success("Admin mode")
        if st.button("Αποσύνδεση", use_container_width=True):
            st.session_state.is_admin=False; st.rerun()
    else:
        with st.expander("Admin login"):
            email=st.text_input("Email")
            password=st.text_input("Κωδικός", type="password")
            if st.button("Σύνδεση", use_container_width=True):
                secret=st.secrets.get("auth",{}).get("admin_password","")
                if email.strip().lower()==ADMIN_EMAIL and secret and password==secret:
                    st.session_state.is_admin=True; st.rerun()
                st.error("Μη έγκυρα στοιχεία.")

    pages=["Υγεία ΚΕΔΙΒΙΜ","Annual Cash Bridge","Program Economics","Cost Base",
           "Admin Workload","Findings & Action Plan","Data Request Room",
           "Ερωτηματολόγια","Στρατηγικό Πλάνο","Backup / Export"]
    page=st.radio("Πλοήγηση",pages)

st.title("ΚΕΔΙΒΙΜ · Diagnostic Hub")
st.caption("Οικονομική, λειτουργική και στρατηγική αποτύπωση · Supabase connected")

# ---------- Load live data ----------
try:
    cash=fetch("cash_bridge","year")
    programs=fetch("programs","year")
    costs=fetch("cost_base","year")
    workload=fetch("admin_workload")
    findings=fetch("findings_actions")
    requests=fetch("data_requests")
except Exception as e:
    st.error("Δεν ήταν δυνατή η σύνδεση με τη βάση δεδομένων.")
    st.code(str(e))
    st.stop()

if page=="Υγεία ΚΕΔΙΒΙΜ":
    revenue=n(cash["revenue"]).sum() if "revenue" in cash else 0
    out=sum(n(cash[c]).sum() for c in ["payroll_admin","direct_program_costs","marketing_it_operating","other_outflows"] if c in cash)
    enroll=n(programs["enrollments"]).sum() if "enrollments" in programs else 0
    hours=(n(workload["cases_per_month"])*n(workload["minutes_per_case"])/60).sum() if len(workload) else 0
    p1=((findings.get("priority",pd.Series(dtype=str)).astype(str)=="P1") &
        (~findings.get("status",pd.Series(dtype=str)).astype(str).str.lower().isin(["done","ολοκληρώθηκε"]))).sum() if len(findings) else 0

    c1,c2,c3,c4=st.columns(4)
    c1.metric("Συνολικά έσοδα",euro(revenue)); c2.metric("Συνολικές εκροές",euro(out))
    c3.metric("Εγγραφές",int(enroll)); c4.metric("Ανοιχτά P1",int(p1))
    c1,c2,c3,c4=st.columns(4)
    c1.metric("Προγράμματα",len(programs)); c2.metric("Admin ώρες/μήνα",f"{hours:.1f}")
    c3.metric("Data Request",f"{int(requests['received'].fillna(False).sum())}/{len(requests)}" if len(requests) else "0/0")
    c4.metric("Πρόσβαση","Admin" if st.session_state.is_admin else "View only")
    if len(cash):
        q=cash.copy()
        for c in ["revenue","payroll_admin","direct_program_costs","marketing_it_operating","other_outflows"]:
            q[c]=n(q[c])
        q["outflows"]=q[["payroll_admin","direct_program_costs","marketing_it_operating","other_outflows"]].sum(axis=1)
        st.subheader("Έσοδα και εκροές")
        st.bar_chart(q.set_index("year")[["revenue","outflows"]])
    else:
        st.info("Η βάση είναι συνδεδεμένη. Περιμένει τα πρώτα πραγματικά οικονομικά δεδομένα.")

elif page=="Annual Cash Bridge":
    st.subheader(page)
    cols=["year","opening_cash","revenue","payroll_admin","direct_program_costs","marketing_it_operating","other_outflows","notes"]
    if st.session_state.is_admin:
        editor_sync("cash_bridge",cash,cols,"cash")
    else:
        st.dataframe(cash[cols] if len(cash) else cash,use_container_width=True,hide_index=True)
    if len(cash):
        q=cash.copy()
        for c in cols[1:7]: q[c]=n(q[c])
        q["net_change"]=q["revenue"]-q[cols[3:7]].sum(axis=1)
        q["closing_cash"]=q["opening_cash"]+q["net_change"]
        st.subheader("Υπολογισμένη εικόνα")
        st.dataframe(q[["year","net_change","closing_cash"]],use_container_width=True,hide_index=True)

elif page=="Program Economics":
    st.subheader(page)
    cols=["year","code","program_name","scientific_lead","applications","enrollments","completed",
          "nominal_tuition","actual_avg_tuition","trainer_fees","other_direct_expenses",
          "withholdings_charges","marketing_cost","admin_allocation","variable_cost_per_person","status","notes"]
    if st.session_state.is_admin:
        editor_sync("programs",programs,cols,"programs")
    else:
        st.dataframe(programs[cols] if len(programs) else programs,use_container_width=True,hide_index=True)
    if len(programs):
        q=programs.copy()
        for c in ["enrollments","actual_avg_tuition","trainer_fees","other_direct_expenses","withholdings_charges","marketing_cost","admin_allocation"]:
            q[c]=n(q[c])
        q["collected_revenue"]=q["enrollments"]*q["actual_avg_tuition"]
        q["direct_contribution"]=q["collected_revenue"]-q[["trainer_fees","other_direct_expenses","withholdings_charges","marketing_cost"]].sum(axis=1)
        q["net_contribution"]=q["direct_contribution"]-q["admin_allocation"]
        q["category"]=q["net_contribution"].apply(lambda x:"Θετική" if x>0 else ("Break-even" if x==0 else "Επανεξέταση"))
        st.subheader("Οικονομικοί δείκτες")
        st.dataframe(q[["program_name","collected_revenue","direct_contribution","net_contribution","category"]],use_container_width=True,hide_index=True)

elif page=="Cost Base":
    st.subheader(page)
    cols=["year","category","subcategory","description","cost_type","amount","source_file","notes"]
    if st.session_state.is_admin: editor_sync("cost_base",costs,cols,"costs")
    else: st.dataframe(costs[cols] if len(costs) else costs,use_container_width=True,hide_index=True)
    if len(costs): st.metric("Συνολικό καταγεγραμμένο κόστος",euro(n(costs["amount"]).sum()))

elif page=="Admin Workload":
    st.subheader(page)
    cols=["role","process","frequency","cases_per_month","minutes_per_case","system_file","duplicate_entry","automation_potential","notes"]
    if st.session_state.is_admin: editor_sync("admin_workload",workload,cols,"workload")
    else: st.dataframe(workload[cols] if len(workload) else workload,use_container_width=True,hide_index=True)
    if len(workload):
        q=workload.copy(); q["hours_per_month"]=n(q["cases_per_month"])*n(q["minutes_per_case"])/60
        st.metric("Συνολικές διοικητικές ώρες/μήνα",f"{q['hours_per_month'].sum():.1f}")
        st.dataframe(q[["role","process","hours_per_month"]],use_container_width=True,hide_index=True)

elif page=="Findings & Action Plan":
    st.subheader(page)
    cols=["finding_code","area","finding","evidence_source","root_cause","impact","priority",
          "proposed_action","owner","horizon","status","success_kpi","due_date"]
    if st.session_state.is_admin: editor_sync("findings_actions",findings,cols,"findings")
    else: st.dataframe(findings[cols] if len(findings) else findings,use_container_width=True,hide_index=True)
    if len(findings):
        st.bar_chart(findings["priority"].fillna("Χωρίς προτεραιότητα").value_counts())

elif page=="Data Request Room":
    st.subheader(page)
    if not len(requests):
        st.info("Δεν υπάρχουν στοιχεία checklist.")
    else:
        cols=["item","category","received","received_at","source_file","notes"]
        if st.session_state.is_admin: editor_sync("data_requests",requests,cols,"requests")
        else: st.dataframe(requests[cols],use_container_width=True,hide_index=True)
        done=int(requests["received"].fillna(False).sum())
        st.progress(done/len(requests)); st.caption(f"{done}/{len(requests)} διαθέσιμα")

elif page=="Ερωτηματολόγια":
    st.subheader(page)
    tab1,tab2=st.tabs(["Διοικητικό προσωπικό","Εκπαιδευόμενοι"])
    with tab1:
        st.info("Η πλήρης φόρμα διοικητικού προσωπικού θα προστεθεί στην επόμενη έκδοση.")
    with tab2:
        st.markdown("Ανώνυμη αποτύπωση εμπειρίας εκπαιδευομένου.")
        with st.form("learner_form"):
            program=st.text_input("Πρόγραμμα")
            overall=st.slider("Συνολική εμπειρία",1,5,4)
            organization=st.slider("Οργάνωση",1,5,4)
            digital=st.slider("Moodle / ψηφιακή εμπειρία",1,5,4)
            support=st.slider("Υποστήριξη",1,5,4)
            nps=st.slider("Πιθανότητα σύστασης",0,10,8)
            comments=st.text_area("Σχόλιο")
            submit=st.form_submit_button("Υποβολή")
            if submit:
                try:
                    db.table("learner_responses").insert({
                        "program_name":program or None,
                        "overall_experience":overall,
                        "organization_rating":organization,
                        "digital_moodle_rating":digital,
                        "support_rating":support,
                        "nps":nps,
                        "comments":comments or None
                    }).execute()
                    st.success("Η απάντηση καταχωρίστηκε.")
                except Exception:
                    st.error("Η υποβολή δεν ολοκληρώθηκε.")

elif page=="Στρατηγικό Πλάνο":
    st.subheader("Στρατηγικό Πλάνο Διάγνωσης, Σταθεροποίησης και Ανάπτυξης")
    st.markdown("""
### 1. Financial Diagnostic
Έσοδα, έξοδα, ταμειακή εικόνα, υποχρεώσεις και ιστορική εξέλιξη.

### 2. Program Economics
Contribution, καθαρή συνεισφορά και break-even ανά πρόγραμμα και κύκλο.

### 3. Operational Audit
Χρόνος, διπλές καταχωρήσεις, ασάφειες ευθύνης, process maps, workload map και quick wins.

### 4. Growth Engine
Marketing funnel, portfolio strategy, συνεργασίες, corporate training, χρηματοδοτούμενες δράσεις και επανάληψη επιτυχημένων κύκλων.

### Πρώτες 30 ημέρες
1–5: Data Room και inventory  
5–10: Ερωτηματολόγια  
7–15: Interviews και workflows  
10–20: Financial reconciliation και Program Economics  
15–25: Marketing, website, systems και ΕΛΚΕ audit  
25–30: Σύνθεση, προτεραιοποίηση και quick wins
""")

elif page=="Backup / Export":
    st.subheader(page)
    tables={"cash_bridge":cash,"programs":programs,"cost_base":costs,"admin_workload":workload,
            "findings_actions":findings,"data_requests":requests}
    out=io.BytesIO()
    with pd.ExcelWriter(out,engine="openpyxl") as w:
        for name,df in tables.items(): df.to_excel(w,sheet_name=name[:31],index=False)
    st.download_button("Λήψη συνολικού Excel backup",out.getvalue(),
                       "KEDIVIM_Diagnostic_Backup.xlsx",
                       "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

st.divider()
st.caption("ΚΕΔΙΒΙΜ Πανεπιστημίου Θεσσαλίας · Diagnostic Hub 2026")
