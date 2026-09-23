import streamlit as st
import pandas as pd
import io, json
from pathlib import Path

st.set_page_config(page_title="ΚΕΔΙΒΙΜ Diagnostic Hub", page_icon="📊", layout="wide")
ADMIN_EMAIL = "dpatsioura@gmail.com"

# ---------- Helpers ----------
def empty_df(cols):
    return pd.DataFrame(columns=cols)

def num(s):
    return pd.to_numeric(s, errors="coerce").fillna(0)

def euro(x):
    try: return f"{float(x):,.0f} €".replace(",", ".")
    except: return "0 €"

def csv_bytes(df):
    return df.to_csv(index=False).encode("utf-8-sig")

def init():
    defaults = {
        "is_admin": False,
        "cash": empty_df(["Έτος","Αρχικό ταμείο","Έσοδα","Μισθοδοσία/Διοίκηση","Άμεσα κόστη προγραμμάτων","Marketing/IT/Λειτουργικά","Λοιπές εκροές"]),
        "programs": empty_df(["Έτος","Κωδικός","Πρόγραμμα/Κύκλος","Επιστημονικά Υπεύθυνος","Αιτήσεις","Εγγραφές","Ολοκλήρωσαν","Ονομαστικά δίδακτρα","Μέσο πραγματικό δίδακτρο","Αμοιβές εκπαιδευτών","Λοιπά άμεσα έξοδα","Κρατήσεις/χρεώσεις","Marketing","Διοικητική επιβάρυνση"]),
        "costs": empty_df(["Έτος","Κατηγορία","Υποκατηγορία","Περιγραφή","Σταθερό/Μεταβλητό","Ποσό","Πηγή/Αρχείο","Σημείωση"]),
        "workload": empty_df(["Ρόλος","Διαδικασία","Συχνότητα","Πλήθος/μήνα","Λεπτά/περίπτωση","Σύστημα/Αρχείο","Διπλή καταχώρηση;","Δυνατότητα αυτοματοποίησης","Σημείωση"]),
        "findings": empty_df(["ID","Πεδίο","Εύρημα","Τεκμηρίωση/Πηγή","Ριζική αιτία","Επίπτωση","Προτεραιότητα","Προτεινόμενη ενέργεια","Υπεύθυνος","Ορίζοντας","Κατάσταση","KPI επιτυχίας"]),
        "data_request": {},
        "learner_responses": empty_df(["Ημερομηνία","Πρόγραμμα","Συνολική εμπειρία","Οργάνωση","Moodle/ψηφιακά","Υποστήριξη","NPS","Σχόλιο"]),
    }
    for k,v in defaults.items():
        if k not in st.session_state: st.session_state[k]=v
init()

# ---------- Style ----------
st.markdown("""
<style>
.block-container{padding-top:1.5rem;max-width:1500px}
[data-testid="stMetric"]{border:1px solid #e6e8eb;border-radius:14px;padding:14px;background:white}
h1,h2,h3{letter-spacing:-.02em}
.small-note{color:#667085;font-size:.9rem}
</style>
""", unsafe_allow_html=True)

# ---------- Login ----------
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
                secret = st.secrets.get("auth", {}).get("admin_password", "")
                if email.strip().lower()==ADMIN_EMAIL and secret and password==secret:
                    st.session_state.is_admin=True; st.rerun()
                st.error("Μη έγκυρα στοιχεία.")

    pages=["Υγεία ΚΕΔΙΒΙΜ","Annual Cash Bridge","Program Economics","Cost Base","Admin Workload",
           "Findings & Action Plan","Data Request Room","Ερωτηματολόγια","Στρατηγικό Πλάνο","Backup / Export"]
    page=st.radio("Πλοήγηση", pages)

st.title("ΚΕΔΙΒΙΜ · Diagnostic Hub")
st.caption("Οικονομική, λειτουργική και στρατηγική αποτύπωση")

def editable(key, df):
    out=st.data_editor(df, num_rows="dynamic" if st.session_state.is_admin else "fixed",
                       disabled=not st.session_state.is_admin, use_container_width=True,
                       hide_index=True, key=f"ed_{key}")
    if st.session_state.is_admin: st.session_state[key]=out
    return out

def program_calc(df):
    d=df.copy()
    for c in ["Εγγραφές","Μέσο πραγματικό δίδακτρο","Αμοιβές εκπαιδευτών","Λοιπά άμεσα έξοδα","Κρατήσεις/χρεώσεις","Marketing","Διοικητική επιβάρυνση"]:
        if c in d: d[c]=num(d[c])
    if len(d):
        d["Εισπραχθέντα έσοδα"]=d["Εγγραφές"]*d["Μέσο πραγματικό δίδακτρο"]
        d["Άμεση συνεισφορά"]=d["Εισπραχθέντα έσοδα"]-d[["Αμοιβές εκπαιδευτών","Λοιπά άμεσα έξοδα","Κρατήσεις/χρεώσεις","Marketing"]].sum(axis=1)
        d["Καθαρή συνεισφορά"]=d["Άμεση συνεισφορά"]-d["Διοικητική επιβάρυνση"]
        d["Κατηγορία"]=d["Καθαρή συνεισφορά"].apply(lambda x:"Θετική" if x>0 else ("Break-even" if x==0 else "Επανεξέταση"))
    return d

if page=="Υγεία ΚΕΔΙΒΙΜ":
    cash, programs, work, findings = st.session_state.cash, program_calc(st.session_state.programs), st.session_state.workload, st.session_state.findings
    rev=num(cash["Έσοδα"]).sum() if len(cash) else 0
    costcols=["Μισθοδοσία/Διοίκηση","Άμεσα κόστη προγραμμάτων","Marketing/IT/Λειτουργικά","Λοιπές εκροές"]
    costs=sum(num(cash[c]).sum() for c in costcols) if len(cash) else 0
    enr=num(programs["Εγγραφές"]).sum() if len(programs) else 0
    contribution=num(programs["Καθαρή συνεισφορά"]).sum() if len(programs) and "Καθαρή συνεισφορά" in programs else 0
    hrs=(num(work["Πλήθος/μήνα"])*num(work["Λεπτά/περίπτωση"])/60).sum() if len(work) else 0
    p1=((findings["Προτεραιότητα"].astype(str)=="P1") & (~findings["Κατάσταση"].astype(str).str.lower().isin(["done","ολοκληρώθηκε"]))).sum() if len(findings) else 0
    a,b,c,d=st.columns(4); a.metric("Συνολικά έσοδα",euro(rev)); b.metric("Λειτουργικό κόστος",euro(costs)); c.metric("Εγγραφές",int(enr)); d.metric("Ανοιχτά P1",int(p1))
    a,b,c,d=st.columns(4); a.metric("Προγράμματα",len(programs)); b.metric("Καθαρή συνεισφορά",euro(contribution)); c.metric("Admin ώρες/μήνα",f"{hrs:.1f}"); d.metric("Πρόσβαση","Admin" if st.session_state.is_admin else "View only")
    st.subheader("Οικονομική εξέλιξη")
    if len(cash):
        q=cash.copy()
        for col in ["Έσοδα"]+costcols:q[col]=num(q[col])
        q["Σύνολο εκροών"]=q[costcols].sum(axis=1)
        st.bar_chart(q.set_index("Έτος")[["Έσοδα","Σύνολο εκροών"]])
    else: st.info("Περιμένει εισαγωγή πραγματικών οικονομικών στοιχείων.")

elif page=="Annual Cash Bridge":
    st.subheader(page); st.caption("Ετήσια γέφυρα ταμειακής θέσης.")
    d=editable("cash",st.session_state.cash)
    if len(d):
        q=d.copy()
        cols=["Αρχικό ταμείο","Έσοδα","Μισθοδοσία/Διοίκηση","Άμεσα κόστη προγραμμάτων","Marketing/IT/Λειτουργικά","Λοιπές εκροές"]
        for c in cols:q[c]=num(q[c])
        q["Καθαρή μεταβολή"]=q["Έσοδα"]-q[cols[2:]].sum(axis=1)
        q["Κλείσιμο ταμείου"]=q["Αρχικό ταμείο"]+q["Καθαρή μεταβολή"]
        st.dataframe(q,use_container_width=True,hide_index=True)
        st.download_button("Εξαγωγή CSV",csv_bytes(q),"cash_bridge.csv","text/csv")

elif page=="Program Economics":
    st.subheader(page); st.caption("Οικονομική απόδοση ανά πρόγραμμα/κύκλο.")
    d=editable("programs",st.session_state.programs); q=program_calc(d)
    if len(q):
        st.dataframe(q,use_container_width=True,hide_index=True)
        st.download_button("Εξαγωγή CSV",csv_bytes(q),"program_economics.csv","text/csv")

elif page=="Cost Base":
    st.subheader(page); d=editable("costs",st.session_state.costs)
    if len(d):
        total=num(d["Ποσό"]).sum(); st.metric("Συνολικό καταγεγραμμένο κόστος",euro(total))
        st.download_button("Εξαγωγή CSV",csv_bytes(d),"cost_base.csv","text/csv")

elif page=="Admin Workload":
    st.subheader(page); d=editable("workload",st.session_state.workload)
    if len(d):
        q=d.copy(); q["Ώρες/μήνα"]=num(q["Πλήθος/μήνα"])*num(q["Λεπτά/περίπτωση"])/60
        st.dataframe(q,use_container_width=True,hide_index=True)
        st.download_button("Εξαγωγή CSV",csv_bytes(q),"admin_workload.csv","text/csv")

elif page=="Findings & Action Plan":
    st.subheader(page); d=editable("findings",st.session_state.findings)
    if len(d):
        c1,c2=st.columns(2)
        with c1: st.bar_chart(d["Προτεραιότητα"].astype(str).value_counts())
        with c2: st.bar_chart(d["Κατάσταση"].astype(str).value_counts())
        st.download_button("Εξαγωγή CSV",csv_bytes(d),"findings_actions.csv","text/csv")

elif page=="Data Request Room":
    st.subheader(page)
    items=[
      "Αρχικό και τελικό διαθέσιμο ανά οικονομικό έτος","Έσοδα ανά έτος και πηγή","Έξοδα ανά κατηγορία",
      "Μισθοδοσία και διοικητικό κόστος","IT / λογισμικό / εξοπλισμός / λειτουργικά","Marketing και προώθηση",
      "Επιστροφές / διαγραφές / ανείσπρακτα","Κρατήσεις / χρεώσεις","Αιτήσεις, εγγραφές, πληρωμές και ολοκληρώσεις ανά πρόγραμμα",
      "Αμοιβές, άμεσα έξοδα, budget και τελική εκτέλεση ανά πρόγραμμα","Ενεργά / ανενεργά / ακυρωμένα προγράμματα",
      "Χρόνοι και βήματα βασικών διοικητικών διαδικασιών","Συστήματα, Excel trackers, templates και manuals",
      "Ροές ΚΕΔΙΒΙΜ ↔ ΕΛΚΕ και ανοιχτές οικονομικές εκκρεμότητες"
    ]
    for i in items:
        st.session_state.data_request.setdefault(i,False)
        st.session_state.data_request[i]=st.checkbox(i,value=st.session_state.data_request[i],disabled=not st.session_state.is_admin,key="dr"+str(abs(hash(i))))
    done=sum(st.session_state.data_request.values()); st.progress(done/len(items)); st.caption(f"{done}/{len(items)} διαθέσιμα")

elif page=="Ερωτηματολόγια":
    st.subheader(page)
    t1,t2=st.tabs(["Διοικητικό προσωπικό","Εκπαιδευόμενοι"])
    with t1:
        st.markdown("""Η διαγνωστική έρευνα διοικητικού προσωπικού οργανώνεται σε 10 άξονες: ρόλος και πραγματική εργασία, χρόνος και φόρτος, νέα προγράμματα/κύκλοι, αιτήσεις/εγγραφές/δίδακτρα, οικονομική πληροφορία, marketing, συστήματα/Moodle, συνεργασία με ΕΛΚΕ, ανθεκτικότητα λειτουργίας και προτάσεις.""")
        st.info("Η πλήρης φόρμα θα συνδεθεί με την κεντρική βάση δεδομένων στην επόμενη έκδοση.")
    with t2:
        st.markdown("Ανώνυμη αποτύπωση learner journey: επιλογή, εγγραφή, πληρωμή, μαθησιακή εμπειρία, Moodle, υποστήριξη και πρόθεση σύστασης/επανάληψης.")
        with st.form("learner"):
            prog=st.text_input("Πρόγραμμα")
            overall=st.slider("Συνολική εμπειρία",1,5,4)
            org=st.slider("Οργάνωση",1,5,4); moodle=st.slider("Moodle / ψηφιακή εμπειρία",1,5,4); support=st.slider("Υποστήριξη",1,5,4)
            nps=st.slider("Πιθανότητα σύστασης",0,10,8); comment=st.text_area("Σχόλιο")
            submit=st.form_submit_button("Υποβολή")
            if submit:
                st.warning("Demo mode: η μόνιμη αποθήκευση ενεργοποιείται μόλις συνδεθεί database.")

elif page=="Στρατηγικό Πλάνο":
    st.subheader("Στρατηγικό Πλάνο Διάγνωσης, Σταθεροποίησης και Ανάπτυξης")
    st.markdown("""
#### 1. Financial Diagnostic
Έσοδα, έξοδα, ταμειακή εικόνα, υποχρεώσεις και ιστορική εξέλιξη.

#### 2. Program Economics
Contribution, καθαρή συνεισφορά και break-even ανά πρόγραμμα και κύκλο.

#### 3. Operational Audit
Χρόνος, διπλές καταχωρήσεις, ασάφειες ευθύνης, process maps, workload map και quick wins.

#### 4. Growth Engine
Marketing funnel, portfolio strategy, συνεργασίες, corporate training, χρηματοδοτούμενες δράσεις, επανάληψη επιτυχημένων κύκλων και αξιοποίηση της βάσης εκπαιδευομένων.

#### Πλάνο πρώτων 30 ημερών
Ημέρες 1–5: Data Room και inventory  
Ημέρες 5–10: Ερωτηματολόγια  
Ημέρες 7–15: Interviews και workflows  
Ημέρες 10–20: Financial reconciliation και Program Economics  
Ημέρες 15–25: Marketing, website, systems και ΕΛΚΕ audit  
Ημέρες 25–30: Σύνθεση, προτεραιοποίηση και quick wins

#### Κανόνας τεκμηρίωσης
Κανένα κρίσιμο συμπέρασμα δεν βασίζεται σε μία μόνο πηγή. Τα οικονομικά ευρήματα συμφωνούνται με πρωτογενή δεδομένα και τα λειτουργικά ευρήματα διασταυρώνονται.
""")

elif page=="Backup / Export":
    st.subheader(page)
    st.warning("Η τρέχουσα έκδοση είναι prototype. Τα δεδομένα του session δεν αποτελούν ακόμη μόνιμη database.")
    tables={"cash":st.session_state.cash,"programs":st.session_state.programs,"costs":st.session_state.costs,"workload":st.session_state.workload,"findings":st.session_state.findings}
    out=io.BytesIO()
    with pd.ExcelWriter(out,engine="openpyxl") as w:
        for name,df in tables.items(): df.to_excel(w,sheet_name=name[:31],index=False)
    st.download_button("Λήψη συνολικού Excel backup",out.getvalue(),"KEDIVIM_Diagnostic_Backup.xlsx","application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    st.markdown("### Επόμενη αναβάθμιση")
    st.write("Persistent database, πλήρη questionnaires, Excel import, PDF executive report και ασφαλέστερο authentication.")

st.divider()
st.caption("ΚΕΔΙΒΙΜ Πανεπιστημίου Θεσσαλίας · Diagnostic Hub 2026")
