# SeeWeeS Multi-Agent Dispatch System

This repository contains an advanced LangGraph-based multi-agent system designed to optimize specialty medical shipments for the SeeWeeS logistics network. 

The system implements 5 out of 5 Focus Areas requested by the operational Playbook:
1. Deterministic Data Cleaning (Cross-referencing Item Master Appendix)
2. Mathematical Resource Allocation Optimization
3. AI Safety Audit Loops
4. Human-in-the-Loop Checkpoints
5. Interactive "What-If" Scenario Simulation

## Setup & Deployment Guide

### 1. Prerequisites
Ensure you have Python 3.10+ installed.
You will need API keys for:
- OpenAI (`OPENAI_API_KEY`)
- LangSmith (`LANGCHAIN_API_KEY`)

### 2. Installation
Clone this repository and open the project directory in your terminal.
Set up a Python virtual environment:
```bash
python3 -m venv .venv
source .venv/bin/activate
```

Install the dependencies:
```bash
pip install -r requirements.txt
```

### 3. Environment Variables
Copy the `.env.example` file and rename it to `.env`:
```bash
cp .env.example .env
```
Open the `.env` file and insert your API keys and SMTP email credentials.

## Execution

### Run the Baseline Optimizer
To run the primary dispatch simulation (which cleans the 14-day CSV and mathematically loads the limited pool of trucks for Day 0 and Day 1):
```bash
python src/main.py
```
*Note: If the Audit Agent detects a weather risk or massive SLA penalty, execution will pause in the terminal and wait for your human approval.*

### Run the "What-If" Scenario Simulator
To run the interactive simulator that allows you to verbally alter the fabric of the simulation (e.g. simulating a truck breakdown or missing drivers):
```bash
python src/what_if_main.py
```
When prompted, type your hypothetical scenario in natural language and press Enter.

## Documentation
For a complete breakdown of the architecture, agents, and business value, please refer to the `final_project_report.pdf` included in this repository.
