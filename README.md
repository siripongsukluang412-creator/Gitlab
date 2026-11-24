# Gitlab
ใช้สำหรับเรียนคอมโปรไฟฟ้า

## DC Circuit Calculator (โปรแกรมคำนวณวงจรไฟฟ้ากระแสตรง)

คำอธิบาย: แอปพลิเคชันหรือเว็บเครื่องมือสำหรับช่วยคำนวณค่าทางไฟฟ้าพื้นฐานในวงจรไฟฟ้ากระแสตรงได้อย่างรวดเร็ว โดยอ้างอิงจากกฎของโอห์มและกฎของเคอร์ชอฟฟ์

วัตถุประสงค์: เพื่อคำนวณหากระแสไฟฟ้า แรงดัน และกำลังไฟฟ้าของวงจรตัวต้านทานได้อย่างแม่นยำ ช่วยลดเวลาและข้อผิดพลาดในการคำนวณด้วยมือ

## โปรเจกต์ใน repo นี้

### `transistor-simulator/` — Lab 02–04: BJT Common-Emitter Simulator

เว็บแอป Flask สำหรับคำนวณ DC operating point ของ BJT แบบ common-emitter
รองรับ 3 โหมด (Divider / Fixed / Emitter) และจำลองจริงด้วย ngspice สำหรับ
วงจร voltage-divider (`.op`, `.ac`, `.tran`) พร้อมกราฟ Bode และ transient
ที่โต้ตอบได้ (hover/touch tooltip, scrub timeline, Play/Pause)

```powershell
cd transistor-simulator
py -m pip install -r requirements.txt
py app.py
```

เปิด <http://127.0.0.1:5000> · รันเทสต์ `py -m unittest discover -s tests -t . -v`

รายละเอียดเพิ่มเติม: [transistor-simulator/README.md](transistor-simulator/README.md)

## ตารางตรวจรับ A1–A5 (Lab 03 · DC Bias)

ค่าที่ใช้ร่วมกันทุกกรณี: `VCC = 12 V`, `RC = 2.2 kΩ`, `β = 100`, `VBE = 0.70 V`
ตรวจผ่านเว็บที่ <http://127.0.0.1:5000> โดยเทียบกับค่าอ้างอิงที่คำนวณมือ
(ดูรายละเอียดและหลักฐานได้ใน [docs/validation.md](transistor-simulator/docs/validation.md))

| กรณี | เลือกโหมดและกรอกค่า | IC อ้างอิง | VCE อ้างอิง | เห็นจริง | สถานะ |
|---|---|---|---|---|---|
| A1 · โหมดเดิม | Divider · R1 = 100 kΩ, R2 = 22 kΩ, RE = 1 kΩ | 1.2299 mA | 8.0522 V | IC 1.23 mA · VCE 8.05 V | PASS |
| A2 · Fixed | Fixed · RB = 1 MΩ | 1.1300 mA | 9.5140 V | IC 1.13 mA · VCE 9.51 V | PASS |
| A3 · Emitter | Emitter · RB = 1 MΩ, RE = 1 kΩ | 1.02634 mA | 8.70545 V | IC 1.03 mA · VCE 8.71 V | PASS |
| A4 · เปลี่ยนค่าเดียว | Emitter · เหมือน A3 แต่ RE = 2 kΩ | 0.94010 mA | 8.03278 V | IC 940.1 µA · VCE 8.03 V | PASS |
| A5 · อินพุตผิด | Fixed · RB = 0 | — | — | HTTP 400 · `R_B must be greater than 0 Ω.` | PASS |

เกณฑ์ผ่าน: `|IC − IC_ref| ≤ 0.01 mA` และ `|VCE − VCE_ref| ≤ 0.02 V`
เทียบค่าอ้างอิงที่ยังไม่ปัดเศษ (หน้าเว็บแสดงแรงดัน 2 ตำแหน่งทศนิยม
และกระแส 2 ตำแหน่ง หรือ 1 ตำแหน่งสำหรับ µA)

## ตารางตรวจรับ B1–B8 (Lab 04 · Browser Acceptance)

ตรวจจริงด้วย **OpenCode Browser** ที่ <http://127.0.0.1:5000> ทุกกรณี
ค่าที่ใช้ร่วมกัน: `VCC = 12 V`, `RC = 2.2 kΩ`, `β = 100`, `VBE = 0.70 V`
และสำหรับ SPICE: `Vin = 10 mV` @ `1 kHz` (Divider Bias)

| กรณี | สิ่งที่ตรวจ | วิธีทำใน Browser | ผลที่เห็นจริง | สถานะ |
|---|---|---|---|---|
| B1 | หน้าเว็บโหลดได้ | `GET /` | HTTP 200 · title `Lab 04: BJT Bias & Amplifier Simulator — ENG29 2121` · มี 3 bias tab + 4 analysis tab + ฟอร์ม · ยังไม่มีผลลัพธ์ | PASS |
| B2 | Analytical DC · Divider | กด **Calculate DC Bias** ค่า default | HTTP 200 · badge `Analytical model` · IC 1.23 mA · VCE 8.05 V · VB 1.94 V · VE 1.24 V · VC 9.29 V · IB 12.3 µA · IE 1.24 mA | PASS |
| B3 | Analytical DC · Fixed | เลือก **Fixed Bias** · `RB = 1000 kΩ` · กด Calculate | HTTP 200 · IC 1.13 mA · VCE 9.51 V · VB 0.70 V · VE 0.00 V · IB 11.3 µA · IE 1.14 mA | PASS |
| B4 | Analytical DC · Emitter | เลือก **Emitter Bias** · `RB = 1000 kΩ`, `RE = 1 kΩ` · กด Calculate | HTTP 200 · IC 1.03 mA · VCE 8.71 V · VB 1.74 V · VE 1.04 V · IB 10.3 µA · IE 1.04 mA | PASS |
| B5 | SPICE DC `.op` | เลือก **SPICE DC (.op)** · กด **Run SPICE Simulation** | HTTP 200 · badge `SPICE simulation` แยกจาก analytical · Engine `ngspice-41` · wall 24–33 ms · VB 1.95 V · VE 1.29 V · VC 9.19 V · VCE 7.90 V · IC 1.28 mA · มี Netlist / ngspice log | PASS |
| B6 | SPICE AC `.ac` + กราฟ Bode | เลือก **SPICE AC (.ac)** · กด Run | HTTP 200 · midband gain 4.86 dB @ 7.36 kHz · fL 1.85 Hz · fH 85.77 MHz · กราฟสี `#facc15`/`#38bdf8` · hover ได้ค่าจริง `f=79.43 Hz  gain=4.86 dB  phase=-178.3°` · marker 2 ตัว + guide · scrub 242.07 → 376.88 · Play → Pause | PASS |
| B7 | SPICE Transient `.tran` + กราฟ | เลือก **SPICE Transient (.tran)** · กด Run | HTTP 200 · Engine `ngspice-41` · Vin(pp) 20.0 mV · Vout(pp) 35.0 mV · gain 1.75× · inverted 180° · hover ได้ `t=0.2248 ms  Vin=9.87 mV  Vout=-17.27 mV` · marker 2 ตัว · scrub ขยับได้ | PASS |
| B8 | ตรวจรับอินพุตผิด | SPICE Transient · ตั้ง `Vin amplitude = 0` · กด Run | HTTP 400 · error `V_in amplitude must be greater than 0 V.` · ไม่มีผล SPICE/กราฟ · ค่าที่กรอกยังอยู่ในฟอร์ม | PASS |

หมายเหตุจากรอบตรวจ B6–B7: พบว่าสคริปต์ JS ที่ฝังไว้ใน `<svg>` ถูก HTML parser ตัด `<`
ในตัวเปรียบเทียบทิ้ง ทำให้ tooltip/scrub/Play ไม่ทำงาน จึงย้ายไปไว้ที่
`static/chart-interactive.js` และแก้พิกัด marker ของกราฟ Bode ให้ตรงกับแกน gain/phase
แล้วตรวจซ้ำจนผ่านทั้ง B6 และ B7 (console ไม่มี error)

ชุดทดสอบหลังแก้: `py -m unittest discover -s tests -t .` → `Ran 53 tests`, `OK` (exit code 0)
