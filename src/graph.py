from __future__ import annotations
import os
from typing import TypedDict, Dict, Any

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from dotenv import load_dotenv

from tools.pdf_tools import PdfRag
from tools.csv_tools import analyze_csv
from tools.weather_tools import get_weather_forecast, derive_dispatch_weather_risk
from tools.email_tools import send_email_smtp
from tools.data_cleaning_tools import clean_shipment_data
from tools.optimization_tools import allocate_resources
from agents import run_context_agent, run_ops_agent, run_planner_agent, run_report_agent, run_cleaning_agent, run_audit_agent, run_override_agent

load_dotenv()

class AppState(TypedDict, total=False):
    pdf_path: str
    csv_path: str
    cleaned_csv_path: str
    cleaning_stats: Dict[str, Any]
    cleaning_agent_summary: str
    resource_csv_path: str
    optimization_plan: Dict[str, Any]
    optimization_summary: str
    audit_decision: str
    override_plan: str

    business_context: str
    csv_summary: Dict[str, Any]
    csv_kpis: Dict[str, Any]
    anomalies_md: str
    ops_insights: str

    weather_forecast: Dict[str, Any]
    weather_risk: Dict[str, Any]

    dispatch_plan: str
    report_html: str


def node_pdf_context(state: AppState) -> AppState:
    rag = PdfRag(persist_dir="chroma_db")
    vectordb = rag.build(state["pdf_path"])
    retriever = rag.retriever(vectordb, k=6)

    query = "Extract KPI definitions, thresholds, SLAs, constraints, dispatch rules, exceptions."
    docs = retriever.invoke(query)
    snippets = "\n\n---\n\n".join(d.page_content for d in docs)

    business_context = run_context_agent(snippets)
    return {"business_context": business_context}


def node_data_cleaning(state: AppState) -> AppState:
    input_csv = state["csv_path"]
    output_csv = input_csv.replace(".csv", "_cleaned.csv")
    
    stats = clean_shipment_data(input_csv, output_csv)
    summary_text = run_cleaning_agent(stats)
    
    return {
        "cleaned_csv_path": output_csv,
        "cleaning_stats": stats,
        "cleaning_agent_summary": summary_text
    }


def node_csv_analysis(state: AppState) -> AppState:
    csv_to_analyze = state.get("cleaned_csv_path", state["csv_path"])
    res = analyze_csv(csv_to_analyze)

    anomalies_md = "(none detected or insufficient numeric data)"
    if not res.anomalies.empty:
        anomalies_md = res.anomalies.head(12).to_markdown(index=False)

    ops_insights = run_ops_agent(summary=res.summary, kpis=res.kpis, anomalies_md=anomalies_md)

    return {
        "csv_summary": res.summary,
        "csv_kpis": res.kpis,
        "anomalies_md": anomalies_md,
        "ops_insights": ops_insights,
    }


def node_weather(state: AppState) -> AppState:
    lat = os.getenv("WEATHER_LAT", "40.7282")
    lon = os.getenv("WEATHER_LON", "-74.0776")
    tz = os.getenv("WEATHER_TZ", "America/New_York")

    forecast = get_weather_forecast(lat, lon, tz)
    risk = derive_dispatch_weather_risk(forecast)
    return {"weather_forecast": forecast, "weather_risk": risk}


def node_planner(state: AppState) -> AppState:
    resource_csv = state.get("resource_csv_path", "data-for-enhancement/Resource_availability_48h.csv")
    cleaned_csv = state.get("cleaned_csv_path", state["csv_path"])
    
    opt_plan, opt_summary = allocate_resources(cleaned_csv, resource_csv)
    
    plan = run_planner_agent(
        business_context=state.get("business_context", ""),
        ops_insights=state.get("ops_insights", ""),
        weather_risk=state.get("weather_risk", {}),
        optimization_summary=opt_summary
    )
    return {
        "dispatch_plan": plan,
        "optimization_plan": opt_plan,
        "optimization_summary": opt_summary
    }


def node_report(state: AppState) -> AppState:
    html = run_report_agent(
        business_context=state.get("business_context", ""),
        cleaning_summary=state.get("cleaning_agent_summary", ""),
        kpis=state.get("csv_kpis", {}),
        anomaly_highlights=state.get("anomalies_md", "(none)"),
        weather_risk=state.get("weather_risk", {}),
        dispatch_plan=state.get("override_plan", "") or state.get("dispatch_plan", ""),
    )
    return {"report_html": html}

def node_human_cleaning_judge(state: AppState) -> AppState:
    return state

def node_human_dispatch_judge(state: AppState) -> AppState:
    return state

def node_audit(state: AppState) -> AppState:
    decision = run_audit_agent(state.get("weather_risk", {}), state.get("optimization_summary", ""))
    return {"audit_decision": decision}

def node_override(state: AppState) -> AppState:
    override_plan = run_override_agent(state.get("weather_risk", {}), state.get("optimization_summary", ""))
    return {"override_plan": override_plan}

def route_after_cleaning(state: AppState) -> str:
    stats = state.get("cleaning_stats", {})
    if stats.get("excluded_rate", 0) > 0.10:
        return "human_cleaning_judge"
    return "csv_analysis"

def route_after_audit(state: AppState) -> str:
    decision = state.get("audit_decision", "SAFE")
    if decision == "OVERRIDE":
        return "override"
    return "report"

def node_email(state: AppState) -> AppState:
    to_email = os.getenv("REPORT_EMAIL_TO", "").strip()
    if not to_email:
        print("REPORT_EMAIL_TO not set -> skipping email send.")
        return {}

    subject = "MSBA Ops Multi-Agent Dispatch Report"
    send_email_smtp(subject=subject, html_body=state["report_html"], to_email=to_email)
    return {}

def build_graph():
    g = StateGraph(AppState)

    g.add_node("pdf_context", node_pdf_context)
    g.add_node("data_cleaning", node_data_cleaning)
    g.add_node("human_cleaning_judge", node_human_cleaning_judge)
    g.add_node("csv_analysis", node_csv_analysis)
    g.add_node("weather", node_weather)
    g.add_node("planner", node_planner)
    g.add_node("audit", node_audit)
    g.add_node("override", node_override)
    g.add_node("human_dispatch_judge", node_human_dispatch_judge)
    g.add_node("report", node_report)
    g.add_node("email", node_email)

    g.set_entry_point("pdf_context")
    g.add_edge("pdf_context", "data_cleaning")
    g.add_conditional_edges("data_cleaning", route_after_cleaning)
    g.add_edge("human_cleaning_judge", "csv_analysis")
    g.add_edge("csv_analysis", "weather")
    g.add_edge("weather", "planner")
    g.add_edge("planner", "audit")
    g.add_conditional_edges("audit", route_after_audit)
    g.add_edge("override", "human_dispatch_judge")
    g.add_edge("human_dispatch_judge", "report")
    g.add_edge("report", "email")
    g.add_edge("email", END)

    memory = MemorySaver()
    return g.compile(checkpointer=memory, interrupt_before=["human_cleaning_judge", "human_dispatch_judge"])
