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


def status_badge(status):
    labels={"Pending":"Σε εκκρεμότητα","Received":"Παραλήφθηκε","Late":"Σε καθυστέρηση",
            "Open":"Ανοιχτό","In progress":"Σε εξέλιξη","Done":"Ολοκληρώθηκε"}
    return labels.get(str(status), str(status))

def section_kpis(items):
    cols=st.columns(len(items))
    for col,(label,value) in zip(cols,items):
        col.metric(label,value)


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

    pages=["Dashboard – Υγεία ΚΕΔΙΒΙΜ","Οικονομική Εικόνα / Cash Flow","Program Economics","Βάση Κόστους",
           "Διοικητικός Φόρτος","Findings & Action Plan","Data Room",
           "Ερωτηματολόγια","Στρατηγικό Πλάνο","Reports & Export"]
    page=st.radio("Πλοήγηση",pages)

h1,h2,h3 = st.columns([1,1,1])  # harmless layout initialization
head1, head2 = st.columns([5,1])
with head1:
    st.title("ΚΕΔΙΒΙΜ · Diagnostic Hub")
    st.caption("Πανεπιστήμιο Θεσσαλίας · Οικονομική, λειτουργική και στρατηγική αποτύπωση")
with head2:
    c1,c2=st.columns(2)
    with c1: st.image("assets/kedivim_logo.png", width=58)
    with c2: st.image("assets/uth_logo.png", width=58)


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

if page=="Dashboard – Υγεία ΚΕΔΙΒΙΜ":
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

elif page=="Οικονομική Εικόνα / Cash Flow":
    st.subheader("Οικονομική Εικόνα / Cash Flow")
    st.caption("Ετήσια εικόνα εσόδων, εκροών και ταμειακής μεταβολής.")
    if st.session_state.is_admin:
        with st.expander("➕ Νέο οικονομικό έτος"):
            with st.form("new_cash",clear_on_submit=True):
                year=st.number_input("Έτος",2000,2100,2026)
                c1,c2=st.columns(2)
                opening=c1.number_input("Αρχικό ταμείο (€)",value=0.0)
                revenue=c2.number_input("Έσοδα (€)",value=0.0)
                c1,c2=st.columns(2)
                payroll=c1.number_input("Μισθοδοσία / Διοίκηση (€)",value=0.0)
                direct=c2.number_input("Άμεσα κόστη προγραμμάτων (€)",value=0.0)
                c1,c2=st.columns(2)
                operating=c1.number_input("Marketing / IT / Λειτουργικά (€)",value=0.0)
                other=c2.number_input("Λοιπές εκροές (€)",value=0.0)
                notes=st.text_area("Σημειώσεις")
                if st.form_submit_button("Αποθήκευση έτους",type="primary"):
                    try:
                        db.table("cash_bridge").insert({"year":year,"opening_cash":opening,"revenue":revenue,
                            "payroll_admin":payroll,"direct_program_costs":direct,
                            "marketing_it_operating":operating,"other_outflows":other,"notes":notes or None}).execute()
                        st.success("Το οικονομικό έτος αποθηκεύτηκε."); st.rerun()
                    except Exception:
                        st.error("Υπάρχει ήδη εγγραφή για αυτό το έτος ή τα στοιχεία δεν ήταν έγκυρα.")
    if len(cash):
        for _,r in cash.sort_values("year",ascending=False).iterrows():
            out=sum(float(r.get(c) or 0) for c in ["payroll_admin","direct_program_costs","marketing_it_operating","other_outflows"])
            net=float(r.get("revenue") or 0)-out
            closing=float(r.get("opening_cash") or 0)+net
            with st.expander(f"💰 {int(r.get('year'))} · Κλείσιμο {euro(closing)}"):
                c1,c2,c3,c4=st.columns(4)
                c1.metric("Έσοδα",euro(r.get("revenue",0))); c2.metric("Εκροές",euro(out))
                c3.metric("Net Change",euro(net)); c4.metric("Closing Cash",euro(closing))

elif page=="Program Economics":
    st.subheader("Program Economics")
    st.caption("Κάθε κύκλος προγράμματος καταχωρίζεται ξεχωριστά. Τα στοιχεία μπορούν να συμπληρώνονται σταδιακά.")

    if st.session_state.is_admin:
        with st.expander("➕ Νέο πρόγραμμα / κύκλος", expanded=False):
            with st.form("new_program_form", clear_on_submit=True):
                st.markdown("#### Ταυτότητα Προγράμματος")
                c1,c2,c3=st.columns(3)
                year=c1.number_input("Έτος", min_value=2000, max_value=2100, value=2026)
                code=c2.text_input("Κωδικός")
                status=c3.selectbox("Status",["active","planned","completed","paused","cancelled"])
                program_name=st.text_input("Τίτλος Προγράμματος *")
                scientific_lead=st.text_input("Επιστημονικός Υπεύθυνος")
                c1,c2,c3=st.columns(3)
                category=c1.text_input("Κατηγορία")
                delivery=c2.selectbox("Τρόπος υλοποίησης",["","Δια ζώσης","Εξ αποστάσεως","Μικτό"])
                funding=c3.text_input("Πηγή χρηματοδότησης")
                c1,c2=st.columns(2)
                start_date=c1.date_input("Ημερομηνία έναρξης", value=None)
                end_date=c2.date_input("Ημερομηνία λήξης", value=None)

                st.markdown("#### Συμμετοχές")
                c1,c2,c3=st.columns(3)
                applications=c1.number_input("Αιτήσεις",min_value=0,value=0)
                enrollments=c2.number_input("Εγγραφές",min_value=0,value=0)
                paid=c3.number_input("Πληρωμένοι εκπαιδευόμενοι",min_value=0,value=0)
                c1,c2,c3=st.columns(3)
                completed=c1.number_input("Ολοκλήρωσαν",min_value=0,value=0)
                certs=c2.number_input("Πιστοποιητικά",min_value=0,value=0)
                maxp=c3.number_input("Μέγιστος αριθμός συμμετεχόντων",min_value=0,value=0)

                st.markdown("#### Οικονομικά")
                c1,c2,c3=st.columns(3)
                nominal=c1.number_input("Ονομαστικά δίδακτρα (€)",min_value=0.0,value=0.0)
                actual=c2.number_input("Μέσο πραγματικό δίδακτρο (€)",min_value=0.0,value=0.0)
                trainer=c3.number_input("Αμοιβές εκπαιδευτών (€)",min_value=0.0,value=0.0)
                c1,c2,c3=st.columns(3)
                other=c1.number_input("Λοιπά άμεσα έξοδα (€)",min_value=0.0,value=0.0)
                charges=c2.number_input("Κρατήσεις / χρεώσεις (€)",min_value=0.0,value=0.0)
                marketing=c3.number_input("Marketing Cost (€)",min_value=0.0,value=0.0)
                c1,c2=st.columns(2)
                admin=c1.number_input("Διοικητική επιβάρυνση (€)",min_value=0.0,value=0.0)
                variable=c2.number_input("Μεταβλητό κόστος / άτομο (€)",min_value=0.0,value=0.0)
                notes=st.text_area("Σημειώσεις")
                submitted=st.form_submit_button("Αποθήκευση προγράμματος",type="primary")
                if submitted:
                    if not program_name.strip():
                        st.error("Ο τίτλος προγράμματος είναι υποχρεωτικός.")
                    else:
                        payload={
                          "year":int(year),"code":code or None,"program_name":program_name.strip(),
                          "scientific_lead":scientific_lead or None,"status":status,
                          "program_category":category or None,"delivery_mode":delivery or None,
                          "funding_source":funding or None,
                          "start_date":start_date.isoformat() if start_date else None,
                          "end_date":end_date.isoformat() if end_date else None,
                          "applications":applications,"enrollments":enrollments,"paid_participants":paid,
                          "completed":completed,"certificates_issued":certs,"max_participants":maxp,
                          "nominal_tuition":nominal,"actual_avg_tuition":actual,"trainer_fees":trainer,
                          "other_direct_expenses":other,"withholdings_charges":charges,
                          "marketing_cost":marketing,"admin_allocation":admin,
                          "variable_cost_per_person":variable,"notes":notes or None
                        }
                        db.table("programs").insert(payload).execute()
                        st.success("Το πρόγραμμα αποθηκεύτηκε.")
                        st.rerun()

    if not len(programs):
        st.info("Δεν έχουν καταχωριστεί ακόμη προγράμματα.")
    else:
        st.markdown("### Καταχωρισμένα προγράμματα")
        search=st.text_input("Αναζήτηση",placeholder="Τίτλος, κωδικός ή Επιστημονικός Υπεύθυνος")
        q=programs.copy()
        if search:
            mask=(q["program_name"].fillna("").str.contains(search,case=False) |
                  q["code"].fillna("").str.contains(search,case=False) |
                  q["scientific_lead"].fillna("").str.contains(search,case=False))
            q=q[mask]
        show_cols=[c for c in ["id","year","code","program_name","scientific_lead","status","enrollments",
                               "actual_avg_tuition","trainer_fees","marketing_cost","admin_allocation"] if c in q]
        st.dataframe(q[show_cols],use_container_width=True,hide_index=True)

        calc=q.copy()
        for c in ["enrollments","actual_avg_tuition","trainer_fees","other_direct_expenses",
                  "withholdings_charges","marketing_cost","admin_allocation","variable_cost_per_person"]:
            if c in calc: calc[c]=n(calc[c])
        calc["Revenue"]=calc["enrollments"]*calc["actual_avg_tuition"]
        calc["Direct Contribution"]=calc["Revenue"]-calc[["trainer_fees","other_direct_expenses","withholdings_charges","marketing_cost"]].sum(axis=1)
        calc["Net Contribution"]=calc["Direct Contribution"]-calc["admin_allocation"]
        denom=calc["actual_avg_tuition"]-calc["variable_cost_per_person"]
        calc["Break-even"]=(calc["admin_allocation"]/denom.where(denom>0)).apply(lambda x: None if pd.isna(x) else int(x)+int(x%1>0))
        st.markdown("### Performance")
        st.dataframe(calc[["program_name","Revenue","Direct Contribution","Net Contribution","Break-even"]],
                     use_container_width=True,hide_index=True)

        if st.session_state.is_admin:
            st.markdown("### Επεξεργασία υπάρχουσας εγγραφής")
            choices={f"{r.get('program_name','')} · {r.get('year','')} · {str(r.get('id',''))[:8]}":r.get("id") for _,r in programs.iterrows()}
            selected_label=st.selectbox("Επίλεξε πρόγραμμα",list(choices.keys()))
            selected_id=choices[selected_label]
            row=programs[programs["id"]==selected_id].iloc[0].to_dict()
            with st.form("edit_program_form"):
                e_name=st.text_input("Τίτλος Προγράμματος",value=str(row.get("program_name") or ""))
                e_lead=st.text_input("Επιστημονικός Υπεύθυνος",value=str(row.get("scientific_lead") or ""))
                c1,c2,c3=st.columns(3)
                e_apps=c1.number_input("Αιτήσεις",min_value=0,value=int(row.get("applications") or 0))
                e_enr=c2.number_input("Εγγραφές",min_value=0,value=int(row.get("enrollments") or 0))
                e_comp=c3.number_input("Ολοκλήρωσαν",min_value=0,value=int(row.get("completed") or 0))
                c1,c2,c3=st.columns(3)
                e_fee=c1.number_input("Μέσο πραγματικό δίδακτρο (€)",min_value=0.0,value=float(row.get("actual_avg_tuition") or 0))
                e_train=c2.number_input("Αμοιβές εκπαιδευτών (€)",min_value=0.0,value=float(row.get("trainer_fees") or 0))
                e_mark=c3.number_input("Marketing Cost (€)",min_value=0.0,value=float(row.get("marketing_cost") or 0))
                e_notes=st.text_area("Σημειώσεις",value=str(row.get("notes") or ""))
                save=st.form_submit_button("Αποθήκευση αλλαγών",type="primary")
                if save:
                    db.table("programs").update({
                      "program_name":e_name,"scientific_lead":e_lead or None,
                      "applications":e_apps,"enrollments":e_enr,"completed":e_comp,
                      "actual_avg_tuition":e_fee,"trainer_fees":e_train,"marketing_cost":e_mark,
                      "notes":e_notes or None
                    }).eq("id",selected_id).execute()
                    st.success("Οι αλλαγές αποθηκεύτηκαν.")
                    st.rerun()
            with st.expander("Διαγραφή εγγραφής"):
                confirm=st.checkbox("Επιβεβαιώνω ότι θέλω να διαγραφεί ο συγκεκριμένος κύκλος.")
                if st.button("Διαγραφή",disabled=not confirm):
                    db.table("programs").delete().eq("id",selected_id).execute()
                    st.success("Η εγγραφή διαγράφηκε.")
                    st.rerun()

elif page=="Βάση Κόστους":
    st.subheader("Βάση Κόστους")
    st.caption("Σταθερά και μεταβλητά κόστη του ΚΕΔΙΒΙΜ.")
    section_kpis([("Εγγραφές κόστους",len(costs)),("Συνολικό κόστος",euro(n(costs["amount"]).sum()) if len(costs) else "0 €")])
    if st.session_state.is_admin:
        with st.expander("➕ Νέα δαπάνη"):
            with st.form("new_cost",clear_on_submit=True):
                c1,c2,c3=st.columns(3)
                year=c1.number_input("Έτος",2000,2100,2026)
                category=c2.text_input("Κατηγορία")
                cost_type=c3.selectbox("Τύπος",["Σταθερό","Μεταβλητό"])
                description=st.text_input("Περιγραφή *")
                c1,c2=st.columns(2)
                amount=c1.number_input("Ποσό (€)",min_value=0.0,value=0.0)
                supplier=c2.text_input("Προμηθευτής")
                recurring=st.checkbox("Επαναλαμβανόμενη δαπάνη")
                notes=st.text_area("Σημειώσεις")
                if st.form_submit_button("Αποθήκευση δαπάνης",type="primary"):
                    if not description.strip(): st.error("Η περιγραφή είναι υποχρεωτική.")
                    else:
                        db.table("cost_base").insert({"year":year,"category":category or None,"description":description,
                            "cost_type":cost_type,"amount":amount,"supplier":supplier or None,
                            "recurring":recurring,"notes":notes or None}).execute()
                        st.success("Η δαπάνη αποθηκεύτηκε."); st.rerun()
    if len(costs):
        search=st.text_input("Αναζήτηση δαπάνης")
        q=costs.copy()
        if search:q=q[q["description"].fillna("").str.contains(search,case=False)]
        for _,r in q.iterrows():
            with st.expander(f"💶 {r.get('description','')} · {euro(r.get('amount',0))}"):
                st.write(f"Κατηγορία: {r.get('category') or '—'} | Έτος: {r.get('year') or '—'} | Τύπος: {r.get('cost_type') or '—'}")
                if st.session_state.is_admin:
                    if st.button("Διαγραφή",key="costdel"+str(r["id"])):
                        db.table("cost_base").delete().eq("id",r["id"]).execute(); st.rerun()

elif page=="Διοικητικός Φόρτος":
    st.subheader("Διοικητικός Φόρτος")
    st.caption("Χρόνος, επαναλαμβανόμενες διαδικασίες, pain points και δυνατότητες automation.")
    hours=(n(workload["cases_per_month"])*n(workload["minutes_per_case"])/60).sum() if len(workload) else 0
    section_kpis([("Διαδικασίες",len(workload)),("Ώρες / μήνα",f"{hours:.1f}")])
    if st.session_state.is_admin:
        with st.expander("➕ Νέα διαδικασία"):
            with st.form("new_work",clear_on_submit=True):
                c1,c2=st.columns(2)
                role=c1.text_input("Ρόλος")
                owner=c2.text_input("Υπεύθυνος")
                process=st.text_input("Διαδικασία *")
                c1,c2,c3=st.columns(3)
                frequency=c1.text_input("Συχνότητα")
                cases=c2.number_input("Πλήθος / μήνα",min_value=0.0,value=0.0)
                minutes=c3.number_input("Λεπτά / περίπτωση",min_value=0.0,value=0.0)
                system=st.text_input("Σύστημα / αρχείο")
                duplicate=st.checkbox("Υπάρχει διπλή καταχώριση")
                automation=st.selectbox("Automation potential",["","Χαμηλό","Μέτριο","Υψηλό"])
                pain=st.text_area("Pain point")
                improvement=st.text_area("Προτεινόμενη βελτίωση")
                if st.form_submit_button("Αποθήκευση διαδικασίας",type="primary"):
                    if not process.strip(): st.error("Η διαδικασία είναι υποχρεωτική.")
                    else:
                        db.table("admin_workload").insert({"role":role or None,"responsible_person":owner or None,
                            "process":process,"frequency":frequency or None,"cases_per_month":cases,
                            "minutes_per_case":minutes,"system_file":system or None,"duplicate_entry":duplicate,
                            "automation_potential":automation or None,"pain_point":pain or None,
                            "proposed_improvement":improvement or None}).execute()
                        st.success("Η διαδικασία αποθηκεύτηκε."); st.rerun()
    if len(workload):
        for _,r in workload.iterrows():
            hrs=float(r.get("cases_per_month") or 0)*float(r.get("minutes_per_case") or 0)/60
            with st.expander(f"⚙️ {r.get('process','')} · {hrs:.1f} ώρες/μήνα"):
                st.write(f"Ρόλος: {r.get('role') or '—'} | Automation: {r.get('automation_potential') or '—'}")
                if r.get("pain_point"): st.warning(r.get("pain_point"))

elif page=="Findings & Action Plan":
    st.subheader("Findings & Action Plan")
    st.caption("Ευρήματα, προτεραιότητες, owners, deadlines και πρόοδος ενεργειών.")
    p1=((findings["priority"].astype(str)=="P1") & (~findings["status"].astype(str).str.lower().isin(["done","ολοκληρώθηκε"]))).sum() if len(findings) else 0
    section_kpis([("Συνολικά ευρήματα",len(findings)),("Ανοιχτά P1",int(p1))])
    if st.session_state.is_admin:
        with st.expander("➕ Νέο εύρημα / action"):
            with st.form("new_finding",clear_on_submit=True):
                c1,c2,c3=st.columns(3)
                code=c1.text_input("Κωδικός")
                area=c2.text_input("Πεδίο")
                priority=c3.selectbox("Priority",["P1","P2","P3"])
                finding=st.text_area("Εύρημα *")
                impact=st.text_area("Επίπτωση")
                action=st.text_area("Προτεινόμενη ενέργεια")
                c1,c2,c3=st.columns(3)
                owner=c1.text_input("Owner")
                status=c2.selectbox("Status",["Open","In progress","Done"])
                due=c3.date_input("Deadline",value=None)
                kpi=st.text_input("KPI επιτυχίας")
                if st.form_submit_button("Αποθήκευση",type="primary"):
                    if not finding.strip(): st.error("Το εύρημα είναι υποχρεωτικό.")
                    else:
                        db.table("findings_actions").insert({"finding_code":code or None,"area":area or None,
                            "finding":finding,"impact":impact or None,"priority":priority,
                            "proposed_action":action or None,"owner":owner or None,"status":status,
                            "due_date":due.isoformat() if due else None,"success_kpi":kpi or None}).execute()
                        st.success("Το εύρημα αποθηκεύτηκε."); st.rerun()
    if len(findings):
        for _,r in findings.sort_values("priority").iterrows():
            with st.expander(f"🚩 {r.get('priority','')} · {r.get('finding','')}"):
                c1,c2,c3=st.columns(3)
                c1.metric("Status",r.get("status") or "—"); c2.metric("Owner",r.get("owner") or "—"); c3.metric("Deadline",str(r.get("due_date") or "—"))
                if r.get("proposed_action"): st.write("Action:",r.get("proposed_action"))
                if r.get("success_kpi"): st.write("KPI:",r.get("success_kpi"))

elif page=="Data Room":
    st.subheader("Data Room")
    st.caption("Αιτήματα δεδομένων, δικαιολογητικά και παρακολούθηση παραλαβής.")

    total=len(requests)
    received_count=int(requests["received"].fillna(False).sum()) if total else 0
    pending=total-received_count
    section_kpis([("Συνολικά αιτήματα",total),("Παραλήφθηκαν",received_count),("Σε εκκρεμότητα",pending)])

    if st.session_state.is_admin:
        with st.expander("➕ Νέο αίτημα δεδομένων"):
            with st.form("new_request",clear_on_submit=True):
                item=st.text_input("Τίτλος αιτήματος *")
                c1,c2=st.columns(2)
                category=c1.selectbox("Κατηγορία",["Οικονομικά","Προγράμματα","Portfolio","Λειτουργία","ΕΛΚΕ","Marketing","IT","Άλλο"])
                owner=c2.text_input("Υπεύθυνος")
                c1,c2=st.columns(2)
                requested=c1.date_input("Ημερομηνία αιτήματος",value=None)
                deadline=c2.date_input("Προθεσμία",value=None)
                notes=st.text_area("Σημειώσεις")
                if st.form_submit_button("Δημιουργία αιτήματος",type="primary"):
                    if not item.strip(): st.error("Ο τίτλος είναι υποχρεωτικός.")
                    else:
                        db.table("data_requests").insert({
                            "item":item.strip(),"category":category,"responsible_person":owner or None,
                            "requested_at":requested.isoformat() if requested else None,
                            "deadline":deadline.isoformat() if deadline else None,"notes":notes or None
                        }).execute()
                        st.success("Το αίτημα δημιουργήθηκε."); st.rerun()

    if total:
        c1,c2,c3=st.columns([2,1,1])
        search=c1.text_input("Αναζήτηση",placeholder="Αναζήτηση αιτήματος...")
        cat_options=["Όλες"]+sorted([x for x in requests["category"].dropna().astype(str).unique()])
        cat=c2.selectbox("Κατηγορία",cat_options)
        state=c3.selectbox("Κατάσταση",["Όλες","Σε εκκρεμότητα","Παραλήφθηκε"])
        q=requests.copy()
        if search: q=q[q["item"].fillna("").str.contains(search,case=False)]
        if cat!="Όλες": q=q[q["category"]==cat]
        if state=="Παραλήφθηκε": q=q[q["received"]==True]
        if state=="Σε εκκρεμότητα": q=q[q["received"]!=True]

        left,right=st.columns([1,1.35])
        with left:
            st.markdown("### Αιτήματα")
            if q.empty: st.info("Δεν βρέθηκαν αιτήματα.")
            else:
                options={}
                for _,r in q.iterrows():
                    icon="✅" if bool(r.get("received")) else "🕒"
                    label=f"{icon} {r.get('item','')}  ·  {r.get('category','')}"
                    options[label]=r["id"]
                selected_label=st.radio("Επιλογή αιτήματος",list(options.keys()),label_visibility="collapsed")
                selected_id=options[selected_label]

        with right:
            row=requests[requests["id"]==selected_id].iloc[0].to_dict()
            st.markdown(f"### {row.get('item','')}")
            st.caption(f"{'Παραλήφθηκε' if row.get('received') else 'Σε εκκρεμότητα'} · Κατηγορία: {row.get('category') or '—'}")
            if st.session_state.is_admin:
                with st.form("request_detail"):
                    c1,c2=st.columns(2)
                    owner=c1.text_input("Υπεύθυνος",value=str(row.get("responsible_person") or ""))
                    source=c2.text_input("Πηγή / αρχείο",value=str(row.get("source_file") or ""))
                    c1,c2=st.columns(2)
                    requested=c1.date_input("Ημερομηνία αιτήματος",value=pd.to_datetime(row.get("requested_at")).date() if row.get("requested_at") else None)
                    deadline=c2.date_input("Προθεσμία",value=pd.to_datetime(row.get("deadline")).date() if row.get("deadline") else None)
                    received=st.checkbox("Το στοιχείο έχει παραληφθεί",value=bool(row.get("received")))
                    verification=st.selectbox("Verification Status",["Pending","Verified","Needs review"],
                        index=["Pending","Verified","Needs review"].index(row.get("verification_status")) if row.get("verification_status") in ["Pending","Verified","Needs review"] else 0)
                    notes=st.text_area("Σημειώσεις",value=str(row.get("notes") or ""))
                    if st.form_submit_button("Αποθήκευση αλλαγών",type="primary"):
                        db.table("data_requests").update({
                            "responsible_person":owner or None,"source_file":source or None,
                            "requested_at":requested.isoformat() if requested else None,
                            "deadline":deadline.isoformat() if deadline else None,
                            "received":received,
                            "received_at":pd.Timestamp.now(tz="UTC").isoformat() if received and not row.get("received_at") else row.get("received_at"),
                            "verification_status":verification,"notes":notes or None
                        }).eq("id",selected_id).execute()
                        st.success("Αποθηκεύτηκε."); st.rerun()
                with st.expander("Διαγραφή αιτήματος"):
                    confirm=st.checkbox("Επιβεβαιώνω τη διαγραφή.",key="del_req_confirm")
                    if st.button("Διαγραφή",disabled=not confirm,key="del_req"):
                        db.table("data_requests").delete().eq("id",selected_id).execute()
                        st.rerun()
            else:
                c1,c2=st.columns(2)
                c1.markdown(f"**Υπεύθυνος**  \n{row.get('responsible_person') or '—'}")
                c2.markdown(f"**Πηγή**  \n{row.get('source_file') or '—'}")
                st.markdown(f"**Σημειώσεις**  \n{row.get('notes') or '—'}")
    else:
        st.info("Δεν υπάρχουν ακόμη αιτήματα στο Data Room.")

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

elif page=="Reports & Export":
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
