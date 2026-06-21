import os
import sys
import re
import base64
import hashlib
import requests
import json
import pandas as pd
import numpy as np
from datetime import datetime
from supabase import create_client, Client

# ==========================================
# Configurations
# ==========================================
SUPABASE_URL = os.environ.get("SUPABASE_URL") or "https://etdwppqkjloghkcyifpq.supabase.co"
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImV0ZHdwcHFramxvZ2hrY3lpZnBxIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc4MjAyMDgzOSwiZXhwIjoyMDk3NTk2ODM5fQ.ckMi3USy2J22gy7amqojMA7dEtsYjer_TC6lI59rl6g"

# Check if we are running in a real database connection or default placeholder
IS_MOCK_ENV = not SUPABASE_URL or not SUPABASE_KEY or "your-project-id" in SUPABASE_URL

# Google Drive Links (Folder 1: Payroll FTE)
GDRIVE_SHARE_LINK = os.environ.get("GDRIVE_SHARE_LINK") or "https://drive.google.com/drive/folders/1jt-MYYEJXq1n0UVfdf96GJigezuWcAH4?usp=sharing"
LOCAL_FILE_PATH = os.environ.get("LOCAL_FILE_PATH")

# File Paths for Folder 2, 3, 4, 5 (stored in workspace)
EMP_MASTER_FILE = "Employee_Master.xlsx"
ADJUST_FILE = "Adjust FTE.xlsx"
OS_NORMAL_FILE = "OS (Normal).xlsx"
OS_OT_FILE = "OS (OT).xlsx"
PROD_FILE = "Productivity Weekly Performance.xlsx"

BATCH_SIZE = 4000

# ==========================================
# 1. Download & File Scan Helpers
# ==========================================
def get_google_drive_direct_url(share_link):
    try:
        file_id = None
        match_d = re.search(r'/d/([a-zA-Z0-9-_]+)', share_link)
        if match_d:
            file_id = match_d.group(1)
        else:
            match_id = re.search(r'id=([a-zA-Z0-9-_]+)', share_link)
            if match_id:
                file_id = match_id.group(1)
                
        if not file_id:
            return None
            
        if 'spreadsheets' in share_link:
            return f"https://docs.google.com/spreadsheets/d/{file_id}/export?format=xlsx"
        else:
            return f"https://drive.google.com/uc?export=download&id={file_id}"
    except Exception as e:
        print(f"Google Drive link conversion error: {e}")
    return None

def scan_google_drive_folder(folder_link):
    print(f"Scanning Google Drive folder: {folder_link}")
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36'
        }
        response = requests.get(folder_link, headers=headers)
        if response.status_code != 200:
            print(f"Failed to load folder HTML. Status: {response.status_code}")
            return []
            
        html = response.text
        filename_matches = list(re.finditer(r'aria-label="([^"]+?\.(?:csv|xlsx|xls))[^"]*"', html))
        if not filename_matches:
            filename_matches = list(re.finditer(r'[^a-zA-Z0-9-_"\'/]([^"\'/]+?\.(?:csv|xlsx|xls))', html))
            
        files_found = []
        folder_id_match = re.search(r'folders/([a-zA-Z0-9-_]+)', folder_link)
        folder_id = folder_id_match.group(1) if folder_id_match else None
        
        for match in filename_matches:
            filename = match.group(1)
            pos = match.start()
            
            window_start = max(0, pos - 1500)
            window_end = min(len(html), pos + 1500)
            window_text = html[window_start:window_end]
            
            window_ids = re.findall(r'(?:data-id=|ssk=[\'"]\d+:[a-zA-Z0-9_]+:)([a-zA-Z0-9-_]{33})', window_text)
            if not window_ids:
                window_ids = re.findall(r'([a-zA-Z0-9-_]{33})', window_text)
                
            if window_ids:
                valid_ids = [wid for wid in window_ids if wid != folder_id]
                if valid_ids:
                    best_id = valid_ids[0]
                    if not any(f['id'] == best_id for f in files_found):
                        files_found.append({
                            "id": best_id,
                            "name": filename,
                            "download_url": f"https://drive.google.com/uc?export=download&id={best_id}"
                        })
                        
        print(f"Total files found in Google Drive folder: {len(files_found)}")
        return files_found
    except Exception as e:
        print(f"Error scanning Google Drive folder: {e}")
        return []

# ==========================================
# 2. Date and Text Cleaning Helpers
# ==========================================
def parse_date(date_str):
    if not date_str or pd.isnull(date_str):
        return None
    date_str = str(date_str).strip()
    for fmt in ('%d/%m/%Y', '%d-%m-%Y', '%Y-%m-%d', '%Y/%m/%d', '%Y-%m-%d %H:%M:%S', '%Y/%m/%d %H:%M:%S'):
        try:
            return datetime.strptime(date_str, fmt).strftime('%Y-%m-%d')
        except ValueError:
            pass
    return None

def clean_cc(cc_val):
    if not cc_val or pd.isnull(cc_val) or str(cc_val).strip() == "" or str(cc_val).strip() == "nan":
        return None
    try:
        return str(int(float(str(cc_val).strip())))
    except ValueError:
        return str(cc_val).strip()

# ==========================================
# 3. Data Processing Helpers (Extract & Transform)
# ==========================================
def process_payroll_files(payroll_files):
    print(f"Processing {len(payroll_files)} payroll files...")
    records = []
    
    for file_path in payroll_files:
        try:
            df = pd.read_csv(file_path, encoding="utf-8-sig")
        except Exception:
            df = pd.read_csv(file_path, encoding="cp874", errors="ignore")
            
        df.columns = [col.replace('\ufeff', '').strip() if isinstance(col, str) else col for col in df.columns]
        
        df['parsed_work_date'] = df['Work Date'].apply(parse_date)
        df['parsed_period_end'] = df['Period End'].apply(parse_date)
        df = df.dropna(subset=['parsed_work_date'])
        
        # Limit to 2026 for testing/production context
        df['datetime_work'] = pd.to_datetime(df['parsed_work_date'])
        df = df[df['datetime_work'].dt.year == 2026]
        
        for index, row in df.iterrows():
            emp_id = str(row['Employee ID']).strip()
            work_d = row['parsed_work_date']
            p_code = str(row.get('Pay Code', '')).strip()
            e_code = str(row.get('Earning Code', '')).strip()
            
            # Primary key MD5 hash
            hash_seed = f"{emp_id}_{work_d}_{p_code}_{e_code}_{index}"
            record_id = hashlib.md5(hash_seed.encode('utf-8')).hexdigest()
            
            records.append({
                "record_id": record_id,
                "employee_id": emp_id,
                "pay_code": p_code if pd.notnull(p_code) else None,
                "pay_code_description": str(row.get('Pay Code Description', '')).strip() if pd.notnull(row.get('Pay Code Description')) else None,
                "earning_code": e_code if pd.notnull(e_code) else None,
                "hours_py": float(row.get('Hours (py)', 0)) if pd.notnull(row.get('Hours (py)')) else 0.0,
                "hours": float(row.get('Hours', 0)) if pd.notnull(row.get('Hours')) else 0.0,
                "minutes": int(row.get('Minutes', 0)) if pd.notnull(row.get('Minutes')) else 0,
                "planned_hour": float(row.get('Planned hour', 0)) if pd.notnull(row.get('Planned hour')) else 0.0,
                "planned_hours": int(row.get('Planned hours', 0)) if pd.notnull(row.get('Planned hours')) else 0,
                "planned_minutes": int(row.get('Planned minutes', 0)) if pd.notnull(row.get('Planned minutes')) else 0,
                "count_val": int(row.get('Count', 0)) if pd.notnull(row.get('Count')) else 0,
                "days_val": int(row.get('Days', 0)) if pd.notnull(row.get('Days')) else 0,
                "amount": float(row.get('Amount', 0)) if pd.notnull(row.get('Amount')) else 0.00,
                "period_end": row['parsed_period_end'],
                "work_date": work_d,
                "correction": str(row.get('Correction', 'N'))[:5] if pd.notnull(row.get('Correction')) else 'N'
            })
            
    print(f"Processed {len(records)} payroll records.")
    return records

def process_employee_master(file_path):
    print(f"Reading Employee Master: {file_path}")
    if not os.path.exists(file_path):
        print(f"Employee Master file not found at: {file_path}")
        return []
    df = pd.read_excel(file_path)
    df.columns = [col.replace('\ufeff', '').strip() if isinstance(col, str) else col for col in df.columns]
    
    emp_records = []
    for _, row in df.iterrows():
        emp_id = str(row.get('รหัสพนักงาน', '')).strip()
        if not emp_id or emp_id == "nan" or emp_id == "None":
            continue
            
        emp_records.append({
            "employee_id": emp_id,
            "first_name": str(row.get('ชื่อ', '')).strip() if pd.notnull(row.get('ชื่อ')) else None,
            "last_name": str(row.get('นามสกุล', '')).strip() if pd.notnull(row.get('นามสกุล')) else None,
            "organization_name": str(row.get('Organization name', '')).strip() if pd.notnull(row.get('Organization name')) else None,
            "position_name": str(row.get('Position Name', '')).strip() if pd.notnull(row.get('Position Name')) else None,
            "job_name": str(row.get('Job Name', '')).strip() if pd.notnull(row.get('Job Name')) else None,
            "cost_center": clean_cc(row.get('Cost Center')),
            "level_name": str(row.get('Level', '')).strip() if pd.notnull(row.get('Level')) else None
        })
        
    return emp_records

def process_adjust_report(file_path):
    print(f"Reading Adjust FTE report: {file_path}")
    if not os.path.exists(file_path):
        print(f"Adjust file not found at: {file_path}")
        return []
    df = pd.read_excel(file_path)
    df.columns = [col.replace('\ufeff', '').strip() if isinstance(col, str) else col for col in df.columns]
    
    records = []
    for _, row in df.iterrows():
        check_in_raw = row.get('Check In')
        check_out_raw = row.get('Check Out')
        
        check_in_dt = pd.to_datetime(check_in_raw, errors='coerce')
        check_out_dt = pd.to_datetime(check_out_raw, errors='coerce')
        
        check_in = check_in_dt.isoformat() if pd.notnull(check_in_dt) else None
        check_out = check_out_dt.isoformat() if pd.notnull(check_out_dt) else None
        
        work_date = check_in_dt.strftime('%Y-%m-%d') if pd.notnull(check_in_dt) else None
        if not work_date:
            continue
            
        emp_id = str(row.get('Employee ID', '')).strip()
        if emp_id == 'nan' or not emp_id:
            emp_id = None
            
        records.append({
            "employee_id": emp_id,
            "name": str(row.get('Name', '')).strip() if pd.notnull(row.get('Name')) else None,
            "check_in": check_in,
            "check_out": check_out,
            "work_normal": float(row.get('งานปกติ', 0)) if pd.notnull(row.get('งานปกติ')) else 0.000,
            "ot_1": float(row.get('OT 1', 0)) if pd.notnull(row.get('OT 1')) else 0.000,
            "ot_1_5": float(row.get('OT 1.5', 0)) if pd.notnull(row.get('OT 1.5')) else 0.000,
            "ot_3": float(row.get('OT 3', 0)) if pd.notnull(row.get('OT 3')) else 0.000,
            "cost_center_departure": clean_cc(row.get('Cost Center Depature')),
            "cost_center_departure_name": str(row.get('Cost Center Depature Name', '')).strip() if pd.notnull(row.get('Cost Center Depature Name')) else None,
            "cost_center_destination": clean_cc(row.get('Cost Center Destination')),
            "cost_center_destination_name": str(row.get('Cost Center Destination Name', '')).strip() if pd.notnull(row.get('Cost Center Destination Name')) else None,
            "work_date": work_date
        })
    print(f"Processed {len(records)} adjust records.")
    return records

def process_outsource_report(norm_file, ot_file):
    records = []
    
    def process_os_file(file_path, pay_type):
        print(f"Reading OS {pay_type} report: {file_path}")
        if not os.path.exists(file_path):
            print(f"OS file not found at: {file_path}")
            return
        df = pd.read_excel(file_path)
        df.columns = [col.replace('\ufeff', '').strip() if isinstance(col, str) else col for col in df.columns]
        
        for _, row in df.iterrows():
            clock_in_raw = row.get('clock_in')
            clock_out_raw = row.get('clock_out')
            
            clock_in_dt = pd.to_datetime(clock_in_raw, errors='coerce')
            clock_out_dt = pd.to_datetime(clock_out_raw, errors='coerce')
            
            clock_in = clock_in_dt.isoformat() if pd.notnull(clock_in_dt) else None
            clock_out = clock_out_dt.isoformat() if pd.notnull(clock_out_dt) else None
            
            work_date = clock_in_dt.strftime('%Y-%m-%d') if pd.notnull(clock_in_dt) else None
            if not work_date:
                continue
                
            emp_id = str(row.get('employee_id', '')).strip()
            if emp_id == 'nan' or not emp_id:
                continue
                
            # Capping outlier hours due to NaT clock_outs
            working_hrs = float(row.get('working_hours', 0)) if pd.notnull(row.get('working_hours')) else 0.000
            if pd.isnull(clock_out_raw) or clock_out is None:
                if working_hrs > 24.0:
                    working_hrs = 8.0 # Capped fallback
            
            records.append({
                "employee_id": emp_id,
                "first_name": str(row.get('first_name', '')).strip() if pd.notnull(row.get('first_name')) else None,
                "last_name": str(row.get('last_name', '')).strip() if pd.notnull(row.get('last_name')) else None,
                "site": str(row.get('site', '')).strip() if pd.notnull(row.get('site')) else None,
                "clock_in": clock_in,
                "clock_out": clock_out,
                "working_hours": working_hrs,
                "cost_center_origin": clean_cc(row.get('cost_center_origin')),
                "cost_center_transfer": str(row.get('cost_center_transfer', '')).strip() if pd.notnull(row.get('cost_center_transfer')) else None,
                "pay_type": pay_type,
                "work_date": work_date
            })
            
    process_os_file(norm_file, 'Normal')
    process_os_file(ot_file, 'OT')
    print(f"Processed {len(records)} outsource records.")
    return records

def process_productivity_report(file_path):
    print(f"Reading Productivity Performance report: {file_path}")
    if not os.path.exists(file_path):
        print(f"Productivity file not found at: {file_path}")
        return []
    excel_file = pd.ExcelFile(file_path)
    records = []
    
    for sheet in excel_file.sheet_names:
        if sheet not in ['XD', 'WH', 'Online']:
            continue
            
        sheet_df = excel_file.parse(sheet)
        sheet_df.columns = [col.replace('\ufeff', '').strip() if isinstance(col, str) else col for col in sheet_df.columns]
        
        metadata_cols = ['Unnamed: 0', 'Unnamed: 1', 'Cost', 'Function', 'SCDC Site', 'BU', 'Topic', 'Type', 'แหล่งข้อมูล', 'UOM']
        metadata_cols = [c for c in metadata_cols if c in sheet_df.columns]
        date_cols = [c for c in sheet_df.columns if c not in metadata_cols]
        
        melted = pd.melt(sheet_df, id_vars=metadata_cols, value_vars=date_cols, var_name='Date', value_name='Volume')
        melted['Volume'] = pd.to_numeric(melted['Volume'], errors='coerce').fillna(0)
        
        for _, row in melted.iterrows():
            date_dt = pd.to_datetime(row['Date'], errors='coerce')
            work_date = date_dt.strftime('%Y-%m-%d') if pd.notnull(date_dt) else None
            if not work_date:
                continue
                
            cost = clean_cc(row.get('Cost'))
            if not cost:
                cost = '99999'
                
            records.append({
                "cost_center": cost,
                "scdc_site": str(row.get('SCDC Site', '')).strip() if pd.notnull(row.get('SCDC Site')) else None,
                "uom": str(row.get('UOM', '')).strip() if pd.notnull(row.get('UOM')) else None,
                "volume": float(row.get('Volume', 0)),
                "work_date": work_date,
                "group_type": sheet
            })
            
    print(f"Processed {len(records)} productivity records.")
    return records

# ==========================================
# 4. Aggregation Logic (PANDAS Engine)
# ==========================================
def calculate_aggregations(payroll_recs, emp_recs, adjust_recs, os_recs, prod_recs):
    print("Running Unified Aggregation Engine...")
    
    # Load into Pandas DataFrames
    df_payroll = pd.DataFrame(payroll_recs)
    df_emp = pd.DataFrame(emp_recs)
    df_adjust = pd.DataFrame(adjust_recs)
    df_os = pd.DataFrame(os_recs)
    df_prod = pd.DataFrame(prod_recs)
    
    # Ensure expected columns exist even if empty
    if df_payroll.empty:
        df_payroll = pd.DataFrame(columns=['record_id', 'employee_id', 'pay_code', 'pay_code_description', 'earning_code', 'hours_py', 'hours', 'minutes', 'planned_hour', 'planned_hours', 'planned_minutes', 'count_val', 'days_val', 'amount', 'period_end', 'work_date', 'correction', 'cost_center'])
    if df_emp.empty:
        df_emp = pd.DataFrame(columns=['employee_id', 'first_name', 'last_name', 'organization_name', 'position_name', 'job_name', 'cost_center', 'level_name'])
    if df_adjust.empty:
        df_adjust = pd.DataFrame(columns=['employee_id', 'name', 'check_in', 'check_out', 'work_normal', 'ot_1', 'ot_1_5', 'ot_3', 'cost_center_departure', 'cost_center_departure_name', 'cost_center_destination', 'cost_center_destination_name', 'work_date'])
    if df_os.empty:
        df_os = pd.DataFrame(columns=['employee_id', 'first_name', 'last_name', 'site', 'clock_in', 'clock_out', 'working_hours', 'cost_center_origin', 'cost_center_transfer', 'pay_type', 'work_date'])
    if df_prod.empty:
        df_prod = pd.DataFrame(columns=['cost_center', 'scdc_site', 'uom', 'volume', 'work_date', 'group_type'])
    
    # 1. Map Cost Centers on payroll
    if not df_payroll.empty and not df_emp.empty:
        df_emp['employee_id'] = df_emp['employee_id'].astype(str).str.strip()
        df_payroll['employee_id'] = df_payroll['employee_id'].astype(str).str.strip()
        emp_cc_map = df_emp.set_index('employee_id')['cost_center'].to_dict()
        df_payroll['cost_center'] = df_payroll['employee_id'].map(emp_cc_map)
        df_payroll = df_payroll.dropna(subset=['cost_center'])
    else:
        df_payroll['cost_center'] = None
        df_payroll = df_payroll.dropna(subset=['cost_center'])
        
    # Get Cost Center Name Map
    cc_names = {}
    if not df_emp.empty:
        for _, r in df_emp.iterrows():
            cc = str(r['cost_center']).strip()
            org = str(r['organization_name']).strip()
            if cc and org and cc != 'nan' and org != 'nan' and org != 'None':
                cc_names[cc] = org
                
    if not df_adjust.empty:
        for _, r in df_adjust.iterrows():
            dep_cc = str(r['cost_center_departure']).strip()
            dep_name = str(r['cost_center_departure_name']).strip()
            dest_cc = str(r['cost_center_destination']).strip()
            dest_name = str(r['cost_center_destination_name']).strip()
            if dep_cc and dep_name and dep_name != 'nan':
                cc_names[dep_cc] = dep_name
            if dest_cc and dest_name and dest_name != 'nan':
                cc_names[dest_cc] = dest_name
                
    # Fallback names
    cc_names['82650'] = 'Online WH Operation Mgmt'
    cc_names['82652'] = 'CDS Online WH'
    cc_names['82658'] = 'SSP Online WH'
    cc_names['82660'] = 'Beautrium Omni WH'
    cc_names['82611'] = 'CDSBC-BDC x CMG Management'
    cc_names['82622'] = 'CDSBC-GG Business Management'

    # Filter target months
    target_months = ['2026-04', '2026-05', '2026-06']
    
    # Helper to resolve month
    df_payroll['month'] = pd.to_datetime(df_payroll['work_date']).dt.strftime('%Y-%m')
    df_adjust['month'] = pd.to_datetime(df_adjust['work_date']).dt.strftime('%Y-%m')
    df_os['month'] = pd.to_datetime(df_os['work_date']).dt.strftime('%Y-%m')
    df_prod['month'] = pd.to_datetime(df_prod['work_date']).dt.strftime('%Y-%m')
    
    df_payroll = df_payroll[df_payroll['month'].isin(target_months)]
    df_adjust = df_adjust[df_adjust['month'].isin(target_months)]
    df_os = df_os[df_os['month'].isin(target_months)]
    df_prod = df_prod[df_prod['month'].isin(target_months)]
    
    # 2. Group cost centers by department
    dept_configs = {
        "XD": {
            "ccs": ['82210', '82301', '82303', '82306', '82308', '82910', '82920'],
            "sheet": "XD",
            "bottom_line_name": "XD Productivity",
            "val_filter": lambda r: str(r['cost_center']).strip() in ['82210', '82301', '82303', '82306', '82308', '82910', '82920'] or (str(r['cost_center']).strip() == '99999' and str(r['scdc_site']).strip().upper() in ['GIC', 'SSP', 'OFM', 'B2S'])
        },
        "WH_NO_CMG": {
            "ccs": ['82607', '82612', '82630', '82640'],
            "sheet": "WH",
            "bottom_line_name": "Office Warehouse - Fashion Productivity (ไม่รวม CMG/GG)",
            "val_filter": lambda r: str(r['cost_center']).strip() in ['82607', '82612', '82630', '82640'] or (str(r['cost_center']).strip() == '99999' and 'Office Warehouse - Fashion' in str(r['scdc_site']))
        },
        "WH_YES_CMG": {
            "ccs": ['82607', '82612', '82630', '82640', '82611', '82622'],
            "sheet": "WH",
            "bottom_line_name": "Office Warehouse - Fashion Productivity (รวม CMG 82611 และ GG 82622)",
            "val_filter": lambda r: str(r['cost_center']).strip() in ['82607', '82612', '82630', '82640', '82611', '82622'] or (str(r['cost_center']).strip() == '99999' and 'Office Warehouse - Fashion' in str(r['scdc_site']))
        },
        "Online": {
            "ccs": ['82650', '82652', '82658', '82660'],
            "sheet": "Online",
            "bottom_line_name": "Online Warehouse Productivity",
            "val_filter": lambda r: str(r['cost_center']).strip() in ['82650', '82652', '82658', '82660'] or (str(r['cost_center']).strip() == '99999' and str(r['scdc_site']) == 'Online Warehouse')
        }
    }
    
    monthly_summaries = []
    daily_details = []
    
    # Pre-calculate daily summaries for easier lookup and detail explorer
    # Iterate months and departments
    for month in target_months:
        # Calculate working days for this month
        # Operating Normal: Mon-Fri
        # OS: Mon-Sat
        try:
            y_str, m_str = month.split('-')
            year = int(y_str)
            month_val = int(m_str)
            
            import calendar
            _, num_days = calendar.monthrange(year, month_val)
            
            wd_normal = 0
            wd_os = 0
            for d_idx in range(1, num_days + 1):
                # 0 is Monday, ..., 6 is Sunday
                weekday = calendar.weekday(year, month_val, d_idx)
                if weekday < 5:  # Mon-Fri
                    wd_normal += 1
                if weekday < 6:  # Mon-Sat
                    wd_os += 1
        except Exception as ex:
            print(f"Error calculating working days for month {month}: {ex}, fallback to 26")
            wd_normal = 26
            wd_os = 26
            
        print(f"Month {month}: Operating Normal WD={wd_normal}, OS WD={wd_os}")
        
        for group_type, cfg in dept_configs.items():
            ccs = cfg["ccs"]
            sheet = cfg["sheet"]
            
            # A. Calculate individual CCs
            individual_records = []
            for cc in ccs:
                # F1 Payroll FTE
                f1_cc = df_payroll[(df_payroll['month'] == month) & (df_payroll['cost_center'] == cc)]
                fte_normal = float(f1_cc[f1_cc['pay_code'] == 'REG_EXPORT']['employee_id'].nunique())
                
                ot_hours = float(f1_cc[f1_cc['pay_code'].isin(['OT_10', 'OT_15', 'OT_30'])]['hours_py'].sum())
                fte_ot = ot_hours / 8.5 / wd_normal
                
                # F3 Adjust
                adj_cc = df_adjust[df_adjust['month'] == month]
                
                dep_normal = float(adj_cc[adj_cc['cost_center_departure'] == cc]['work_normal'].sum())
                dep_ot = float(adj_cc[adj_cc['cost_center_departure'] == cc][['ot_1', 'ot_1_5', 'ot_3']].sum(axis=1).sum())
                
                dest_normal = float(adj_cc[adj_cc['cost_center_destination'] == cc]['work_normal'].sum())
                dest_ot = float(adj_cc[adj_cc['cost_center_destination'] == cc][['ot_1', 'ot_1_5', 'ot_3']].sum(axis=1).sum())
                
                # F5 OS
                os_cc = df_os[df_os['month'] == month]
                os_norm_hrs = float(os_cc[(os_cc['pay_type'] == 'Normal') & (os_cc['cost_center_origin'] == cc)]['working_hours'].sum())
                os_norm = os_norm_hrs / 8.0 / wd_os
                
                # For OS OT, cost_center = cost_center_transfer (numeric part) fallback to origin
                if not os_cc.empty:
                    os_cc = os_cc.copy()
                    os_cc['transfer_cc'] = os_cc['cost_center_transfer'].astype(str).str.extract(r'^(\d+)')
                    os_cc['resolved_cc'] = os_cc['transfer_cc'].fillna(os_cc['cost_center_origin'])
                else:
                    os_cc['resolved_cc'] = None
                    
                os_ot_hrs = float(os_cc[(os_cc['pay_type'] == 'OT') & (os_cc['resolved_cc'] == cc)]['working_hours'].sum())
                os_ot = os_ot_hrs / 8.0 / wd_os
                
                # Net Total FTE
                net_norm = fte_normal - dep_normal + dest_normal
                net_ot = fte_ot - dep_ot + dest_ot
                net_total_fte = net_norm + net_ot + os_norm + os_ot
                
                # Volume
                prod_cc = df_prod[(df_prod['month'] == month) & (df_prod['group_type'] == sheet)]
                cc_vols = prod_cc[prod_cc['cost_center'] == cc]
                volume = float(cc_vols['volume'].sum())
                
                # Days with volume
                daily_vols = cc_vols.groupby('work_date')['volume'].sum()
                days_with_volume = int((daily_vols > 0).sum())
                
                rec = {
                    "month": month,
                    "cost_center": cc,
                    "cost_center_name": cc_names.get(cc, "Unknown"),
                    "group_type": group_type,
                    "fte_normal": fte_normal,
                    "fte_ot": fte_ot,
                    "adjust_norm_minus": dep_normal,
                    "adjust_ot_minus": dep_ot,
                    "adjust_norm_plus": dest_normal,
                    "adjust_ot_plus": dest_ot,
                    "os_norm": os_norm,
                    "os_ot": os_ot,
                    "net_total_fte": net_total_fte,
                    "volume": volume,
                    "days_with_volume": days_with_volume
                }
                individual_records.append(rec)
                monthly_summaries.append(rec)
                
                # Now calculate DAILY break down for this CC in this month
                # For daily chart/table detail explorer
                # Get unique dates in this month
                dates = pd.date_range(start=f"{month}-01", end=f"{month}-30" if month=="2026-06" or month=="2026-04" else f"{month}-31")
                for d in dates:
                    d_str = d.strftime('%Y-%m-%d')
                    
                    # F1
                    f1_day = f1_cc[f1_cc['work_date'] == d_str]
                    day_fte_norm = float(f1_day[f1_day['pay_code'] == 'REG_EXPORT']['employee_id'].nunique())
                    day_ot_hrs = float(f1_day[f1_day['pay_code'].isin(['OT_10', 'OT_15', 'OT_30'])]['hours_py'].sum())
                    day_fte_ot = day_ot_hrs / 8.5
                    
                    # F3
                    adj_day = adj_cc[adj_cc['work_date'] == d_str]
                    day_dep_norm = float(adj_day[adj_day['cost_center_departure'] == cc]['work_normal'].sum())
                    day_dep_ot = float(adj_day[adj_day['cost_center_departure'] == cc][['ot_1', 'ot_1_5', 'ot_3']].sum(axis=1).sum())
                    day_dest_norm = float(adj_day[adj_day['cost_center_destination'] == cc]['work_normal'].sum())
                    day_dest_ot = float(adj_day[adj_day['cost_center_destination'] == cc][['ot_1', 'ot_1_5', 'ot_3']].sum(axis=1).sum())
                    
                    # F5 OS
                    os_day = os_cc[os_cc['work_date'] == d_str]
                    day_os_norm_hrs = float(os_day[(os_day['pay_type'] == 'Normal') & (os_day['cost_center_origin'] == cc)]['working_hours'].sum())
                    day_os_norm = day_os_norm_hrs / 8.0
                    day_os_ot_hrs = float(os_day[(os_day['pay_type'] == 'OT') & (os_day['resolved_cc'] == cc)]['working_hours'].sum())
                    day_os_ot = day_os_ot_hrs / 8.0
                    
                    # Net Daily FTE
                    day_net_norm = day_fte_norm - day_dep_norm + day_dest_norm
                    day_net_ot = day_fte_ot - day_dep_ot + day_dest_ot
                    day_net_total = day_net_norm + day_net_ot + day_os_norm + day_os_ot
                    
                    # Volume
                    day_vol = float(cc_vols[cc_vols['work_date'] == d_str]['volume'].sum())
                    
                    # Daily Productivity
                    day_prod = day_vol / day_net_total if day_net_total > 0 else 0.0
                    
                    daily_details.append({
                        "work_date": d_str,
                        "cost_center": cc,
                        "group_type": group_type,
                        "fte_normal": day_fte_norm,
                        "fte_ot": day_fte_ot,
                        "adjust_norm_minus": day_dep_norm,
                        "adjust_ot_minus": day_dep_ot,
                        "adjust_norm_plus": day_dest_norm,
                        "adjust_ot_plus": day_dest_ot,
                        "os_norm": day_os_norm,
                        "os_ot": day_os_ot,
                        "net_total_fte": day_net_total,
                        "volume": day_vol,
                        "productivity": day_prod
                    })
            
            # B. Calculate Bottom Line (99999) for this group
            sum_fte_normal = sum(r["fte_normal"] for r in individual_records)
            sum_fte_ot = sum(r["fte_ot"] for r in individual_records)
            sum_adj_norm_minus = sum(r["adjust_norm_minus"] for r in individual_records)
            sum_adj_ot_minus = sum(r["adjust_ot_minus"] for r in individual_records)
            sum_adj_norm_plus = sum(r["adjust_norm_plus"] for r in individual_records)
            sum_adj_ot_plus = sum(r["adjust_ot_plus"] for r in individual_records)
            sum_os_norm = sum(r["os_norm"] for r in individual_records)
            sum_os_ot = sum(r["os_ot"] for r in individual_records)
            sum_net_total_fte = sum(r["net_total_fte"] for r in individual_records)
            
            # Bottom Line Volume logic
            prod_group = df_prod[(df_prod['month'] == month) & (df_prod['group_type'] == sheet)]
            if group_type == "WH_YES_CMG":
                # includes fashion 99999 + CMG 82611 + GG 82622 volumes
                vol_99999 = float(prod_group[(prod_group['cost_center'] == '99999') & (prod_group['scdc_site'].str.contains('Office Warehouse - Fashion', na=False))]['volume'].sum())
                vol_82611 = float(prod_group[prod_group['cost_center'] == '82611']['volume'].sum())
                vol_82622 = float(prod_group[prod_group['cost_center'] == '82622']['volume'].sum())
                volume_99999 = vol_99999 + vol_82611 + vol_82622
                
                # Days with volume for group 99999
                is_component = prod_group.apply(
                    lambda r: (str(r['cost_center']).strip() == '99999' and 'Office Warehouse - Fashion' in str(r['scdc_site'])) or str(r['cost_center']).strip() in ['82611', '82622'],
                    axis=1
                )
                daily_grp = prod_group[is_component].groupby('work_date')['volume'].sum()
                days_with_volume_99999 = int((daily_grp > 0).sum())
            else:
                # filter by config lamda
                grp_vols = prod_group[prod_group.apply(cfg["val_filter"], axis=1)]
                # extract 99999 row
                volume_99999 = float(grp_vols[grp_vols['cost_center'] == '99999']['volume'].sum())
                
                # Days with volume
                daily_grp = grp_vols[grp_vols['cost_center'] == '99999'].groupby('work_date')['volume'].sum()
                days_with_volume_99999 = int((daily_grp > 0).sum())
                
            rec_99999 = {
                "month": month,
                "cost_center": "99999",
                "cost_center_name": cfg["bottom_line_name"],
                "group_type": group_type,
                "fte_normal": sum_fte_normal,
                "fte_ot": sum_fte_ot,
                "adjust_norm_minus": sum_adj_norm_minus,
                "adjust_ot_minus": sum_adj_ot_minus,
                "adjust_norm_plus": sum_adj_norm_plus,
                "adjust_ot_plus": sum_adj_ot_plus,
                "os_norm": sum_os_norm,
                "os_ot": sum_os_ot,
                "net_total_fte": sum_net_total_fte,
                "volume": volume_99999,
                "days_with_volume": days_with_volume_99999
            }
            monthly_summaries.append(rec_99999)
            
            # Bottom Line DAILY breakdowns (Sum of individual CCs for that day)
            dates = pd.date_range(start=f"{month}-01", end=f"{month}-30" if month=="2026-06" or month=="2026-04" else f"{month}-31")
            for d in dates:
                d_str = d.strftime('%Y-%m-%d')
                day_recs = [r for r in daily_details if r["work_date"] == d_str and r["group_type"] == group_type and r["cost_center"] != "99999"]
                
                day_fte_norm = sum(r["fte_normal"] for r in day_recs)
                day_fte_ot = sum(r["fte_ot"] for r in day_recs)
                day_dep_norm = sum(r["adjust_norm_minus"] for r in day_recs)
                day_dep_ot = sum(r["adjust_ot_minus"] for r in day_recs)
                day_dest_norm = sum(r["adjust_norm_plus"] for r in day_recs)
                day_dest_ot = sum(r["adjust_ot_plus"] for r in day_recs)
                day_os_norm = sum(r["os_norm"] for r in day_recs)
                day_os_ot = sum(r["os_ot"] for r in day_recs)
                day_net_total = sum(r["net_total_fte"] for r in day_recs)
                
                # Day volume for 99999
                prod_day = prod_group[prod_group['work_date'] == d_str]
                if prod_day.empty:
                    day_vol_99999 = 0.0
                else:
                    if group_type == "WH_YES_CMG":
                        v_99999 = float(prod_day[(prod_day['cost_center'] == '99999') & (prod_day['scdc_site'].str.contains('Office Warehouse - Fashion', na=False))]['volume'].sum())
                        v_82611 = float(prod_day[prod_day['cost_center'] == '82611']['volume'].sum())
                        v_82622 = float(prod_day[prod_day['cost_center'] == '82622']['volume'].sum())
                        day_vol_99999 = v_99999 + v_82611 + v_82622
                    else:
                        day_grp_vols = prod_day[prod_day.apply(cfg["val_filter"], axis=1)]
                        day_vol_99999 = float(day_grp_vols[day_grp_vols['cost_center'] == '99999']['volume'].sum()) if not day_grp_vols.empty else 0.0
                    
                day_prod_99999 = day_vol_99999 / day_net_total if day_net_total > 0 else 0.0
                
                daily_details.append({
                    "work_date": d_str,
                    "cost_center": "99999",
                    "group_type": group_type,
                    "fte_normal": day_fte_norm,
                    "fte_ot": day_fte_ot,
                    "adjust_norm_minus": day_dep_norm,
                    "adjust_ot_minus": day_dep_ot,
                    "adjust_norm_plus": day_dest_norm,
                    "adjust_ot_plus": day_dest_ot,
                    "os_norm": day_os_norm,
                    "os_ot": day_os_ot,
                    "net_total_fte": day_net_total,
                    "volume": day_vol_99999,
                    "productivity": day_prod_99999
                })

    print(f"Calculated {len(monthly_summaries)} monthly summaries and {len(daily_details)} daily details.")
    return monthly_summaries, daily_details

# ==========================================
# 5. Save Data (Supabase or Local JSON)
# ==========================================
def save_mock_data_js(monthly_summaries, daily_records):
    # This writes a JavaScript file defining variables for Web UI Mock Mode fallback
    js_content = f"""// ==========================================
// Auto-generated Mock Data from ETL Pipeline
// Generated at {datetime.now().isoformat()}
// ==========================================

const MOCK_MONTHLY_SUMMARIES = {json.dumps(monthly_summaries, indent=2, ensure_ascii=False)};

const MOCK_DAILY_RECORDS = {json.dumps(daily_records, indent=2, ensure_ascii=False)};
"""
    dest_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "web", "mock_data.js")
    try:
        # Create directory if not exists
        os.makedirs(os.path.dirname(dest_path), exist_ok=True)
        with open(dest_path, "w", encoding="utf-8") as f:
            f.write(js_content)
        print(f"Successfully saved fallback mock data to: {dest_path}")
    except Exception as e:
        print(f"Failed to save fallback mock data to {dest_path}: {e}")

def download_file_from_gdrive(env_var_name, default_local_path):
    link = os.environ.get(env_var_name)
    if not link:
        return default_local_path
    
    print(f"Downloading {env_var_name} from Google Drive: {link}")
    dl_url = get_google_drive_direct_url(link)
    if not dl_url:
        print(f"Could not convert Google Drive link for {env_var_name}, using local fallback: {default_local_path}")
        return default_local_path
        
    try:
        response = requests.get(dl_url)
        if response.status_code == 200:
            local_temp_name = f"temp_{env_var_name.lower()}.xlsx"
            with open(local_temp_name, "wb") as lf:
                lf.write(response.content)
            return local_temp_name
        else:
            print(f"Failed to download {env_var_name} (Status {response.status_code}), using local fallback: {default_local_path}")
    except Exception as e:
        print(f"Error downloading {env_var_name}: {e}, using local fallback: {default_local_path}")
        
    return default_local_path

def run_etl():
    print("=== Start Google Drive/Local to Supabase Unified ETL Pipeline ===")
    
    payroll_files = []
    gdrive_files = []
    
    # ------------------------------------------
    # STEP 1: Scan Google Drive Folder if provided
    # ------------------------------------------
    if GDRIVE_SHARE_LINK and "folders/" in GDRIVE_SHARE_LINK:
        gdrive_files = scan_google_drive_folder(GDRIVE_SHARE_LINK)
        
    # Track paths of files to process
    emp_master_path = EMP_MASTER_FILE
    adjust_path = ADJUST_FILE
    os_normal_path = OS_NORMAL_FILE
    os_ot_path = OS_OT_FILE
    prod_path = PROD_FILE

    # Helper function to find a file in the scanned Google Drive folder by matching substring
    def find_gdrive_file(keyword, extension=".xlsx"):
        for f in gdrive_files:
            fname = f['name'].lower()
            if keyword.lower() in fname and (fname.endswith(extension) or fname.endswith('.xls')):
                return f
        return None

    # Helper function to download a file from Google Drive if found
    def download_matched_file(f, default_local_path):
        if not f:
            return default_local_path
        print(f"Matched file in Google Drive: {f['name']}")
        try:
            print(f"Downloading {f['name']}...")
            response = requests.get(f['download_url'])
            if response.status_code == 200:
                local_temp_name = f"temp_{f['name'].replace(' ', '_')}"
                with open(local_temp_name, "wb") as lf:
                    lf.write(response.content)
                return local_temp_name
            else:
                print(f"Failed to download {f['name']} (Status {response.status_code}), using local fallback: {default_local_path}")
        except Exception as e:
            print(f"Error downloading {f['name']}: {e}, using local fallback: {default_local_path}")
        return default_local_path

    # Process files from Google Drive
    if gdrive_files:
        # A. Payroll CSV files (all CSV files in the folder)
        for f in gdrive_files:
            if f['name'].endswith('.csv'):
                try:
                    print(f"Downloading payroll file: {f['name']}")
                    response = requests.get(f['download_url'])
                    if response.status_code == 200:
                        local_name = f"downloaded_{f['id']}.csv"
                        with open(local_name, "wb") as lf:
                            lf.write(response.content)
                        payroll_files.append(local_name)
                except Exception as e:
                    print(f"Failed to download payroll file {f['name']}: {e}")
                    
        # B. Other Excel files (first check if they exist in the scanned folder)
        emp_master_path = download_matched_file(find_gdrive_file("Employee_Master") or find_gdrive_file("Employee Master"), EMP_MASTER_FILE)
        adjust_path = download_matched_file(find_gdrive_file("Adjust FTE") or find_gdrive_file("Adjust_FTE"), ADJUST_FILE)
        os_normal_path = download_matched_file(find_gdrive_file("OS (Normal)") or find_gdrive_file("OS Normal") or find_gdrive_file("OS_Normal"), OS_NORMAL_FILE)
        os_ot_path = download_matched_file(find_gdrive_file("OS (OT)") or find_gdrive_file("OS OT") or find_gdrive_file("OS_OT"), OS_OT_FILE)
        prod_path = download_matched_file(find_gdrive_file("Productivity"), PROD_FILE)

    # ------------------------------------------
    # STEP 1.5: Fallback to individual env vars if not downloaded from the folder
    # ------------------------------------------
    if emp_master_path == EMP_MASTER_FILE:
        emp_master_path = download_file_from_gdrive("GDRIVE_EMP_MASTER", EMP_MASTER_FILE)
    if adjust_path == ADJUST_FILE:
        adjust_path = download_file_from_gdrive("GDRIVE_ADJUST", ADJUST_FILE)
    if os_normal_path == OS_NORMAL_FILE:
        os_normal_path = download_file_from_gdrive("GDRIVE_OS_NORMAL", OS_NORMAL_FILE)
    if os_ot_path == OS_OT_FILE:
        os_ot_path = download_file_from_gdrive("GDRIVE_OS_OT", OS_OT_FILE)
    if prod_path == PROD_FILE:
        prod_path = download_file_from_gdrive("GDRIVE_PROD", PROD_FILE)

    # If GDRIVE_SHARE_LINK was a direct CSV file link instead of a folder
    if not gdrive_files and GDRIVE_SHARE_LINK and "folders/" not in GDRIVE_SHARE_LINK:
        dl_url = get_google_drive_direct_url(GDRIVE_SHARE_LINK)
        if dl_url:
            try:
                response = requests.get(dl_url)
                if response.status_code == 200:
                    local_name = "downloaded_file.csv"
                    with open(local_name, "wb") as lf:
                        lf.write(response.content)
                    payroll_files.append(local_name)
            except Exception as e:
                print(f"Failed to download file: {e}")

    # Fallback to local files if LOCAL_FILE_PATH is provided
    if not payroll_files and LOCAL_FILE_PATH and os.path.exists(LOCAL_FILE_PATH):
        print(f"Local file path provided: {LOCAL_FILE_PATH}")
        if os.path.isdir(LOCAL_FILE_PATH):
            import glob
            payroll_files = glob.glob(os.path.join(LOCAL_FILE_PATH, "*.csv"))
        else:
            payroll_files = [LOCAL_FILE_PATH]

    # ------------------------------------------
    # STEP 2: Process Raw Daily Data Frames
    # ------------------------------------------
    payroll_recs = process_payroll_files(payroll_files)
    emp_recs = process_employee_master(emp_master_path)
    adjust_recs = process_adjust_report(adjust_path)
    os_recs = process_outsource_report(os_normal_path, os_ot_path)
    prod_recs = process_productivity_report(prod_path)
    
    # ------------------------------------------
    # STEP 2.5: Filter datasets to target range (2026-04-01 to 2026-06-30)
    # to significantly reduce database transaction size and prevent timeouts.
    # ------------------------------------------
    start_date = "2026-04-01"
    end_date = "2026-06-30"
    target_months = ['2026-04', '2026-05', '2026-06']

    payroll_recs = [r for r in payroll_recs if r.get('work_date') and start_date <= r['work_date'] <= end_date]
    adjust_recs = [r for r in adjust_recs if r.get('work_date') and start_date <= r['work_date'] <= end_date]
    os_recs = [r for r in os_recs if r.get('work_date') and start_date <= r['work_date'] <= end_date]
    prod_recs = [r for r in prod_recs if r.get('work_date') and start_date <= r['work_date'] <= end_date]
    
    print(f"Filtered records to range {start_date} to {end_date}:")
    print(f"  - Payroll records: {len(payroll_recs)}")
    print(f"  - Employee master records: {len(emp_recs)}")
    print(f"  - Adjust records: {len(adjust_recs)}")
    print(f"  - Outsource records: {len(os_recs)}")
    print(f"  - Productivity records: {len(prod_recs)}")

    # ------------------------------------------
    # STEP 3: Run Aggregation Engine
    # ------------------------------------------
    monthly_summaries, daily_details = calculate_aggregations(
        payroll_recs, emp_recs, adjust_recs, os_recs, prod_recs
    )
    
    # Write mock fallbacks first
    save_mock_data_js(monthly_summaries, daily_details)
    
    # ------------------------------------------
    # STEP 4: Load into Supabase (if connected)
    # ------------------------------------------
    if IS_MOCK_ENV:
        print("WARNING: Running in Dry-Run/Mock mode. Database sync skipped.")
    else:
        print(f"Connecting to Supabase: {SUPABASE_URL}")
        supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
        
        # A. Upsert Employee Master
        print("Clearing old Employee Master records from Supabase...")
        try:
            supabase.table("employee_master").delete().neq("employee_id", "").execute()
        except Exception as e:
            print(f"Error clearing Employee Master records: {e}")

        if emp_recs:
            print(f"Uploading {len(emp_recs)} Employee Master records to Supabase...")
            for i in range(0, len(emp_recs), BATCH_SIZE):
                batch = emp_recs[i:i + BATCH_SIZE]
                try:
                    supabase.table("employee_master").upsert(batch, on_conflict="employee_id").execute()
                except Exception as e:
                    print(f"Error loading Employee Master batch starting at {i}: {e}")
                    
        # B. Upsert Payroll Report
        print(f"Clearing old Payroll records from Supabase for range {start_date} to {end_date}...")
        try:
            supabase.table("payroll_report").delete().gte("work_date", start_date).lte("work_date", end_date).execute()
        except Exception as e:
            print(f"Error clearing Payroll records: {e}")

        if payroll_recs:
            print(f"Uploading {len(payroll_recs)} Payroll records to Supabase...")
            for i in range(0, len(payroll_recs), BATCH_SIZE):
                batch = payroll_recs[i:i + BATCH_SIZE]
                try:
                    supabase.table("payroll_report").upsert(batch, on_conflict="record_id").execute()
                except Exception as e:
                    print(f"Error loading Payroll batch starting at {i}: {e}")
                    
        # C. Insert/Upsert Adjust Report
        print(f"Clearing old Adjust records from Supabase for range {start_date} to {end_date}...")
        try:
            supabase.table("adjust_report").delete().gte("work_date", start_date).lte("work_date", end_date).execute()
        except Exception as e:
            print(f"Error clearing Adjust records: {e}")

        if adjust_recs:
            print(f"Uploading {len(adjust_recs)} Adjust records to Supabase...")
            for i in range(0, len(adjust_recs), BATCH_SIZE):
                batch = adjust_recs[i:i + BATCH_SIZE]
                try:
                    supabase.table("adjust_report").insert(batch).execute()
                except Exception as e:
                    print(f"Error loading Adjust records: {e}")
                
        # D. Insert/Upsert Outsource Report
        print(f"Clearing old Outsource records from Supabase for range {start_date} to {end_date}...")
        try:
            supabase.table("outsource_report").delete().gte("work_date", start_date).lte("work_date", end_date).execute()
        except Exception as e:
            print(f"Error clearing Outsource records: {e}")

        if os_recs:
            print(f"Uploading {len(os_recs)} Outsource records to Supabase...")
            for i in range(0, len(os_recs), BATCH_SIZE):
                batch = os_recs[i:i + BATCH_SIZE]
                try:
                    supabase.table("outsource_report").insert(batch).execute()
                except Exception as e:
                    print(f"Error loading Outsource records: {e}")
                
        # E. Insert/Upsert Productivity Report
        print(f"Clearing old Productivity records from Supabase for range {start_date} to {end_date}...")
        try:
            supabase.table("productivity_report").delete().gte("work_date", start_date).lte("work_date", end_date).execute()
        except Exception as e:
            print(f"Error clearing Productivity records: {e}")

        if prod_recs:
            print(f"Uploading {len(prod_recs)} Productivity records to Supabase...")
            for i in range(0, len(prod_recs), BATCH_SIZE):
                batch = prod_recs[i:i + BATCH_SIZE]
                try:
                    supabase.table("productivity_report").insert(batch).execute()
                except Exception as e:
                    print(f"Error loading Productivity records: {e}")
                
        # F. Upsert Monthly Productivity Summary
        print(f"Clearing old Monthly Summaries from Supabase for months {target_months}...")
        try:
            supabase.table("monthly_productivity_summary").delete().in_("month", target_months).execute()
        except Exception as e:
            print(f"Error clearing Monthly Summaries: {e}")

        if monthly_summaries:
            print(f"Uploading {len(monthly_summaries)} Monthly Productivity Summaries to Supabase...")
            for i in range(0, len(monthly_summaries), BATCH_SIZE):
                batch = monthly_summaries[i:i + BATCH_SIZE]
                try:
                    supabase.table("monthly_productivity_summary").upsert(
                        batch, on_conflict="month,cost_center,group_type"
                    ).execute()
                except Exception as e:
                    print(f"Error loading Monthly Summaries batch starting at {i}: {e}")
                    
        print("=== Database synchronization completed successfully! ===")
        
    # ------------------------------------------
    # STEP 5: Cleanup temporary downloaded files
    # ------------------------------------------
    for file in payroll_files:
        if "downloaded_" in file or "temp_" in file:
            if os.path.exists(file):
                os.remove(file)
                
    # Clean up downloaded report files
    for temp_file in [emp_master_path, adjust_path, os_normal_path, os_ot_path, prod_path]:
        if temp_file and "temp_" in temp_file and os.path.exists(temp_file):
            os.remove(temp_file)
            
    print("=== ETL Pipeline Completed Successfully! ===")

if __name__ == "__main__":
    run_etl()
