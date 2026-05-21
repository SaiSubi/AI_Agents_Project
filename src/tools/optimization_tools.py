import pandas as pd
import math

def allocate_resources(cleaned_csv_path, resource_csv_path):
    df_shipments = pd.read_csv(cleaned_csv_path)
    df_resources = pd.read_csv(resource_csv_path)
    
    # Filter to valid rows and planning days
    if 'reason_code' in df_shipments.columns:
        df_shipments = df_shipments[~df_shipments['reason_code'].str.startswith("excluded")]
    df_shipments = df_shipments[df_shipments['planning_day'].isin(['Day0', 'Day1'])]
    
    # Define Tiers based on medicine_type
    def get_tier(med_type):
        if med_type in ['Emergency Drug', 'Clinical Trial Drug', 'Monoclonal Antibody', 'Antiviral', 'Hormone']:
            return 'Tier 1'
        return 'Tier 2'
        
    df_shipments['tier'] = df_shipments['medicine_type'].apply(get_tier)
    df_shipments['is_cold'] = df_shipments['temp_control'].apply(lambda x: 'Cold' in str(x) or '(-20C)' in str(x))
    
    # Priority sorting (highest penalty first)
    def get_priority(row):
        score = 0
        if row['tier'] == 'Tier 1': score += 100
        else: score += 40
        if row['is_cold']: score += 80
        return score
        
    df_shipments['priority'] = df_shipments.apply(get_priority, axis=1)
    
    # Output structure
    plan = {
        'Day0': {'corridors': {}},
        'Day1': {'corridors': {}},
        'metrics': {
            'total_penalty': 0,
            'delayed_shipments': 0,
            'tier1_violations': 0,
            'tier2_violations': 0
        }
    }
    
    # Parse resources
    resources = {'Day0': {}, 'Day1': {}}
    for _, r in df_resources.iterrows():
        resources[r['day']][r['resource_type']] = r['available_count']
        
    # Day 0 Allocation
    day0_shipments = df_shipments[df_shipments['planning_day'] == 'Day0'].sort_values('priority', ascending=False)
    
    def pack_shipments(shipment_list, day):
        corridors = {}
        avail_drivers = resources[day].get('driver', 0)
        avail_std = resources[day].get('truck_standard', 0)
        avail_tmp = resources[day].get('truck_temp_controlled', 0)
        
        delayed = []
        
        for _, s in shipment_list.iterrows():
            c = s['corridor_id']
            if c not in corridors:
                corridors[c] = {'trucks': []}
                
            packed = False
            # Try existing open trucks
            for t in corridors[c]['trucks']:
                if len(t['shipments']) < 9:
                    if s['is_cold'] and t['type'] == 'temp_controlled':
                        t['shipments'].append(s)
                        packed = True
                        break
                    elif not s['is_cold'] and t['type'] == 'standard':
                        t['shipments'].append(s)
                        packed = True
                        break
            
            if not packed:
                # Need new truck
                if s['is_cold'] and avail_tmp > 0 and avail_drivers > 0:
                    avail_tmp -= 1
                    avail_drivers -= 1
                    corridors[c]['trucks'].append({'type': 'temp_controlled', 'shipments': [s]})
                    packed = True
                elif not s['is_cold'] and avail_std > 0 and avail_drivers > 0:
                    avail_std -= 1
                    avail_drivers -= 1
                    corridors[c]['trucks'].append({'type': 'standard', 'shipments': [s]})
                    packed = True
                # If we cannot pack because of constraints, we delay.
                
            if not packed:
                delayed.append(s)
                
        # Update plan
        for c in corridors:
            plan[day]['corridors'][c] = {
                'trucks_used': len(corridors[c]['trucks']),
                'std_trucks': sum(1 for t in corridors[c]['trucks'] if t['type'] == 'standard'),
                'tmp_trucks': sum(1 for t in corridors[c]['trucks'] if t['type'] == 'temp_controlled'),
                'shipments_delivered': sum(len(t['shipments']) for t in corridors[c]['trucks'])
            }
            
        return delayed
        
    delayed_from_0 = pack_shipments(day0_shipments, 'Day0')
    
    # Calculate Day0 penalties
    for _, s in pd.DataFrame(delayed_from_0).iterrows() if delayed_from_0 else []:
        plan['metrics']['delayed_shipments'] += 1
        plan['metrics']['total_penalty'] += 10 # Delay penalty
        if s['tier'] == 'Tier 1':
            plan['metrics']['total_penalty'] += 100
            plan['metrics']['tier1_violations'] += 1
        else:
            plan['metrics']['total_penalty'] += 40
            plan['metrics']['tier2_violations'] += 1
            
    # Day 1 Allocation
    day1_df = df_shipments[df_shipments['planning_day'] == 'Day1']
    if len(delayed_from_0) > 0:
        day1_shipments = pd.concat([day1_df, pd.DataFrame(delayed_from_0)]).sort_values('priority', ascending=False)
    else:
        day1_shipments = day1_df.sort_values('priority', ascending=False)
        
    if len(day1_shipments) > 0:
        delayed_from_1 = pack_shipments(day1_shipments, 'Day1')
    else:
        delayed_from_1 = []
        
    # Calculate Day 1 penalties for anything that couldn't fit on Day 1
    for _, s in pd.DataFrame(delayed_from_1).iterrows() if delayed_from_1 else []:
        plan['metrics']['delayed_shipments'] += 1
        plan['metrics']['total_penalty'] += 10
        if s['tier'] == 'Tier 1':
            plan['metrics']['total_penalty'] += 100
            plan['metrics']['tier1_violations'] += 1
        else:
            plan['metrics']['total_penalty'] += 40
            plan['metrics']['tier2_violations'] += 1
            
    # Cast metrics to int
    for k in plan['metrics']:
        plan['metrics'][k] = int(plan['metrics'][k])

            
    # Generate a string summary for the LLM
    summary = f"Optimization Summary:\n"
    summary += f"- Total Penalties Incurred: {plan['metrics']['total_penalty']}\n"
    summary += f"- Total Delayed Shipments: {plan['metrics']['delayed_shipments']}\n"
    summary += f"  - Tier 1 SLA Violations: {plan['metrics']['tier1_violations']}\n"
    summary += f"  - Tier 2 SLA Violations: {plan['metrics']['tier2_violations']}\n\n"
    
    summary += "Day 0 Allocation:\n"
    for c, data in plan['Day0']['corridors'].items():
        summary += f"  {c}: Delivered {data['shipments_delivered']} units using {data['std_trucks']} standard and {data['tmp_trucks']} temp-controlled trucks.\n"
        
    summary += "\nDay 1 Allocation:\n"
    for c, data in plan['Day1']['corridors'].items():
        summary += f"  {c}: Delivered {data['shipments_delivered']} units using {data['std_trucks']} standard and {data['tmp_trucks']} temp-controlled trucks.\n"
        
    if len(delayed_from_1) > 0:
        summary += f"\nCritical Issue: {len(delayed_from_1)} shipments could not be delivered on Day 1 due to resource exhaustion.\n"
        
    return plan, summary

if __name__ == "__main__":
    cleaned_csv = "/Users/saisubramanian/UCLA/Spring Quarter/Industry Seminar II/MSBA_AI_Agents_Demo-data-enhancement-seewees/data-for-enhancement/Incoming_shipments_14d_multi_corridor_cleaned.csv"
    resource_csv = "/Users/saisubramanian/UCLA/Spring Quarter/Industry Seminar II/MSBA_AI_Agents_Demo-data-enhancement-seewees/data-for-enhancement/Resource_availability_48h.csv"
    
    try:
        plan, summary = allocate_resources(cleaned_csv, resource_csv)
        print(summary)
    except Exception as e:
        print("Error testing optimization:", e)
