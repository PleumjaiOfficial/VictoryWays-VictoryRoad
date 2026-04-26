# Victory Academy — Database Schema
> Supabase (PostgreSQL) · อัปเดตล่าสุด: เมษายน 2568

---

## ภาพรวม Tables

| Table | คำอธิบาย |
|---|---|
| `victory_roads` | Victory Road (ห้องเรียน/กลุ่ม) |
| `cohort_sprints` | Parent sprint สำหรับ Cohort VR |
| `sprints` | Sprint จริง (personal หรือ sub-sprint) |
| `students` | ข้อมูลนักเรียน |
| `teachers` | ข้อมูลครู |
| `sprint_attendance` | การเข้าเรียน + คะแนน + feedback ต่อ sprint ต่อนักเรียน |
| `student_performance` | คะแนน normalized สำหรับ analytics |
| `student_payments` | การเงิน: ค่าเรียนนักเรียน |
| `teacher_expenses` | การเงิน: ค่าสอนครู |
| `app_settings` | การตั้งค่า app |

---

## 1. `victory_roads`

Victory Road คือ "ห้องเรียน" หนึ่งที่มีนักเรียนและ sprint ในนั้น

| Column | Type | Nullable | หมายเหตุ |
|---|---|---|---|
| `id` | UUID | PK | auto-generated |
| `name` | TEXT | NOT NULL | ชื่อ Victory Road |
| `level` | TEXT | | ระดับชั้นนักเรียน เช่น "มัธยมศึกษาปีที่ 3" |
| `road_type` | TEXT | | `"cohort"` = เรียนกลุ่ม, `"personalize"` = เรียนตัวต่อตัว |
| `students` | JSONB | | array ของ student objects `[{id, nickname, name, ...}]` |
| `status` | TEXT | | `"draft"` หรือ `"published"` |
| `created_at` | TIMESTAMPTZ | | auto |

**Enum values:**
- `road_type`: `cohort` | `personalize`
- `status`: `draft` | `published`

---

## 2. `cohort_sprints`

Parent sprint ใช้เฉพาะ Cohort VR — เป็นตัว "หัวข้อ" ที่มี sub-sprint แขวนอยู่

| Column | Type | Nullable | หมายเหตุ |
|---|---|---|---|
| `id` | UUID | PK | |
| `victory_road_id` | UUID | FK → `victory_roads.id` | |
| `name` | TEXT | | ชื่อ sprint หลัก |
| `sprint_type` | TEXT | | `"regular"` (เรียนทั่วไป) หรือ `"test"` (ทดสอบ) |
| `order_index` | INT | | ลำดับการแสดงผล |

---

## 3. `sprints`

Sprint จริงที่ใช้สอน — ใช้ได้ทั้ง Personalize (personal sprint) และ Cohort (sub-sprint)

| Column | Type | Nullable | หมายเหตุ |
|---|---|---|---|
| `id` | UUID | PK | |
| `victory_road_id` | UUID | FK → `victory_roads.id` | |
| `cohort_sprint_id` | UUID | FK → `cohort_sprints.id` | NULL ถ้าเป็น personal sprint |
| `name` | TEXT | | ชื่อ sprint / sub-sprint |
| `subject` | TEXT | | วิชา (ดู enum ด้านล่าง) |
| `sprint_type` | TEXT | | ประเภท sprint (ดู enum ด้านล่าง) |
| `date` | DATE | | วันที่สอน |
| `start_time` | TEXT | | เวลาเริ่ม format `"HH:MM"` เช่น `"16:30"` |
| `end_time` | TEXT | | เวลาจบ format `"HH:MM"` เช่น `"17:30"` |
| `minutes` | INT | | ระยะเวลา (นาที) คำนวณจาก end_time − start_time |
| `teacher` | TEXT | | ชื่อครูผู้สอน |
| `lecture_link` | TEXT | | URL สไลด์/วิดีโอ lecture |
| `ws_link` | TEXT | | URL Worksheet |
| `cover_photo` | TEXT | | URL รูปปก (จาก Supabase Storage bucket `cover_photo_sprint`) ถ้าว่าง = ใช้ default ตามวิชา |
| `done` | BOOLEAN | | `true` = สอนจบแล้ว |
| `student_scores` | JSONB | | `{"nickname": {"earned": 8, "max": 10}}` |
| `order_index` | INT | | ลำดับการแสดงผลภายใน road |

**Enum values:**
- `subject`: `คณิตศาสตร์` | `วิทยาศาสตร์` | `ภาษาอังกฤษ` | `ภาษาไทย`
- `sprint_type` (sub-sprint): `foundation` (สร้างพื้นฐาน) | `practice` (เพิ่มความชำนาญ) | `test` (ทดสอบ)

**Default cover photos** (Supabase Storage bucket: `cover_photo_sprint`):
| วิชา | ไฟล์ |
|---|---|
| คณิตศาสตร์ | `math_bd_logo.png` |
| วิทยาศาสตร์ | `sci_bd_logo.png` |
| ภาษาอังกฤษ | `eng_bd_logo.png` |
| ภาษาไทย | `thai_bd_logo.png` |

---

## 4. `students`

| Column | Type | Nullable | หมายเหตุ |
|---|---|---|---|
| `id` | UUID | PK | |
| `nickname` | TEXT | NOT NULL | ชื่อเล่น (ใช้แทน key ในระบบ) |
| `name` | TEXT | NOT NULL | ชื่อจริง |
| `surname` | TEXT | | นามสกุล |
| `level` | TEXT | | ระดับชั้น เช่น "มัธยมศึกษาปีที่ 3" |
| `phone` | TEXT | | เบอร์โทรศัพท์ |
| `line_id` | TEXT | | Line ID |
| `username` | TEXT | | username สำหรับ login เว็บไซต์ |
| `password_hash` | TEXT | | SHA-256 hash ของ password |
| `created_at` | TIMESTAMPTZ | | auto |

---

## 5. `teachers`

| Column | Type | Nullable | หมายเหตุ |
|---|---|---|---|
| `id` | UUID | PK | |
| `nickname` | TEXT | NOT NULL | ชื่อเล่น |
| `name` | TEXT | NOT NULL | ชื่อจริง |
| `surname` | TEXT | | นามสกุล |
| `subjects` | TEXT | | วิชาที่สอน comma-separated เช่น `"คณิตศาสตร์,วิทยาศาสตร์"` |
| `username` | TEXT | | username |
| `password_hash` | TEXT | | SHA-256 hash ของ password |
| `created_at` | TIMESTAMPTZ | | auto |

---

## 6. `sprint_attendance`

บันทึกการเข้าเรียน + คะแนน + feedback ของนักเรียนแต่ละคนต่อ sprint

| Column | Type | Nullable | หมายเหตุ |
|---|---|---|---|
| `id` | UUID | PK | |
| `sprint_id` | UUID | FK → `sprints.id` | |
| `student_id` | UUID | FK → `students.id` | |
| `status` | TEXT | | `"present"` | `"absent"` | `"n/a"` |
| `teacher_feedback` | TEXT | | Feedback จากครูถึงนักเรียน (กรอกจากเว็บไซต์ครู) |
| `student_ws_link` | TEXT | | Link worksheet ที่นักเรียนส่ง |
| `updated_at` | TIMESTAMPTZ | | |

**Unique constraint:** `(sprint_id, student_id)`

---

## 7. `student_performance`

ข้อมูลคะแนน normalized สำหรับ analytics และ dashboard นักเรียน
(sync อัตโนมัติทุกครั้งที่ admin บันทึกคะแนน)

| Column | Type | Nullable | หมายเหตุ |
|---|---|---|---|
| `id` | UUID | PK | |
| `student_id` | UUID | FK → `students.id` | |
| `sprint_id` | UUID | FK → `sprints.id` | |
| `victory_road_id` | UUID | FK → `victory_roads.id` | |
| `subject` | TEXT | | วิชา |
| `date` | DATE | | วันที่สอน |
| `earned` | NUMERIC | | คะแนนที่ได้ |
| `max` | NUMERIC | | คะแนนเต็ม |
| `score_pct` | NUMERIC | | เปอร์เซ็นต์ `(earned/max * 100)` |

**Unique constraint:** `(student_id, sprint_id)`

---

## 8. `student_payments`

ติดตามการชำระค่าเรียนของนักเรียนต่อ Victory Road

| Column | Type | Nullable | หมายเหตุ |
|---|---|---|---|
| `id` | UUID | PK | |
| `student_id` | UUID | FK → `students.id` | |
| `victory_road_id` | UUID | FK → `victory_roads.id` | |
| `payment_status` | TEXT | | `"pending"` | `"success"` |
| `fee` | NUMERIC | | ค่าเรียนทั้งหมดที่ต้องชำระ |
| `amount` | NUMERIC | | ยอดที่รับแล้ว |
| `note` | TEXT | | หมายเหตุ |
| `updated_at` | TIMESTAMPTZ | | |

**Unique constraint:** `(student_id, victory_road_id)`

---

## 9. `teacher_expenses`

บันทึกค่าสอนครูต่อ sprint

| Column | Type | Nullable | หมายเหตุ |
|---|---|---|---|
| `id` | UUID | PK | |
| `sprint_id` | UUID | FK → `sprints.id` | |
| `teacher_id` | UUID | FK → `teachers.id` | |
| `teacher_name` | TEXT | | snapshot ชื่อครู ณ เวลาบันทึก |
| `sprint_name` | TEXT | | snapshot ชื่อ sprint |
| `victory_road_id` | UUID | FK → `victory_roads.id` | |
| `victory_road_name` | TEXT | | snapshot ชื่อ VR |
| `subject` | TEXT | | วิชา |
| `amount` | NUMERIC | | ค่าสอน (บาท) |
| `payment_status` | TEXT | | `"unpaid"` | `"paid"` |
| `expense_date` | DATE | | วันที่สอน |
| `note` | TEXT | | หมายเหตุ |
| `created_at` | TIMESTAMPTZ | | auto |

**Unique constraint:** `(sprint_id, teacher_id)`

---

## 10. `app_settings`

Key-value store สำหรับการตั้งค่า app

| Column | Type | หมายเหตุ |
|---|---|---|
| `key` | TEXT PK | ชื่อ setting |
| `value` | TEXT | ค่า |

**Keys ที่ใช้อยู่:**
| Key | Value | ความหมาย |
|---|---|---|
| `sim_open` | `"true"` / `"false"` | เปิด/ปิด Victory Partner (simulation mode) |

---

## Relationships Diagram

```
victory_roads
    ├── cohort_sprints (1:many)
    │       └── sprints (1:many) ← sub-sprints
    ├── sprints (1:many) ← personal sprints
    └── student_payments (1:many)

students
    ├── sprint_attendance (1:many)
    ├── student_performance (1:many)
    └── student_payments (1:many)

teachers
    └── teacher_expenses (1:many)

sprints
    ├── sprint_attendance (1:many)
    ├── student_performance (1:many)
    └── teacher_expenses (1:many)
```

---

## Storage Buckets

| Bucket | Access | เก็บอะไร |
|---|---|---|
| `cover_photo_sprint` | Public | รูปปก sprint (default + custom) |
