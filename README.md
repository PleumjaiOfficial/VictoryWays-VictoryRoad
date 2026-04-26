# Victory Partner

AI ผู้ช่วยสร้างแผนการเรียนและ Worksheet สำหรับ Victory Academy

## วิธีใช้งาน

### 1. ติดตั้ง
```bash
cd VictoryPartner
pip install -r requirements.txt
```

### 2. ตั้งค่า API Keys
```bash
cp .env.example .env
# แก้ไข .env ใส่ ANTHROPIC_API_KEY และ SUPABASE credentials
```

### 3. วาง Logo
วาง logo ไว้ที่ `assets/logos/`:
- `logo_top_left.png`  — มุมบนซ้าย
- `logo_top_right.png` — มุมบนขวา
- `logo_bottom_left.png`  — มุมล่างซ้าย
- `logo_bottom_right.png` — มุมล่างขวา
- `watermark.png` — ลายน้ำ

### 4. รันแอป
```bash
streamlit run app.py
```

## โครงสร้างโปรเจค
```
VictoryPartner/
├── app.py                    # หน้าหลัก Streamlit
├── requirements.txt
├── .env                      # API keys (ห้าม commit)
├── assets/logos/             # ไฟล์ logo
├── data/                     # Worksheet ที่ generate แล้ว
└── utils/
    ├── plan_generator.py     # สร้างแผนด้วย Claude API
    ├── worksheet_generator.py # สร้าง Word document
    └── db_client.py          # เชื่อมต่อ Supabase
```
