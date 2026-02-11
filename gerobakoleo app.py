import streamlit as st
import json
import os
import requests
import pandas as pd
from datetime import datetime
from openpyxl.styles import Font, Alignment, Border, Side, PatternFill
import openpyxl

# ================= KONFIGURASI (EDIT DISINI) =================
TOKEN_BOT = "8285539149:AAHQd-_W9aaBGSz3AUPg0oCuxabZUL6yJo4"  # 👈 GANTI DENGAN TOKEN ANDA
ID_OWNER  = "8505488457"
PIN_OWNER = "8888"

# ================= DATABASE & FILE =================
FILE_DB_GEROBAK = "database_gerobak.json"
FILE_DB_STAFF   = "database_staff.json"
FILE_DB_MENU    = "database_menu.json"
FILE_DB_LOKASI  = "database_lokasi.json"
FILE_EXCEL_REP  = "LAPORAN_GEROBAK_FINAL.xlsx"

# Default Data
MENU_DEFAULT = {"Strawberry Milk": 10000, "Coklat Milk": 12000, "Kopi Aren": 15000}
LOKASI_DEFAULT = {"1": "Gerobak Alun-Alun", "2": "Gerobak Stasiun"}

# ================= FUNGSI BANTUAN =================
def kirim_telegram(pesan):
    if TOKEN_BOT == "PASTE_TOKEN_BOT_ANDA_DISINI": return
    try:
        requests.post(f"https://api.telegram.org/bot{TOKEN_BOT}/sendMessage", 
                      data={"chat_id": ID_OWNER, "text": pesan, "parse_mode": "Markdown"})
    except: pass

def kirim_file_excel_telegram():
    if TOKEN_BOT == "PASTE_TOKEN_BOT_ANDA_DISINI": return
    if os.path.exists(FILE_EXCEL_REP):
        try:
            with open(FILE_EXCEL_REP, 'rb') as f:
                requests.post(f"https://api.telegram.org/bot{TOKEN_BOT}/sendDocument", 
                              data={'chat_id': ID_OWNER, 'caption': '📊 Laporan Excel Lengkap'}, files={'document': f})
        except: pass

def format_rupiah(angka):
    return f"Rp {int(angka):,}".replace(",", ".")

def load_json(filename):
    if os.path.exists(filename):
        try:
            with open(filename, 'r') as f: return json.load(f)
        except: return {}
    return {}

def save_json(filename, data):
    with open(filename, 'w') as f: json.dump(data, f, indent=4)

def get_data(filename, default):
    data = load_json(filename)
    if not data:
        save_json(filename, default); return default
    return data

# ================= EXCEL RAPI =================
def rapikan_excel(filename):
    try:
        wb = openpyxl.load_workbook(filename)
        ws = wb.active
        header_fill = PatternFill(start_color="1F4E78", end_color="1F4E78", fill_type="solid")
        font_white = Font(bold=True, color="FFFFFF")
        border = Border(left=Side(style='thin'), right=Side(style='thin'), top=Side(style='thin'), bottom=Side(style='thin'))
        
        for cell in ws[1]:
            cell.fill = header_fill
            cell.font = font_white
            cell.alignment = Alignment(horizontal="center", vertical="center")
            cell.border = border

        for col in ws.columns:
            max_len = 0
            col_letter = col[0].column_letter
            for cell in col:
                cell.border = border
                try:
                    if len(str(cell.value)) > max_len: max_len = len(str(cell.value))
                except: pass
                header = ws[f"{col_letter}1"].value
                if header and any(x in str(header).upper() for x in ['HARGA', 'OMZET', 'TUNAI', 'QRIS', 'TOTAL']):
                    cell.number_format = '#,##0 "Rp"'
            ws.column_dimensions[col_letter].width = (max_len + 4)
        wb.save(filename)
    except: pass

def simpan_laporan_excel(list_data):
    try:
        df_new = pd.DataFrame(list_data)
        cols = ["TANGGAL", "JAM_LAPOR", "LOKASI", "STAFF", "JAM_MASUK", "JAM_PLG", 
                "ITEM_MENU", "HARGA", "STOK_AWAL", "SISA_STOK", "TERJUAL", "TOTAL_OMZET", 
                "SETOR_TUNAI", "SETOR_QRIS", "CATATAN"]
        for c in cols:
            if c not in df_new.columns: df_new[c] = "-"
        df_new = df_new[cols]
        if os.path.exists(FILE_EXCEL_REP):
            df_old = pd.read_excel(FILE_EXCEL_REP)
            df_final = pd.concat([df_old, df_new], ignore_index=True)
        else:
            df_final = df_new
        df_final.to_excel(FILE_EXCEL_REP, index=False)
        rapikan_excel(FILE_EXCEL_REP)
        return True
    except: return False

# ================= APLIKASI UTAMA =================
def main():
    st.set_page_config(page_title="Sistem Gerobak V3", page_icon="🥤")
    if TOKEN_BOT == "PASTE_TOKEN_BOT_ANDA_DISINI":
        st.error("⚠️ TOKEN BELUM DIISI! Edit file app.py baris ke-10."); st.stop()

    MENU = get_data(FILE_DB_MENU, MENU_DEFAULT)
    LOKASI = get_data(FILE_DB_LOKASI, LOKASI_DEFAULT)
    STAFF = load_json(FILE_DB_STAFF)
    GEROBAK = load_json(FILE_DB_GEROBAK)

    if 'user' not in st.session_state: st.session_state['user'] = None
    if 'pin' not in st.session_state: st.session_state['pin'] = None

    # --- SIDEBAR LOGIN ---
    with st.sidebar:
        st.header("🔐 Login")
        if not st.session_state['user']:
            p = st.text_input("PIN", type="password", max_chars=6)
            if st.button("Masuk"):
                if p == PIN_OWNER: st.session_state['user']="OWNER"; st.session_state['pin']=p; st.rerun()
                elif p in STAFF: st.session_state['user']=STAFF[p]; st.session_state['pin']=p; st.rerun()
                else: st.error("PIN Salah")
            st.divider()
            st.write("Daftar Staff:")
            n_b = st.text_input("Nama"); p_b = st.text_input("PIN Baru")
            if st.button("Daftar"):
                ds = load_json(FILE_DB_STAFF); ds[p_b]=n_b; save_json(FILE_DB_STAFF, ds); st.rerun()
        else:
            st.success(f"👤 {st.session_state['user']}")
            if st.button("Keluar"): st.session_state['user']=None; st.rerun()

    if st.session_state['user']:
        user = st.session_state['user']
        pin = st.session_state['pin']

        if user == "OWNER":
            st.warning("🔧 **ADMIN PANEL**")
            t1, t2 = st.tabs(["Gerobak", "Menu"])
            with t1:
                for id_l, nm_l in LOKASI.items():
                    inf = GEROBAK.get(nm_l)
                    st.write(f"{nm_l}: {'🔴 AKTIF' if inf else '🟢 KOSONG'}")
                    if inf and st.button(f"Reset {nm_l}"): del GEROBAK[nm_l]; save_json(FILE_DB_GEROBAK, GEROBAK); st.rerun()
                st.write("---")
                id_b = st.text_input("ID Lokasi"); nm_b = st.text_input("Nama Gerobak")
                if st.button("Tambah Lokasi"): 
                    dl = get_data(FILE_DB_LOKASI, LOKASI_DEFAULT); dl[id_b]=nm_b; save_json(FILE_DB_LOKASI, dl); st.rerun()
            with t2:
                st.dataframe(pd.DataFrame(list(MENU.items()), columns=['Menu','Harga']), hide_index=True)
                m_n = st.text_input("Menu Baru"); h_n = st.number_input("Harga", step=500)
                if st.button("Simpan Menu"): MENU[m_n]=int(h_n); save_json(FILE_DB_MENU, MENU); st.rerun()

        # === OPERASIONAL ===
        st.title("🥤 Kasir Gerobak")
        lokasi = st.selectbox("Lokasi:", list(LOKASI.values()))
        shift = GEROBAK.get(lokasi)

        tb1, tb2 = st.tabs(["☀️ OPENING", "🌙 CLOSING"])

        with tb1:
            if shift and shift['pin_pic'] != pin: st.error("Gerobak sedang dipakai staff lain.")
            else:
                with st.form("op"):
                    st.write("📦 **Stok Awal:**")
                    stok_in = {}
                    for m in MENU:
                        val = shift['stok'].get(m, 0) if shift else 0
                        stok_in[m] = st.number_input(f"{m}", value=int(val), min_value=0)
                    if st.form_submit_button("SIMPAN OPENING"):
                        jm = datetime.now().strftime("%H:%M")
                        GEROBAK[lokasi] = {"tanggal": datetime.now().strftime("%d-%m-%Y"), "jam_masuk": shift['jam_masuk'] if shift else jm, "pic": user, "pin_pic": pin, "stok": stok_in}
                        save_json(FILE_DB_GEROBAK, GEROBAK)
                        kirim_telegram(f"☀️ *OPENING* {lokasi}\n👤 {user}\n🕒 {jm}"); st.rerun()

        with tb2:
            if not shift: st.info("Isi stok awal dulu.")
            elif shift['pin_pic'] != pin: st.error("Bukan shift Anda.")
            else:
                with st.form("cl"):
                    st.write("📊 **Hitung Jualan:**")
                    list_excel = []
                    txt_jual = []  # List barang laku
                    txt_stok = []  # List sisa stok
                    total_omzet = 0
                    tgl = datetime.now().strftime("%d-%m-%Y")
                    jam_plg = datetime.now().strftime("%H:%M")
                    
                    for item, harga in MENU.items():
                        awal = int(shift['stok'].get(item, 0))
                        sisa = st.number_input(f"Sisa {item} (Awal: {awal})", min_value=0, max_value=awal)
                        laku = awal - sisa
                        duit = laku * harga
                        total_omzet += duit
                        
                        list_excel.append({
                            "TANGGAL": tgl, "JAM_LAPOR": jam_plg, "LOKASI": lokasi, "STAFF": user,
                            "JAM_MASUK": shift['jam_masuk'], "JAM_PLG": jam_plg,
                            "ITEM_MENU": item, "HARGA": harga, "STOK_AWAL": awal, "SISA_STOK": sisa,
                            "TERJUAL": laku, "TOTAL_OMZET": duit
                        })

                        if laku > 0: txt_jual.append(f"- {item}: {laku} pcs")
                        txt_stok.append(f"- {item}: {sisa} pcs") # Selalu catat sisa stok

                    st.markdown(f"### 💰 Omzet: {format_rupiah(total_omzet)}")
                    tunai = st.number_input("Tunai", step=500); qris = st.number_input("QRIS", step=500); catatan = st.text_area("Catatan")
                    
                    if st.form_submit_button("KIRIM LAPORAN"):
                        list_excel.append({
                            "TANGGAL": tgl, "JAM_LAPOR": jam_plg, "LOKASI": lokasi, "STAFF": user,
                            "JAM_MASUK": shift['jam_masuk'], "JAM_PLG": jam_plg,
                            "ITEM_MENU": "TOTAL SETORAN", "TOTAL_OMZET": total_omzet,
                            "SETOR_TUNAI": tunai, "SETOR_QRIS": qris, "CATATAN": catatan
                        })
                        simpan_laporan_excel(list_excel); kirim_file_excel_telegram()
                        
                        selisih = (tunai+qris) - total_omzet
                        stat = "PAS ✅" if selisih==0 else (f"SELISIH {format_rupiah(selisih)}")
                        
                        # FORMAT PESAN TELEGRAM LENGKAP
                        msg = (f"🌙 *CLOSING LAPORAN*\n"
                               f"📍 {lokasi}\n👤 {user}\n"
                               f"🕒 {shift['jam_masuk']} - {jam_plg}\n\n"
                               f"📦 *Sisa Stok Akhir:*\n{chr(10).join(txt_stok)}\n\n"
                               f"📊 *Rincian Terjual:*\n{chr(10).join(txt_jual) if txt_jual else '- Nihil'}\n\n"
                               f"💰 *Omzet: {format_rupiah(total_omzet)}*\n"
                               f"💵 Tunai: {format_rupiah(tunai)}\n"
                               f"💳 QRIS: {format_rupiah(qris)}\n"
                               f"📝 Status: {stat}\n"
                               f"Catatan: {catatan}")
                        
                        kirim_telegram(msg)
                        del GEROBAK[lokasi]; save_json(FILE_DB_GEROBAK, GEROBAK); st.balloons(); st.rerun()

if __name__ == "__main__":
    main()
                    
