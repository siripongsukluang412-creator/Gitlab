# Transistor DC Bias Simulator — ENG29 2121

เว็บแอป Flask สำหรับคำนวณ DC operating point ของ BJT แบบ
common-emitter voltage-divider bias (Lab 02)

## ความต้องการของระบบ

- Python 3.10 ขึ้นไป (ทดสอบด้วย 3.14)
- Flask 3.1

## ติดตั้งและรัน

```powershell
cd transistor-simulator
py -m pip install -r requirements.txt
py app.py
```

เปิดเบราว์เซอร์ที่ <http://127.0.0.1:5000>

> หมายเหตุ: บนเครื่องนี้คำสั่ง `python` อาจชี้ไปที่ Microsoft Store
> ให้ใช้ `py` แทน

## การใช้งาน

1. กรอกค่า V_CC, R_1, R_2, R_C, R_E, β, V_BE
2. เลือกหน่วยของแต่ละช่อง (V/mV, Ω/kΩ/MΩ)
3. กด **Calculate DC Bias**
4. ดูผล IB, IC, IE, VCE, VB, VC, VE และสถานะ region

ค่าเริ่มต้นเป็นตัวอย่างจากโจทย์:

| พารามิเตอร์ | ค่า |
|---|---|
| V_CC | 12.0 V |
| R_1 | 100 kΩ |
| R_2 | 22 kΩ |
| R_C | 2.2 kΩ |
| R_E | 1.0 kΩ |
| β | 100 |
| V_BE | 0.70 V |

## วิธีคำนวณ

ใช้ Thevenin equivalent ของตัวแบ่งแรงดัน เพื่อให้กระแสเบสปรากฏชัด
แทนการประมาณว่า IB ≈ 0:

```
VBB = VCC * R2 / (R1 + R2)
RTH = R1 || R2
IB  = (VBB - VBE) / (RTH + (β + 1) * RE)
IC  = β * IB
IE  = (β + 1) * IB
VCE = VCC - IC * RC - IE * RE
```

- `VBB <= VBE` → **cutoff**
- `VCE < 0.2 V` (`VCE_SAT`) → **saturation**
- อื่น ๆ → **active**

รายละเอียดการตรวจสอบด้วยการคำนวณมืออยู่ใน
[`docs/validation.md`](docs/validation.md)

## รัน test

```powershell
py -m unittest discover -s tests -t . -v
```

มี 21 tests ครอบคลุม:

- ค่าตัวอย่างที่คำนวณมือ (independent reference)
- ขอบเขต cutoff / saturation
- validation ทุกฟิลด์
- HTTP route, การแปลงหน่วย และการแสดงผล

## โครงสร้าง

```
transistor-simulator/
├── app.py                  # Flask routes + unit conversion
├── dc_bias.py              # pure engineering logic (no Flask)
├── templates/index.html    # form, circuit diagram, results
├── static/style.css        # responsive layout
├── tests/
│   ├── test_dc_bias.py     # engineering logic
│   └── test_web.py         # HTTP routes
├── requirements.txt
├── README.md
├── AGENTS.md
└── docs/
    ├── design-note.md
    ├── validation.md
    └── reflection.md
```

## ข้อจำกัด

- DC bias เท่านั้น ไม่มี AC, transient หรือ frequency response
- ไม่มี circuit editor และไม่รองรับ FET
- ค่า `VCE_SAT = 0.2 V` เป็นค่าคงที่ (typical small-signal BJT)
