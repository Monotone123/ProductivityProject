#!/bin/zsh

# ==========================================================================
# Local ETL Execution Wrapper for macOS (Macbook)
# สคริปต์ครอบสำหรับสั่งรัน ETL ภายในเครื่อง Macbook
# ==========================================================================

# 1. ระบุตัวแปรการเชื่อมต่อ Supabase ของคุณ
export SUPABASE_URL="https://etdwppqkjloghkcyifpq.supabase.co"
export SUPABASE_SERVICE_ROLE_KEY="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImV0ZHdwcHFramxvZ2hrY3lpZnBxIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc4MjAyMDgzOSwiZXhwIjoyMDk3NTk2ODM5fQ.ckMi3USy2J22gy7amqojMA7dEtsYjer_TC6lI59rl6g"

# 2. ระบุพิกัดไฟล์เวลาทำงาน (Folder 1: Payroll FTE Normal)
export LOCAL_FILE_PATH=""
export ONEDRIVE_SHARE_LINK=""
export GDRIVE_SHARE_LINK="https://drive.google.com/drive/folders/1jt-MYYEJXq1n0UVfdf96GJigezuWcAH4?usp=sharing"

# 3. ระบุพิกัดไฟล์ประวัติพนักงานหลัก (Folder 2: Emp Master)
export LOCAL_EMP_MASTER_PATH=""
export EMP_MASTER_SHARE_LINK="https://drive.google.com/drive/folders/1IZA_tR5K1j4B2IPq3OP-wL5YePeImOv6?usp=sharing"


# 3. ระบุโฟลเดอร์ของโครงการในเครื่อง
PROJECT_DIR="/Users/anusorn/.gemini/antigravity/scratch/onedrive-supabase-etl-app"

# 4. เรียกทำงานสคริปต์ประมวลผลข้อมูล
echo "--- Starting Local ETL Job at $(date) ---"
cd "$PROJECT_DIR"
python3 etl/etl_pipeline.py
echo "--- Finished Local ETL Job at $(date) ---"
