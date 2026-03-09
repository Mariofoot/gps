#!/usr/bin/env python3
"""
Stáhne všechna CSV z Google Drive složky do /data/
Přeskočí soubory které už existují.
Vygeneruje data/index.json se seznamem všech CSV.
"""
import os, json, pathlib
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
import io

SCOPES     = ['https://www.googleapis.com/auth/drive.readonly']
SA_JSON    = os.environ['GDRIVE_SERVICE_ACCOUNT']
FOLDER_ID  = os.environ['GDRIVE_FOLDER_ID']
OUTPUT_DIR = pathlib.Path('data')
OUTPUT_DIR.mkdir(exist_ok=True)

# Autentizace
sa_info = json.loads(SA_JSON)
creds   = service_account.Credentials.from_service_account_info(sa_info, scopes=SCOPES)
service = build('drive', 'v3', credentials=creds)

# Stažení CSV
existing = {f.name for f in OUTPUT_DIR.glob('*.csv')}

results = service.files().list(
    q=f"'{FOLDER_ID}' in parents and mimeType='text/csv' and trashed=false",
    fields="files(id, name, modifiedTime)",
    orderBy="modifiedTime desc",
    pageSize=1000
).execute()

files      = results.get('files', [])
downloaded = 0
skipped    = 0

print(f"📁 Nalezeno {len(files)} CSV souborů v Drive")

for f in files:
    fname = f['name']
    fpath = OUTPUT_DIR / fname

    if fname in existing:
        print(f"  ⏭  Přeskočeno: {fname}")
        skipped += 1
        continue

    print(f"  ⬇  Stahuji: {fname}")
    request = service.files().get_media(fileId=f['id'])
    buf = io.BytesIO()
    dl  = MediaIoBaseDownload(buf, request)
    done = False
    while not done:
        _, done = dl.next_chunk()

    fpath.write_bytes(buf.getvalue())
    downloaded += 1

# Vygeneruj index.json se všemi CSV soubory
all_csv = sorted([f.name for f in OUTPUT_DIR.glob('*.csv')])
index   = {"files": all_csv, "count": len(all_csv)}
(OUTPUT_DIR / 'index.json').write_text(json.dumps(index, ensure_ascii=False, indent=2))

print(f"\n✅ Hotovo — staženo: {downloaded}, přeskočeno: {skipped}")
print(f"📋 index.json aktualizován — celkem {len(all_csv)} CSV souborů")
