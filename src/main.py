from __future__ import annotations
from dotenv import load_dotenv
load_dotenv()  # must be before importing graph/agents
from tracing import init_langsmith_tracing
init_langsmith_tracing()  # must be before importing graph/agents
from graph import build_graph


if __name__ == "__main__":
 
    app = build_graph()

    state = {
        "pdf_path": "data-for-enhancement/SeeWeeS Specialty Dispatch Playbook.md",
        "csv_path": "data-for-enhancement/Incoming_shipments_14d_multi_corridor.csv",
    }

    thread = {"configurable": {"thread_id": "1"}}
    
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
                exit(1)
        elif next_node == "human_dispatch_judge":
            print("\n[CHECKPOINT] AuditAgent has triggered a Safety Override!")
            print("Override Plan Proposed:")
            print(snapshot.values.get("override_plan", ""))
            ans = input("\nApprove this Override Plan? (y/n): ")
            if ans.lower() != 'y':
                print("Aborting execution.")
                exit(1)

    report_html = final_state.get("report_html", "")
    with open("baseline_report.html", "w") as f:
        f.write(report_html)
    print("\n=== REPORT GENERATED SUCCESSFULLY (Saved to baseline_report.html) ===\n")
    print(report_html[:1500])
