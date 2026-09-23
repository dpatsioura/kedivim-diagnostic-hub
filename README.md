# ΚΕΔΙΒΙΜ Diagnostic Hub

Streamlit prototype για την οικονομική, λειτουργική και στρατηγική διάγνωση του ΚΕΔΙΒΙΜ Πανεπιστημίου Θεσσαλίας.

## Deploy στο Streamlit Community Cloud
1. Ανέβασε όλα τα αρχεία αυτού του φακέλου στο GitHub repository.
2. Στο Streamlit Community Cloud δημιούργησε νέο app από το repository και επίλεξε `app.py`.
3. Στα Secrets του app πρόσθεσε:

```toml
[auth]
admin_password = "ΝΕΟΣ_ΚΩΔΙΚΟΣ"
```

Μην αποθηκεύσεις πραγματικό κωδικό στο GitHub.

## Σημαντικό για την έκδοση 1
Η εφαρμογή λειτουργεί ως prototype και τα δεδομένα παραμένουν στο Streamlit session. Δεν πρέπει ακόμη να χρησιμοποιηθεί ως μόνιμο αρχείο πραγματικών οικονομικών/προσωπικών δεδομένων.

## Επόμενη φάση
Persistent database (π.χ. Supabase/PostgreSQL), πλήρη questionnaires, Excel import, PDF executive report και ισχυρό authentication.
