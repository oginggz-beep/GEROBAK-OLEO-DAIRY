import streamlit as st
import pytz
import gspread
import pandas as pd
from datetime import datetime

# ================= KONFIGURASI =================
TOKEN_BOT  = "8285539149:AAHQd-_W9aaBGSz3AUPg0oCuxabZUL6yJo4"
ID_OWNER   = "8505488457"
PIN_OWNER  = "8888" 
NAMA_SHEET = "DATABASE_GEROBAK_APP" # Pastikan nama file Google Sheet SAMA PERSIS

# ================= KONEKSI GOOGLE SHEETS =================
def connect_gsheet():
    try:
        # Cek apakah secrets ada
        if "gcp_service_account" not in st.secrets:
            st.error("❌ EROR: Secrets belum dimasukkan di Streamlit Cloud!")
            return None
            
        # Ambil kredensial
        creds_dict = dict(st.secrets["gcp_service_account"])
        
        # Coba Login
        client = gspread.service_account_from_dict(creds_dict)
        
        # Coba Buka File
        sheet = client.open(NAMA_SHEET)
        return sheet
        
    except gspread.SpreadsheetNotFound:
        st.error(f"❌ EROR: File Google Sheet '{NAMA_SHEET}' TIDAK DITEMUKAN.")
        st.warning("👉 Pastikan nama file di Google Drive SAMA PERSIS (huruf besar/kecil).")
        st.warning("👉 Pastikan kamu sudah klik SHARE dan masukkan email bot (client_email) sebagai Editor.")
        return None
    except Exception as e:
        st.error(f"❌ EROR LAIN: {e}")
        st.info("Coba cek: Apakah 'Google Sheets API' dan 'Google Drive API' sudah di-ENABLE di Google Cloud Console?")
        return None

def get_waktu_wib():
    tz = pytz.timezone('Asia/Jakarta')
    return datetime.now(tz)

def kirim_telegram(pesan):
    try:
        import requests
        url = f"https://api.telegram.org/bot{TOKEN_BOT}/sendMessage"
        requests.post(url, data={"chat_id": ID_OWNER, "text": pesan})
    except: pass

def format_rupiah(angka):
    return f"Rp {int(angka):,}".replace(",", ".")

# ================= APLIKASI UTAMA =================
def main():
    st.set_page_config(page_title="Tes Koneksi", page_icon="🔧")
    st.title("🔧 Mode Perbaikan Koneksi")

    # TEST KONEKSI LANGSUNG
    sheet = connect_gsheet()
    
    if sheet:
        st.success("✅ KONEKSI SUKSES! Google Sheets Terhubung.")
        st.balloons()
        
        # Coba baca data
        try:
            ws = sheet.worksheet("STAFF")
            data = ws.get_all_records()
            st.write("Data Staff ditemukan:", data)
        except:
            st.warning("Koneksi berhasil, tapi Tab 'STAFF' belum ada. Aplikasi akan membuatnya otomatis nanti.")
            
        if st.button("LANJUT KE APLIKASI KASIR"):
            st.session_state['koneksi_ok'] = True
            st.rerun()
            
    else:
        st.error("⛔ Koneksi Gagal. Lihat pesan error di atas.")
        st.stop()

    # --- JIKA KONEKSI OK, BARU JALANKAN APLIKASI ---
    # (Kode aplikasi kasir normal ada di bawah sini, tapi kita tes koneksi dulu)
    # Jika tombol Lanjut ditekan, baru load aplikasi penuh
    if 'koneksi_ok' in st.session_state and st.session_state['koneksi_ok']:
        # [DISINI MASUKKAN KODE LOGIC APLIKASI SEPERTI SEBELUMNYA]
        # Untuk tes sekarang, kita fokus benerin koneksi dulu.
        st.write("Koneksi aman. Silakan request kode full lagi jika tes ini berhasil.")

if __name__ == "__main__":
    main()

