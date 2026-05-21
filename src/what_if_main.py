from dotenv import load_dotenv
load_dotenv()

from graph import build_graph
from agents import run_whatif_agent
from tools.scenario_tools import apply_what_if_scenario
import sys
import json

def main():
    print("\n--- SEU LOGISTICS WHAT-IF SCENARIO SIMULATOR ---")
    scenario_text = input("Enter a hypothetical scenario (e.g., 'What if we lose 2 drivers on Day 0?'):\n> ").strip()
    
    resource_csv = "data-for-enhancement/Resource_availability_48h.csv"
    shipment_csv = "data-for-enhancement/Incoming_shipments_14d_multi_corridor.csv"
    
    if scenario_text:
        print("\n[WhatIfAgent] Translating scenario into data modifications...")
        json_output = run_whatif_agent(scenario_text)
        print("[WhatIfAgent] Generated JSON:\n", json_output)
        
        resource_csv, shipment_csv = apply_what_if_scenario(
            json_output, 
            resource_csv, 
            shipment_csv
        )
        print(f"[System] Altered data files saved to:\n  - {resource_csv}\n  - {shipment_csv}\n")
    else:
        print("\nNo scenario entered. Proceeding with baseline data.")

    # Initialize Graph
    app = build_graph()

    state = {
        "pdf_path": "data-for-enhancement/SeeWeeS Specialty Dispatch Playbook.md",
        "csv_path": shipment_csv, # Either original or what-if
        "resource_csv_path": resource_csv, # Pass this explicitly
    }

    thread = {"configurable": {"thread_id": "whatif_1"}}
    
    print("Starting LangGraph execution...")
    final_state = None
    
    while True:
        events = app.stream(state if final_state is None else None, thread, stream_mode="values")
        for event in events:
            final_state = event
            
        snapshot = app.get_state(thread)
        if not snapshot.next:
            break # Finished!
            
        next_node = snapshot.next[0]
        if next_node == "human_cleaning_judge":
            stats = snapshot.values.get("cleaning_stats", {})
            print(f"\n[CHECKPOINT] High Exclusion Rate Detected: {stats.get('excluded_rate', 0)*100:.1f}%")
            ans = input("Proceed with planning? (y/n): ")
            if ans.lower() != 'y':
                print("Aborting execution.")
                sys.exit(1)
        elif next_node == "human_dispatch_judge":
            print("\n[CHECKPOINT] AuditAgent has triggered a Safety Override!")
            print("Override Plan Proposed:")
            print(snapshot.values.get("override_plan", ""))
            ans = input("\nApprove this Override Plan? (y/n): ")
            if ans.lower() != 'y':
                print("Aborting execution.")
                sys.exit(1)

    report_html = final_state.get("report_html", "")
    with open("whatif_report.html", "w") as f:
        f.write(report_html)
    print("\n=== REPORT GENERATED SUCCESSFULLY (Saved to whatif_report.html) ===\n")
    print(report_html[:1500])

if __name__ == "__main__":
    main()
