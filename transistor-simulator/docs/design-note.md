# Design Note — Transistor DC Bias Simulator (ENG29 2121)

วันที่: 2026-11-10
สถานะ: อนุมัติและดำเนินการแล้ว (UI สุดท้ายปรับตาม mock ที่ผู้ใช้ให้มา)

## 1. บริบทและเป้าหมาย

แล็บสั้นของวิชา ENG29 2121 ต้องการเว็บแอป Flask จริงที่คำนวณ DC operating point
ของ BJT แบบ common-emitter voltage-divider bias เพื่อสาธิตบน localhost และ
commit ขึ้น GitHub ภายในวันนี้

เป้าหมาย:

- รับอินพุต VCC, R1, R2, RC, RE, β, VBE
- แสดงผล IB, IC, IE, VCE, VB, VC, VE พร้อมหน่วย
- ตรวจสอบอินพุตและเตือน region (cutoff / active / saturation)
- มีการตรวจสอบผลกับการคำนวณมือที่เป็นอิสระจากโค้ด
- logic วิศวกรรมแยกจาก Flask อย่างชัดเจน

ไม่ทำ (non-goals):

- AC analysis, transient, frequency response
- circuit editor / schematic capture
- FET, op-amp, multi-transistor
- ฐานข้อมูล, authentication, deployment

anti-goals (ถือว่าล้มเหลวถ้าเกิด):

- สูตรวิศวกรรมฝังอยู่ใน route หรือ template
- แอป crash เมื่ออินพุตผิด
- ตัวเลขใน UI ไม่ตรงกับที่คำนวณมือ
- ต้องติดตั้งอะไรนอกเหนือจาก Flask เพื่อรัน

## 2. ข้อจำกัด

- Python 3.14 (ติดตั้งแล้ว), Flask ยังไม่ติดตั้ง — จะเพิ่มใน `requirements.txt`
- รันด้วย `py` (alias `python` ของเครื่องเสีย)
- ทำงานในโฟลเดอร์ใหม่ `transistor-simulator/` ไม่แตะ DC calculator เดิม
- ต้องรันและ commit ได้วันนี้

## 3. แนวทางที่พิจารณา

| แนวทาง | ลักษณะ | ข้อดี | ข้อเสีย |
|---|---|---|---|
| **A. Validation ด้วย test (เลือก)** | ค่าตัวอย่างคำนวณมือเก็บใน `tests/` และ `docs/validation.md` | เล็กสุด ตรงกับเอกสาร validation | ไม่เห็นการเทียบบนหน้าเว็บ |
| B. วิธีที่สองในแอป | คำนวณซ้ำด้วย KVL/node voltage แล้วโชว์ delta | เดโมน่าเชื่อถือ | เพิ่มโค้ด/ทดสอบซ้ำซ้อน เกินแล็บสั้น |
| C. เทียบกับ ngspice | จำลอง SPICE จริง | อิสระที่สุด | ติดตั้งหนัก เสี่ยงไม่ทันวันนี้ |

เลือก **A** เพราะเป็นความหมายมาตรฐานของ "independent engineering calculation"
ในรายงานแล็บ: ค่าอ้างอิงที่คำนวณมือแยกจาก implementation และตรวจด้วย test
อัตโนมัติ

## 4. การตัดสินใจด้านดีไซน์

### 4.1 โครงสร้างไฟล์

```
transistor-simulator/
├── app.py                  # Flask routes เท่านั้น
├── dc_bias.py              # pure functions, ไม่ import Flask
├── templates/index.html
├── static/style.css
├── tests/test_dc_bias.py
├── tests/test_web.py
├── requirements.txt
├── README.md
├── AGENTS.md
└── docs/{design-note,validation,reflection}.md
```

### 4.2 สมการ (voltage-divider bias)

```
VBB = VCC * R2 / (R1 + R2)
RTH = (R1 * R2) / (R1 + R2)
IB  = (VBB - VBE) / (RTH + (β + 1) * RE)
IC  = β * IB
IE  = (β + 1) * IB
VCE = VCC - IC * RC - IE * RE
VE  = IE * RE
VC  = VCC - IC * RC
VB  = VE + VBE
```

### 4.3 การตัดสิน region

- `VBB <= VBE` → **cutoff**: IB = IC = IE = 0, VCE = VCC, VE = 0, VC = VCC, VB = VBB
- `VCE < VCE_SAT` → **saturation** (เตือนว่าค่าที่ได้มาจาก linear model และของจริงถูก clamp)
- อื่น ๆ → **active**

`VCE_SAT = 0.2 V` เป็นค่าคงที่ใน `dc_bias.py` พร้อม docstring (ไม่เพิ่มช่อง input)

### 4.4 การตรวจสอบอินพุต

ทุกฟิลด์ต้องกรอก เป็นตัวเลข finite และ:

- VCC > 0
- R1 > 0, R2 > 0
- RC ≥ 0, RE ≥ 0
- 1 ≤ β ≤ 10000
- 0 ≤ VBE ≤ 2

ผิด → route ตอบ HTTP 400 พร้อมข้อความภาษาไทยรายฟิลด์ และคงค่าที่กรอกไว้

### 4.5 Routes

- `GET /` → ฟอร์มพร้อมค่าเริ่มต้น (ตัวอย่างใน §5)
- `POST /` → validate → คำนวณ → render ผลลัพธ์; อินพุตผิด → 400 + error
- ไม่มี API/JSON endpoint (เกินขอบเขตแล็บ)

### 4.6 UI (sketch)

```
+--------------------------------------------------------------+
| Transistor DC Bias Simulator — ENG29 2121                    |
| BJT Common-Emitter / Voltage-Divider Bias                    |
+--------------------------------------------------------------+
| อินพุต                        | ผลลัพธ์ (Q-point)            |
|  VCC (V)   [ 12      ]       |  IB  = 12.86 µA              |
|  R1  (Ω)   [ 47000   ]       |  IC  = 1.286 mA              |
|  R2  (Ω)   [ 10000   ]       |  IE  = 1.299 mA              |
|  RC  (Ω)   [ 2200    ]       |  VCE = 7.871 V               |
|  RE  (Ω)   [ 1000    ]       |  VB  = 1.999 V               |
|  β         [ 100     ]       |  VC  = 9.170 V               |
|  VBE (V)   [ 0.7     ]       |  VE  = 1.299 V               |
|  [ คำนวณ ]                   |  สถานะ: Active ✓             |
|                              |  VBB = 2.105 V, RTH = 8.246 kΩ|
+--------------------------------------------------------------+
```

- ภาษาไทย + สัญลักษณ์อังกฤษมาตรฐาน
- responsive: 2 คอลัมน์บนจอใหญ่, เรียงลงบนมือถือ
- แสดง error/warning เป็นกล่องสีชัดเจน

### 4.7 เทคโนโลยีและสไตล์

- Flask + Jinja2, CSS ธรรมดา (ไม่ใช้ framework)
- `unittest` (stdlib) ตามสไตล์เดิมของ repo — รันด้วย `py -m unittest discover -s tests`
- type hints + docstring สั้น ๆ ใน `dc_bias.py`
- `AGENTS.md` ระบุ: logic แยกจาก Flask, ห้าม hardcode ผลลัพธ์ใน template, test ก่อนแก้

## 5. ตัวอย่างตรวจสอบ (independent hand calculation)

VCC = 12 V, R1 = 47 kΩ, R2 = 10 kΩ, RC = 2.2 kΩ, RE = 1 kΩ, β = 100, VBE = 0.7 V

```
VBB = 12 * 10 / 57            = 2.1053 V
RTH = 47k || 10k              = 8.2456 kΩ
IB  = (2.1053 - 0.7) / (8245.6 + 101*1000)
    = 1.4053 / 109245.6       = 12.864 µA
IC  = 100 * 12.864 µA         = 1.2864 mA
IE  = 101 * 12.864 µA         = 1.2993 mA
VCE = 12 - 1.2864m*2200 - 1.2993m*1000
    = 12 - 2.830 - 1.299      = 7.871 V   → Active
VE  = 1.299 V,  VC = 9.170 V,  VB = 1.999 V
```

ค่านี้จะถูก assert ใน `tests/test_dc_bias.py` และอธิบายทีละขั้นใน `docs/validation.md`

## 6. สิ่งที่เหลือให้ผู้สร้างตัดสิน

- จำนวนตำแหน่งทศนิยม/รูปแบบหน่วย (เลือก: 3-4 significant digits + auto unit)
- โทนสีและรายละเอียด CSS
- เนื้อหา `docs/reflection.md` (สรุปสิ่งที่เรียนรู้จากงานนี้)

## 7. เกณฑ์ตรวจรับ

1. `py -m unittest discover -s tests` ผ่านทั้งหมด
2. `py app.py` เปิด http://127.0.0.1:5000 ได้
3. กรอกค่าตัวอย่าง §5 แล้วได้ผลตรงกับที่คำนวณมือ
4. อินพุตผิด (เช่น R1 = 0, β = -5, ตัวอักษร) แสดง error ภาษาไทยและไม่ crash
5. เคส cutoff และ saturation แสดง warning ถูกต้อง
6. README มีขั้นตอนติดตั้ง/รันที่ทำตามได้จริง
7. commit ขึ้น `main` และ push ไป GitHub สำเร็จ
