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

ตารางนี้ใช้ค่าเริ่มต้นของแต่ละโหมดในหน้าเว็บ เพื่อตรวจผลผ่าน Browser
ก่อนเทียบค่าที่คำนวณด้วยมือ

| รหัส | หัวข้อ | สิ่งที่ตรวจ | ค่าที่ใช้ตรวจ / ผลที่คาดหวัง | สถานะ |
|---|---|---|---|---|
| A1 | หน้าเว็บ Flask | เปิด `http://127.0.0.1:5000` ได้, มีแท็บ Divider/Fixed/Emitter, ฟอร์มและวงจรแสดงตามโหมด | `py app.py` แล้วเปิดเบราว์เซอร์ | ผ่าน |
| A2 | Divider Bias | สมการ Thevenin และผลลัพธ์เดิมของแล็บต้องไม่เปลี่ยน | `VCC=12 V, R1=100 kΩ, R2=22 kΩ, RC=2.2 kΩ, RE=1 kΩ, β=100, VBE=0.7 V` → `VB=1.94 V, VE=1.24 V, VC=9.29 V, VCE=8.05 V, IB=12.3 µA, IC=1.23 mA, IE=1.24 mA` | ผ่าน |
| A3 | Fixed Bias | ใช้ `R_B` ตัวเดียว ไม่มี `R_E`, คำนวณ IB/IC/IE/VCE ถูกต้อง | `VCC=12 V, RB=470 kΩ, RC=2.2 kΩ, β=100, VBE=0.7 V` → `VB=0.70 V, VE=0.00 V, VC=6.71 V, VCE=6.71 V, IB=24.0 µA, IC=2.40 mA, IE=2.43 mA` | ผ่าน |
| A4 | Emitter Bias | ใช้ `R_B` จาก VCC ไปฐาน และ `R_E` ลงกราวด์, คำนวณจุดทำงานถูกต้อง | `VCC=12 V, RB=470 kΩ, RC=2.2 kΩ, RE=1 kΩ, β=100, VBE=0.7 V` → `VB=2.70 V, VE=2.00 V, VC=7.65 V, VCE=5.65 V, IB=19.8 µA, IC=1.98 mA, IE=2.00 mA` | ผ่าน |
| A5 | Validation และหน่วย | ตรวจอินพุตตามโหมด, แปลงหน่วย V/mV และ Ω/kΩ/MΩ, แสดง cutoff/saturation | `RB=0` หรือ `RE=0` ต้องได้ HTTP 400; ค่า kΩ กับ Ω ต้องให้ผลเดียวกัน; `VCE < 0.2 V` ต้องขึ้น saturation | ผ่าน |

### ค่าผลลัพธ์ที่แสดงบนหน้าเว็บ (ค่า default)

| โหมด | VB | VE | VC | VCE | IB | IC | IE |
|---|---:|---:|---:|---:|---:|---:|---:|
| Divider Bias (A2) | 1.94 V | 1.24 V | 9.29 V | 8.05 V | 12.3 µA | 1.23 mA | 1.24 mA |
| Fixed Bias (A3) | 0.70 V | 0.00 V | 6.71 V | 6.71 V | 24.0 µA | 2.40 mA | 2.43 mA |
| Emitter Bias (A4) | 2.70 V | 2.00 V | 7.65 V | 5.65 V | 19.8 µA | 1.98 mA | 2.00 mA |

> ค่าข้างต้นเป็นค่าที่แสดงใน Browser เมื่อใช้ค่า default ของแต่ละโหมด
> และสถานะทั้งสามโหมดเป็น **Active region approximation OK**

> หมายเหตุ: ค่าในตาราง A2–A4 เป็นผลจากค่า default ของหน้าเว็บ
> หากตรวจด้วยค่าอื่น ให้ใช้สมการในหัวข้อถัดไปและเทียบกับการคำนวณมือ

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
