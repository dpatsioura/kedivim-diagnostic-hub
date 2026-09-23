import streamlit as st
import pandas as pd
import io
import uuid
from datetime import datetime, timezone
from supabase import create_client

st.set_page_config(page_title="ΚΕΔΙΒΙΜ · Diagnostic Hub", page_icon="📊", layout="wide")

@st.cache_resource
def db():
    c=st.secrets["supabase"]
    return create_client(c["url"],c["secret_key"])
sb=db()

ADMIN_EMAIL="dpatsioura@gmail.com"
if "admin" not in st.session_state: st.session_state.admin=False

def get(table, order=None, include_deleted=False):
    q=sb.table(table).select("*")
    if not include_deleted:
        q=q.is_("deleted_at","null")
    if order:q=q.order(order)
    return pd.DataFrame(q.execute().data or [])

def soft_delete(table, row_id):
    sb.table(table).update({"deleted_at":datetime.now(timezone.utc).isoformat(),"deleted_by":ADMIN_EMAIL}).eq("id",row_id).execute()

def restore_row(table, row_id):
    sb.table(table).update({"deleted_at":None,"deleted_by":None}).eq("id",row_id).execute()

def attachment_upload(entity_type, entity_id, uploaded):
    ext=Path(uploaded.name).suffix.lower()
    safe=f"{uuid.uuid4().hex}{ext}"
    path=f"{entity_type}/{entity_id}/{safe}"
    data=uploaded.getvalue()
    sb.storage.from_("kedivim-attachments").upload(path,data,{"content-type":uploaded.type or "application/octet-stream"})
    sb.table("attachments").insert({"entity_type":entity_type,"entity_id":entity_id,
        "file_name":uploaded.name,"storage_path":path,"mime_type":uploaded.type,
        "file_size":len(data),"uploaded_by":ADMIN_EMAIL}).execute()

def list_attachments(entity_type, entity_id):
    return pd.DataFrame(sb.table("attachments").select("*").eq("entity_type",entity_type).eq("entity_id",entity_id).execute().data or [])

def signed_attachment(path):
    r=sb.storage.from_("kedivim-attachments").create_signed_url(path,3600)
    return r.get("signedURL") or r.get("signedUrl")

def delete_attachment(att_id, path):
    sb.storage.from_("kedivim-attachments").remove([path])
    sb.table("attachments").delete().eq("id",att_id).execute()

def purge_row(table, entity_type, row_id):
    ats=list_attachments(entity_type,row_id)
    for _,a in ats.iterrows(): delete_attachment(a["id"],a["storage_path"])
    sb.table(table).delete().eq("id",row_id).execute()

def attachment_panel(entity_type, entity_id, key):
    st.markdown("##### 📎 Συνημμένα")
    ats=list_attachments(entity_type,entity_id)
    if len(ats):
        for _,a in ats.iterrows():
            c1,c2,c3=st.columns([5,1.2,1])
            c1.write("📎 "+str(a["file_name"]))
            try:
                c2.link_button("Προβολή",signed_attachment(a["storage_path"]),use_container_width=True)
            except:
                c2.write("—")
            if st.session_state.admin and c3.button("🗑️",key=f"attdel_{key}_{a['id']}",help="Διαγραφή αρχείου"):
                delete_attachment(a["id"],a["storage_path"]); st.rerun()
    else:
        st.caption("Δεν υπάρχουν συνημμένα.")
    if st.session_state.admin:
        fs=st.file_uploader("Προσθήκη αρχείων",type=["pdf","jpg","jpeg","png"],
                            accept_multiple_files=True,key=f"upload_{key}",
                            help="PDF, JPG, JPEG ή PNG. Μπορείς να επιλέξεις περισσότερα από ένα.")
        if fs and st.button("⬆️ Ανέβασμα αρχείων",key=f"upbtn_{key}",type="secondary"):
            for f in fs: attachment_upload(entity_type,entity_id,f)
            st.success(f"Ανέβηκαν {len(fs)} αρχεία."); st.rerun()

def upload_new_record_files(label, key):
    return st.file_uploader(label,type=["pdf","jpg","jpeg","png"],accept_multiple_files=True,key=key,
                            help="Προαιρετικά. PDF, JPG, JPEG ή PNG.")

def num(x): return pd.to_numeric(x,errors="coerce").fillna(0)
def eur(x):
    try:return f"{float(x):,.0f} €".replace(",",".")
    except:return "0 €"

def show_save_error(exc):
    msg=str(exc)
    if "duplicate key" in msg.lower() or "unique" in msg.lower():
        st.error("Υπάρχει ήδη εγγραφή με αυτά τα μοναδικά στοιχεία. Τα δεδομένα σου παραμένουν στη φόρμα.")
    else:
        st.error("Η αποθήκευση δεν ολοκληρώθηκε. Τα δεδομένα σου παραμένουν στη φόρμα για να τα διορθώσεις ή να ξαναπροσπαθήσεις.")

def reset_keys(keys):
    for k in keys:
        st.session_state.pop(k, None)

def toast_saved(message="Η εγγραφή καταχωρήθηκε επιτυχώς."):
    st.session_state["_saved_toast"]=message

if st.session_state.pop("_saved_toast",None):
    st.toast("✓ Η εγγραφή καταχωρήθηκε επιτυχώς.", icon="✅")

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
            st.caption("Οι τιμές παραμένουν στη φόρμα μέχρι να πατήσεις Αποθήκευση.")
            with st.form("new_program",clear_on_submit=False,enter_to_submit=False):
                title=st.text_input("Τίτλος προγράμματος *",key="np_title")
                c1,c2,c3=st.columns(3)
                year=c1.number_input("Έτος",2000,2100,2026,key="np_year")
                code=c2.text_input("Κωδικός",key="np_code")
                status=c3.selectbox("Status",["planned","active","completed","paused","cancelled"],key="np_status")
                lead=st.text_input("Επιστημονικός Υπεύθυνος",key="np_lead")
                c1,c2,c3=st.columns(3)
                apps=c1.number_input("Αιτήσεις",min_value=0,key="np_apps")
                enr=c2.number_input("Εγγραφές",min_value=0,key="np_enr")
                comp=c3.number_input("Ολοκλήρωσαν",min_value=0,key="np_comp")
                c1,c2=st.columns(2)
                fee=c1.number_input("Μέσο πραγματικό δίδακτρο (€)",min_value=0.0,key="np_fee")
                trainer=c2.number_input("Αμοιβές εκπαιδευτών (€)",min_value=0.0,key="np_trainer")
                notes=st.text_area("Σημειώσεις",key="np_notes")
                new_files=upload_new_record_files("📎 Επισύναψη αρχείων προγράμματος","np_files")
                submitted=st.form_submit_button("💾 Αποθήκευση",type="primary")
            if submitted:
                if not title.strip():
                    st.error("Ο τίτλος είναι υποχρεωτικός. Τα υπόλοιπα στοιχεία παραμένουν στη φόρμα.")
                else:
                    try:
                        res=sb.table("programs").insert({"program_name":title.strip(),"year":year,"code":code or None,"status":status,
                          "scientific_lead":lead or None,"applications":apps,"enrollments":enr,"completed":comp,
                          "actual_avg_tuition":fee,"trainer_fees":trainer,"notes":notes or None}).execute()
                        rid=res.data[0]["id"]
                        for f in (new_files or []): attachment_upload("program",rid,f)
                        reset_keys(["np_title","np_year","np_code","np_status","np_lead","np_apps","np_enr","np_comp","np_fee","np_trainer","np_notes","np_files"])
                        toast_saved(); st.rerun()
                    except Exception as exc: show_save_error(exc)
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
                    with st.form("edit_"+str(r["id"]),enter_to_submit=False):
                        etitle=st.text_input("Τίτλος",value=str(r.get("program_name") or ""))
                        elead=st.text_input("Επιστημονικός Υπεύθυνος",value=str(r.get("scientific_lead") or ""))
                        e1,e2,e3=st.columns(3)
                        eapps=e1.number_input("Αιτήσεις",min_value=0,value=int(r.get("applications") or 0))
                        eenr=e2.number_input("Εγγραφές",min_value=0,value=int(r.get("enrollments") or 0))
                        ecomp=e3.number_input("Ολοκλήρωσαν",min_value=0,value=int(r.get("completed") or 0))
                        e1,e2=st.columns(2)
                        efee=e1.number_input("Μέσο δίδακτρο (€)",min_value=0.0,value=float(r.get("actual_avg_tuition") or 0))
                        etrainer=e2.number_input("Αμοιβές εκπαιδευτών (€)",min_value=0.0,value=float(r.get("trainer_fees") or 0))
                        estat=st.selectbox("Status",["planned","active","completed","paused","cancelled"],index=["planned","active","completed","paused","cancelled"].index(r.get("status")) if r.get("status") in ["planned","active","completed","paused","cancelled"] else 0)
                        if st.form_submit_button("Αποθήκευση αλλαγών"):
                            sb.table("programs").update({"program_name":etitle,"scientific_lead":elead or None,
                              "applications":eapps,"enrollments":eenr,"completed":ecomp,
                              "actual_avg_tuition":efee,"trainer_fees":etrainer,"status":estat}).eq("id",r["id"]).execute();st.rerun()
                attachment_panel("program",r["id"],"program_"+str(r["id"]))
                if st.session_state.admin:
                    if st.button("🗑️ Μεταφορά στον Κάδο",key="trash_program_"+str(r["id"])):
                        soft_delete("programs",r["id"]);st.rerun()

elif page=="Οικονομικά":
    st.caption("Έσοδα, έξοδα και οικονομική εικόνα")
    tab1,tab2=st.tabs(["Έσοδα / Cash Flow","Έξοδα"])
    with tab1:
        if st.session_state.admin:
            with st.expander("➕ Νέα ετήσια οικονομική εγγραφή"):
                st.caption("Το Enter αλλάζει πεδίο/οριστικοποιεί την τιμή, δεν αποθηκεύει τη φόρμα.")
                with st.form("cash_new",clear_on_submit=False,enter_to_submit=False):
                    year=st.number_input("Έτος",2000,2100,2026,key="cf_year")
                    c1,c2=st.columns(2)
                    opening=c1.number_input("Αρχικό διαθέσιμο (€)",key="cf_open")
                    revenue=c2.number_input("Έσοδα (€)",key="cf_rev")
                    c1,c2=st.columns(2)
                    payroll=c1.number_input("Μισθοδοσία / Διοίκηση (€)",key="cf_payroll")
                    direct=c2.number_input("Άμεσα κόστη προγραμμάτων (€)",key="cf_direct")
                    c1,c2=st.columns(2)
                    op=c1.number_input("Marketing / IT / Λειτουργικά (€)",key="cf_op")
                    other=c2.number_input("Λοιπές εκροές (€)",key="cf_other")
                    new_files=upload_new_record_files("📎 Επισύναψη αρχείων οικονομικής εγγραφής","cf_files")
                    submitted=st.form_submit_button("💾 Αποθήκευση",type="primary")
                if submitted:
                    try:
                        payload={"year":year,"opening_cash":opening,"revenue":revenue,"payroll_admin":payroll,
                                 "direct_program_costs":direct,"marketing_it_operating":op,"other_outflows":other,
                                 "deleted_at":None,"deleted_by":None}
                        existing=sb.table("cash_bridge").select("id").eq("year",year).limit(1).execute().data or []
                        if existing:
                            rid=existing[0]["id"]
                            sb.table("cash_bridge").update(payload).eq("id",rid).execute()
                        else:
                            res=sb.table("cash_bridge").insert(payload).execute()
                            rid=res.data[0]["id"]
                        for f in (new_files or []): attachment_upload("cash",rid,f)
                        reset_keys(["cf_year","cf_open","cf_rev","cf_payroll","cf_direct","cf_op","cf_other","cf_files"])
                        toast_saved(); st.rerun()
                    except Exception as exc: show_save_error(exc)
        if len(cash):
            for _,r in cash.sort_values("year",ascending=False).iterrows():
                out=sum(float(r.get(c) or 0) for c in ["payroll_admin","direct_program_costs","marketing_it_operating","other_outflows"])
                with st.expander(f"💰 {int(r['year'])} · Έσοδα {eur(r.get('revenue',0))}"):
                    a,b,c=st.columns(3);a.metric("Έσοδα",eur(r.get("revenue",0)));b.metric("Εκροές",eur(out));c.metric("Net",eur(float(r.get("revenue") or 0)-out))
                    if st.session_state.admin:
                        with st.form("editcash_"+str(r["id"]),enter_to_submit=False):
                            c1,c2=st.columns(2)
                            erev=c1.number_input("Έσοδα (€)",value=float(r.get("revenue") or 0),key="rev_"+str(r["id"]))
                            eopen=c2.number_input("Αρχικό διαθέσιμο (€)",value=float(r.get("opening_cash") or 0),key="open_"+str(r["id"]))
                            if st.form_submit_button("Αποθήκευση αλλαγών"):
                                sb.table("cash_bridge").update({"revenue":erev,"opening_cash":eopen}).eq("id",r["id"]).execute();st.rerun()
                    attachment_panel("cash",r["id"],"cash_"+str(r["id"]))
                    if st.session_state.admin and st.button("🗑️ Μεταφορά στον Κάδο",key="trash_cash_"+str(r["id"])):
                        soft_delete("cash_bridge",r["id"]);st.rerun()
    with tab2:
        if st.session_state.admin:
            with st.expander("➕ Νέο έξοδο"):
                st.caption("Η φόρμα καθαρίζει μόνο μετά από επιτυχημένη αποθήκευση.")
                with st.form("cost_new",clear_on_submit=False,enter_to_submit=False):
                    desc=st.text_input("Περιγραφή *",key="ce_desc")
                    c1,c2,c3=st.columns(3)
                    year=c1.number_input("Έτος",2000,2100,2026,key="ce_year")
                    cat=c2.text_input("Κατηγορία",key="ce_cat")
                    amount=c3.number_input("Ποσό (€)",min_value=0.0,key="ce_amount")
                    new_files=upload_new_record_files("📎 Επισύναψη παραστατικών / αρχείων","ce_files")
                    submitted=st.form_submit_button("💾 Αποθήκευση εξόδου",type="primary")
                if submitted:
                    if not desc.strip():
                        st.error("Η περιγραφή είναι υποχρεωτική. Τα υπόλοιπα στοιχεία παραμένουν.")
                    else:
                        try:
                            res=sb.table("cost_base").insert({"description":desc,"year":year,"category":cat or None,"amount":amount}).execute()
                            rid=res.data[0]["id"]
                            for f in (new_files or []): attachment_upload("cost",rid,f)
                            reset_keys(["ce_desc","ce_year","ce_cat","ce_amount","ce_files"])
                            toast_saved("Το έξοδο καταχωρήθηκε επιτυχώς."); st.rerun()
                        except Exception as exc: show_save_error(exc)
        if len(costs):
            for _,r in costs.sort_values("year",ascending=False).iterrows():
                with st.expander(f"💶 {r.get('description','')} · {eur(r.get('amount',0))} · {r.get('category') or '—'}"):
                    if st.session_state.admin:
                        with st.form("editcost_"+str(r["id"]),enter_to_submit=False):
                            c1,c2=st.columns(2)
                            edesc=c1.text_input("Περιγραφή",value=str(r.get("description") or ""))
                            ecat=c2.text_input("Κατηγορία",value=str(r.get("category") or ""))
                            eamount=st.number_input("Ποσό (€)",min_value=0.0,value=float(r.get("amount") or 0),key="amt_"+str(r["id"]))
                            if st.form_submit_button("Αποθήκευση αλλαγών"):
                                sb.table("cost_base").update({"description":edesc,"category":ecat or None,"amount":eamount}).eq("id",r["id"]).execute();st.rerun()
                    attachment_panel("cost",r["id"],"cost_"+str(r["id"]))
                    if st.session_state.admin and st.button("🗑️ Μεταφορά στον Κάδο",key="trash_cost_"+str(r["id"])):
                        soft_delete("cost_base",r["id"]);st.rerun()

elif page=="Monitoring":
    st.caption("Εκκρεμότητες, actions και deadlines")
    if st.session_state.admin:
        with st.expander("➕ Νέα εκκρεμότητα"):
            st.caption("Τα στοιχεία παραμένουν μέχρι να πατήσεις Αποθήκευση.")
            with st.form("new_action",clear_on_submit=False,enter_to_submit=False):
                finding=st.text_input("Θέμα *",key="mo_finding")
                action=st.text_area("Action",key="mo_action")
                c1,c2,c3=st.columns(3)
                priority=c1.selectbox("Priority",["P1","P2","P3"],key="mo_priority")
                owner=c2.text_input("Responsible",key="mo_owner")
                due=c3.date_input("Deadline",value=None,key="mo_due")
                new_files=upload_new_record_files("📎 Επισύναψη τεκμηρίωσης","mo_files")
                submitted=st.form_submit_button("💾 Αποθήκευση",type="primary")
            if submitted:
                if not finding.strip():
                    st.error("Το θέμα είναι υποχρεωτικό. Τα υπόλοιπα στοιχεία παραμένουν.")
                else:
                    try:
                        res=sb.table("findings_actions").insert({"finding":finding,"proposed_action":action or None,"priority":priority,
                          "owner":owner or None,"due_date":due.isoformat() if due else None,"status":"Open"}).execute()
                        rid=res.data[0]["id"]
                        for f in (new_files or []): attachment_upload("monitoring",rid,f)
                        reset_keys(["mo_finding","mo_action","mo_priority","mo_owner","mo_due","mo_files"])
                        toast_saved(); st.rerun()
                    except Exception as exc: show_save_error(exc)
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
                attachment_panel("monitoring",r["id"],"mon_"+str(r["id"]))
                if st.session_state.admin and st.button("🗑️ Μεταφορά στον Κάδο",key="trash_mon_"+str(r["id"])):
                    soft_delete("findings_actions",r["id"]);st.rerun()

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
    st.caption("Κατάσταση συστήματος και Κάδος")
    st.success("Supabase: συνδεδεμένο")
    st.write("Mode:", "Admin" if st.session_state.admin else "Read only")

    st.subheader("🗑️ Κάδος")
    if not st.session_state.admin:
        st.info("Ο Κάδος είναι διαθέσιμος μόνο στον Admin.")
    else:
        configs=[
            ("Προγράμματα","programs","program","program_name"),
            ("Cash Flow","cash_bridge","cash","year"),
            ("Έξοδα","cost_base","cost","description"),
            ("Monitoring","findings_actions","monitoring","finding"),
        ]
        trashed=[]
        for label,table,etype,titlecol in configs:
            df=get(table,include_deleted=True)
            if len(df) and "deleted_at" in df:
                df=df[df["deleted_at"].notna()]
                for _,r in df.iterrows():
                    trashed.append((label,table,etype,titlecol,r))
        if not trashed:
            st.info("Ο Κάδος είναι άδειος.")
        else:
            st.warning(f"{len(trashed)} διαγραμμένες εγγραφές.")
            if st.button("⚠️ Άδειασμα Κάδου",type="secondary"):
                st.session_state["confirm_empty_trash"]=True
            if st.session_state.get("confirm_empty_trash"):
                st.error("Η ενέργεια είναι οριστική και διαγράφει και τα συνημμένα.")
                c1,c2=st.columns(2)
                if c1.button("Ναι, οριστική διαγραφή όλων"):
                    for _,table,etype,_,r in trashed: purge_row(table,etype,r["id"])
                    st.session_state["confirm_empty_trash"]=False;st.rerun()
                if c2.button("Ακύρωση"):
                    st.session_state["confirm_empty_trash"]=False;st.rerun()

            for label,table,etype,titlecol,r in trashed:
                title=str(r.get(titlecol) or "Χωρίς τίτλο")
                with st.expander(f"{label} · {title}"):
                    st.caption(f"Διαγράφηκε: {r.get('deleted_at')}")
                    c1,c2=st.columns(2)
                    if c1.button("↩️ Επαναφορά",key="restore_"+str(r["id"])):
                        restore_row(table,r["id"]);st.rerun()
                    if c2.button("❌ Οριστική διαγραφή",key="purge_"+str(r["id"])):
                        st.session_state["purge_id"]=str(r["id"])
                    if st.session_state.get("purge_id")==str(r["id"]):
                        st.error("Να διαγραφεί οριστικά η εγγραφή και τα συνημμένα της;")
                        a,b=st.columns(2)
                        if a.button("Επιβεβαίωση",key="yes_"+str(r["id"])):
                            purge_row(table,etype,r["id"]);st.session_state.pop("purge_id",None);st.rerun()
                        if b.button("Ακύρωση",key="no_"+str(r["id"])):
                            st.session_state.pop("purge_id",None);st.rerun()
