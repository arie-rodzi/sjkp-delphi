"""
Sistem Delphi SJKP — Streamlit + Google Sheets
- Pakar: log masuk -> Protokol, Profil, Borang Penilaian (sheet 1,2,3 sahaja)
- Admin: log masuk (kata laluan berbeza) -> semua + analisis CVI/CVR automatik + muat turun
Data disimpan ke Google Sheets (satu sumber; tiada kerja kumpul fail).
"""
import io
from datetime import datetime

import pandas as pd
import streamlit as st

import cvi

# ----------------------------------------------------------------------------
# ITEM POOL (sepadan dengan Soal Selidik BM + Delphi Round 1 v2)
# (kod, construct, kata_kunci, pernyataan, jenis)
# ----------------------------------------------------------------------------
ITEMS = [
    # A — kategorikal
    ("A1", "A. Latar Belakang", "Jantina", "Jantina", "cat"),
    ("A2", "A. Latar Belakang", "Umur", "Umur", "cat"),
    ("A3", "A. Latar Belakang", "Perkahwinan", "Status perkahwinan", "cat"),
    ("A4", "A. Latar Belakang", "Tanggungan", "Bilangan tanggungan", "cat"),
    ("A5", "A. Latar Belakang", "Pendidikan", "Tahap pendidikan", "cat"),
    ("A6", "A. Latar Belakang", "Jenis pendapatan", "Jenis pekerjaan / pendapatan utama", "cat"),
    ("A7", "A. Latar Belakang", "Tempoh kerja", "Tempoh pekerjaan / perniagaan", "cat"),
    ("A8", "A. Latar Belakang", "Pendapatan", "Pendapatan kasar bulanan", "cat"),
    ("A9", "A. Latar Belakang", "Komitmen", "Komitmen kewangan bulanan", "cat"),
    ("A10", "A. Latar Belakang", "Rekod kredit", "Status rekod kredit (CCRIS/CTOS)", "cat"),
    ("A11", "A. Latar Belakang", "Negeri", "Negeri kediaman", "cat"),
    # B — kategorikal
    ("B1", "B. Perumahan/Permohonan", "Pembeli pertama", "Pembeli rumah pertama", "cat"),
    ("B2", "B. Perumahan/Permohonan", "Kediaman sebelum", "Status kediaman sebelum permohonan", "cat"),
    ("B3", "B. Perumahan/Permohonan", "Jenis hartanah", "Jenis hartanah", "cat"),
    ("B4", "B. Perumahan/Permohonan", "Harga", "Julat harga hartanah", "cat"),
    ("B5", "B. Perumahan/Permohonan", "Jumlah pinjaman", "Jumlah pinjaman dipohon", "cat"),
    ("B6", "B. Perumahan/Permohonan", "Tempoh pinjaman", "Tempoh pinjaman dipohon", "cat"),
    ("B7", "B. Perumahan/Permohonan", "Jenis pembiayaan", "Jenis pembiayaan (konvensional/Islam)", "cat"),
    ("B8", "B. Perumahan/Permohonan", "Jenis SJKP", "Jenis SJKP dipohon (Madani / Standard / Tidak pasti)", "cat"),
    ("B9", "B. Perumahan/Permohonan", "Kesedaran", "Pernah dengar SJKP sebelum memohon", "cat"),
    ("B10", "B. Perumahan/Permohonan", "Sumber maklumat", "Cara mula tahu SJKP", "cat"),
    ("B11", "B. Perumahan/Permohonan", "Atribusi jaminan", "Sedar pembiayaan dijamin SJKP", "cat"),
    ("B12", "B. Perumahan/Permohonan", "Tahun mohon", "Tahun permohonan", "cat"),
    ("B13", "B. Perumahan/Permohonan", "Hasil (laluan)", "Hasil permohonan", "cat"),
    ("B14", "B. Perumahan/Permohonan", "Sejarah penolakan", "Pernah ditolak pinjaman sebelum ini", "cat"),
    ("B15", "B. Perumahan/Permohonan", "Bayaran balik", "Status bayaran balik (jika diluluskan)", "cat"),
    ("B16", "B. Perumahan/Permohonan", "Sebab ditolak", "Sebab utama ditolak (jika ditolak)", "cat"),
    ("B17", "B. Perumahan/Permohonan", "Bank", "Bank pemproses", "cat"),
    # C — Kebolehcapaian Kredit
    ("C1", "C. Kebolehcapaian Kredit", "Akses pembiayaan", "SJKP meningkatkan akses pembiayaan perumahan kepada golongan berpendapatan tidak tetap.", "likert"),
    ("C2", "C. Kebolehcapaian Kredit", "Peranan jaminan", "SJKP membolehkan pinjaman perumahan diperoleh yang sukar dicapai tanpa jaminan.", "likert"),
    ("C3", "C. Kebolehcapaian Kredit", "Kelayakan", "Kriteria kelayakan SJKP boleh dicapai oleh golongan berpendapatan tidak tetap.", "likert"),
    ("C4", "C. Kebolehcapaian Kredit", "Peluang", "SJKP meningkatkan peluang mendapat pembiayaan berbanding permohonan biasa.", "likert"),
    ("C5", "C. Kebolehcapaian Kredit", "Kesesuaian sasaran", "SJKP sesuai dengan keperluan pekerja gig, bebas dan bekerja sendiri.", "likert"),
    ("C6", "C. Kebolehcapaian Kredit", "Pembeli pertama", "SJKP memberi peluang lebih baik kepada pembeli rumah pertama.", "likert"),
    ("C7", "C. Kebolehcapaian Kredit", "Kemudahan akses", "Proses permohonan pembiayaan melalui SJKP mudah diakses.", "likert"),
    # D — Kemampuan Milik
    ("D1", "D. Kemampuan Milik", "Ansuran", "Ansuran bulanan pembiayaan SJKP berpatutan berbanding pendapatan.", "likert"),
    ("D2", "D. Kemampuan Milik", "Pendahuluan", "SJKP membolehkan pembelian dengan pendahuluan rendah atau tanpa pendahuluan.", "likert"),
    ("D3", "D. Kemampuan Milik", "Kos jaminan", "Kos jaminan SJKP (yuran atau caj) adalah berpatutan.", "likert"),
    ("D4", "D. Kemampuan Milik", "Tempoh sesuai", "Tempoh pembiayaan SJKP sesuai dengan kemampuan kewangan pemohon.", "likert"),
    ("D5", "D. Kemampuan Milik", "Margin pembiayaan", "Margin pembiayaan yang diberikan mencukupi untuk keperluan pembelian.", "likert"),
    ("D6", "D. Kemampuan Milik", "Jurang harga", "SJKP mengurangkan jurang antara kemampuan dan harga pasaran rumah.", "likert"),
    ("D7", "D. Kemampuan Milik", "Capaian rumah", "SJKP membolehkan pemilikan rumah yang sebelum ini di luar kemampuan.", "likert"),
    # E — Pengesahan & Bank
    ("E1", "E. Pengesahan & Bank", "Pengesahan pendapatan", "Pendapatan tidak tetap mudah disahkan dalam permohonan SJKP.", "likert"),
    ("E2", "E. Pengesahan & Bank", "Kesesuaian dokumen", "Dokumen yang diperlukan sesuai dengan jenis pekerjaan tidak tetap.", "likert"),
    ("E3", "E. Pengesahan & Bank", "Format pendapatan", "Format bukti pendapatan yang diminta mudah dipenuhi.", "likert"),
    ("E4", "E. Pengesahan & Bank", "Panduan permohonan", "Panduan permohonan SJKP adalah jelas dan mencukupi.", "likert"),
    ("E5", "E. Pengesahan & Bank", "Maklumat jelas", "Maklumat tentang SJKP yang disampaikan adalah jelas.", "likert"),
    ("E6", "E. Pengesahan & Bank", "Jaminan mencukupi", "Jaminan SJKP mencukupi tanpa memerlukan cagaran atau penjamin tambahan.", "likert"),
    ("E7", "E. Pengesahan & Bank", "Kesediaan bank", "Bank bersedia meluluskan permohonan yang mempunyai jaminan SJKP.", "likert"),
    ("E8", "E. Pengesahan & Bank", "Tempoh proses", "Tempoh pemprosesan pinjaman adalah memuaskan.", "likert"),
    ("E9", "E. Pengesahan & Bank", "Komunikasi bank", "Komunikasi daripada bank sepanjang proses adalah jelas.", "likert"),
    # F — Inklusi Kewangan
    ("F1", "F. Inklusi Kewangan", "Penilaian adil", "Bank menilai jenis pendapatan tidak tetap secara adil.", "likert"),
    ("F2", "F. Inklusi Kewangan", "Rekod digital", "Bank menerima rekod pendapatan digital (e-dompet, platform, e-invois).", "likert"),
    ("F3", "F. Inklusi Kewangan", "Sistem merangkumi", "SJKP menjadikan sistem kewangan formal lebih merangkumi golongan berpendapatan tidak tetap.", "likert"),
    ("F4", "F. Inklusi Kewangan", "Keyakinan", "SJKP meningkatkan keyakinan golongan tidak tetap menggunakan pembiayaan formal.", "likert"),
    ("F5", "F. Inklusi Kewangan", "Pengiktirafan", "Golongan berpendapatan tidak tetap diiktiraf sebagai peminjam yang layak melalui SJKP.", "likert"),
    ("F6", "F. Inklusi Kewangan", "Akses saksama", "SJKP menyediakan peluang pembiayaan yang lebih saksama kepada golongan terpinggir.", "likert"),
    # G — Hasil Pemilikan
    ("G1", "G. Hasil Pemilikan", "Pemilikan", "Rumah yang dibiayai melalui SJKP telah siap dan diduduki.", "likert"),
    ("G2", "G. Hasil Pemilikan", "Kepantasan", "SJKP mempercepat proses pemilikan rumah.", "likert"),
    ("G3", "G. Hasil Pemilikan", "Kestabilan", "SJKP meningkatkan kestabilan tempat tinggal keluarga.", "likert"),
    ("G4", "G. Hasil Pemilikan", "Kualiti hidup", "Kualiti hidup keluarga bertambah baik selepas pembiayaan melalui SJKP.", "likert"),
    ("G5", "G. Hasil Pemilikan", "Kejayaan milik", "SJKP membantu golongan tidak tetap berjaya memiliki rumah.", "likert"),
    ("G6", "G. Hasil Pemilikan", "Kurang sewa", "SJKP mengurangkan keperluan untuk terus menyewa.", "likert"),
    # H — Keberkesanan
    ("H1", "H. Keberkesanan", "Laluan bayaran", "SJKP menyediakan laluan bayaran balik yang praktikal.", "likert"),
    ("H2", "H. Keberkesanan", "Mekanisme berkesan", "SJKP merupakan mekanisme berkesan membantu golongan tidak tetap memperoleh pembiayaan.", "likert"),
    ("H3", "H. Keberkesanan", "Sumbangan dasar", "SJKP membantu menangani cabaran perumahan mampu milik di Malaysia.", "likert"),
    ("H4", "H. Keberkesanan", "Pemilikan mampu milik", "SJKP berkesan membantu golongan tidak tetap mencapai pemilikan rumah mampu milik.", "likert"),
    ("H5", "H. Keberkesanan", "Relevan", "SJKP relevan dengan keperluan pembeli rumah masa kini.", "likert"),
    ("H6", "H. Keberkesanan", "Kepuasan", "Manfaat yang diperoleh melalui SJKP adalah memuaskan.", "likert"),
    # T — terbuka
    ("T1", "T. Terbuka", "Kekuatan", "Kekuatan utama SJKP", "open"),
    ("T2", "T. Terbuka", "Kelemahan", "Masalah / kelemahan dihadapi", "open"),
    ("T3", "T. Terbuka", "Cadangan", "Cadangan penambahbaikan", "open"),
]
TARGETS = {"C. Kebolehcapaian Kredit": 4, "D. Kemampuan Milik": 4, "E. Pengesahan & Bank": 6,
           "F. Inklusi Kewangan": 4, "G. Hasil Pemilikan": 4, "H. Keberkesanan": 4}
META = {c: (con, kw, txt) for c, con, kw, txt, k in ITEMS}
RATED = [(c, con, kw, txt, k) for c, con, kw, txt, k in ITEMS if k in ("likert", "open")]

RESP_HEADERS = ["timestamp", "expert_id", "nama", "item_code", "construct",
                "relevance", "clarity", "essential", "decision", "comment"]
PROF_HEADERS = ["timestamp", "expert_id", "nama", "institusi", "jawatan", "bidang",
                "pengalaman", "kelayakan", "kebiasaan_sjkp", "emel"]

# ----------------------------------------------------------------------------
# UI / Tema
# ----------------------------------------------------------------------------
CSS = """
<style>
#MainMenu, footer {visibility:hidden;}
.block-container {padding-top:2.2rem; max-width:1080px;}
h1,h2,h3 {color:#1F3864;}
.hero {text-align:center; padding:8px 0 2px;}
.hero h1 {font-size:2rem; margin-bottom:2px;}
.hero p {color:#5b6472; margin-top:0;}
.sec-banner{background:linear-gradient(90deg,#1F3864,#2E5090);color:#fff;
  padding:9px 16px;border-radius:10px;font-weight:600;margin:2px 0 14px;font-size:1.02rem;}
.badge{display:inline-block;background:#EAF1F7;color:#1F3864;font-weight:700;
  font-size:.72rem;padding:2px 9px;border-radius:20px;margin-right:8px;letter-spacing:.3px;}
.kw{color:#2E5090;font-style:italic;font-size:.85rem;}
.stmt{font-size:1rem;margin:8px 0 2px;line-height:1.4;}
.stButton>button, .stFormSubmitButton>button{border-radius:9px;font-weight:600;padding:.5rem 1.2rem;}
div[data-testid="stMetric"]{background:#F4F6F9;border:1px solid #e6e9ef;
  border-radius:12px;padding:12px 16px;}
div[data-testid="stMetricValue"]{color:#1F3864;}
section[data-testid="stSidebar"]{background:#0f1f3d;}
section[data-testid="stSidebar"] * {color:#dfe6f2 !important;}
</style>
"""

SEC_LABEL = {"A": "A · Latar Belakang", "B": "B · Perumahan", "C": "C · Kebolehcapaian",
             "D": "D · Kemampuan", "E": "E · Pengesahan & Bank", "F": "F · Inklusi",
             "G": "G · Hasil", "H": "H · Keberkesanan", "T": "Terbuka"}


def grouped_items():
    g = {}
    for it in ITEMS:
        g.setdefault(it[1], []).append(it)
    return g


# ----------------------------------------------------------------------------
# Google Sheets
# ----------------------------------------------------------------------------
@st.cache_resource
def get_spreadsheet():
    import gspread
    from google.oauth2.service_account import Credentials
    scopes = ["https://www.googleapis.com/auth/spreadsheets",
              "https://www.googleapis.com/auth/drive"]
    creds = Credentials.from_service_account_info(
        dict(st.secrets["gcp_service_account"]), scopes=scopes)
    return gspread.authorize(creds).open_by_key(st.secrets["sheet_id"])


def get_ws(title, headers):
    import gspread
    ss = get_spreadsheet()
    try:
        return ss.worksheet(title)
    except gspread.WorksheetNotFound:
        w = ss.add_worksheet(title=title, rows=2000, cols=max(10, len(headers)))
        w.append_row(headers)
        return w


def read_df(title, headers):
    try:
        recs = get_ws(title, headers).get_all_records()
        return pd.DataFrame(recs) if recs else pd.DataFrame(columns=headers)
    except Exception as e:
        st.error(f"Gagal membaca '{title}': {e}")
        return pd.DataFrame(columns=headers)


# ----------------------------------------------------------------------------
# Auth
# ----------------------------------------------------------------------------
def login():
    st.markdown('<div class="hero"><h1>🏠 Sistem Delphi SJKP</h1>'
                '<p>Pengesahan kandungan soal selidik — Pusingan 1</p></div>',
                unsafe_allow_html=True)
    _, mid, _ = st.columns([1, 1.4, 1])
    with mid:
        with st.container(border=True):
            role = st.radio("Peranan", ["Pakar", "Admin"], horizontal=True)
            if role == "Pakar":
                st.caption("Pakar **tidak perlu kata laluan** — masukkan nama sahaja.")
                nama = st.text_input("Nama anda")
                if st.button("Mula menilai  →", type="primary", use_container_width=True):
                    if not nama.strip():
                        st.warning("Sila masukkan nama.")
                    else:
                        st.session_state.auth = "expert"
                        st.session_state.nama = nama.strip()
                        st.session_state.expert_id = nama.strip().lower().replace(" ", "_")
                        st.rerun()
            else:
                pwd = st.text_input("Kata laluan admin", type="password")
                if st.button("Log masuk", type="primary", use_container_width=True):
                    if pwd and pwd == st.secrets.get("admin_password"):
                        st.session_state.auth = "admin"
                        st.rerun()
                    else:
                        st.error("Kata laluan salah.")


# ----------------------------------------------------------------------------
# Expert pages
# ----------------------------------------------------------------------------
def page_protokol():
    st.header("1. Protokol")
    with st.container(border=True):
        st.markdown("""
**Strategi:** Pusingan 1 memuatkan pool item yang besar (7 calon setiap construct)
supaya statistik CVI/CVR dapat menapis dan **mengurangkan** bilangan item secara berasas.

**Skala:** Relevan & Jelas (1 = tidak … 4 = sangat) · Penting: Penting / Berguna / Tidak perlu ·
Keputusan: Kekal / Ubah / Buang.

**Konsensus:** I-CVI ≥ 0.78 (kekal) · 0.70–0.77 (ubah) · < 0.70 (buang) ·
S-CVI/Ave ≥ 0.90 · CVR ≥ nilai kritikal panel.
""")
    st.info("Seterusnya: lengkapkan **2. Profil** dan **3. Penilaian** di menu tepi.")


def page_profil():
    st.header("2. Profil Pakar")
    with st.form("profil"):
        with st.container(border=True):
            c = st.columns(2)
            institusi = c[0].text_input("Institusi / Organisasi")
            jawatan = c[1].text_input("Jawatan")
            bidang = c[0].text_input("Bidang kepakaran")
            pengalaman = c[1].text_input("Tahun pengalaman")
            kelayakan = c[0].text_input("Kelayakan tertinggi")
            kebiasaan = c[1].selectbox("Kebiasaan dengan SJKP", ["Tinggi", "Sederhana", "Rendah"])
            emel = st.text_input("E-mel")
        if st.form_submit_button("💾  Simpan profil", type="primary"):
            get_ws("profiles", PROF_HEADERS).append_row([
                datetime.now().isoformat(timespec="seconds"), st.session_state.expert_id,
                st.session_state.nama, institusi, jawatan, bidang, pengalaman,
                kelayakan, kebiasaan, emel])
            st.success("Profil disimpan. Terima kasih!")


def _item_card(code, con, kw, txt, kind):
    with st.container(border=True):
        st.markdown(f'<span class="badge">{code}</span> <span class="kw">{kw}</span>',
                    unsafe_allow_html=True)
        st.markdown(f'<div class="stmt">{txt}</div>', unsafe_allow_html=True)
        if kind in ("likert", "open"):
            c = st.columns(2)
            rel = c[0].radio("Relevan", [1, 2, 3, 4], index=2, horizontal=True, key=f"r_{code}")
            cla = c[1].radio("Jelas", [1, 2, 3, 4], index=2, horizontal=True, key=f"c_{code}")
            ess = st.radio("Penting?", ["Penting", "Berguna", "Tidak perlu"],
                           horizontal=True, key=f"e_{code}")
        else:
            rel = cla = ess = ""
        dec = st.radio("Cadangan", ["Kekal", "Ubah", "Buang"], horizontal=True, key=f"d_{code}")
        com = st.text_input("Komen (pilihan)", key=f"k_{code}", placeholder="Cadangan penambahbaikan…")
    return (con, rel, cla, ess, dec, com)


def page_penilaian():
    st.header("3. Borang Penilaian")
    st.caption("Isi ikut tab bahagian di bawah, kemudian tekan **Hantar** sekali sahaja.")
    g = grouped_items()
    with st.form("nilai"):
        answers = {}
        tab_labels = [SEC_LABEL.get(con.split(".")[0], con) for con in g]
        tabs = st.tabs(tab_labels)
        for tab, (con, its) in zip(tabs, g.items()):
            with tab:
                tgt = TARGETS.get(con)
                st.markdown(f'<div class="sec-banner">{con}'
                            + (f'  ·  sasaran kekal: {tgt} item' if tgt else '')
                            + '</div>', unsafe_allow_html=True)
                for code, c2, kw, txt, kind in its:
                    answers[code] = _item_card(code, c2, kw, txt, kind)
        st.markdown("---")
        if st.form_submit_button("✅  Hantar semua penilaian", type="primary",
                                 use_container_width=True):
            ts = datetime.now().isoformat(timespec="seconds")
            rows = [[ts, st.session_state.expert_id, st.session_state.nama, code, con,
                     rel, cla, ess, dec, com]
                    for code, (con, rel, cla, ess, dec, com) in answers.items()]
            get_ws("responses", RESP_HEADERS).append_rows(rows)
            st.success(f"{len(rows)} penilaian dihantar. Terima kasih!")
            st.balloons()


# ----------------------------------------------------------------------------
# Admin
# ----------------------------------------------------------------------------
def to_excel(dfs):
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as xl:
        for name, df in dfs.items():
            df.to_excel(xl, sheet_name=name[:31], index=False)
    return buf.getvalue()


def _style_decision(df, col="Keputusan"):
    cmap = {"Kekal": "background-color:#E4F2E4", "Ubah": "background-color:#FFF6D5",
            "Buang": "background-color:#FBE4E4"}
    if col not in df.columns:
        return df
    return df.style.apply(
        lambda s: [cmap.get(v, "") for v in s] if s.name == col else ["" for _ in s], axis=0)


def page_admin():
    st.header("📊 Panel Admin — Analisis Delphi")
    resp = read_df("responses", RESP_HEADERS)
    prof = read_df("profiles", PROF_HEADERS)
    if resp.empty:
        st.info("Belum ada maklum balas daripada pakar.")
        return
    for col in ("relevance", "clarity"):
        resp[col] = pd.to_numeric(resp[col], errors="coerce")
    n_exp = resp["expert_id"].nunique()
    c1, c2, c3 = st.columns(3)
    c1.metric("👥 Bil. pakar", n_exp)
    c2.metric("📝 Maklum balas", len(resp))
    c3.metric("🗂️ Profil", len(prof))

    meta_rated = {c: META[c] for c, *_ in RATED}
    rel_tbl = cvi.cvi_table(resp, meta_rated, "relevance")
    cla_tbl = cvi.cvi_table(resp, meta_rated, "clarity")
    cvr_tbl = cvi.cvr_table(resp, meta_rated)

    t = st.tabs(["🎯 Ringkasan", "✅ I-CVI (Relevan)", "🔤 Kejelasan",
                 "📐 CVR", "👤 Profil", "🗄️ Data mentah", "⬇️ Muat turun"])
    with t[0]:
        st.dataframe(cvi.scvi_summary(rel_tbl, TARGETS), use_container_width=True, hide_index=True)
        st.caption("S-CVI/Ave ≥ 0.90 = baik. Bandingkan **Bil. Kekal** vs **Sasaran** untuk memilih item terbaik.")
    with t[1]:
        st.dataframe(_style_decision(rel_tbl), use_container_width=True, hide_index=True)
    with t[2]:
        st.dataframe(_style_decision(cla_tbl), use_container_width=True, hide_index=True)
    with t[3]:
        crit = cvi.CVR_CRITICAL.get(n_exp)
        st.info(f"Nilai kritikal CVR (Lawshe) untuk N = {n_exp}: "
                + (f"**{crit}**" if crit else "— (N tiada dalam jadual; rujuk jadual penuh)"))
        st.dataframe(cvr_tbl, use_container_width=True, hide_index=True)
    with t[4]:
        st.dataframe(prof, use_container_width=True, hide_index=True)
    with t[5]:
        st.dataframe(resp, use_container_width=True, hide_index=True)
    with t[6]:
        xls = to_excel({"Relevan_CVI": rel_tbl, "Kejelasan_CVI": cla_tbl, "CVR": cvr_tbl,
                        "Ringkasan": cvi.scvi_summary(rel_tbl, TARGETS),
                        "Profil": prof, "Data_mentah": resp})
        st.download_button("⬇️  Muat turun analisis (.xlsx)", xls,
                           "SJKP_Delphi_Analisis.xlsx",
                           "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                           type="primary")


# ----------------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------------
def main():
    st.set_page_config(page_title="Delphi SJKP", page_icon="🏠", layout="wide")
    st.markdown(CSS, unsafe_allow_html=True)
    if "auth" not in st.session_state:
        st.session_state.auth = None
    if st.session_state.auth is None:
        login()
        return
    with st.sidebar:
        st.markdown("### 🏠 Delphi SJKP")
        st.write(f"**Peranan:** {st.session_state.auth}")
        if st.session_state.auth == "expert":
            st.write(f"**Nama:** {st.session_state.nama}")
        st.divider()
        if st.session_state.auth == "expert":
            tab = st.radio("Menu", ["1. Protokol", "2. Profil", "3. Penilaian"])
        st.divider()
        if st.button("🚪 Log keluar", use_container_width=True):
            for k in list(st.session_state.keys()):
                del st.session_state[k]
            st.rerun()
    if st.session_state.auth == "admin":
        page_admin()
    else:
        {"1. Protokol": page_protokol, "2. Profil": page_profil,
         "3. Penilaian": page_penilaian}[tab]()


if __name__ == "__main__":
    main()
