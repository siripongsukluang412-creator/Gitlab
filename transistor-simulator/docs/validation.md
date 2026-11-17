# Validation — independent engineering calculation

เอกสารนี้อธิบายการคำนวณมือที่ใช้เป็นค่าอ้างอิงอิสระจากโค้ด
(test ใน `tests/test_dc_bias.py` assert ค่าเหล่านี้)

## 1. ตัวอย่างอ้างอิงหลัก (textbook example)

ค่าที่ใช้:

```
VCC = 12 V    R1 = 47 kΩ    R2 = 10 kΩ
RC  = 2.2 kΩ  RE = 1 kΩ     β = 100    VBE = 0.7 V
```

### ขั้นที่ 1 — Thevenin equivalent ของตัวแบ่งแรงดัน

```
VBB = VCC * R2 / (R1 + R2)
    = 12 * 10,000 / (47,000 + 10,000)
    = 120,000 / 57,000
    = 2.105263 V

RTH = R1 * R2 / (R1 + R2)
    = 47,000 * 10,000 / 57,000
    = 8,245.614 Ω
```

### ขั้นที่ 2 — กระแสเบส

```
IB = (VBB - VBE) / (RTH + (β + 1) * RE)
   = (2.105263 - 0.7) / (8,245.614 + 101 * 1,000)
   = 1.405263 / 109,245.614
   = 12.8633 µA
```

### ขั้นที่ 3 — กระแส collector และ emitter

```
IC = β * IB       = 100 * 12.8633 µA = 1.28633 mA
IE = (β + 1) * IB = 101 * 12.8633 µA = 1.29920 mA
```

### ขั้นที่ 4 — แรงดันที่ขาต่าง ๆ

```
VCE = VCC - IC*RC - IE*RE
    = 12 - 1.28633m*2,200 - 1.29920m*1,000
    = 12 - 2.82993 - 1.29920
    = 7.87087 V

VE = IE * RE      = 1.29920 V
VC = VCC - IC*RC  = 12 - 2.82993 = 9.17007 V
VB = VE + VBE     = 1.29920 + 0.7 = 1.99920 V
```

### ผลลัพธ์

| ปริมาณ | ค่า |
|---|---|
| VBB | 2.1053 V |
| RTH | 8,245.6 Ω |
| IB | 12.863 µA |
| IC | 1.2863 mA |
| IE | 1.2992 mA |
| VCE | 7.8709 V |
| VB | 1.9992 V |
| VC | 9.1701 V |
| VE | 1.2992 V |
| Region | **active** (VCE = 7.87 V > 0.2 V) |

ค่าเหล่านี้ถูก assert ใน
`tests/test_dc_bias.py::TestKnownExample::test_textbook_example_values`

## 2. ตัวอย่างค่าเริ่มต้นของแอป

```
VCC = 12 V   R1 = 100 kΩ  R2 = 22 kΩ
RC  = 2.2 kΩ RE = 1 kΩ    β = 100   VBE = 0.7 V
```

| ปริมาณ | ค่า (exact Thevenin) |
|---|---|
| VBB | 2.1639 V |
| RTH | 18,032.8 Ω |
| IB | 12.299 µA |
| IC | 1.2299 mA |
| IE | 1.2422 mA |
| VCE | 8.0522 V |
| VB | 1.9422 V |
| VC | 9.2943 V |
| VE | 1.2422 V |
| Region | active |

## 3. เปรียบเทียบกับวิธีประมาณ (IB ≈ 0)

ตำราหลายฉบับใช้วิธีประมาณโดยไม่คิดกระแสเบส:

```
VB  = VCC * R2 / (R1 + R2)
VE  = VB - VBE
IE  = VE / RE
IC  ≈ IE
```

สำหรับตัวอย่างในข้อ 2 วิธีประมาณให้:

| ปริมาณ | Exact (แอป) | Approximate |
|---|---|---|
| VB | 1.9422 V | 2.1639 V |
| VE | 1.2422 V | 1.4639 V |
| IC | 1.2299 mA | 1.4494 mA |
| VCE | 8.0522 V | 7.3473 V |

แอปเลือกใช้ **exact Thevenin** เพราะไม่ต้องสมมติว่า IB ≈ 0
และให้ผลที่ถูกต้องกว่าเมื่อ `RTH` ไม่ได้เล็กกว่า `(β+1)·RE` มากนัก
(ในตัวอย่างนี้ `(β+1)·RE = 101 kΩ` เทียบกับ `RTH = 18 kΩ`)

## 4. การตรวจสอบขอบเขต

| กรณี | เงื่อนไข | ผลที่คาด |
|---|---|---|
| Cutoff | VBB ≤ VBE | IB = IC = IE = 0, VCE = VCC |
| Saturation | VCE < 0.2 V | เตือนว่าค่ามาจาก linear model |
| Active | 0.2 V ≤ VCE | ไม่มี warning |

ทดสอบใน `tests/test_dc_bias.py::TestRegions`

## 5. โหมด Fixed Bias

สมการ:

```text
IB  = (VCC - VBE) / RB
IC  = β * IB
IE  = (β + 1) * IB
VCE = VCC - IC * RC
VE  = 0
VC  = VCE
VB  = VBE
```

ตัวอย่าง: `VCC = 12 V, RB = 470 kΩ, RC = 2.2 kΩ, β = 100, VBE = 0.7 V`

| ปริมาณ | ค่า |
|---|---|
| IB | 24.0426 µA |
| IC | 2.40426 mA |
| IE | 2.42830 mA |
| VCE | 6.7106 V |
| VB | 0.7 V |
| VC | 6.7106 V |
| VE | 0 V |
| Region | active |

## 6. โหมด Emitter Bias (แหล่งจ่ายเดียว)

สมการ:

```text
IB  = (VCC - VBE) / (RB + (β + 1) * RE)
IC  = β * IB
IE  = (β + 1) * IB
VCE = VCC - IC * RC - IE * RE
VE  = IE * RE
VC  = VCC - IC * RC
VB  = VE + VBE
```

ตัวอย่าง: `VCC = 12 V, RB = 470 kΩ, RC = 2.2 kΩ, RE = 1 kΩ, β = 100, VBE = 0.7 V`

| ปริมาณ | ค่า |
|---|---|
| IB | 19.7898 µA |
| IC | 1.97898 mA |
| IE | 1.99877 mA |
| VCE | 5.6475 V |
| VB | 2.6988 V |
| VC | 7.6462 V |
| VE | 1.9988 V |
| Region | active |

ทั้งสองโหมดใช้ `VCC <= VBE` เป็น cutoff และ `VCE < 0.2 V` เป็น saturation
เหมือนกับโหมด divider

## 7. การตรวจสอบชั้น HTTP

`tests/test_web.py` ตรวจ:

- GET `/` แสดงฟอร์มและผลลัพธ์ว่าง
- POST ค่าถูกต้อง → 200 และแสดงค่าที่ตรงกับข้อ 1
- การแปลงหน่วย kΩ ↔ Ω และ V ↔ mV ให้ผลเดียวกัน
- อินพุตผิด → 400 พร้อมข้อความ
- cutoff / saturation แสดงสถานะถูกต้อง

## 8. ข้อจำกัดของการตรวจสอบ

- ค่าอ้างอิงมาจากการคำนวณมือด้วยสมการเดียวกัน ไม่ได้เทียบกับ SPICE
- `VCE_SAT = 0.2 V` เป็นค่าคงที่ typical ไม่ได้มาจาก datasheet
- โมเดลเป็น linear DC bias ไม่รวม effects ของอุณหภูมิหรือ early effect

## 9. ผลตรวจรับ A1–A5 (OpenCode Browser)

### 9.1 เงื่อนไขการตรวจ

| รายการ | ค่า |
|---|---|
| URL | <http://127.0.0.1:5000> |
| วิธีตรวจ | OpenCode Browser (browser_navigate, browser_snapshot, browser_fill_form, browser_click, browser_network_list) |
| ค่าที่ใช้ร่วมกัน | `VCC = 12 V`, `RC = 2.2 kΩ`, `β = 100`, `VBE = 0.70 V` |
| หน่วยบนฟอร์ม | แรงดัน `V`, ความต้านทาน `kΩ` (RB = 1000 kΩ = 1 MΩ) |
| ความละเอียดที่แสดง | แรงดัน 2 ตำแหน่งทศนิยม (V), กระแส 2 ตำแหน่ง (mA) หรือ 1 ตำแหน่ง (µA) |
| เกณฑ์ผ่าน | `abs(IC − IC_ref) ≤ 0.01 mA` และ `abs(VCE − VCE_ref) ≤ 0.02 V` เทียบค่าอ้างอิงที่ยังไม่ปัดเศษ |

ค่าอ้างอิงในตารางคำนวณมือจากสมการในหัวข้อ 5–6 ก่อนเปิดหน้าเว็บ
ไม่ได้อ่านจาก `dc_bias.py` หรือจากผลของโปรแกรม

### 9.2 ตารางผลตรวจ

| กรณี | เลือกโหมดและกรอกค่า | คาดหมายก่อนรัน | เห็นจริง | วิธีตรวจ | สถานะ |
|---|---|---|---|---|---|
| A1 · โหมดเดิม | Divider · R1 = 100 kΩ, R2 = 22 kΩ, RE = 1 kΩ, RC = 2.2 kΩ | ผลตรงกับ Lab 2 เดิม: IC = 1.2299 mA, VCE = 8.0522 V | IC = 1.23 mA, VCE = 8.05 V (VB 1.94 V, VE 1.24 V, VC 9.29 V, IB 12.3 µA, IE 1.24 mA) | OpenCode Browser | PASS |
| A2 · Fixed | Fixed · RB = 1 MΩ (1000 kΩ), ไม่กรอก RE | IB = 11.30 µA → IC = 1.1300 mA, VCE = 9.5140 V | IC = 1.13 mA, VCE = 9.51 V (VB 0.70 V, VE 0.00 V, VC 9.51 V, IB 11.3 µA, IE 1.14 mA) | OpenCode Browser | PASS |
| A3 · Emitter | Emitter · RB = 1 MΩ, RE = 1 kΩ | IC = 1.02634 mA, VCE = 8.70545 V | IC = 1.03 mA, VCE = 8.71 V (VB 1.74 V, VE 1.04 V, VC 9.74 V, IB 10.3 µA, IE 1.04 mA) | OpenCode Browser | PASS |
| A4 · เปลี่ยนค่าเดียว | Emitter · เหมือน A3 แต่ RE = 2 kΩ | ทำนาย: IC **ลด** จาก A3 เพราะตัวส่วน `RB + (β+1)·RE` ใหญ่ขึ้น และ VCE **ลด** เพราะ `VE = IE·RE` เพิ่มมากกว่าที่ `IC·RC` ลด; ค่าอ้างอิง IC = 0.94010 mA, VCE = 8.03278 V | IC = 940.1 µA (= 0.9401 mA), VCE = 8.03 V (VB 2.60 V, VE 1.90 V, VC 9.93 V, IB 9.4 µA, IE 949.5 µA) | OpenCode Browser | PASS |
| A5 · อินพุตผิด | Fixed · RB = 0 | Flask ตรวจและตอบ HTTP 400 พร้อมข้อความ `R_B must be greater than 0 Ω.` และไม่แสดงผลของรอบก่อน | HTTP 400 (POST `/`) · ข้อความจาก Flask: `R_B must be greater than 0 Ω.` · ฝั่งผลลัพธ์ว่าง (`Enter the parameters and press Calculate DC Bias ...`) ไม่มีตัวเลขค้างจากรอบก่อน | OpenCode Browser | PASS |

### 9.3 ค่าอ้างอิงที่ใช้เทียบ (คำนวณมือ ยังไม่ปัดเศษ)

```text
A1 Divider (R1 = 100 kΩ, R2 = 22 kΩ, RC = 2.2 kΩ, RE = 1 kΩ)
  VBB = 12 * 22 / 122            = 2.163934 V
  RTH = 100k * 22k / 122k        = 18,032.79 Ω
  IB  = (2.163934 - 0.70) / (18,032.79 + 101 * 1,000) = 12.2987 µA
  IC  = 100 * 12.2987 µA         = 1.22987 mA
  IE  = 101 * 12.2987 µA         = 1.24216 mA
  VCE = 12 - 1.22987m*2,200 - 1.24216m*1,000 = 8.0521 V

A2 Fixed (RB = 1 MΩ)
  IB  = (12 - 0.70) / 1,000,000  = 11.3000 µA
  IC  = 1.13000 mA
  VCE = 12 - 1.13000m * 2,200    = 9.5140 V

A3 Emitter (RB = 1 MΩ, RE = 1 kΩ)
  IB  = 11.3 / (1,000,000 + 101 * 1,000) = 10.26340 µA
  IC  = 1.026340 mA
  IE  = 1.036603 mA
  VCE = 12 - 1.026340m*2,200 - 1.036603m*1,000 = 8.70545 V

A4 Emitter (RB = 1 MΩ, RE = 2 kΩ)
  IB  = 11.3 / (1,000,000 + 101 * 2,000) = 9.40100 µA
  IC  = 0.940100 mA
  IE  = 0.949501 mA
  VCE = 12 - 0.940100m*2,200 - 0.949501m*2,000 = 8.03278 V
```

### 9.4 ผลต่างเทียบเกณฑ์

| กรณี | IC ที่เห็น | IC อ้างอิง | ผลต่าง IC | VCE ที่เห็น | VCE อ้างอิง | ผลต่าง VCE | เกณฑ์ |
|---|---|---|---|---|---|---|---|
| A1 | 1.23 mA | 1.2299 mA | 0.0001 mA | 8.05 V | 8.0522 V | 0.0022 V | ผ่าน |
| A2 | 1.13 mA | 1.1300 mA | 0.0000 mA | 9.51 V | 9.5140 V | 0.0040 V | ผ่าน |
| A3 | 1.03 mA | 1.02634 mA | 0.0037 mA | 8.71 V | 8.70545 V | 0.0046 V | ผ่าน |
| A4 | 940.1 µA (0.9401 mA) | 0.94010 mA | 0.0000 mA | 8.03 V | 8.03278 V | 0.0028 V | ผ่าน |

### 9.5 หลักฐาน

ข้อความจากหน้าเว็บ (A5, ตอบกลับจาก Flask ด้วย HTTP 400):

```text
R_B must be greater than 0 Ω.
```

Screenshots:

- A1 Divider — `docs/screenshots/A1-divider.png`
- A4 Emitter (RE = 2 kΩ) — `docs/screenshots/A4-emitter-re2k.png`
- A5 Fixed (RB = 0) — `docs/screenshots/A5-fixed-rb0-error.png`

> หมายเหตุ: ไม่มีการแก้ไขโค้ดในรอบตรวจนี้ จึงไม่มีผลก่อน–หลังให้บันทึก
> และไม่ได้เพิ่ม unittest ใหม่ (tests เดิมยังใช้ตรวจสอบซ้ำหลังแก้ README/เอกสาร)
