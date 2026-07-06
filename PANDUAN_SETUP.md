# Sistem Delphi SJKP — Panduan Pemasangan

Aplikasi web (Streamlit) untuk kajian Delphi Pusingan 1. Data disimpan terus ke **Google Sheets**.
Pakar log masuk → isi Protokol/Profil/Penilaian. Admin log masuk → lihat semua + analisis CVI/CVR automatik + muat turun.

---

## Apa yang anda dapat
- `app.py` — aplikasi utama
- `cvi.py` — enjin pengiraan I-CVI / S-CVI / CVR / kappa*
- `requirements.txt` — pakej diperlukan
- `.streamlit/secrets.toml.example` — templat kata laluan & kredential

---

## Langkah 1 — Sediakan Google Sheet
1. Buka Google Sheet baharu, namakan **SJKP_Delphi**.
2. Salin **Sheet ID** dari URL:
   `https://docs.google.com/spreadsheets/d/`**`INI_SHEET_ID`**`/edit`
3. Tak perlu buat tab apa-apa — aplikasi akan cipta tab `responses` dan `profiles` secara automatik.

## Langkah 2 — Service Account (supaya app boleh tulis ke Sheet)
1. Pergi ke https://console.cloud.google.com → cipta projek (atau guna sedia ada).
2. **APIs & Services → Enable APIs**: aktifkan **Google Sheets API** dan **Google Drive API**.
3. **Credentials → Create Credentials → Service account** → siapkan.
4. Pada service account → **Keys → Add key → JSON** → muat turun fail JSON.
5. Buka fail JSON, ambil nilai `client_email` (contoh `sjkp-delphi@xxxx.iam.gserviceaccount.com`).
6. Balik ke Google Sheet anda → **Share** → tampal `client_email` tadi → beri akses **Editor**.

## Langkah 3 — Isi secrets
1. Salin `.streamlit/secrets.toml.example` → `.streamlit/secrets.toml`.
2. Isi `sheet_id`, `admin_password`, `expert_password`.
3. Salin nilai dari fail JSON service account ke bahagian `[gcp_service_account]`
   (pastikan `private_key` kekal dengan `\n`).

## Langkah 4 — Jalankan
### Lokal
```
pip install -r requirements.txt
streamlit run app.py
```
Buka http://localhost:8501

### Streamlit Community Cloud (percuma, ada URL boleh kongsi)
1. Muat naik `app.py`, `cvi.py`, `requirements.txt` ke satu repo GitHub (jangan muat naik secrets).
2. https://share.streamlit.io → New app → pilih repo → main file `app.py`.
3. **Settings → Secrets** → tampal kandungan `secrets.toml` anda → Save.
4. App akan hidup pada URL awam. Hantar URL + kata laluan pakar kepada panel.

---

## Cara guna
- **Pakar:** buka URL → pilih *Pakar* → masukkan nama + kata laluan pakar →
  isi Protokol/Profil/Penilaian → *Hantar semua penilaian*.
- **Admin:** pilih *Admin* → masukkan kata laluan admin →
  lihat tab Ringkasan, I-CVI, Kejelasan, CVR, Profil, Data mentah → *Muat turun analisis (.xlsx)*.

## Peraturan keputusan (auto)
- I-CVI ≥ 0.78 → **Kekal**; 0.70–0.77 → **Ubah**; < 0.70 → **Buang**
- S-CVI/Ave ≥ 0.90 baik
- CVR ≥ nilai kritikal Lawshe (bergantung saiz panel)
- Dalam tiap construct, kekalkan item I-CVI/CVR tertinggi sehingga capai *Sasaran*.

## Nota
- Kendall's W (ranking) untuk **Pusingan 2** — boleh ditambah kemudian.
- Sahkan julat pendapatan/harga (Bahagian A/B) dengan had kelayakan SJKP semasa.
- Keselamatan: kata laluan dalam secrets sahaja; jangan commit ke repo awam.
