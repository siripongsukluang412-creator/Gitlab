# Transistor DC Bias Simulator — ENG29 2121

เว็บแอป Flask สำหรับคำนวณ DC operating point ของ BJT
แบบ common-emitter (Lab 02) รองรับ 3 โหมดแหล่งจ่ายเดียว:

- **Divider Bias** — voltage-divider bias (ค่าเดิมของแล็บ)
- **Fixed Bias** — ไบอัสฐานด้วย `R_B` ตัวเดียว ไม่มี `R_E`
- **Emitter Bias** — `R_B` จาก VCC ไปฐาน และ `R_E` ลงกราวด์

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

1. เลือกโหมด **Divider Bias**, **Fixed Bias**, หรือ **Emitter Bias**
2. กรอกค่าอินพุตของโหมดนั้น (หน่วย V/mV, Ω/kΩ/MΩ)
3. กด **Calculate DC Bias**
4. ดูผล IB, IC, IE, VCE, VB, VC, VE และสถานะ region

| โหมด | อินพุต |
|---|---|
| Divider Bias | `V_CC, R_1, R_2, R_C, R_E, β, V_BE` |
| Fixed Bias | `V_CC, R_B, R_C, β, V_BE` |
| Emitter Bias | `V_CC, R_B, R_C, R_E, β, V_BE` |

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

## ตารางตรวจรับ A1–A5

ค่าที่ใช้ร่วมกันทุกกรณี: `VCC = 12 V`, `RC = 2.2 kΩ`, `β = 100`, `VBE = 0.70 V`
ตรวจด้วย **OpenCode Browser** ที่ <http://127.0.0.1:5000> โดยเทียบกับค่าอ้างอิง
ที่คำนวณมือแบบไม่อิงโปรแกรม (ดูรายละเอียดและหลักฐานใน
[docs/validation.md](docs/validation.md))

| กรณี | เลือกโหมดและกรอกค่า | IC อ้างอิง | VCE อ้างอิง | เห็นจริง | สถานะ |
|---|---|---|---|---|---|
| A1 · โหมดเดิม | Divider · R1 = 100 kΩ, R2 = 22 kΩ, RE = 1 kΩ | 1.2299 mA | 8.0522 V | IC 1.23 mA · VCE 8.05 V | PASS |
| A2 · Fixed | Fixed · RB = 1 MΩ | 1.1300 mA | 9.5140 V | IC 1.13 mA · VCE 9.51 V | PASS |
| A3 · Emitter | Emitter · RB = 1 MΩ, RE = 1 kΩ | 1.02634 mA | 8.70545 V | IC 1.03 mA · VCE 8.71 V | PASS |
| A4 · เปลี่ยนค่าเดียว | Emitter · เหมือน A3 แต่ RE = 2 kΩ | 0.94010 mA | 8.03278 V | IC 940.1 µA · VCE 8.03 V | PASS |
| A5 · อินพุตผิด | Fixed · RB = 0 | — | — | HTTP 400 · `R_B must be greater than 0 Ω.` | PASS |

เกณฑ์ผ่าน: `|IC − IC_ref| ≤ 0.01 mA` และ `|VCE − VCE_ref| ≤ 0.02 V`
โดยเทียบค่าอ้างอิงที่ยังไม่ปัดเศษ หน้าเว็บแสดงแรงดัน 2 ตำแหน่งทศนิยม
และกระแส 2 ตำแหน่งทศนิยม (µA 1 ตำแหน่ง)

## วิธีคำนวณ

### Divider Bias

ใช้ Thevenin equivalent ของตัวแบ่งแรงดัน เพื่อให้กระแสเบสปรากฏชัด
แทนการประมาณว่า IB ≈ 0:

```text
VBB = VCC * R2 / (R1 + R2)
RTH = R1 || R2
IB  = (VBB - VBE) / (RTH + (β + 1) * RE)
IC  = β * IB
IE  = (β + 1) * IB
VCE = VCC - IC * RC - IE * RE
VE  = IE * RE
VC  = VCC - IC * RC
VB  = VE + VBE
```

- `VBB <= VBE` → **cutoff**
- `VCE < 0.2 V` (`VCE_SAT`) → **saturation**
- อื่น ๆ → **active**

### Fixed Bias

```text
IB  = (VCC - VBE) / RB
IC  = β * IB
IE  = (β + 1) * IB
VCE = VCC - IC * RC
VE  = 0
VC  = VCE
VB  = VBE
```

### Emitter Bias (แหล่งจ่ายเดียว)

```text
IB  = (VCC - VBE) / (RB + (β + 1) * RE)
IC  = β * IB
IE  = (β + 1) * IB
VCE = VCC - IC * RC - IE * RE
VE  = IE * RE
VC  = VCC - IC * RC
VB  = VE + VBE
```

ทั้ง Fixed Bias และ Emitter Bias ใช้ `VCC <= VBE` เป็นเงื่อนไข cutoff
และ `VCE < 0.2 V` เป็นเงื่อนไข saturation

ผลลัพธ์ทุกโหมดถูกส่งกลับเป็น `dict` คีย์เดียวกัน
(`vb, ve, vc, vce, ib, ic, ie, region, warnings`) โดยค่าภายในเป็น SI
และหน่วยแสดงผลอยู่ใน `dc_bias.RESULT_UNITS`

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
