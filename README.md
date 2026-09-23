# ΚΕΔΙΒΙΜ · Diagnostic Hub — FINAL UX

Changes in this build:
- All NEW-entry forms preserve entered values until explicit Save.
- Enter does not submit forms.
- Forms reset only after a successful database save.
- Failed saves keep the draft values and show a friendly error.
- Successful saves show a toast notification.
- Cash Flow year conflict is handled as update/upsert behavior rather than crashing on the unique year constraint.
- Existing attachments, edit, trash, restore and permanent-delete functionality remains.

Database prerequisite:
Run `SUPABASE_UPGRADE_CLEAN_V2.sql` once if it has not already been run.

No new secrets are required.


## UI refinement
Budget vs Actual is now card-based instead of a raw dataframe.
Each program shows:
- Budget and Actual revenue
- Budget and Actual expenses
- execution percentages and progress bars
- variance
- actual result
- expandable recent transaction details
If no budget exists, the UI explicitly says so instead of showing meaningless zeroes.
