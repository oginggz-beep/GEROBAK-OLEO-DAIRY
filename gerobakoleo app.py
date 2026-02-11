import streamlit as st
import json
import os
import requests
from datetime import datetime

# ================= KONFIGURASI =================
TOKEN_BOT  = "8285539149:AAHQd-_W9aaBGSz3AUPg0oCuxabZUL6yJo4"
ID_OWNER   = "8505488457"
FILE_DB    = "database_gerobak.json" # Pengganti file temp

# DATA SETUP
DATA_STAFF = {"1111": "Budi (Pagi)", "2222": "Siti (Malam)", "9999": "BOSS OWNER"}
DATA_GEROBAK = {"1": "Gerobak Alun-Alun", "2": "Gerobak Stasiun", "3": "Gerobak Pasar"}
MENU_HARGA = {
    "Strawberry Milk": 10000, "Coklat Milk": 12000,
    "Kopi Susu Aren": 15000, "Matcha Latte": 15000
}
PERLENGKAPAN = ["Mesin Press", "Termos Es", "Lap Tangan", "Gunting", "Tempat Sampah"]

# ================= FUNGSI BANTUAN =================
def kirim_telegram(pesan):
    try:
        url = f"https://api.telegram.org/bot{TOKEN_BOT}/sendMessage"
        requests.post(url, data={"chat_id": ID_OWNER, "text": pesan})
        return True
    except: return False

def format_rupiah(angka):
    return f"Rp {angka:,}".replace(",", ".")

def load_db():
    if os.path.exists(FILE_DB):
        with open(FILE_DB, 'r') as f: return json.load(f)
    return {}

def save_db(data):
    with open(FILE_DB, 'w') as f: json.dump(data, f)

# ================= APLIKASI WEB UTAMA =================
def main():
    st.set_page_config(page_title="Kasir Gerobak", page_icon="🥤")

    # --- JUDUL ---
    st.title("🥤 Sistem Kasir & Absensi")
    st.markdown("---")

    # --- SIDEBAR (LOGIN) ---
    with st.sidebar:
        st.header("🔐 Login Staff")
        pin_input = st.text_input("Masukkan PIN", type="password")
        
        staff_nama = None
        if pin_input in DATA_STAFF:
            staff_nama = DATA_STAFF[pin_input]
            st.success(f"Halo, {staff_nama}!")
        elif pin_input:
            st.error("PIN Salah!")

    # JIKA BELUM LOGIN, STOP DISINI
    if not staff_nama:
        st.info("Silakan masukkan PIN di menu sebelah kiri (tanda panah >) untuk memulai.")
        return

    # --- PILIH GEROBAK ---
    pilihan_gerobak = st.selectbox("📍 Pilih Lokasi Gerobak:", list(DATA_GEROBAK.values()))
    
    # LOAD DATA DARI MEMORI
    db = load_db()
    
    # Cek apakah gerobak ini sedang dipakai?
    data_aktif = db.get(pilihan_gerobak)
    
    # TAMPILKAN STATUS
    if data_aktif:
        st.warning(f"⚠️ STATUS: SHIFT BERJALAN (Oleh: {data_aktif['pic']})")
        st.caption(f"Masuk jam: {data_aktif.get('jam_masuk', '-')}")
    else:
        st.success("✅ STATUS: GEROBAK KOSONG (Siap Opening)")

    # ================= TAB MENU =================
    tab1, tab2 = st.tabs(["☀️ OPENING (Pagi)", "🌙 CLOSING (Malam)"])

    # --- TAB 1: OPENING ---
    with tab1:
        st.header("Form Absen Masuk")
        
        # Validasi: Tidak boleh opening kalau sudah ada orang (Kecuali pemiliknya mau update)
        if data_aktif and data_aktif['pin_pic'] != pin_input:
            st.error(f"⛔ Gerobak ini sedang dipakai {data_aktif['pic']}. Anda tidak bisa masuk.")
        else:
            with st.form("form_opening"):
                st.write("📦 **Input Stok Awal (Bawaan):**")
                stok_input = {}
                for menu in MENU_HARGA:
                    # Ambil nilai lama jika update, atau 0 jika baru
                    val_lama = data_aktif['stok'].get(menu, 0) if data_aktif else 0
                    stok_input[menu] = st.number_input(f"Jml {menu}", min_value=0, value=val_lama)
                
                tombol_buka = st.form_submit_button("✅ SIMPAN OPENING")
                
                if tombol_buka:
                    jam_skrg = datetime.now().strftime("%H:%M")
                    data_baru = {
                        "tanggal": datetime.now().strftime("%Y-%m-%d"),
                        "jam_masuk": data_aktif['jam_masuk'] if data_aktif else jam_skrg,
                        "pic": staff_nama,
                        "pin_pic": pin_input,
                        "stok": stok_input
                    }
                    # Simpan ke DB
                    db[pilihan_gerobak] = data_baru
                    save_db(db)
                    
                    # Kirim Telegram
                    list_stok = [f"{k}: {v}" for k,v in stok_input.items()]
                    msg = f"☀️ *OPENING WEB*\n📍 {pilihan_gerobak}\n👤 {staff_nama}\n🕒 Jam: {data_baru['jam_masuk']}\n\n📦 STOK:\n" + "\n".join(list_stok)
                    kirim_telegram(msg)
                    
                    st.success("Data Opening Tersimpan!")
                    st.rerun() # Refresh halaman

    # --- TAB 2: CLOSING ---
    with tab2:
        st.header("Form Laporan Pulang")
        
        if not data_aktif:
            st.info("Belum ada data Opening. Silakan Opening dulu.")
        elif data_aktif['pin_pic'] != pin_input:
            st.error("⛔ Anda bukan staff yang membuka gerobak ini!")
        else:
            with st.form("form_closing"):
                st.subheader("1. Hitung Stok Akhir")
                stok_awal = data_aktif['stok']
                sisa_input = {}
                omzet_sistem = 0
                laporan_txt = []
                
                # Input Sisa & Hitung Duit
                for menu, harga in MENU_HARGA.items():
                    awal = stok_awal.get(menu, 0)
                    sisa = st.number_input(f"Sisa Fisik {menu} (Awal: {awal})", min_value=0, max_value=awal)
                    laku = awal - sisa
                    duit = laku * harga
                    omzet_sistem += duit
                    sisa_input[menu] = sisa
                    laporan_txt.append(f"{menu}: {laku} x {int(harga/1000)}k = {int(duit/1000)}k")

                st.subheader("2. Cek Alat")
                kondisi_alat = {}
                for alat in PERLENGKAPAN:
                    kondisi_alat[alat] = st.radio(f"Kondisi {alat}?", ["AMAN", "RUSAK/HILANG"], horizontal=True, key=alat)

                st.subheader("3. Setoran Uang")
                st.info(f"💰 Target Setoran (Sistem): **{format_rupiah(omzet_sistem)}**")
                
                uang_tunai = st.number_input("Uang Tunai (Laci)", min_value=0, step=1000)
                uang_qris = st.number_input("Uang QRIS/Transfer", min_value=0, step=1000)
                catatan = st.text_area("Catatan Tambahan")

                tombol_tutup = st.form_submit_button("🚀 KIRIM LAPORAN & PULANG")

                if tombol_tutup:
                    total_fisik = uang_tunai + uang_qris
                    selisih = total_fisik - omzet_sistem
                    status_keu = "✅ PAS"
                    if selisih < 0: status_keu = f"⚠️ MINUS {format_rupiah(abs(selisih))}"
                    elif selisih > 0: status_keu = f"ℹ️ LEBIH {format_rupiah(selisih)}"

                    # Susun Pesan
                    msg = (f"🌙 *CLOSING WEB*\n📍 {pilihan_gerobak}\n👤 {staff_nama}\n"
                           f"🕒 Kerja: {data_aktif['jam_masuk']} - Selesai\n\n"
                           f"📊 *JUALAN:*\n" + "\n".join(laporan_txt) + "\n\n"
                           f"💰 *KEUANGAN:*\nTarget: {format_rupiah(omzet_sistem)}\n"
                           f"Tunai: {format_rupiah(uang_tunai)}\nQRIS: {format_rupiah(uang_qris)}\n"
                           f"Status: {status_keu}\n\n📝 {catatan}")
                    
                    kirim_telegram(msg)
                    
                    # Hapus Data (Buka Gembok)
                    del db[pilihan_gerobak]
                    save_db(db)
                    
                    st.success("Laporan Terkirim! Hati-hati di jalan.")
                    st.balloons() # Efek balon
                    st.rerun()

if __name__ == "__main__":
    main()
    