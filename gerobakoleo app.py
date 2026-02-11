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
FILE_EXCEL_REP  = "LAPORAN_RINCIAN_MENU.xlsx"

# Default Data
MENU_DEFAULT = {"Strawberry Milk": 10000, "Coklat Milk": 12000, "Kopi Aren": 15000}
LOKASI_DEFAULT = {"1": "Gerobak Alun-Alun", "2": "Gerobak Stasiun"}

# ================= FUNGSI BANTUAN =================
def kirim_telegram(pesan):
    if TOKEN_BOT == "PASTE_TOKEN_BOT_ANDA_DISINI": return
    try:
        requests.post(f"https://api.telegram.org/bot{TOKEN_BOT}/sendMessage", 
                      data={"chat_id": ID_OWNER, "text": pesan, "parse_mode": "Markdown"})
    except Exception as e: 
        print(f"Error Telegram: {e}")

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

# --- FUNGSI MANAJEMEN DATA ---
def get_data(filename, default):
    data = load_json(filename)
    if not data:
        save_json(filename, default); return default
    return data

# ================= APLIKASI UTAMA =================
def main():
    st.set_page_config(page_title="POS Laporan Stok", page_icon="🥤")
    
    if TOKEN_BOT == "PASTE_TOKEN_BOT_ANDA_DISINI":
        st.error("⚠️ TOKEN BELUM DIISI! Edit file app.py baris ke-10."); st.stop()

    # Load Data
    MENU = get_data(FILE_DB_MENU, MENU_DEFAULT)
    LOKASI = get_data(FILE_DB_LOKASI, LOKASI_DEFAULT)
    STAFF = load_json(FILE_DB_STAFF)
    GEROBAK = load_json(FILE_DB_GEROBAK)

    if 'user' not in st.session_state: st.session_state['user'] = None
    if 'pin' not in st.session_state: st.session_state['pin'] = None

    # --- LOGIN ---
    with st.sidebar:
        st.header("🔐 Login")
        if not st.session_state['user']:
            p = st.text_input("PIN", type="password", max_chars=6)
            if st.button("Login"):
                if p == PIN_OWNER: st.session_state['user']="OWNER"; st.session_state['pin']=p; st.rerun()
                elif p in STAFF: st.session_state['user']=STAFF[p]; st.session_state['pin']=p; st.rerun()
                else: st.error("PIN Salah")
        else:
            st.success(f"👤 {st.session_state['user']}")
            if st.button("Keluar"): st.session_state['user']=None; st.rerun()

    # --- AREA KERJA ---
    if st.session_state['user']:
        user = st.session_state['user']
        pin = st.session_state['pin']

        st.title("🥤 Kasir & Laporan Stok")
        lokasi = st.selectbox("Pilih Lokasi:", list(LOKASI.values()))
        shift = GEROBAK.get(lokasi)

        tb1, tb2 = st.tabs(["☀️ BUKA SHIFT (Stok)", "🌙 TUTUP SHIFT"])

        # --- TAB OPENING (DENGAN LAPORAN STOK TELEGRAM) ---
        with tb1:
            if shift and shift['pin_pic'] != pin:
                st.error("⛔ Shift ini sedang digunakan staf lain.")
            else:
                with st.form("opening_form"):
                    st.write("📦 **Input Stok Awal Barang:**")
                    stok_opening = {}
                    cols = st.columns(2)
                    for i, m in enumerate(MENU):
                        val_lama = shift['stok'].get(m, 0) if shift else 0
                        with cols[i%2]:
                            stok_opening[m] = st.number_input(f"{m}", value=int(val_lama), min_value=0)
                    
                    submit_opening = st.form_submit_button("SIMPAN & KIRIM STOK KE BOS")

                    if submit_opening:
                        jam_skrg = datetime.now().strftime("%H:%M")
                        GEROBAK[lokasi] = {
                            "tanggal": datetime.now().strftime("%d-%m-%Y"),
                            "jam_masuk": shift['jam_masuk'] if shift else jam_skrg,
                            "pic": user,
                            "pin_pic": pin,
                            "stok": stok_opening
                        }
                        save_json(FILE_DB_GEROBAK, GEROBAK)
                        
                        # --- LAPORAN STOK KE TELEGRAM ---
                        txt_stok = []
                        for item, jml in stok_opening.items():
                            txt_stok.append(f"• {item}: *{jml}*")
                        
                        rincian_stok = "\n".join(txt_stok)
                        msg_opening = (f"☀️ *LAPORAN STOK AWAL*\n\n"
                                       f"📍 Lokasi: *{lokasi}*\n"
                                       f"👤 Staff: *{user}*\n"
                                       f"🕒 Jam: *{jam_skrg}*\n\n"
                                       f"📦 *Rincian Stok:*\n{rincian_stok}\n\n"
                                       f"✅ _Gerobak sudah siap berjualan._")
                        
                        kirim_telegram(msg_opening)
                        st.success("Stok berhasil disimpan dan dilaporkan ke Bos!"); st.rerun()

        # --- TAB CLOSING ---
        with tb2:
            if not shift:
                st.info("Harap isi Stok Awal di tab Buka Shift dulu.")
            else:
                st.write("🌙 Halaman tutup shift dan rincian jualan harian.")
                # (Sama seperti kodingan sebelumnya untuk bagian Closing...)
                st.write("Gunakan kodingan closing Anda yang sebelumnya di sini.")

    else:
        st.info("👈 Silakan Login di menu samping.")

if __name__ == "__main__":
    main()
    
