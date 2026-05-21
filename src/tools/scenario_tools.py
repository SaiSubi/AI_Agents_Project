import pandas as pd
import json

def apply_what_if_scenario(json_str: str, resource_csv: str, shipment_csv: str) -> tuple[str, str]:
    """
    Parses the JSON output from the WhatIfAgent and applies modifications
    to the underlying pandas dataframes, saving them as temporary files.
    """
    try:
        data = json.loads(json_str)
    except json.JSONDecodeError:
        print("Failed to decode JSON from WhatIfAgent. Using unmodified CSVs.")
        return resource_csv, shipment_csv

    # We will primarily modify the resource csv, as shipment additions are more complex 
    # and the prompt is restricted to resource changes.
    new_resource_csv = resource_csv.replace(".csv", "_whatif.csv")
    new_shipment_csv = shipment_csv.replace(".csv", "_whatif.csv")
    
    df_res = pd.read_csv(resource_csv)
    df_ship = pd.read_csv(shipment_csv)
    
    mods = data.get("resource_modifications", [])
    for mod in mods:
        day = mod.get("day")
        res_type = mod.get("resource_type")
        change = mod.get("change", 0)
        
        mask = (df_res["day"] == day) & (df_res["resource_type"] == res_type)
        if mask.any():
            df_res.loc[mask, "available_count"] += change
            # Ensure it doesn't go below 0
            df_res.loc[mask, "available_count"] = df_res.loc[mask, "available_count"].clip(lower=0)

    # Note: If shipment_modifications were passed, we could apply them here.
    
    df_res.to_csv(new_resource_csv, index=False)
    df_ship.to_csv(new_shipment_csv, index=False)
    
    return new_resource_csv, new_shipment_csv
