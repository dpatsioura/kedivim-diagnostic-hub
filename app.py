import streamlit as st
import pandas as pd
import io
from supabase import create_client

st.set_page_config(page_title="ΚΕΔΙΒΙΜ · Diagnostic Hub", page_icon="📊", layout="wide")

@st.cache_resource
def db():
    c=st.secrets["supabase"]
    return create_client(c["url"],c["secret_key"])
sb=db()

ADMIN_EMAIL="dpatsioura@gmail.com"
if "admin" not in st.session_state: st.session_state.admin=False

def get(table, order=None):
    q=sb.table(table).select("*")
    if order:q=q.order(order)
    return pd.DataFrame(q.execute().data or [])

def num(x): return pd.to_numeric(x,errors="coerce").fillna(0)
def eur(x):
    try:return f"{float(x):,.0f} €".replace(",",".")
    except:return "0 €"

st.markdown("""
<style>
.block-container{padding-top:1rem;max-width:1450px}
[data-testid="stSidebar"]{background:#f8fafc;border-right:1px solid #e8edf3}
[data-testid="stSidebar"] img{max-width:220px;margin:0 auto 14px auto;display:block}
[data-testid="stMetric"]{background:white;border:1px solid #e7ebf0;border-radius:14px;padding:15px;box-shadow:0 2px 10px rgba(15,23,42,.035)}
[data-testid="stForm"],div[data-testid="stExpander"]{border:1px solid #e7ebf0!important;border-radius:14px!important}
.stButton>button{border-radius:9px;font-weight:600}
h1,h2,h3{letter-spacing:-.025em}
</style>
""",unsafe_allow_html=True)

with st.sidebar:
    st.image("assets/kedivim_uth_logo.jpg",use_container_width=True)
    st.markdown("### Diagnostic Hub")
    pages=["Dashboard","Προγράμματα","Οικονομικά","Monitoring","Reports","Ρυθμίσεις"]
    page=st.radio("Menu",pages,label_visibility="collapsed")
    st.divider()
    if st.session_state.admin:
        st.success("Admin")
        if st.button("Αποσύνδεση",use_container_width=True):
            st.session_state.admin=False;st.rerun()
    else:
        with st.expander("Admin login"):
            email=st.text_input("Email")
            pw=st.text_input("Κωδικός",type="password")
            if st.button("Σύνδεση",use_container_width=True):
                if email.strip().lower()==ADMIN_EMAIL and pw==st.secrets.get("auth",{}).get("admin_password",""):
                    st.session_state.admin=True;st.rerun()
                st.error("Μη έγκυρα στοιχεία")

try:
    programs=get("programs","year")
    cash=get("cash_bridge","year")
    costs=get("cost_base","year")
    findings=get("findings_actions")
except Exception as e:
    st.error("Δεν ήταν δυνατή η σύνδεση με τη βάση.")
    st.stop()

st.title("ΚΕΔΙΒΙΜ · Diagnostic Hub")

if page=="Dashboard":
    st.caption("Συνοπτική εικόνα δραστηριότητας και οικονομικής πορείας")
    revenue=num(cash["revenue"]).sum() if len(cash) else 0
    cash_out=sum(num(cash[c]).sum() for c in ["payroll_admin","direct_program_costs","marketing_it_operating","other_outflows"] if c in cash) if len(cash) else 0
    extra_cost=num(costs["amount"]).sum() if len(costs) else 0
    enroll=num(programs["enrollments"]).sum() if len(programs) else 0
    open_actions=len(findings[~findings["status"].fillna("").str.lower().isin(["done","ολοκληρώθηκε"])]) if len(findings) else 0
    a,b,c,d,e=st.columns(5)
    a.metric("Προγράμματα",len(programs)); b.metric("Εγγραφές",int(enroll))
    c.metric("Έσοδα",eur(revenue)); d.metric("Έξοδα",eur(cash_out+extra_cost)); e.metric("Καθαρό αποτέλεσμα",eur(revenue-cash_out-extra_cost))
    if len(cash):
        q=cash.copy()
        q["Έσοδα"]=num(q["revenue"])
        q["Έξοδα"]=sum((num(q[c]) for c in ["payroll_admin","direct_program_costs","marketing_it_operating","other_outflows"]),start=pd.Series(0,index=q.index))
        st.subheader("Οικονομική πορεία")
        st.bar_chart(q.set_index("year")[["Έσοδα","Έξοδα"]])
    c1,c2=st.columns(2)
    with c1:
        st.subheader("Πρόσφατα προγράμματα")
        if len(programs):
            for _,r in programs.sort_values("created_at",ascending=False).head(5).iterrows():
                st.write(f"• {r.get('program_name','')} · {r.get('status') or '—'}")
        else: st.info("Δεν υπάρχουν ακόμη προγράμματα.")
    with c2:
        st.subheader("Εκκρεμότητες")
        if open_actions:
            for _,r in findings[~findings["status"].fillna("").str.lower().isin(["done","ολοκληρώθηκε"])].head(5).iterrows():
                st.write(f"• {r.get('finding','')} · {r.get('priority') or '—'}")
        else: st.info("Δεν υπάρχουν ανοιχτές εκκρεμότητες.")

elif page=="Προγράμματα":
    st.caption("Μητρώο προγραμμάτων και κύκλων")
    if st.session_state.admin:
        with st.expander("➕ Νέο πρόγραμμα / κύκλος",expanded=False):
            with st.form("new_program",clear_on_submit=True):
                title=st.text_input("Τίτλος προγράμματος *")
                c1,c2,c3=st.columns(3)
                year=c1.number_input("Έτος",2000,2100,2026); code=c2.text_input("Κωδικός"); status=c3.selectbox("Status",["planned","active","completed","paused","cancelled"])
                lead=st.text_input("Επιστημονικός Υπεύθυνος")
                c1,c2,c3=st.columns(3)
                apps=c1.number_input("Αιτήσεις",min_value=0); enr=c2.number_input("Εγγραφές",min_value=0); comp=c3.number_input("Ολοκλήρωσαν",min_value=0)
                c1,c2=st.columns(2)
                fee=c1.number_input("Μέσο πραγματικό δίδακτρο (€)",min_value=0.0); trainer=c2.number_input("Αμοιβές εκπαιδευτών (€)",min_value=0.0)
                notes=st.text_area("Σημειώσεις")
                if st.form_submit_button("Αποθήκευση",type="primary"):
                    if not title.strip():st.error("Ο τίτλος είναι υποχρεωτικός.")
                    else:
                        sb.table("programs").insert({"program_name":title.strip(),"year":year,"code":code or None,"status":status,
                          "scientific_lead":lead or None,"applications":apps,"enrollments":enr,"completed":comp,
                          "actual_avg_tuition":fee,"trainer_fees":trainer,"notes":notes or None}).execute()
                        st.success("Αποθηκεύτηκε.");st.rerun()
    search=st.text_input("Αναζήτηση προγράμματος")
    q=programs.copy()
    if search and len(q):
        q=q[q["program_name"].fillna("").str.contains(search,case=False)]
    if len(q):
        for _,r in q.sort_values("year",ascending=False).iterrows():
            with st.expander(f"📘 {r.get('program_name','')} · {r.get('year','')} · {r.get('status') or '—'}"):
                c1,c2,c3,c4=st.columns(4)
                c1.metric("Αιτήσεις",int(r.get("applications") or 0));c2.metric("Εγγραφές",int(r.get("enrollments") or 0))
                c3.metric("Ολοκλήρωσαν",int(r.get("completed") or 0));c4.metric("Revenue",eur((r.get("enrollments") or 0)*(r.get("actual_avg_tuition") or 0)))
                st.write("Επιστημονικός Υπεύθυνος:",r.get("scientific_lead") or "—")
                if st.session_state.admin:
                    with st.form("edit_"+str(r["id"])):
                        e1,e2=st.columns(2)
                        eenr=e1.number_input("Εγγραφές",min_value=0,value=int(r.get("enrollments") or 0))
                        efee=e2.number_input("Μέσο δίδακτρο (€)",min_value=0.0,value=float(r.get("actual_avg_tuition") or 0))
                        estat=st.selectbox("Status",["planned","active","completed","paused","cancelled"],index=["planned","active","completed","paused","cancelled"].index(r.get("status")) if r.get("status") in ["planned","active","completed","paused","cancelled"] else 0)
                        if st.form_submit_button("Αποθήκευση αλλαγών"):
                            sb.table("programs").update({"enrollments":eenr,"actual_avg_tuition":efee,"status":estat}).eq("id",r["id"]).execute();st.rerun()

elif page=="Οικονομικά":
    st.caption("Έσοδα, έξοδα και οικονομική εικόνα")
    tab1,tab2=st.tabs(["Έσοδα / Cash Flow","Έξοδα"])
    with tab1:
        if st.session_state.admin:
            with st.expander("➕ Νέα ετήσια οικονομική εγγραφή"):
                with st.form("cash_new",clear_on_submit=True):
                    year=st.number_input("Έτος",2000,2100,2026,key="cy")
                    c1,c2=st.columns(2); opening=c1.number_input("Αρχικό διαθέσιμο (€)"); revenue=c2.number_input("Έσοδα (€)")
                    c1,c2=st.columns(2); payroll=c1.number_input("Μισθοδοσία / Διοίκηση (€)"); direct=c2.number_input("Άμεσα κόστη προγραμμάτων (€)")
                    c1,c2=st.columns(2); op=c1.number_input("Marketing / IT / Λειτουργικά (€)"); other=c2.number_input("Λοιπές εκροές (€)")
                    if st.form_submit_button("Αποθήκευση",type="primary"):
                        sb.table("cash_bridge").insert({"year":year,"opening_cash":opening,"revenue":revenue,"payroll_admin":payroll,
                          "direct_program_costs":direct,"marketing_it_operating":op,"other_outflows":other}).execute();st.rerun()
        if len(cash):
            for _,r in cash.sort_values("year",ascending=False).iterrows():
                out=sum(float(r.get(c) or 0) for c in ["payroll_admin","direct_program_costs","marketing_it_operating","other_outflows"])
                with st.expander(f"💰 {int(r['year'])} · Έσοδα {eur(r.get('revenue',0))}"):
                    a,b,c=st.columns(3);a.metric("Έσοδα",eur(r.get("revenue",0)));b.metric("Εκροές",eur(out));c.metric("Net",eur(float(r.get("revenue") or 0)-out))
    with tab2:
        if st.session_state.admin:
            with st.expander("➕ Νέο έξοδο"):
                with st.form("cost_new",clear_on_submit=True):
                    desc=st.text_input("Περιγραφή *");c1,c2,c3=st.columns(3)
                    year=c1.number_input("Έτος",2000,2100,2026,key="costyear");cat=c2.text_input("Κατηγορία");amount=c3.number_input("Ποσό (€)",min_value=0.0)
                    if st.form_submit_button("Αποθήκευση εξόδου",type="primary"):
                        if desc.strip():
                            sb.table("cost_base").insert({"description":desc,"year":year,"category":cat or None,"amount":amount}).execute();st.rerun()
        if len(costs):
            for _,r in costs.sort_values("year",ascending=False).iterrows():
                st.write(f"💶 {r.get('description','')} · {eur(r.get('amount',0))} · {r.get('category') or '—'}")

elif page=="Monitoring":
    st.caption("Εκκρεμότητες, actions και deadlines")
    if st.session_state.admin:
        with st.expander("➕ Νέα εκκρεμότητα"):
            with st.form("new_action",clear_on_submit=True):
                finding=st.text_input("Θέμα *");action=st.text_area("Action")
                c1,c2,c3=st.columns(3);priority=c1.selectbox("Priority",["P1","P2","P3"]);owner=c2.text_input("Responsible");due=c3.date_input("Deadline",value=None)
                if st.form_submit_button("Αποθήκευση",type="primary"):
                    if finding.strip():
                        sb.table("findings_actions").insert({"finding":finding,"proposed_action":action or None,"priority":priority,
                          "owner":owner or None,"due_date":due.isoformat() if due else None,"status":"Open"}).execute();st.rerun()
    if len(findings):
        filt=st.selectbox("Filter",["Όλα","Open","In progress","Done"])
        q=findings if filt=="Όλα" else findings[findings["status"]==filt]
        for _,r in q.iterrows():
            with st.expander(f"🚩 {r.get('priority') or ''} · {r.get('finding','')}"):
                st.write("Action:",r.get("proposed_action") or "—")
                st.write("Responsible:",r.get("owner") or "—"," | Deadline:",r.get("due_date") or "—")
                if st.session_state.admin:
                    status=st.selectbox("Status",["Open","In progress","Done"],index=["Open","In progress","Done"].index(r.get("status")) if r.get("status") in ["Open","In progress","Done"] else 0,key="s"+str(r["id"]))
                    if st.button("Update",key="u"+str(r["id"])):
                        sb.table("findings_actions").update({"status":status}).eq("id",r["id"]).execute();st.rerun()

elif page=="Reports":
    st.caption("Εξαγωγές και αντίγραφα δεδομένων")
    out=io.BytesIO()
    with pd.ExcelWriter(out,engine="openpyxl") as w:
        programs.to_excel(w,sheet_name="Προγράμματα",index=False)
        cash.to_excel(w,sheet_name="Cash Flow",index=False)
        costs.to_excel(w,sheet_name="Έξοδα",index=False)
        findings.to_excel(w,sheet_name="Monitoring",index=False)
    st.download_button("⬇️ Λήψη συνολικού Excel",out.getvalue(),"KEDIVIM_Monitoring.xlsx","application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    st.info("Τα PDF executive reports θα προστεθούν όταν υπάρχουν αρκετά πραγματικά δεδομένα για ουσιαστική αναφορά.")

elif page=="Ρυθμίσεις":
    st.caption("Κατάσταση συστήματος")
    st.success("Supabase: συνδεδεμένο")
    st.write("Mode:", "Admin" if st.session_state.admin else "Read only")
    st.write("Η εφαρμογή χρησιμοποιεί το υπάρχον Supabase project και τα Streamlit Secrets.")
