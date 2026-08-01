# credentials/

Put your Google service account JSON key here as `service-account.json`
(or point `GOOGLE_SHEETS_CREDENTIALS_FILE` in `.env` at a different path).

**Never commit the key file** — `*.json` in this folder is gitignored, but
this README is deliberately not (so the folder isn't empty and its purpose
is documented). See the main [README](../README.md#setting-up-google-sheets)
for the full setup walkthrough: creating the Google Cloud project, the
service account, and sharing your Sheet with it.
