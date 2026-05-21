from __future__ import annotations
from typing import Dict, Any
from langchain_openai import ChatOpenAI
from prompts import PDF_CONTEXT_PROMPT, OPS_ANALYSIS_PROMPT, PLANNER_PROMPT, REPORT_PROMPT, DATA_CLEANING_PROMPT, AUDIT_PROMPT, OVERRIDE_PROMPT, WHATIF_PROMPT

llm = ChatOpenAI(
    model="gpt-4.1-mini",
    temperature=0.2,
    tags=["msba-demo", "multi-agent"],
    metadata={"repo": "MSBA_AI_Agents_Demo"}
)

def run_whatif_agent(scenario_text: str) -> str:
    return llm.invoke(WHATIF_PROMPT.format_messages(scenario_text=scenario_text)).content.strip()

def run_audit_agent(weather_risk: Dict[str, Any], optimization_summary: str) -> str:
    return llm.invoke(AUDIT_PROMPT.format_messages(
        weather_risk=weather_risk,
        optimization_summary=optimization_summary
    )).content.strip()

def run_override_agent(weather_risk: Dict[str, Any], optimization_summary: str) -> str:
    return llm.invoke(OVERRIDE_PROMPT.format_messages(
        weather_risk=weather_risk,
        optimization_summary=optimization_summary
    )).content

def run_cleaning_agent(cleaning_stats: Dict[str, Any]) -> str:
    return llm.invoke(DATA_CLEANING_PROMPT.format_messages(cleaning_stats=cleaning_stats)).content



def run_context_agent(snippets: str) -> str:
    return llm.invoke(PDF_CONTEXT_PROMPT.format_messages(snippets=snippets)).content

def run_ops_agent(summary: Dict[str, Any], kpis: Dict[str, Any], anomalies_md: str) -> str:
    return llm.invoke(OPS_ANALYSIS_PROMPT.format_messages(
        summary=summary, kpis=kpis, anomalies_md=anomalies_md
    )).content

def run_planner_agent(business_context: str, ops_insights: str, weather_risk: Dict[str, Any], optimization_summary: str) -> str:
    return llm.invoke(PLANNER_PROMPT.format_messages(
        business_context=business_context,
        ops_insights=ops_insights,
        weather_risk=weather_risk,
        optimization_summary=optimization_summary
    )).content

def run_report_agent(
    business_context: str,
    cleaning_summary: str,
    kpis: Dict[str, Any],
    anomaly_highlights: str,
    weather_risk: Dict[str, Any],
    dispatch_plan: str,
) -> str:
    return llm.invoke(REPORT_PROMPT.format_messages(
        business_context=business_context,
        cleaning_summary=cleaning_summary,
        kpis=kpis,
        anomaly_highlights=anomaly_highlights,
        weather_risk=weather_risk,
        dispatch_plan=dispatch_plan
    )).content
