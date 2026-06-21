-- ==========================================
-- SQL Schema Setup for Supabase Database
-- โครงสร้างตารางและดัชนีสำหรับข้อมูลเงินเดือนและข้อมูลพนักงาน
-- ==========================================

-- 1. สร้างตารางข้อมูลพนักงานหลัก (employee_master)
CREATE TABLE IF NOT EXISTS employee_master (
    employee_id VARCHAR(50) PRIMARY KEY,      -- รหัสพนักงาน
    first_name VARCHAR(100),                  -- ชื่อ
    last_name VARCHAR(100),                   -- นามสกุล
    organization_name VARCHAR(255),           -- ชื่อหน่วยงาน (Organization name)
    position_name VARCHAR(255),               -- ชื่อตำแหน่ง (Position Name)
    job_name VARCHAR(255),                    -- ชื่อลักษณะงาน (Job Name)
    cost_center VARCHAR(50),                  -- รหัสศูนย์ต้นทุน (Cost Center)
    level_name VARCHAR(100),                  -- ระดับพนักงาน (Level)
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 2. สร้างตารางรายงานเงินเดือน/การทำงาน (payroll_report)
CREATE TABLE IF NOT EXISTS payroll_report (
    record_id VARCHAR(150) PRIMARY KEY,       -- ไอดีอ้างอิงหลัก สำหรับเช็คข้อมูลซ้ำ (ใช้ทำ UPSERT)
    employee_id VARCHAR(50) NOT NULL,         -- รหัสพนักงาน (Employee ID)
    pay_code VARCHAR(50),                     -- รหัสการจ่าย (Pay Code)
    pay_code_description VARCHAR(255),        -- รายละเอียดรหัสการจ่าย (Pay Code Description)
    earning_code VARCHAR(50),                 -- รหัสรายได้ (Earning Code)
    hours_py DECIMAL(10, 2),                  -- ชั่วโมงสะสม (Hours (py))
    hours DECIMAL(10, 2),                     -- ชั่วโมงทำงาน (Hours)
    minutes INTEGER,                          -- นาที (Minutes)
    planned_hour DECIMAL(10, 2),              -- ชั่วโมงที่วางแผน (Planned hour)
    planned_hours INTEGER,                    -- ชั่วโมงที่วางแผนจำนวนเต็ม (Planned hours)
    planned_minutes INTEGER,                  -- นาทีที่วางแผน (Planned minutes)
    count_val INTEGER,                        -- จำนวนนับ (Count)
    days_val INTEGER,                         -- จำนวนวัน (Days)
    amount DECIMAL(12, 2) DEFAULT 0.00,       -- ยอดเงิน (Amount)
    period_end DATE,                          -- วันสิ้นสุดรอบ (Period End)
    work_date DATE NOT NULL,                  -- วันทำงาน (Work Date)
    correction CHAR(5),                       -- ข้อมูลแก้ไข (Correction เช่น Y/N)
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 3. ตารางประวัติการโอนย้ายคนงานรายวัน (adjust_report)
CREATE TABLE IF NOT EXISTS adjust_report (
    id SERIAL PRIMARY KEY,
    employee_id VARCHAR(50),                  -- รหัสพนักงานที่โอนย้าย
    name VARCHAR(255),                        -- ชื่อพนักงาน
    check_in TIMESTAMPTZ,                     -- เวลาเข้างานต่างไซต์
    check_out TIMESTAMPTZ,                    -- เวลาออกงานต่างไซต์
    work_normal DECIMAL(10, 3) DEFAULT 0.000, -- FTE งานปกติ
    ot_1 DECIMAL(10, 3) DEFAULT 0.000,        -- FTE โอที 1 เท่า
    ot_1_5 DECIMAL(10, 3) DEFAULT 0.000,      -- FTE โอที 1.5 เท่า
    ot_3 DECIMAL(10, 3) DEFAULT 0.000,        -- FTE โอที 3 เท่า
    cost_center_departure VARCHAR(50),         -- รหัสศูนย์ต้นทุนต้นทาง
    cost_center_departure_name VARCHAR(255),   -- ชื่อ CC ต้นทาง
    cost_center_destination VARCHAR(50),       -- รหัสศูนย์ต้นทุนปลายทาง
    cost_center_destination_name VARCHAR(255), -- ชื่อ CC ปลายทาง
    work_date DATE NOT NULL,                  -- วันทำงานจริง
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 4. ตารางประวัติพนักงานภายนอกรายวัน (outsource_report)
CREATE TABLE IF NOT EXISTS outsource_report (
    id SERIAL PRIMARY KEY,
    employee_id VARCHAR(50) NOT NULL,         -- รหัสพนักงาน Outsource
    first_name VARCHAR(100),                  -- ชื่อ
    last_name VARCHAR(100),                   -- นามสกุล
    site VARCHAR(100),                        -- ไซต์งาน
    clock_in TIMESTAMPTZ,                     -- เวลาเข้างาน
    clock_out TIMESTAMPTZ,                    -- เวลาออกงาน
    working_hours DECIMAL(10, 3) DEFAULT 0.000,-- ชั่วโมงที่ทำงานจริง
    cost_center_origin VARCHAR(50),           -- CC ต้นสังกัดเดิม
    cost_center_transfer VARCHAR(255),        -- CC ที่ไปช่วยงาน (สำหรับ OT)
    pay_type VARCHAR(50),                     -- ประเภท Normal หรือ OT
    work_date DATE NOT NULL,                  -- วันทำงานจริง
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 5. ตารางประวัติปริมาณการผลิตผลงานรายวัน (productivity_report)
CREATE TABLE IF NOT EXISTS productivity_report (
    id SERIAL PRIMARY KEY,
    cost_center VARCHAR(50) NOT NULL,         -- รหัสศูนย์ต้นทุน
    scdc_site VARCHAR(255),                   -- ไซต์งานย่อย
    uom VARCHAR(50),                          -- หน่วยนับ (เช่น Box, Pallet)
    volume DECIMAL(12, 3) DEFAULT 0.000,      -- ปริมาณงานที่ได้
    work_date DATE NOT NULL,                  -- วันทำงานจริง
    group_type VARCHAR(50) NOT NULL,          -- กลุ่มใหญ่ เช่น XD, WH, Online
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 6. ตารางสรุปค่าเฉลี่ยรายศูนย์ต้นทุนรายเดือน (monthly_productivity_summary)
CREATE TABLE IF NOT EXISTS monthly_productivity_summary (
    month VARCHAR(7) NOT NULL,                -- เดือนที่ทำรายการ (YYYY-MM)
    cost_center VARCHAR(50) NOT NULL,         -- รหัสศูนย์ต้นทุน
    cost_center_name VARCHAR(255),            -- ชื่อศูนย์ต้นทุน
    group_type VARCHAR(50) NOT NULL,          -- กลุ่มย่อยแผนก (XD, WH_NO_CMG, WH_YES_CMG, Online)
    fte_normal DECIMAL(10, 3) DEFAULT 0.000,
    fte_ot DECIMAL(10, 3) DEFAULT 0.000,
    adjust_norm_minus DECIMAL(10, 3) DEFAULT 0.000,
    adjust_ot_minus DECIMAL(10, 3) DEFAULT 0.000,
    adjust_norm_plus DECIMAL(10, 3) DEFAULT 0.000,
    adjust_ot_plus DECIMAL(10, 3) DEFAULT 0.000,
    os_norm DECIMAL(10, 3) DEFAULT 0.000,
    os_ot DECIMAL(10, 3) DEFAULT 0.000,
    net_total_fte DECIMAL(10, 3) DEFAULT 0.000,
    volume DECIMAL(12, 3) DEFAULT 0.000,
    days_with_volume INTEGER DEFAULT 0,       -- จำนวนวันที่มี Volume จริงในเดือนนี้
    created_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (month, cost_center, group_type)
);

-- 7. สร้างดัชนี (Index) ค้นหาวันที่และ CC
CREATE INDEX IF NOT EXISTS idx_payroll_report_date ON payroll_report (work_date DESC);
CREATE INDEX IF NOT EXISTS idx_adjust_report_date ON adjust_report (work_date DESC);
CREATE INDEX IF NOT EXISTS idx_outsource_report_date ON outsource_report (work_date DESC);
CREATE INDEX IF NOT EXISTS idx_productivity_report_date ON productivity_report (work_date DESC);

-- 8. เปิดใช้ Row Level Security (RLS)
ALTER TABLE employee_master ENABLE ROW LEVEL SECURITY;
ALTER TABLE payroll_report ENABLE ROW LEVEL SECURITY;
ALTER TABLE adjust_report ENABLE ROW LEVEL SECURITY;
ALTER TABLE outsource_report ENABLE ROW LEVEL SECURITY;
ALTER TABLE productivity_report ENABLE ROW LEVEL SECURITY;
ALTER TABLE monthly_productivity_summary ENABLE ROW LEVEL SECURITY;

-- 9. สร้าง Read Policy (สำหรับ Anon Key ให้อ่านได้สาธารณะทั้งหมด)
CREATE POLICY "Allow public read access on employee_master" ON employee_master FOR SELECT USING (true);
CREATE POLICY "Allow public read access on payroll_report" ON payroll_report FOR SELECT USING (true);
CREATE POLICY "Allow public read access on adjust_report" ON adjust_report FOR SELECT USING (true);
CREATE POLICY "Allow public read access on outsource_report" ON outsource_report FOR SELECT USING (true);
CREATE POLICY "Allow public read access on productivity_report" ON productivity_report FOR SELECT USING (true);
CREATE POLICY "Allow public read access on monthly_productivity_summary" ON monthly_productivity_summary FOR SELECT USING (true);

-- 10. สร้าง Write Policy (สำหรับ Service Role ให้เขียนได้ทั้งหมด)
CREATE POLICY "Allow service_role write access on employee_master" ON employee_master FOR ALL TO service_role USING (true);
CREATE POLICY "Allow service_role write access on payroll_report" ON payroll_report FOR ALL TO service_role USING (true);
CREATE POLICY "Allow service_role write access on adjust_report" ON adjust_report FOR ALL TO service_role USING (true);
CREATE POLICY "Allow service_role write access on outsource_report" ON outsource_report FOR ALL TO service_role USING (true);
CREATE POLICY "Allow service_role write access on productivity_report" ON productivity_report FOR ALL TO service_role USING (true);
CREATE POLICY "Allow service_role write access on monthly_productivity_summary" ON monthly_productivity_summary FOR ALL TO service_role USING (true);
