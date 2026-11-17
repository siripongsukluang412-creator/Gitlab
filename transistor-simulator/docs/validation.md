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
