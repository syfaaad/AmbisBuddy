"""
Run this ONCE on PythonAnywhere Bash Console after git pull:
    python migrate_tka.py

It will:
1. Rename old 'TKA' category subjects to 'TKA IPA' (safe default)
2. Re-seed any missing subjects for TKA IPA / TKA IPS / TKA Bahasa & Vokasi
"""

import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), 'ambisbuddy.db')

def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def migrate():
    conn = get_conn()
    cursor = conn.cursor()

    # 1. Rename leftover category='TKA' -> 'TKA IPA'
    cursor.execute("UPDATE subjects SET category='TKA IPA' WHERE category='TKA'")
    renamed = cursor.rowcount
    print(f"Renamed {renamed} old TKA subjects -> TKA IPA")

    # 2. Seed missing TKA IPS + Bahasa & Vokasi subjects
    new_subjects = {
        "TKA IPS": [
            {
                "name": "Geografi",
                "topics": [
                    ("Dinamika Litosfer & Pedosfer", ["Batuan dan mineral", "Proses pelapukan dan erosi", "Jenis tanah di Indonesia"]),
                    ("Dinamika Atmosfer & Hidrosfer", ["Jenis awan dan curah hujan", "Siklus hidrologi", "El Nino & La Nina"]),
                    ("Kependudukan & Lingkungan", ["Sensus penduduk", "Piramida penduduk", "Dampak pertumbuhan penduduk"]),
                    ("SIG & Penginderaan Jauh", ["Komponen SIG", "Interpretasi citra", "Overlay peta"]),
                ]
            },
            {
                "name": "Sejarah",
                "topics": [
                    ("Sejarah Indonesia Kuno", ["Kerajaan Hindu-Buddha", "Majapahit & Sriwijaya", "Masuknya Islam"]),
                    ("Masa Kolonialisme", ["VOC dan dampaknya", "Tanam paksa", "Pergerakan nasional"]),
                    ("Kemerdekaan Indonesia", ["Proklamasi 17 Agustus 1945", "Peristiwa Rengasdengklok", "Sidang PPKI"]),
                    ("Sejarah Dunia Modern", ["Perang Dunia I & II", "Perang Dingin", "Gerakan Non-Blok"]),
                ]
            },
            {
                "name": "Sosiologi",
                "topics": [
                    ("Struktur & Diferensiasi Sosial", ["Stratifikasi sosial", "Diferensiasi sosial", "Mobilitas sosial"]),
                    ("Konflik & Integrasi Sosial", ["Sebab konflik", "Mediasi & arbitrase", "Integrasi sosial"]),
                    ("Lembaga Sosial", ["Lembaga keluarga", "Lembaga agama", "Lembaga pendidikan"]),
                    ("Perubahan Sosial", ["Teori perubahan sosial", "Modernisasi dan globalisasi", "Dampak media sosial"]),
                ]
            },
            {
                "name": "Ekonomi",
                "topics": [
                    ("Teori Ekonomi Dasar", ["Permintaan dan penawaran", "Elastisitas", "Mekanisme pasar"]),
                    ("Pelaku Ekonomi & Pasar", ["Jenis pasar", "Monopoli & oligopoli", "Pasar bebas"]),
                    ("Kebijakan Ekonomi Makro", ["Inflasi dan deflasi", "Kebijakan fiskal", "Kebijakan moneter"]),
                    ("Perdagangan Internasional", ["Neraca pembayaran", "Kurs dan devisa", "ASEAN & MEA"]),
                ]
            },
        ],
        "TKA Bahasa & Vokasi": [
            {
                "name": "Bahasa Inggris (TKA)",
                "topics": [
                    ("Reading Comprehension", ["Main idea & detail", "Inference questions", "Vocabulary in context"]),
                    ("Grammar & Structure", ["Tenses review", "Passive voice", "Conditional sentences"]),
                    ("Writing Skills", ["Essay structure", "Argumentation", "Coherence and cohesion"]),
                ]
            },
            {
                "name": "Bahasa Indonesia (TKA)",
                "topics": [
                    ("Membaca & Memahami Teks", ["Teks eksposisi", "Teks argumentasi", "Teks narasi"]),
                    ("Kebahasaan & EYD", ["Tata bahasa baku", "Penggunaan kata", "Ejaan yang disempurnakan"]),
                    ("Sastra Indonesia", ["Puisi dan prosa", "Drama", "Nilai-nilai sastra"]),
                ]
            },
        ]
    }

    for category, subjects in new_subjects.items():
        for subj_data in subjects:
            subj_name = subj_data["name"]
            existing = cursor.execute("SELECT id FROM subjects WHERE name=?", (subj_name,)).fetchone()
            if existing:
                # Update category if mismatched
                cursor.execute("UPDATE subjects SET category=? WHERE name=?", (category, subj_name))
                subj_id = existing["id"]
                print(f"  Updated category for: {subj_name}")
            else:
                cursor.execute("INSERT INTO subjects (name, category) VALUES (?, ?)", (subj_name, category))
                subj_id = cursor.lastrowid
                print(f"  Inserted: {subj_name} [{category}]")

            for topic_name, subtopic_names in subj_data["topics"]:
                t_existing = cursor.execute("SELECT id FROM topics WHERE subject_id=? AND name=?", (subj_id, topic_name)).fetchone()
                if t_existing:
                    topic_id = t_existing["id"]
                else:
                    cursor.execute("INSERT INTO topics (subject_id, name) VALUES (?, ?)", (subj_id, topic_name))
                    topic_id = cursor.lastrowid

                for subt_name in subtopic_names:
                    st_existing = cursor.execute("SELECT id FROM subtopics WHERE topic_id=? AND name=?", (topic_id, subt_name)).fetchone()
                    if not st_existing:
                        cursor.execute("INSERT INTO subtopics (topic_id, name) VALUES (?, ?)", (topic_id, subt_name))

    conn.commit()
    conn.close()
    print("Migration complete!")

if __name__ == "__main__":
    migrate()
