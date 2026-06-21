# คู่มือการใช้งานระบบ (Walkthrough) - Google Drive ➔ Supabase ETL & Web App

โครงสร้างระบบแบบประหยัดและฟรี 100% ได้รับการจัดทำเรียบร้อยแล้วที่โฟลเดอร์โครงการ:
📂 [/Users/anusorn/.gemini/antigravity/scratch/onedrive-supabase-etl-app](file:///Users/anusorn/.gemini/antigravity/scratch/onedrive-supabase-etl-app)

ระบบนี้พัฒนาขึ้นเพื่อนำข้อมูลจาก **2 แหล่ง (2 Google Drive Folders)** มารวมกัน (Merge/JOIN) เพื่อให้ระบบรายงานสามารถแสดงชื่อพนักงาน, ตำแหน่ง, และหน่วยงานเพิ่มเติมจากข้อมูลเวลาทำงานปกติ ดังนี้ครับ:
1. **Folder 1 (Payroll FTE Normal):** โฟลเดอร์เวลาปฏิบัติงานพนักงาน (ไฟล์ CSV รายเดือน)
2. **Folder 2 (Employee Master):** โฟลเดอร์ประวัติพนักงานหลัก (ไฟล์ `Employee Master.xlsx`)

---

## 📂 1. โครงสร้างโฟลเดอร์ของโครงการ

* 📁 [database/](file:///Users/anusorn/.gemini/antigravity/scratch/onedrive-supabase-etl-app/database/)
  * [schema.sql](file:///Users/anusorn/.gemini/antigravity/scratch/onedrive-supabase-etl-app/database/schema.sql) — สคริปต์ SQL สำหรับสร้างตาราง `payroll_report`, `employee_master`, ดัชนีความเร็ว และ SQL View `payroll_details_view` สำหรับทำ JOIN ข้อมูลแบบ Real-time
* 📁 [etl/](file:///Users/anusorn/.gemini/antigravity/scratch/onedrive-supabase-etl-app/etl/)
  * [etl_pipeline.py](file:///Users/anusorn/.gemini/antigravity/scratch/onedrive-supabase-etl-app/etl/etl_pipeline.py) — สคริปต์หลัก Python ทำการสแกน 2 โฟลเดอร์ Google Drive แบบไร้ไฟล์ข้ำซ้อน คัดกรองวันทำงานเฉพาะปีปัจจุบัน และอัปโหลดขึ้น Supabase ด้วยการทำ UPSERT
* 📁 [web/](file:///Users/anusorn/.gemini/antigravity/scratch/onedrive-supabase-etl-app/web/)
  * [index.html](file:///Users/anusorn/.gemini/antigravity/scratch/onedrive-supabase-etl-app/web/index.html) — หน้าจอแสดงผล Dashboard ดีไซน์พรีเมียม
  * [style.css](file:///Users/anusorn/.gemini/antigravity/scratch/onedrive-supabase-etl-app/web/style.css) — ตกแต่งสไตล์ Dark Mode / Glassmorphism
  * [app.js](file:///Users/anusorn/.gemini/antigravity/scratch/onedrive-supabase-etl-app/web/app.js) — ลอจิกคิวรีข้อมูล Supabase ผ่าน PostgREST API บน View การ JOIN ข้อมูล, ระบบค้นหาตามชื่อ/ตำแหน่ง และระบบแบ่งหน้า (Pagination)
* 📁 [.github/workflows/](file:///Users/anusorn/.gemini/antigravity/scratch/onedrive-supabase-etl-app/.github/workflows/)
  * [daily_etl.yml](file:///Users/anusorn/.gemini/antigravity/scratch/onedrive-supabase-etl-app/.github/workflows/daily_etl.yml) — การตั้งเวลา Scheduling รันวันละ 1 ครั้งเวลา 07:00 น. ผ่าน GitHub Actions แบบฟรี
* 📄 [run_etl.sh](file:///Users/anusorn/.gemini/antigravity/scratch/onedrive-supabase-etl-app/run_etl.sh) — สคริปต์ shell สำหรับใช้ทดสอบรัน ETL บนเครื่อง Macbook ในเครื่องโลคอล

---

## ⚙️ 2. ขั้นตอนการตั้งค่าเพื่อใช้งานจริง

### ขั้นตอนที่ 1: ตั้งค่าฐานข้อมูล Supabase
1. เข้าสู่หน้าต่างโครงการของคุณบน **Supabase Dashboard**
2. ไปที่เมนู **SQL Editor** ทางด้านซ้ายมือ
3. กดสร้าง Query ใหม่ (New Query) คัดลอกเนื้อหาโค้ดในไฟล์ [schema.sql](file:///Users/anusorn/.gemini/antigravity/scratch/onedrive-supabase-etl-app/database/schema.sql) ไปวางแล้วกด **Run**
4. ระบบจะทำการเตรียมตาราง `employee_master`, `payroll_report` และ SQL View `payroll_details_view` ไว้ให้โดยอัตโนมัติ

### ขั้นตอนที่ 2: เตรียมลิงก์แชร์โฟลเดอร์ Google Drive
ในสคริปต์ได้ทำการกำหนดค่าตั้งต้น (Default URLs) สำหรับโฟลเดอร์ทดสอบของคุณไว้เรียบร้อยแล้ว:
* **GDRIVE_SHARE_LINK** (โฟลเดอร์ Payroll): `https://drive.google.com/drive/folders/1jt-MYYEJXq1n0UVfdf96GJigezuWcAH4?usp=sharing`
* **EMP_MASTER_SHARE_LINK** (โฟลเดอร์ Master): `https://drive.google.com/drive/folders/1IZA_tR5K1j4B2IPq3OP-wL5YePeImOv6?usp=sharing`

> [!TIP]
> หากต้องการใช้โฟลเดอร์อื่น ให้ตั้งสิทธิ์แชร์โฟลเดอร์เป็น **"ทุกคนที่มีลิงก์สามารถดูได้" (Anyone with the link can view)** แล้วนำลิงก์นั้นไปตั้งใน Secrets (สำหรับ GitHub) หรือ Environment Variables (สำหรับ Mac)

---

## 🧪 3. การทดสอบการทำงานของระบบ (Local Testing)

### การทดสอบสคริปต์ ETL (Python)
คุณสามารถสั่งรันจำลองระบบสแกนข้อมูลและดาวน์โหลดจาก Google Drive เพื่อดูผลการทำงานได้ทันที:

1. เปิด Terminal และตรวจสอบการเชื่อมต่ออินเทอร์เน็ต:
   ```bash
   python3 etl/etl_pipeline.py
   ```
   *(เนื่องจากยังไม่ได้ระบุคีย์จริง Supabase ระบบจะรันในโหมด **Dry-Run** โดยจะทำการดาวน์โหลดไฟล์ Excel และ CSV จากทั่งสองโฟลเดอร์จำลองการล้างทำความสะอาดข้อมูล และล้างไฟล์ชั่วคราวออกให้อย่างสะอาดเรียบร้อย)*

2. หากพร้อมรันขึ้นฐานข้อมูลจริง ให้กรอกคีย์ลงในไฟล์ [run_etl.sh](file:///Users/anusorn/.gemini/antigravity/scratch/onedrive-supabase-etl-app/run_etl.sh) แล้วรัน:
   ```bash
   chmod +x run_etl.sh
   ./run_etl.sh
   ```

### การรันเว็บแอปพลิเคชัน (Web Dashboard)
คุณสามารถเปิดดูผลลัพธ์ผ่านหน้าจอ Dashboard โดยรันเว็บเซิร์ฟเวอร์จำลอง:

1. เข้าไปยังโฟลเดอร์โครงการและรันเซิร์ฟเวอร์:
   ```bash
   python3 -m http.server 8000 --directory web
   ```
2. เปิดเบราว์เซอร์เข้าสู่ลิงก์: [http://localhost:8000](http://localhost:8000)
3. **ระบบจำลอง (Mock Mode):** หน้าเว็บจะจำลองการแสดงข้อมูลของพนักงานพร้อมชื่อ, ตำแหน่ง, และหน่วยงานแบบสมบูรณ์ สามารถทดสอบพิมพ์ค้นหา (เช่น พิมพ์ชื่อ "สิริกร") ค้นหาตามตำแหน่งงาน หรือจัดเรียงแบ่งหน้าได้ทันทีเพื่อทดสอบหน้าตาการแสดงผล
4. **เชื่อมต่อฐานข้อมูลจริง:** ให้คลิกแท็บ **Credentials** ใส่ลิงก์โครงการและคีย์ anon ของคุณ หน้าเว็บจะเชื่อมโยงดึงข้อมูลที่ Merge เสร็จแล้วจาก SQL View บน Supabase มาแสดงผลแบบสดๆ (Real-time)!

---

## ⏰ 4. การตั้งเวลาทำงานอัตโนมัติ (Scheduling)

### ทางเลือก A: รันฟรีผ่านคลาวด์ 100% (GitHub Actions)
เมื่อคุณนำโค้ดไป Push ลงบน GitHub Repository ส่วนตัว (Private Repository):
1. ไปที่แท็บ **Settings > Secrets and variables > Actions** ใน Repository ของคุณ
2. เพิ่ม **Repository Secrets** ดังนี้:
   * `SUPABASE_URL` : URL โครงการ Supabase
   * `SUPABASE_SERVICE_ROLE_KEY` : คีย์เขียนข้อมูล (service_role)
   * `GDRIVE_SHARE_LINK` : ลิงก์โฟลเดอร์เวลาทำงาน (โฟลเดอร์ 1)
   * `EMP_MASTER_SHARE_LINK` : ลิงก์โฟลเดอร์ประวัติพนักงาน (โฟลเดอร์ 2)
3. ระบบจะสแตนด์บายเพื่อดาวน์โหลดไฟล์ ล้างข้อมูล และประมวลผล JOIN ขึ้นระบบในเวลา **07:00 น. ของทุกวัน** โดยไม่มีค่าใช้จ่าย!

### ทางเลือก B: รันอัตโนมัติบน Macbook (macOS Cron Job)
หากต้องการรันสคริปต์ภายในเครื่อง Macbook ของคุณผ่านไฟล์จริงหรือไฟล์ที่ซิงค์ลงใน Finder:
1. เปิด Terminal ในเครื่องและเข้าสู่คำสั่งแก้ไข:
   ```bash
   crontab -e
   ```
2. พิมพ์ตั้งเวลา เช่น รันทุกเช้าเวลา **08:30 น.** (กดปุ่ม `i` บนคีย์บอร์ดเพื่อเข้าสู่โหมดพิมพ์ คัดลอกข้อความด้านล่างไปวาง แล้วกด `Esc` ตามด้วยพิมพ์ `:wq` เพื่อบันทึก):
   ```text
   30 8 * * * /bin/zsh /Users/anusorn/.gemini/antigravity/scratch/onedrive-supabase-etl-app/run_etl.sh >> /Users/anusorn/.gemini/antigravity/scratch/onedrive-supabase-etl-app/etl.log 2>&1
   ```
