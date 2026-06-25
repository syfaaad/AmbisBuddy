import os
import sqlite3
import random
from datetime import datetime, timedelta
from flask import Flask, jsonify, request, render_template, session
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps

app = Flask(__name__)
app.secret_key = "super_secret_ambisbuddy_key_123"
DB_NAME = "ambisbuddy.db"

def get_db_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 1. Users Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    """)
    
    # 2. User Profiles Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_profiles (
            user_id INTEGER PRIMARY KEY,
            nickname TEXT,
            target_campus TEXT,
            target_major TEXT,
            exam_focus TEXT, -- 'SNBT', 'TKA', 'Both'
            weakest_subject TEXT,
            strongest_subject TEXT,
            target_study_hours REAL DEFAULT 2.0,
            onboarded INTEGER DEFAULT 0,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    """)
    
    # 3. Subjects Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS subjects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            category TEXT NOT NULL -- 'SNBT' or 'TKA'
        )
    """)
    
    # 4. Topics Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS topics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            subject_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            FOREIGN KEY (subject_id) REFERENCES subjects(id) ON DELETE CASCADE
        )
    """)
    
    # 5. Subtopics Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS subtopics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            topic_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            FOREIGN KEY (topic_id) REFERENCES topics(id) ON DELETE CASCADE
        )
    """)
    
    # 6. User Progress Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_progress (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            subtopic_id INTEGER NOT NULL,
            status TEXT NOT NULL DEFAULT 'Belum Belajar', -- 'Belum Belajar', 'Sedang Belajar', 'Sudah Menguasai'
            updated_at TEXT NOT NULL,
            UNIQUE(user_id, subtopic_id),
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (subtopic_id) REFERENCES subtopics(id) ON DELETE CASCADE
        )
    """)
    
    # 7. Daily Targets Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS daily_targets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            is_completed INTEGER DEFAULT 0, -- 0 for False, 1 for True
            created_at TEXT NOT NULL, -- YYYY-MM-DD
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    """)
    
    # 8. Journal Entries Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS journal_entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            content TEXT NOT NULL, -- Bagaimana kisah hari ini
            learned_today TEXT NOT NULL, -- Apa yang dipelajari hari ini
            difficulties TEXT NOT NULL, -- Kesulitan yang dihadapi
            tomorrow_plan TEXT NOT NULL, -- Rencana belajar besok
            created_at TEXT NOT NULL, -- YYYY-MM-DD HH:MM
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    """)
    
    # 9. Mood Records Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS mood_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            mood TEXT NOT NULL, -- 'Happy', 'Excited', 'Focused', 'Tired', 'Stressed'
            created_at TEXT NOT NULL, -- YYYY-MM-DD
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    """)
    
    # 10. Study Sessions Table (Pomodoro log)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS study_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            subject_id INTEGER NOT NULL,
            duration_seconds INTEGER NOT NULL,
            created_at TEXT NOT NULL, -- YYYY-MM-DD HH:MM
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (subject_id) REFERENCES subjects(id) ON DELETE CASCADE
        )
    """)
    
    # 11. Streak Data Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS streak_data (
            user_id INTEGER PRIMARY KEY,
            current_streak INTEGER DEFAULT 0,
            last_active_date TEXT, -- YYYY-MM-DD
            longest_streak INTEGER DEFAULT 0,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    """)
    
    # 12. Ambis Forest Trees Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS ambis_forest_trees (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            streak_length INTEGER NOT NULL,
            started_date TEXT NOT NULL,
            completed_date TEXT NOT NULL,
            total_study_seconds INTEGER NOT NULL,
            targets_completed INTEGER NOT NULL,
            top_subject TEXT NOT NULL,
            planted_at TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    """)
    
    # 13. AI Reflections Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS ai_reflections (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            reflection_text TEXT NOT NULL,
            created_at TEXT NOT NULL, -- YYYY-MM-DD
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    """)

    # Seed Default User
    cursor.execute("SELECT COUNT(*) FROM users")
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO users (id, username, password) VALUES (1, 'ambis_user', 'scrypt:32768:8:1$ZPnZUJ5iqOKgsy9h$d827ac39b4453936a6b26b3ddc50342056a79c3d8c003e4b97e9f0207c89fe1aa90aa7e30b6bef4b9210ae581f71f2c7afd1054c9e4a6ecee3469c6325b6cc8d')")
        cursor.execute("INSERT INTO user_profiles (user_id, nickname, target_campus, target_major, exam_focus, weakest_subject, strongest_subject, target_study_hours, onboarded) VALUES (1, 'Pejuang SNBT', 'Universitas Indonesia', 'Teknik Informatika', 'Both', 'Penalaran Matematika', 'Literasi Bahasa Inggris', 3.0, 0)")
        cursor.execute("INSERT INTO streak_data (user_id, current_streak, last_active_date, longest_streak) VALUES (1, 5, ?, 5)", ((datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d"),))
    
    # Seed Real SNBT & TKA Subjects, Topics, and Subtopics
    cursor.execute("SELECT COUNT(*) FROM subjects")
    if cursor.fetchone()[0] == 0:
        # Define Syllabus
        syllabus = {
            "SNBT": {
                "Penalaran Umum": {
                    "Penalaran Induktif": ["Logika Analitis", "Kesimpulan Logis Wacana", "Pola Deret Gambar/Angka"],
                    "Penalaran Deduktif": ["Silogisme Kategoris", "Modus Ponens & Modus Tollens", "Implikasi & Negasi"],
                    "Penalaran Kuantitatif": ["Hubungan Kuantitatif A & B", "Analisis Data Tabel & Grafik", "Operasi Aritmetika Dasar"]
                },
                "Pengetahuan & Pemahaman Umum": {
                    "Memahami Wacana": ["Ide Pokok & Judul Teks", "Simpulan & Kelemahan Paragraf", "Sikap Penulis & Nada Teks"],
                    "Kosa Kata & Sinonim": ["Makna Kata Kontekstual", "Hubungan Kata/Analogi", "Kata Serapan & Istilah"]
                },
                "Pemahaman Bacaan & Menulis": {
                    "Tata Bahasa": ["Ejaan & Tanda Baca (EYD)", "Kalimat Efektif & Tidak Efektif", "Konjungsi Antarkalimat & Intrakalimat"],
                    "Kepaduan Paragraf": ["Koherensi Kalimat", "Penggabungan Paragraf", "Kata Rumpung & Melengkapi Paragraf"]
                },
                "Penalaran Matematika": {
                    "Bilangan & Aritmetika": ["Aritmetika Sosial & Persentase", "Pola Bilangan & Barisan/Deret", "Rasio dan Proporsi"],
                    "Aljabar": ["Persamaan & Pertidaksamaan Linear", "Sistem Persamaan Linear Dua Variabel", "Fungsi Kuadrat & Grafik"],
                    "Geometri": ["Geometri Datar & Sifat Bangun", "Geometri Ruang (Volume & Luas)", "Dalil Phytagoras & Koordinat"],
                    "Statistika & Peluang": ["Rata-rata, Median, Modus", "Penyajian Data (Diagram/Histogram)", "Peluang Kejadian Sederhana"]
                },
                "Literasi Bahasa Indonesia": {
                    "Strategi Membaca": ["Menemukan Informasi Tersurat", "Menafsirkan Informasi Tersirat", "Membandingkan Dua Teks"],
                    "Analisis Kritis": ["Mengevaluasi Opini vs Fakta", "Menilai Validitas Argumen Penulis", "Menilai Relevansi Bukti"]
                },
                "Literasi Bahasa Inggris": {
                    "Reading Comprehension": ["Identifying Main Idea", "Author's Tone and Purpose", "Determining Fact vs Opinion"],
                    "Information Synthesis": ["Synthesizing Information from Passages", "Contextual Vocabulary", "Pronoun Reference"]
                }
            },
            "TKA": {
                "Matematika IPA": {
                    "Aljabar Lanjut": ["Fungsi Komposisi & Invers", "Polinomial & Teorema Sisa", "Matriks & Determinan"],
                    "Trigonometri": ["Persamaan Trigonometri", "Rumus Jumlah & Selisih Sudut", "Fungsi & Grafik Trigonometri"],
                    "Kalkulus": ["Limit Fungsi Aljabar & Trigonometri", "Turunan Fungsi & Aplikasi Ekstrim", "Integral Tentu & Aplikasi Luas"]
                },
                "Fisika": {
                    "Mekanika": ["Kinematika Gerak Lurus & Melingkar", "Hukum Newton & Gaya Gesek", "Usaha, Energi, & Impuls", "Dinamika Rotasi & Kesetimbangan"],
                    "Termodinamika": ["Suhu, Kalor, & Perpindahan Panas", "Teori Kinetik Gas & Hukum Termodinamika"],
                    "Gelombang & Optik": ["Optika Geometri & Alat Optik", "Gelombang Bunyi & Efek Doppler", "Gelombang Elektromagnetik"],
                    "Listrik & Magnet": ["Listrik Statis & Hukum Coulomb", "Rangkaian Arus Searah (DC)", "Induksi Elektromagnetik"]
                },
                "Kimia": {
                    "Dasar Kimia & Stoikiometri": ["Hukum Dasar Kimia & Konsep Mol", "Persamaan Reaksi & Stoikiometri Larutan"],
                    "Struktur & Ikatan": ["Struktur Atom & Mekanika Kuantum", "Sifat Periodik Unsur & Ikatan Kimia"],
                    "Kimia Fisik": ["Termokimia & Entalpi Reaksi", "Laju Reaksi & Faktor Kecepatan", "Kesetimbangan Kimia"],
                    "Kimia Organik": ["Senyawa Hidrokarbon & Gugus Fungsi", "Polimer & Makromolekul Organik"]
                },
                "Biologi": {
                    "Biologi Sel & Genetika": ["Struktur Sel & Transpor Membran", "Sintesis Protein & Pembelahan Sel", "Hukum Mendel & Genetika Manusia"],
                    "Struktur & Fungsi Organ": ["Sistem Pencernaan, Respirasi, & Sirkulasi", "Sistem Koordinasi & Homeostasis"],
                    "Ekologi & Evolusi": ["Aliran Energi & Siklus Biogeokimia", "Teori Evolusi & Seleksi Alam"]
                }
            }
        }
        
        # Insert into Database
        for category, subjects in syllabus.items():
            for subject_name, topics in subjects.items():
                cursor.execute("INSERT INTO subjects (name, category) VALUES (?, ?)", (subject_name, category))
                subject_id = cursor.lastrowid
                for topic_name, subtopics in topics.items():
                    cursor.execute("INSERT INTO topics (subject_id, name) VALUES (?, ?)", (subject_id, topic_name))
                    topic_id = cursor.lastrowid
                    for subtopic_name in subtopics:
                        cursor.execute("INSERT INTO subtopics (topic_id, name) VALUES (?, ?)", (topic_id, subtopic_name))
        
        # Seed Ambis Forest with a couple of mock history trees so the forest has some trees initially
        now = datetime.now()
        tree1_start = (now - timedelta(days=45)).strftime("%Y-%m-%d")
        tree1_end = (now - timedelta(days=12)).strftime("%Y-%m-%d")
        tree2_start = (now - timedelta(days=90)).strftime("%Y-%m-%d")
        tree2_end = (now - timedelta(days=58)).strftime("%Y-%m-%d")
        
        cursor.executemany("""
            INSERT INTO ambis_forest_trees (user_id, name, streak_length, started_date, completed_date, total_study_seconds, targets_completed, top_subject, planted_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, [
            (1, "Pohon Beringin Fokus", 33, tree1_start, tree1_end, 33 * 3 * 3600, 95, "Penalaran Matematika", tree1_end),
            (1, "Cemara Ambis", 32, tree2_start, tree2_end, 32 * 2.5 * 3600, 80, "Fisika", tree2_end)
        ])

    
    # Advanced Dynamic Seeder for Syllabus
    extended_syllabus = {
        "SNBT": {
            "Penalaran Umum": {
                "Penalaran Induktif": ["Logika Analitis", "Kesimpulan Logis Wacana", "Pola Deret Gambar/Angka"],
                "Penalaran Deduktif": ["Silogisme Kategoris", "Modus Ponens & Modus Tollens", "Implikasi & Negasi"],
                "Penalaran Kuantitatif": ["Hubungan Kuantitatif A & B", "Analisis Data Tabel & Grafik", "Operasi Aritmetika Dasar"]
            },
            "Pengetahuan & Pemahaman Umum": {
                "Memahami Wacana": ["Ide Pokok & Judul Teks", "Simpulan & Kelemahan Paragraf", "Sikap Penulis & Nada Teks"],
                "Kosa Kata & Sinonim": ["Makna Kata Kontekstual", "Hubungan Kata/Analogi", "Kata Serapan & Istilah"]
            },
            "Pemahaman Bacaan & Menulis": {
                "Tata Bahasa": ["Ejaan & Tanda Baca (EYD)", "Kalimat Efektif & Tidak Efektif", "Konjungsi Antarkalimat & Intrakalimat"],
                "Kepaduan Paragraf": ["Koherensi Kalimat", "Penggabungan Paragraf", "Kata Rumpung & Melengkapi Paragraf"]
            },
            "Pengetahuan Kuantitatif": {
                "Bilangan & Aritmetika": ["Aritmetika Sosial & Persentase", "Pola Bilangan & Barisan/Deret", "Rasio dan Proporsi"],
                "Aljabar": ["Persamaan & Pertidaksamaan Linear", "Sistem Persamaan Linear Dua Variabel", "Fungsi Kuadrat & Grafik"],
                "Geometri": ["Geometri Datar & Sifat Bangun", "Geometri Ruang (Volume & Luas)", "Dalil Phytagoras & Koordinat"],
                "Statistika & Peluang": ["Rata-rata, Median, Modus", "Penyajian Data (Diagram/Histogram)", "Peluang Kejadian Sederhana"]
            },
            "Literasi Bahasa Indonesia": {
                "Strategi Membaca Dasar": ["Menemukan Informasi Tersurat", "Menafsirkan Informasi Tersirat", "Membandingkan Dua Teks"],
                "Analisis Kritis": ["Mengevaluasi Opini vs Fakta", "Menilai Validitas Argumen Penulis", "Menilai Relevansi Bukti"],
                "Teks Spesifik": ["Teks Prosedur", "Teks Eksposisi", "Teks Eksplanasi & Argumentasi"]
            },
            "Literasi Bahasa Inggris": {
                "Reading Comprehension": ["Identifying Main Idea", "Author's Tone and Purpose", "Determining Fact vs Opinion"],
                "Information Synthesis": ["Synthesizing Information from Passages", "Contextual Vocabulary", "Pronoun Reference"]
            },
            "Penalaran Matematika": {
                "Pemecahan Masalah HOTS": ["Aplikasi Bilangan dalam Kehidupan", "Aplikasi Aljabar & Fungsi", "Geometri Pengukuran Kompleks", "Data dan Ketidakpastian (Peluang Analitik)"]
            }
        },
        "TKA IPA": {
            "Saintek": {
                "Matematika Tingkat Lanjut": ["Fungsi Komposisi & Invers", "Polinomial & Teorema Sisa", "Matriks & Determinan", "Limit, Turunan, Integral"],
                "Fisika": ["Kinematika & Dinamika", "Usaha & Energi", "Termodinamika", "Listrik & Magnet", "Optika & Gelombang"],
                "Kimia": ["Stoikiometri", "Struktur Atom & Ikatan Kimia", "Termokimia & Laju Reaksi", "Kesetimbangan Kimia", "Kimia Organik"],
                "Biologi": ["Biologi Sel & Genetika", "Sistem Organ Manusia", "Metabolisme", "Ekologi & Evolusi"]
            }
        },
        "TKA IPS": {
            "Soshum": {
                "Ekonomi": ["Konsep Dasar Ekonomi", "Permintaan & Penawaran", "Makro & Mikroekonomi", "Akuntansi Dasar"],
                "Sosiologi": ["Interaksi Sosial", "Struktur Sosial & Mobilitas", "Konflik & Integrasi Sosial", "Lembaga Sosial"],
                "Geografi": ["Pengetahuan Dasar Geografi", "Atmosfer & Litosfer", "Hidrosfer & Biosfer", "Kependudukan & SIG"],
                "Sejarah": ["Sejarah Indonesia", "Sejarah Dunia", "Pergerakan Nasional", "Perang Dunia & Perang Dingin"],
                "PPKn": ["Pancasila & Konstitusi", "Sistem Pemerintahan RI", "HAM & Demokrasi"],
                "Antropologi": ["Konsep Dasar Budaya", "Dinamika Budaya", "Etnografi"]
            }
        },
        "TKA Bahasa & Vokasi": {
            "Bahasa Asing": {
                "Bahasa Pilihan": ["Bahasa Jepang", "Bahasa Arab", "Bahasa Jerman", "Bahasa Prancis", "Bahasa Mandarin", "Bahasa Korea"]
            },
            "Vokasi": {
                "SMK / MAK": ["Produk atau Projek Kreatif", "Kewirausahaan"]
            }
        }
    }
    
    # Safe insertion helper
    
    # Clean up old TKA
    conn.execute("DELETE FROM subjects WHERE category = 'TKA'")

    for category, subjects in extended_syllabus.items():
        for subject_name, topics in subjects.items():
            # Check subject
            cur = conn.execute("SELECT id FROM subjects WHERE name = ? AND category = ?", (subject_name, category)).fetchone()
            if not cur:
                conn.execute("INSERT INTO subjects (name, category) VALUES (?, ?)", (subject_name, category))
                subject_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
            else:
                subject_id = cur["id"]
                
            for topic_name, subtopics in topics.items():
                cur_t = conn.execute("SELECT id FROM topics WHERE name = ? AND subject_id = ?", (topic_name, subject_id)).fetchone()
                if not cur_t:
                    conn.execute("INSERT INTO topics (subject_id, name) VALUES (?, ?)", (subject_id, topic_name))
                    topic_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
                else:
                    topic_id = cur_t["id"]
                    
                for subtopic_name in subtopics:
                    cur_s = conn.execute("SELECT id FROM subtopics WHERE name = ? AND topic_id = ?", (subtopic_name, topic_id)).fetchone()
                    if not cur_s:
                        conn.execute("INSERT INTO subtopics (topic_id, name) VALUES (?, ?)", (topic_id, subtopic_name))

    conn.commit()
    conn.close()

# Initialize/Migrate database on start
init_db()

@app.route("/")
def index():
    return render_template("index.html")


# --- AUTHENTICATION API ---
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            return jsonify({"error": "Unauthorized"}), 401
        return f(*args, **kwargs)
    return decorated_function

@app.route("/api/auth/status", methods=["GET"])
def auth_status():
    user_id = session.get("user_id")
    if user_id:
        conn = get_db_connection()
        user = conn.execute("SELECT username FROM users WHERE id = ?", (user_id,)).fetchone()
        conn.close()
        if user:
            return jsonify({"logged_in": True, "username": user["username"]})
    return jsonify({"logged_in": False}), 401

@app.route("/api/auth/register", methods=["POST"])
def register():
    data = request.json
    username = data.get("username")
    password = data.get("password")
    if not username or not password:
        return jsonify({"error": "Username dan password wajib diisi"}), 400
    
    conn = get_db_connection()
    user = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
    if user:
        conn.close()
        return jsonify({"error": "Username sudah terdaftar"}), 400
        
    hashed_pw = generate_password_hash(password)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, hashed_pw))
    conn.commit()
    user_id = cursor.lastrowid
    conn.close()
    
    session["user_id"] = user_id
    return jsonify({"success": True})

@app.route("/api/auth/login", methods=["POST"])
def login():
    data = request.json
    username = data.get("username")
    password = data.get("password")
    
    conn = get_db_connection()
    user = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
    conn.close()
    
    if user and check_password_hash(user["password"], password):
        session["user_id"] = user["id"]
        return jsonify({"success": True})
        
    return jsonify({"error": "Username atau password salah"}), 401

@app.route("/api/auth/logout", methods=["POST"])
def logout():
    session.pop("user_id", None)
    return jsonify({"success": True})

# --- PROFILE & ONBOARDING API ---

@app.route("/api/profile", methods=["GET"])
@login_required
def get_profile():
    conn = get_db_connection()
    profile = conn.execute("SELECT * FROM user_profiles WHERE user_id = ?", (session["user_id"],)).fetchone()
    conn.close()
    if profile:
        return jsonify(dict(profile))
    return jsonify({"onboarded": 0})

@app.route("/api/profile", methods=["POST"])
@login_required
def save_profile():
    data = request.json
    if not data:
        return jsonify({"error": "Data tidak valid"}), 400
    
    nickname = data.get("nickname")
    target_campus = data.get("target_campus")
    target_major = data.get("target_major")
    exam_focus = data.get("exam_focus")
    weakest_subject = data.get("weakest_subject")
    strongest_subject = data.get("strongest_subject")
    target_study_hours = float(data.get("target_study_hours", 2.0))
    
    onboarded = int(data.get("onboarded", 1))
    
    conn = get_db_connection()
    # Update or insert profile
    conn.execute("""
        INSERT INTO user_profiles (user_id, nickname, target_campus, target_major, exam_focus, weakest_subject, strongest_subject, target_study_hours, onboarded)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(user_id) DO UPDATE SET
            nickname=excluded.nickname,
            target_campus=excluded.target_campus,
            target_major=excluded.target_major,
            exam_focus=excluded.exam_focus,
            weakest_subject=excluded.weakest_subject,
            strongest_subject=excluded.strongest_subject,
            target_study_hours=excluded.target_study_hours,
            onboarded=excluded.onboarded
    """, (session["user_id"], nickname, target_campus, target_major, exam_focus, weakest_subject, strongest_subject, target_study_hours, onboarded))
    
    # Reset streak to 1 if first time onboarding
    conn.execute("""
        INSERT INTO streak_data (user_id, current_streak, last_active_date, longest_streak)
        VALUES (?, 1, ?, 1)
        ON CONFLICT(user_id) DO UPDATE SET current_streak = MAX(current_streak, 1)
    """, (session["user_id"], datetime.now().strftime("%Y-%m-%d")))
    
    conn.commit()
    conn.close()
    return jsonify({"success": True, "message": "Onboarding selesai!"})


# --- SYLLABUS & MATERIALS API ---

@app.route("/api/materials", methods=["GET"])
@login_required
def get_materials():
    conn = get_db_connection()
    
    # Always return ALL subjects - let the JavaScript client do the filtering by tab
    subjects_query = "SELECT * FROM subjects ORDER BY category, name"
    subjects_rows = conn.execute(subjects_query).fetchall()

    
    # Get user progress mappings
    progress_rows = conn.execute("SELECT subtopic_id, status FROM user_progress WHERE user_id = ?", (session["user_id"],)).fetchall()
    progress_map = {row["subtopic_id"]: row["status"] for row in progress_rows}
    
    result = []
    for s_row in subjects_rows:
        subject_id = s_row["id"]
        subject_name = s_row["name"]
        subject_category = s_row["category"]
        
        topics_rows = conn.execute("SELECT * FROM topics WHERE subject_id = ?", (subject_id,)).fetchall()
        topics_list = []
        
        for t_row in topics_rows:
            topic_id = t_row["id"]
            topic_name = t_row["name"]
            
            subtopics_rows = conn.execute("SELECT * FROM subtopics WHERE topic_id = ?", (topic_id,)).fetchall()
            subtopics_list = []
            
            for sub_row in subtopics_rows:
                sub_id = sub_row["id"]
                sub_name = sub_row["name"]
                
                status = progress_map.get(sub_id, "Belum Belajar")
                subtopics_list.append({
                    "id": sub_id,
                    "name": sub_name,
                    "status": status
                })
                
            topics_list.append({
                "id": topic_id,
                "name": topic_name,
                "subtopics": subtopics_list
            })
            
        result.append({
            "id": subject_id,
            "name": subject_name,
            "category": subject_category,
            "topics": topics_list
        })
        
    conn.close()
    return jsonify(result)

@app.route("/api/materials/progress", methods=["PUT"])
@login_required
def update_progress():
    data = request.json
    if not data or "subtopic_id" not in data or "status" not in data:
        return jsonify({"error": "Data tidak lengkap"}), 400
    
    subtopic_id = data["subtopic_id"]
    status = data["status"]
    updated_at = datetime.now().strftime("%Y-%m-%d %H:%M")
    
    conn = get_db_connection()
    conn.execute("""
        INSERT INTO user_progress (user_id, subtopic_id, status, updated_at)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(user_id, subtopic_id) DO UPDATE SET
            status=excluded.status,
            updated_at=excluded.updated_at
    """, (session["user_id"], subtopic_id, status, updated_at))
    conn.commit()
    conn.close()
    return jsonify({"success": True})


# --- DAILY TARGETS API ---

@app.route("/api/targets", methods=["GET"])
@login_required
def get_targets():
    today = datetime.now().strftime("%Y-%m-%d")
    conn = get_db_connection()
    targets = conn.execute("SELECT * FROM daily_targets WHERE user_id = ? AND created_at = ? ORDER BY id ASC", (session["user_id"], today)).fetchall()
    conn.close()
    return jsonify([dict(t) for t in targets])

@app.route("/api/targets", methods=["POST"])
@login_required
def add_target():
    data = request.json
    if not data or "title" not in data:
        return jsonify({"error": "Judul target wajib diisi"}), 400
    
    title = data["title"]
    today = datetime.now().strftime("%Y-%m-%d")
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO daily_targets (user_id, title, is_completed, created_at) VALUES (?, ?, 0, ?)",
        (session["user_id"], title, today)
    )
    conn.commit()
    new_id = cursor.lastrowid
    conn.close()
    
    return jsonify({"id": new_id, "title": title, "is_completed": 0, "created_at": today}), 201

@app.route("/api/targets/<int:target_id>", methods=["PUT"])
@login_required
def update_target(target_id):
    data = request.json
    is_completed = data.get("is_completed")
    if is_completed is None:
        return jsonify({"error": "Status wajib diisi"}), 400
    
    conn = get_db_connection()
    conn.execute("UPDATE daily_targets SET is_completed = ? WHERE id = ? AND user_id = ?", (1 if is_completed else 0, target_id, session["user_id"]))
    conn.commit()
    conn.close()
    return jsonify({"success": True})

@app.route("/api/targets/<int:target_id>", methods=["DELETE"])
@login_required
def delete_target(target_id):
    conn = get_db_connection()
    conn.execute("DELETE FROM daily_targets WHERE id = ? AND user_id = ?", (target_id, session["user_id"]))
    conn.commit()
    conn.close()
    return jsonify({"success": True})


# --- POMODORO STUDY SESSIONS API ---

@app.route("/api/study-sessions", methods=["GET"])
@login_required
def get_study_sessions():
    conn = get_db_connection()
    sessions = conn.execute("""
        SELECT s.*, sub.name as subject_name 
        FROM study_sessions s
        JOIN subjects sub ON s.subject_id = sub.id
        WHERE s.user_id = ?
        ORDER BY s.id DESC
    """, (session["user_id"],)).fetchall()
    conn.close()
    return jsonify([dict(s) for s in sessions])

@app.route("/api/study-sessions", methods=["POST"])
@login_required
def add_study_session():
    data = request.json
    if not data or "subject_id" not in data or "duration_seconds" not in data:
        return jsonify({"error": "Data tidak lengkap"}), 400
    
    subject_id = data["subject_id"]
    duration_seconds = int(data["duration_seconds"])
    created_at = datetime.now().strftime("%Y-%m-%d %H:%M")
    
    conn = get_db_connection()
    conn.execute(
        "INSERT INTO study_sessions (user_id, subject_id, duration_seconds, created_at) VALUES (?, ?, ?, ?)",
        (session["user_id"], subject_id, duration_seconds, created_at)
    )
    
    # Dynamic streak updating logic on study session save
    today_date = datetime.now().strftime("%Y-%m-%d")
    streak = conn.execute("SELECT * FROM streak_data WHERE user_id = ?", (session["user_id"],)).fetchone()
    if streak:
        current = streak["current_streak"]
        last_date = streak["last_active_date"]
        longest = streak["longest_streak"]
        
        if last_date != today_date:
            yesterday_date = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
            if last_date == yesterday_date:
                current += 1
            else:
                current = 1 # Streak broken
            
            new_longest = max(longest, current)
            conn.execute("""
                UPDATE streak_data 
                SET current_streak = ?, last_active_date = ?, longest_streak = ? 
                WHERE user_id = ?
            """, (current, today_date, new_longest, session["user_id"]))
    else:
        conn.execute("""
            INSERT INTO streak_data (user_id, current_streak, last_active_date, longest_streak)
            VALUES (?, 1, ?, 1)
        """, (session["user_id"], today_date))
        
    conn.commit()
    conn.close()
    return jsonify({"success": True})


# --- JOURNALS & MOOD API ---

@app.route("/api/journals", methods=["GET"])
@login_required
def get_journals():
    conn = get_db_connection()
    journals = conn.execute("""
        SELECT j.*, m.mood 
        FROM journal_entries j
        LEFT JOIN mood_records m ON j.user_id = m.user_id AND SUBSTR(j.created_at, 1, 10) = m.created_at
        WHERE j.user_id = ?
        ORDER BY j.id DESC
    """, (session["user_id"],)).fetchall()
    conn.close()
    return jsonify([dict(j) for j in journals])

@app.route("/api/journals", methods=["POST"])
@login_required
def add_journal():
    data = request.json
    if not data or "content" not in data or "mood" not in data:
        return jsonify({"error": "Data tidak lengkap"}), 400
    
    content = data["content"]
    learned_today = data.get("learned_today", "")
    difficulties = data.get("difficulties", "")
    tomorrow_plan = data.get("tomorrow_plan", "")
    mood = data["mood"]
    
    today_date = datetime.now().strftime("%Y-%m-%d")
    now_time = datetime.now().strftime("%Y-%m-%d %H:%M")
    
    conn = get_db_connection()
    # 1. Save Mood
    existing_mood = conn.execute("SELECT id FROM mood_records WHERE user_id = ? AND created_at = ?", (session["user_id"], today_date)).fetchone()
    if not existing_mood:
        conn.execute("INSERT INTO mood_records (user_id, mood, created_at) VALUES (?, ?, ?)", (session["user_id"], mood, today_date))
    
    # 2. Save Journal
    conn.execute("""
        INSERT INTO journal_entries (user_id, content, learned_today, difficulties, tomorrow_plan, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (session["user_id"], content, learned_today, difficulties, tomorrow_plan, now_time))
    
    # 3. Update Streak
    streak = conn.execute("SELECT * FROM streak_data WHERE user_id = ?", (session["user_id"],)).fetchone()
    if streak:
        current = streak["current_streak"]
        last_date = streak["last_active_date"]
        longest = streak["longest_streak"]
        
        if last_date != today_date:
            yesterday_date = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
            if last_date == yesterday_date:
                current += 1
            else:
                current = 1
            new_longest = max(longest, current)
            conn.execute("""
                UPDATE streak_data 
                SET current_streak = ?, last_active_date = ?, longest_streak = ? 
                WHERE user_id = ?
            """, (current, today_date, new_longest, session["user_id"]))
    else:
        conn.execute("""
            INSERT INTO streak_data (user_id, current_streak, last_active_date, longest_streak)
            VALUES (?, 1, ?, 1)
        """, (session["user_id"], today_date))

    conn.commit()
    conn.close()
    return jsonify({"success": True})

@app.route("/api/journals/<int:journal_id>", methods=["DELETE"])
@login_required
def delete_journal(journal_id):
    conn = get_db_connection()
    conn.execute("DELETE FROM journal_entries WHERE id = ? AND user_id = ?", (journal_id, session["user_id"]))
    conn.commit()
    conn.close()
    return jsonify({"success": True})


# --- STREAK & AMBIS FOREST API ---

@app.route("/api/streak", methods=["GET"])
@login_required
def get_streak():
    conn = get_db_connection()
    streak = conn.execute("SELECT * FROM streak_data WHERE user_id = ?", (session["user_id"],)).fetchone()
    conn.close()
    
    current = streak["current_streak"] if streak else 0
    longest = streak["longest_streak"] if streak else 0
    
    # Growth Stages
    # Hari 1-3 = Bibit, Hari 4-7 = Tunas, Hari 8-14 = Tanaman Muda, Hari 15-30 = Pohon Kecil, >30 = Pohon Besar
    if current >= 31:
        stage = "Pohon Besar"
        emoji = "🌳"
    elif current >= 15:
        stage = "Pohon Kecil"
        emoji = "🌲"
    elif current >= 8:
        stage = "Tanaman Muda"
        emoji = "🌿"
    elif current >= 4:
        stage = "Tunas"
        emoji = "🌱"
    elif current >= 1:
        stage = "Bibit"
        emoji = "🌰"
    else:
        stage = "Belum Ada"
        emoji = "❌"
        
    return jsonify({
        "current_streak": current,
        "longest_streak": longest,
        "stage": stage,
        "emoji": emoji
    })


@app.route("/api/forest/daily", methods=["GET"])
@login_required
def get_daily_forest():
    conn = get_db_connection()
    # Get user target hours
    profile = conn.execute("SELECT target_study_hours FROM user_profiles WHERE user_id = ?", (session["user_id"],)).fetchone()
    target_hours = profile["target_study_hours"] if profile else 2.0
    target_seconds = target_hours * 3600
    
    # Aggregate daily study seconds
    daily_stats = conn.execute("""
        SELECT SUBSTR(created_at, 1, 10) as study_date, SUM(duration_seconds) as total_sec
        FROM study_sessions 
        WHERE user_id = ?
        GROUP BY study_date
        ORDER BY study_date ASC
    """, (session["user_id"],)).fetchall()
    conn.close()
    
    trees = []
    for row in daily_stats:
        date = row["study_date"]
        sec = row["total_sec"]
        
        # Determine tree growth stage based on progress vs target
        ratio = sec / target_seconds if target_seconds > 0 else 0
        
        if ratio >= 1.0:
            stage = "Pohon Raksasa"
            emoji = "🌳"
        elif ratio >= 0.7:
            stage = "Pohon Besar"
            emoji = "🌲"
        elif ratio >= 0.4:
            stage = "Pohon Kecil"
            emoji = "🪴"
        elif ratio >= 0.1:
            stage = "Tunas"
            emoji = "🌿"
        else:
            stage = "Bibit"
            emoji = "🌱"
            
        trees.append({
            "date": date,
            "total_seconds": sec,
            "ratio": min(ratio, 1.0),
            "stage": stage,
            "emoji": emoji
        })
        
    return jsonify(trees)

@app.route("/api/forest", methods=["GET"])
@login_required
def get_forest():
    conn = get_db_connection()
    trees = conn.execute("SELECT * FROM ambis_forest_trees WHERE user_id = ? ORDER BY id DESC", (session["user_id"],)).fetchall()
    conn.close()
    return jsonify([dict(t) for t in trees])

@app.route("/api/forest/plant", methods=["POST"])
@login_required
def plant_tree():
    # Helper endpoint allowing student to manual plant or simulate a completed 30-day streak tree
    data = request.json
    name = data.get("name", "Pohon Belajarku")
    duration = int(data.get("duration", 30))
    top_subject = data.get("top_subject", "TPS Penalaran Kuantitatif")
    
    now_date = datetime.now().strftime("%Y-%m-%d")
    start_date = (datetime.now() - timedelta(days=duration)).strftime("%Y-%m-%d")
    
    conn = get_db_connection()
    # Count targets completed in last 30 days
    targets = conn.execute("SELECT COUNT(*) FROM daily_targets WHERE user_id = ? AND is_completed = 1", (session["user_id"],)).fetchone()[0]
    # Count study seconds
    study_sec = conn.execute("SELECT SUM(duration_seconds) FROM study_sessions WHERE user_id = ?", (session["user_id"],)).fetchone()[0]
    total_study = study_sec if study_sec else (duration * 3600)
    
    conn.execute("""
        INSERT INTO ambis_forest_trees (user_id, name, streak_length, started_date, completed_date, total_study_seconds, targets_completed, top_subject, planted_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (session["user_id"], name, duration, start_date, now_date, total_study, max(targets, 15), top_subject, now_date))
    
    conn.commit()
    conn.close()
    return jsonify({"success": True})


# --- DETAILED STATISTICS API ---

@app.route("/api/stats", methods=["GET"])
@login_required
def get_detail_stats():
    conn = get_db_connection()
    
    # 1. Total study hours & sessions per subject
    subject_hours = conn.execute("""
        SELECT s.name, COALESCE(SUM(ss.duration_seconds), 0) as total_seconds, COUNT(ss.id) as sessions
        FROM subjects s
        LEFT JOIN study_sessions ss ON s.id = ss.subject_id AND ss.user_id = ?
        GROUP BY s.id
    """, (session["user_id"],)).fetchall()
    
    subject_hours_list = []
    total_sec_all = 0
    most_studied = "Belum ada"
    max_sec = 0
    
    for row in subject_hours:
        sec = row["total_seconds"]
        total_sec_all += sec
        if sec > max_sec:
            max_sec = sec
            most_studied = row["name"]
            
        subject_hours_list.append({
            "subject": row["name"],
            "hours": round(sec / 3600.0, 2),
            "sessions": row["sessions"]
        })
        
    # 2. Progress check-off counts per subject
    progress_counts = conn.execute("""
        SELECT s.name, 
               COUNT(sub.id) as total_subtopics,
               SUM(CASE WHEN up.status = 'Sudah Menguasai' THEN 1 ELSE 0 END) as mastered_count,
               SUM(CASE WHEN up.status = 'Sedang Belajar' THEN 1 ELSE 0 END) as learning_count
        FROM subjects s
        JOIN topics t ON s.id = t.subject_id
        JOIN subtopics sub ON t.id = sub.topic_id
        LEFT JOIN user_progress up ON sub.id = up.subtopic_id AND up.user_id = ?
        GROUP BY s.id
    """, (session["user_id"],)).fetchall()
    
    subject_progress_list = []
    mastered_total = 0
    subtopics_total = 0
    
    for row in progress_counts:
        mastered = row["mastered_count"] if row["mastered_count"] else 0
        total_sub = row["total_subtopics"]
        mastered_total += mastered
        subtopics_total += total_sub
        
        subject_progress_list.append({
            "subject": row["name"],
            "total_subtopics": total_sub,
            "mastered": mastered,
            "learning": row["learning_count"] if row["learning_count"] else 0,
            "percentage": round((mastered / total_sub) * 100, 1) if total_sub > 0 else 0
        })

    # 3. Last 7 Days daily study activity
    daily_activity = []
    today = datetime.now()
    for i in range(6, -1, -1):
        day = today - timedelta(days=i)
        day_str = day.strftime("%Y-%m-%d")
        day_label = day.strftime("%a") # e.g. Mon, Tue
        
        seconds = conn.execute("""
            SELECT SUM(duration_seconds) FROM study_sessions 
            WHERE user_id = ? AND SUBSTR(created_at, 1, 10) = ?
        """, (session["user_id"], day_str)).fetchone()[0]
        
        daily_activity.append({
            "day": day_label,
            "hours": round((seconds if seconds else 0) / 3600.0, 2)
        })
        
    # 4. Mood counts
    moods_query = conn.execute("""
        SELECT mood, COUNT(*) as count FROM mood_records WHERE user_id = ? GROUP BY mood
    """, (session["user_id"],)).fetchall()
    mood_counts = {row["mood"]: row["count"] for row in moods_query}
    
    # 5. Overall SNBT & TKA completed percentages
    overall_progress = conn.execute("""
        SELECT s.category, COUNT(sub.id) as total,
               SUM(CASE WHEN up.status = 'Sudah Menguasai' THEN 1 ELSE 0 END) as mastered
        FROM subjects s
        JOIN topics t ON s.id = t.subject_id
        JOIN subtopics sub ON t.id = sub.topic_id
        LEFT JOIN user_progress up ON sub.id = up.subtopic_id AND up.user_id = ?
        GROUP BY s.category
    """, (session["user_id"],)).fetchall()
    
    snbt_percent = 0
    tka_percent = 0
    for row in overall_progress:
        tot = row["total"]
        mast = row["mastered"] if row["mastered"] else 0
        pct = round((mast / tot) * 100, 1) if tot > 0 else 0
        if row["category"] == "SNBT":
            snbt_percent = pct
        elif row["category"] == "TKA":
            tka_percent = pct

    conn.close()
    
    return jsonify({
        "total_study_hours": round(total_sec_all / 3600.0, 1),
        "most_studied_subject": most_studied,
        "daily_activity": daily_activity,
        "subject_hours": subject_hours_list,
        "subject_progress": subject_progress_list,
        "mood_distribution": {
            "Happy": mood_counts.get("Happy", 0),
            "Excited": mood_counts.get("Excited", 0),
            "Focused": mood_counts.get("Focused", 0),
            "Tired": mood_counts.get("Tired", 0),
            "Stressed": mood_counts.get("Stressed", 0)
        },
        "snbt_completion_percentage": snbt_percent,
        "tka_completion_percentage": tka_percent
    })


# --- REFLECTION AI (RULE-BASED SYSTEM ENGINE) ---

@app.route("/api/reflection", methods=["GET"])
@login_required
def get_reflection():
    today_date = datetime.now().strftime("%Y-%m-%d")
    conn = get_db_connection()
    
    profile = conn.execute("SELECT * FROM user_profiles WHERE user_id = ?", (session["user_id"],)).fetchone()
    if not profile:
        conn.close()
        return jsonify({"reflection": "Halo! Silakan selesaikan proses onboarding terlebih dahulu agar AI dapat menganalisis pola belajarmu."})
        
    nickname = profile["nickname"]
    target_campus = profile["target_campus"]
    target_major = profile["target_major"]
    weakest = profile["weakest_subject"]
    strongest = profile["strongest_subject"]
    target_hours = profile["target_study_hours"]
    
    # 1. Today's study session totals
    seconds_today = conn.execute("SELECT SUM(duration_seconds) FROM study_sessions WHERE user_id = ? AND SUBSTR(created_at, 1, 10) = ?", (session["user_id"], today_date)).fetchone()[0]
    hours_today = round((seconds_today if seconds_today else 0) / 3600.0, 2)
    
    # 2. Today's journal & mood
    journal_today = conn.execute("SELECT * FROM journal_entries WHERE user_id = ? AND SUBSTR(created_at, 1, 10) = ? ORDER BY id DESC", (session["user_id"], today_date)).fetchone()
    mood_today_row = conn.execute("SELECT mood FROM mood_records WHERE user_id = ? AND created_at = ?", (session["user_id"], today_date)).fetchone()
    mood_today = mood_today_row["mood"] if mood_today_row else "Focused"
    
    # 3. Today's targets stats
    total_targets = conn.execute("SELECT COUNT(*) FROM daily_targets WHERE user_id = ? AND created_at = ?", (session["user_id"], today_date)).fetchone()[0]
    completed_targets = conn.execute("SELECT COUNT(*) FROM daily_targets WHERE user_id = ? AND created_at = ? AND is_completed = 1", (session["user_id"], today_date)).fetchone()[0]
    
    # 4. Mastered subtopics today
    subtopics_mastered = conn.execute("SELECT COUNT(*) FROM user_progress WHERE user_id = ? AND status = 'Sudah Menguasai' AND SUBSTR(updated_at, 1, 10) = ?", (session["user_id"], today_date)).fetchone()[0]
    
    conn.close()
    
    # Core Intelligent Response Generator
    greeting = f"Halo {nickname}! Ini adalah evaluasi belajar harianmu untuk persiapan masuk {target_major} di {target_campus}.\n\n"
    
    # Performance summary
    performance = ""
    if hours_today > 0:
        performance += f"🎯 Hari ini kamu telah belajar selama **{hours_today} jam** (Target: {target_hours} jam). Dedikasi yang luar biasa! "
        if hours_today >= target_hours:
            performance += "Kamu berhasil mencapai target jam belajarmu hari ini. Pertahankan konsistensi ini! 🔥\n\n"
        else:
            performance += f"Sedikit lagi mencapai targetmu. Tidak apa-apa, setiap menit belajar membawamu lebih dekat ke {target_campus}.\n\n"
    else:
        performance += f"⚠️ Hari ini AI mencatat belum ada sesi belajar yang direkam menggunakan Pomodoro Timer. Istirahat itu penting, namun pastikan besok kamu menyisihkan waktu minimal 30 menit untuk mereview materi terlemahmu: **{weakest}**.\n\n"
        
    # Journal and Mood Analysis
    journal_insight = ""
    if journal_today:
        story = journal_today["content"]
        difficulties = journal_today["difficulties"]
        
        journal_insight += f"🧠 **Analisis Cerita & Hambatan:**\nKamu mencatat bahwa kamu belajar mengenai hal-hari ini dan merasakan mood **{mood_today}**. "
        if mood_today in ["Tired", "Stressed"]:
            journal_insight += "Wajar sekali jika merasa lelah atau tertekan di kelas 12. Jangan memaksakan diri secara berlebihan. Pomodoro 25 menit belajar + 5 menit istirahat sangat disarankan untuk menjaga energi mentalmu. "
        else:
            journal_insight += "Senang mendengar suasana hatimu positif saat belajar! Ini adalah waktu terbaik untuk menaklukkan bab-bab yang sulit. "
            
        if difficulties and len(difficulties.strip()) > 3:
            journal_insight += f"Mengenai kesulitanmu pada *\"{difficulties}\"*, coba pecah materi tersebut menjadi submateri terkecil dan pelajari peta konsepnya terlebih dahulu di menu Silabus.\n\n"
        else:
            journal_insight += "Kamu tidak melaporkan hambatan besar hari ini, kerja bagus!\n\n"
    else:
        journal_insight += f"📝 **Rekomendasi Aktivitas:**\nKamu belum menulis jurnal atau mood hari ini. Menulis evaluasi belajar harian terbukti membantu memperkuat memori jangka panjang dan meredakan burnout persiapan SNBT.\n\n"

    # Targets & Mastered check-off Analysis
    progress_insight = ""
    if total_targets > 0:
        progress_insight += f"✅ **Target Harian:**\nKamu berhasil menyelesaikan **{completed_targets} dari {total_targets}** target belajar hari ini. "
        if completed_targets == total_targets:
            progress_insight += "Semua target tercapai bersih! Kamu berhak mendapat bintang belajar hari ini. ⭐\n"
        else:
            progress_insight += "Ada beberapa target yang tertunda. Coba jadwalkan ulang target tersebut untuk besok pagi agar tidak menumpuk.\n"
            
    if subtopics_mastered > 0:
        progress_insight += f"📚 Hari ini kamu juga menandai **{subtopics_mastered} submateri** baru sebagai 'Sudah Menguasai'. Progres yang konkret!\n"
    
    progress_insight += "\n"

    # Future Action Plan
    action_plan = f"💡 **Saran Belajar Besok:**\n1. Mulai hari dengan meninjau ulang materi terkuatmu (**{strongest}**) selama 15 menit untuk memicu rasa percaya diri.\n"
    action_plan += f"2. Sediakan 1 sesi Pomodoro (25 menit) khusus untuk mencicil materi terlemahmu (**{weakest}**).\n"
    action_plan += f"3. Tulis jurnal belajarmu segera setelah menyelesaikan target harian untuk menjaga agar pohon belajarmu di **Ambis Forest** terus tumbuh subur! 🌳"
    
    reflection_text = greeting + performance + journal_insight + progress_insight + action_plan
    
    return jsonify({
        "reflection": reflection_text,
        "mood_today": mood_today,
        "hours_today": hours_today,
        "completed_targets": completed_targets,
        "total_targets": total_targets
    })

if __name__ == "__main__":
    app.run(debug=True, host="127.0.0.1", port=5000)
