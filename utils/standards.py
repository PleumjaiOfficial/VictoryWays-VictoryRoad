"""
Victory Partner — Standards Suggester
ให้ Claude แนะนำตัวชี้วัดชั้นปีจากหลักสูตรแกนกลาง สพฐ พ.ศ. 2551
"""

import anthropic
import json
import os


def suggest_standards(subject: str, level: str, topic: str) -> list[str]:
    """
    ให้ Claude แนะนำตัวชี้วัด สพฐ ที่เกี่ยวข้องกับวิชา ระดับชั้น และหัวข้อที่สอน
    Returns: list ของตัวชี้วัด เช่น ["ค 1.1 ป.6/2 : บวก ลบ คูณ หารเศษส่วน", ...]
    """
    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

    prompt = f"""คุณเป็นผู้เชี่ยวชาญหลักสูตรแกนกลางการศึกษาขั้นพื้นฐาน พ.ศ. 2551 ของ สพฐ.

วิชา: {subject}
ระดับชั้น: {level}
หัวข้อที่สอน: {topic}

กรุณาแนะนำตัวชี้วัดชั้นปี (ตัวชี้วัด) ที่เกี่ยวข้องกับหัวข้อนี้มากที่สุด 3-5 ข้อ

ตอบเฉพาะ JSON array เท่านั้น ไม่มีข้อความอื่น:
["รหัส : คำอธิบายตัวชี้วัด", ...]

ตัวอย่างรูปแบบ:
["ค 1.1 ป.6/1 : เข้าใจความหมายและความสัมพันธ์ของจำนวนนับ", "ค 1.1 ป.6/2 : บวก ลบ คูณ หารเศษส่วนและจำนวนคละ"]"""

    response = client.messages.create(
        model="claude-3-haiku-20240307",
        max_tokens=600,
        messages=[{"role": "user", "content": prompt}],
    )

    raw = response.content[0].text.strip()
    start = raw.find("[")
    end = raw.rfind("]") + 1
    if start >= 0 and end > start:
        return json.loads(raw[start:end])
    return []
