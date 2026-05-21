import pandas as pd
import re
import uuid

# --- Playbook Rules as Python Dictionaries ---

CANONICAL_MASTER = {
    "RMD-100": {"item_id": 10021, "name": "Remdesivir 100mg", "type": "Antiviral", "temp": "Cold (2-8C)", "class": "Antiviral"},
    "RMD-200": {"item_id": 10021, "name": "Remdesivir 200mg", "type": "Antiviral", "temp": "Cold (2-8C)", "class": "Antiviral"},
    "INS-LIS": {"item_id": 10022, "name": "Insulin Lispro", "type": "Hormone", "temp": "Cold (2-8C)", "class": "Endocrine"},
    "PMB-KEY": {"item_id": 10035, "name": "Pembrolizumab", "type": "Monoclonal Antibody", "temp": "Cold (2-8C)", "class": "Oncology Biologic"},
    "EPI-AI": {"item_id": 10040, "name": "Epinephrine Auto-Injector", "type": "Emergency Drug", "temp": "Room Temp (20-25C)", "class": "Emergency"},
    "HEP-SOD": {"item_id": 10050, "name": "Heparin Sodium", "type": "Anticoagulant", "temp": "Room Temp (20-25C)", "class": "Anticoagulant"},
    "MOR-SUL": {"item_id": 10060, "name": "Morphine Sulfate", "type": "Opioid Analgesic", "temp": "Controlled Storage", "class": "Controlled"},
    "ALB-INH": {"item_id": 10070, "name": "Albuterol Inhaler", "type": "Bronchodilator", "temp": "Room Temp (20-25C)", "class": "Respiratory"},
    "EXP-ONC-CT": {"item_id": 99999, "name": "Experimental Oncology Drug (Clinical Trial)", "type": "Clinical Trial Drug", "temp": "Strict Cold Chain (-20C)", "class": "Clinical Trial"},
    "LEV-INH": {"item_id": 10071, "name": "Levalbuterol Inhaler", "type": "Bronchodilator", "temp": "Room Temp (20-25C)", "class": "Respiratory"},
    "INS-ASP": {"item_id": 10023, "name": "Insulin Aspart", "type": "Hormone", "temp": "Cold (2-8C)", "class": "Endocrine"},
}

ALIAS_TABLE = {
    "Remdesivir 100 mg": "RMD-100",
    "Remdesivir 200 mg": "RMD-200",
    "Pembrolizumab (Keytruda)": "PMB-KEY",
    "EpiPen Auto Injector": "EPI-AI",
    "Heparin Na": "HEP-SOD",
    "Morphine Sulphate": "MOR-SUL",
    "Albuterol Inhaler 90mcg": "ALB-INH"
}

LEGACY_ID_TABLE = {
    10020: "RMD-100",
    20021: "RMD-200",
    1070: "ALB-INH",
    99999: "EXP-ONC-CT"
}

REGEX_RULES = {
    "Antiviral": r"^RMD-\d{4}-\d{4}$",
    "Oncology Biologic": r"^PMB-\d{4}-\d{5}$",
    "Emergency": r"^EPI-\d{4}-\d{4}$",
    "Controlled": r"^CTRL-\d{4}-\d{6}$",
    "Respiratory": r"^INH-\d{4}-\d{5}$",
    "Clinical Trial": r"^CT-\d{4}-[A-Z0-9]{6}$",
    "Endocrine": r"^INS-\d{4}-\d{4}$"
}

def generate_id(product_class):
    if product_class == "Antiviral": return f"RMD-2026-{str(uuid.uuid4().int)[:4]}"
    elif product_class == "Oncology Biologic": return f"PMB-2026-{str(uuid.uuid4().int)[:5]}"
    elif product_class == "Emergency": return f"EPI-2026-{str(uuid.uuid4().int)[:4]}"
    elif product_class == "Controlled": return f"CTRL-2026-{str(uuid.uuid4().int)[:6]}"
    elif product_class == "Respiratory": return f"INH-2026-{str(uuid.uuid4().int)[:5]}"
    elif product_class == "Clinical Trial": return f"CT-2026-{str(uuid.uuid4().hex)[:6].upper()}"
    elif product_class == "Endocrine": return f"INS-2026-{str(uuid.uuid4().int)[:4]}"
    return None

def clean_shipment_data(input_csv_path: str, output_csv_path: str) -> dict:
    df = pd.read_csv(input_csv_path)
    cleaned_rows = []
    
    exact_match_map = {}
    for cid, info in CANONICAL_MASTER.items():
        key = (info["item_id"], info["name"])
        exact_match_map[key] = cid
        
    for idx, row in df.iterrows():
        raw_item_id = row['item_id']
        raw_name = row['item_name']
        unique_id = row['unique_item_id']
        
        canonical_id = None
        reason = None
        
        # 1. Try Exact Match
        if (raw_item_id, raw_name) in exact_match_map:
            canonical_id = exact_match_map[(raw_item_id, raw_name)]
            reason = "exact_match"
        # 2. Try Alias Match
        elif raw_name in ALIAS_TABLE:
            canonical_id = ALIAS_TABLE[raw_name]
            reason = "alias_match"
        # 3. Try Legacy ID Match
        elif raw_item_id in LEGACY_ID_TABLE:
            canonical_id = LEGACY_ID_TABLE[raw_item_id]
            reason = "legacy_id_map"
        else:
            reason = "excluded_unresolved"
            
        # 4. Check / Generate unique_item_id
        if canonical_id and reason != "excluded_unresolved":
            product_class = CANONICAL_MASTER[canonical_id]["class"]
            
            if pd.isna(unique_id) or str(unique_id).strip() == "":
                generated = generate_id(product_class)
                if generated:
                    unique_id = generated
                    reason = "generated_identifier"
                else:
                    reason = "excluded_unresolved_missing_uid"
                    canonical_id = None
            else:
                pattern = REGEX_RULES.get(product_class)
                if pattern and not re.match(pattern, str(unique_id)):
                    generated = generate_id(product_class)
                    if generated:
                        unique_id = generated
                        reason = "generated_identifier"
                    else:
                        reason = "excluded_unresolved_invalid_uid"
                        canonical_id = None

        new_row = row.copy()
        new_row['canonical_item_id'] = canonical_id
        new_row['unique_item_id'] = unique_id
        new_row['reason_code'] = reason
        
        if canonical_id:
            new_row['medicine_type'] = CANONICAL_MASTER[canonical_id]['type']
            new_row['temp_control'] = CANONICAL_MASTER[canonical_id]['temp']
            
        cleaned_rows.append(new_row)
        
    cleaned_df = pd.DataFrame(cleaned_rows)
    
    # Save the cleaned data
    cleaned_df.to_csv(output_csv_path, index=False)
    
    # Calculate stats
    stats = {
        "total_rows": int(len(df)),
        "exact_matches": int(len(cleaned_df[cleaned_df['reason_code'] == 'exact_match'])),
        "alias_matches": int(len(cleaned_df[cleaned_df['reason_code'] == 'alias_match'])),
        "legacy_mappings": int(len(cleaned_df[cleaned_df['reason_code'] == 'legacy_id_map'])),
        "generated_identifiers": int(len(cleaned_df[cleaned_df['reason_code'] == 'generated_identifier'])),
        "excluded_rows": int(len(cleaned_df[cleaned_df['reason_code'].str.startswith('excluded', na=False)])),
        "excluded_rate": float(len(cleaned_df[cleaned_df['reason_code'].str.startswith('excluded', na=False)]) / len(df)) if len(df) > 0 else 0.0,
        "reason_code_breakdown": {k: int(v) for k, v in cleaned_df['reason_code'].value_counts().to_dict().items()}
    }
    return stats
