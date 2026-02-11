import streamlit as st
import gspread

def main():
    st.set_page_config(page_title="Cek Mata Bot", page_icon="🕵️‍♂️")
    st.title("🕵️‍♂️ Diagnosa: Apa yang dilihat Bot?")

    try:
        # 1. Cek apakah Secrets ada
        if "gcp_service_account" not in st.secrets:
            st.error("❌ Secrets belum dimasukkan di Streamlit!")
            st.stop()
            
        # 2. Ambil Email Bot dari Secrets
        creds_dict = dict(st.secrets["gcp_service_account"])
        email_bot = creds_dict.get("client_email", "Tidak ditemukan")
        
        st.info(f"🤖 Email Bot Anda adalah:\n\n`{email_bot}`")
        st.warning("👆 Pastikan email DI ATAS INI yang Anda undang (Share) di Google Sheet sebagai EDITOR.")

        # 3. Suruh Bot melihat semua file
        client = gspread.service_account_from_dict(creds_dict)
        file_list = client.openall()

        st.divider()
        st.subheader("📂 Daftar File yang Dilihat Bot:")
        
        if not file_list:
            st.error("❌ KOSONG! Bot tidak melihat satu pun file.")
            st.write("Artinya: Anda belum Share file ke email bot di atas, atau salah email.")
        else:
            st.success(f"✅ Bot melihat {len(file_list)} file. Ini nama aslinya:")
            
            ketemu = False
            for f in file_list:
                st.code(f.title) # Tampilkan nama file persis
                if f.title == "DATABASE_GEROBAK_APP":
                    ketemu = True
            
            if ketemu:
                st.balloons()
                st.success("🎉 NAMA FILE SUDAH BENAR! Harusnya aplikasi bisa jalan.")
            else:
                st.error("⚠️ File 'DATABASE_GEROBAK_APP' TIDAK ADA di daftar di atas.")
                st.write("Solusi: Copy salah satu nama file yang muncul di kotak hitam di atas, lalu pakai nama itu di kodingan aplikasi Anda.")

    except Exception as e:
        st.error(f"Error Koneksi: {e}")

if __name__ == "__main__":
    main()
    
