"""
Victory Partner — Plan Generator
ใช้ Claude API สร้างแผนการเรียนตามหลักสูตร สพฐ
"""

import anthropic
import json
import os


def generate_lesson_plan(
    student_name: str,
    level: str,
    subjects: list[str],
    goal: str,
    topics: str,
    schedule_dates: list[str],
    hours_per_block: float,
) -> dict:
    """
    ส่ง input ไปให้ Claude แล้วได้ block diagram structure กลับมา

    Returns:
        dict: {
            "student_name": ...,
            "level": ...,
            "blocks": [
                {
                    "date": "2025-06-01",
                    "subjects": [
                        {
                            "subject": "คณิตศาสตร์",
                            "topic": "เศษส่วน",
                            "type": "พื้นฐาน",   # พื้นฐาน / กลาง / ทดสอบ
                            "lecture_link": "",
                            "hours": 1.5,
                            "color": "green"      # green / blue / red
                        }
                    ]
                }
            ]
        }
    """
    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

    prompt = f"""คุณเป็น Victory Partner ผู้ช่วย AI ด้านการศึกษาไทย

ให้สร้างแผนการเรียนสำหรับ:
- นักเรียน: {student_name}
- ระดับชั้น: {level}
- วิชา: {', '.join(subjects)}
- เป้าหมาย: {goal}
- เนื้อหาที่ต้องสอน: {topics}
- วันที่เรียน: {', '.join(schedule_dates)}
- ชั่วโมงต่อ block: {hours_per_block}

อ้างอิงหลักสูตรแกนกลางการศึกษาขั้นพื้นฐาน พ.ศ. 2551 ของ สพฐ.

กรุณาตอบเป็น JSON เท่านั้น ในรูปแบบ:
{{
  "blocks": [
    {{
      "date": "YYYY-MM-DD",
      "subjects": [
        {{
          "subject": "ชื่อวิชา",
          "topic": "หัวข้อ",
          "type": "พื้นฐาน",
          "hours": {hours_per_block},
          "color": "green",
          "lecture_link": ""
        }}
      ]
    }}
  ]
}}

กฎการกำหนดสี:
- สีเขียว (green): คาบเรียนพื้นฐาน
- สีฟ้า (blue): แบบฝึกหัดระดับกลาง
- สีแดง (red): วันทดสอบเก็บคะแนน

จัดสัดส่วนให้เหมาะสม: 60% พื้นฐาน, 30% กลาง, 10% ทดสอบ"""

    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=4096,
        messages=[{"role": "user", "content": prompt}],
    )

    raw = message.content[0].text
    # ดึง JSON ออกจาก response
    start = raw.find("{")
    end = raw.rfind("}") + 1
    plan = json.loads(raw[start:end])
    plan["student_name"] = student_name
    plan["level"] = level
    return plan
