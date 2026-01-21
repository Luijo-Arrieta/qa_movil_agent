#!/usr/bin/env python3
"""
Generate Dashboard Data

Parses pytest log files and generates JSON data for the static dashboard.

Usage:
    poetry run python scripts/generate_dashboard.py
    poetry run python scripts/generate_dashboard.py --log reports/logs/pytest_20260120_154421.log
"""

import json
import re
import shutil
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Optional
import argparse


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class TokenUsage:
    prompt: int = 0
    completion: int = 0
    total: int = 0


@dataclass
class AICall:
    call_number: int
    call_type: str  # "decide_action" or "check_completion"
    provider: str = ""
    model: str = ""
    duration_ms: int = 0
    tokens: TokenUsage = field(default_factory=TokenUsage)
    system_prompt_chars: int = 0
    context_chars: int = 0
    decision: Optional[dict] = None


@dataclass
class ToolCall:
    tool: str
    tool_id: str = ""
    args: dict = field(default_factory=dict)
    status: str = ""  # "success" or "error"
    result: str = ""
    duration_ms: int = 0


@dataclass
class LoopIteration:
    iteration_number: int
    ui_elements_count: int = 0
    ui_stability_ms: int = 0
    ai_calls: list = field(default_factory=list)
    tool_calls: list = field(default_factory=list)


@dataclass
class StepExecution:
    index: int
    description: str
    status: str = "pending"  # "passed", "failed", "pending"
    duration_ms: int = 0
    attempts: int = 0
    warnings_count: int = 0
    loop_iterations: list = field(default_factory=list)
    screenshots: list = field(default_factory=list)


@dataclass
class TestPlan:
    total_steps: int = 0
    objective: str = ""
    steps: list = field(default_factory=list)


@dataclass
class TestMetadata:
    timestamp_start: str = ""
    timestamp_end: str = ""
    duration_seconds: float = 0.0
    status: str = "unknown"
    ai_provider: str = ""
    ai_model: str = ""
    qai_version: str = ""
    device_name: str = ""
    app_package: str = ""
    log_file_path: str = ""
    objective: str = ""


@dataclass
class CostMetrics:
    token_prices: dict = field(default_factory=dict)
    trm: dict = field(default_factory=dict)
    total_usd: float = 0.0
    total_cop: float = 0.0
    per_step_costs: list = field(default_factory=list)


@dataclass
class ExecutionSummary:
    total_steps: int = 0
    completed_steps: int = 0
    failed_steps: int = 0
    total_actions: int = 0
    total_ai_calls: int = 0
    total_tokens: int = 0
    total_tokens_prompt: int = 0
    total_tokens_completion: int = 0


@dataclass
class TestRun:
    id: str
    metadata: TestMetadata = field(default_factory=TestMetadata)
    plan: TestPlan = field(default_factory=TestPlan)
    steps: list = field(default_factory=list)
    summary: ExecutionSummary = field(default_factory=ExecutionSummary)
    costs: CostMetrics = field(default_factory=CostMetrics)
    available_tools: list = field(default_factory=list)


# =============================================================================
# Regex Patterns
# =============================================================================

PATTERNS = {
    # Metadata (logs have timestamp prefix like "2026-01-20 17:35:06.212 - src.v2.ai_orchestrator - INFO - ")
    "qai_version": re.compile(r"Inicializando orquestador de IA \((QAI V\d+)"),
    "ai_provider": re.compile(r"AI_ORCHESTRATOR: Proveedor seleccionado: (\w+)"),
    "ai_model": re.compile(r"Cliente \w+ configurado con modelo: (.+)"),
    "session_id": re.compile(r"Driver activo con session_id: ([\w-]+)"),

    # Plan (from TEST_RUNNER logs)
    "total_steps": re.compile(r"TEST_RUNNER: Total de pasos en el plan: (\d+)"),
    "objective": re.compile(r"TEST_RUNNER: Objetivo general: '(.+?)'"),
    "plan_step": re.compile(r"INFO -\s+(\d+)\. (.+)$", re.MULTILINE),

    # Step execution
    "step_start": re.compile(r"▶ PASO (\d+)/(\d+): (.+)"),
    "step_time_start": re.compile(r"Iniciando paso \d+ a las (\d+:\d+:\d+\.\d+)"),
    "step_complete": re.compile(r"✅ PASO (\d+) COMPLETADO en ([\d.]+)s"),
    "step_failed": re.compile(r"❌ FALLO EN PASO (\d+)"),

    # Loop iterations
    "loop_iteration": re.compile(r"Loop agéntico iteración (\d+)"),
    "ui_elements": re.compile(r"(\d+) elementos encontrados en (\d+)ms"),
    "ui_stable": re.compile(r"UI estable después de ([\d.]+)s"),

    # AI calls
    "ai_call_number": re.compile(r"AI_ORCHESTRATOR: Llamada #(\d+)"),
    "ai_call_completitud": re.compile(r"AI_ORCHESTRATOR: Llamada de completitud #(\d+)"),
    "tokens": re.compile(r"Tokens - prompt: (\d+), completion: (\d+), total: (\d+)"),
    "ai_duration": re.compile(r"Respuesta (?:de completitud )?recibida en (\d+)ms"),
    "system_prompt_chars": re.compile(r"Longitud del system prompt: (\d+) chars"),
    "context_chars": re.compile(r"Longitud del contexto: (\d+) chars"),
    "ai_decision": re.compile(r"Decisión -> (\w+)\((.+?)\)"),

    # Tool calls
    "tool_call_start": re.compile(r"┌─ TOOL CALL"),
    "tool_name": re.compile(r"│ Tool: (\w+)"),
    "tool_args": re.compile(r"│ Args: (\{.+?\})"),
    "tool_id": re.compile(r"│ ID: (.+)"),
    "tool_status": re.compile(r"│ Status: (Success|Error|Inprogress)"),
    "tool_result": re.compile(r"│ Result: (.+)"),
    "tool_duration": re.compile(r"│ Duration: (\d+)ms"),

    # Available tools
    "available_tools": re.compile(r"Herramientas disponibles: \[(.+?)\]"),

    # Warnings
    "warning": re.compile(r"WARNING|⚠️"),

    # Session timestamp from log filename or log header
    "log_timestamp": re.compile(r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})"),
}


# =============================================================================
# Parser Class
# =============================================================================

class LogParser:
    """Parse pytest log files into structured TestRun data."""

    def __init__(self, log_path: Path):
        self.log_path = log_path
        self.content = ""
        self.lines = []
        self.test_run: Optional[TestRun] = None

    def parse(self) -> TestRun:
        """Parse the log file and return a TestRun object."""
        self.content = self.log_path.read_text(encoding="utf-8")
        self.lines = self.content.split("\n")

        # Extract ID from filename
        log_id = self.log_path.stem  # e.g., "pytest_20260120_154421"
        self.test_run = TestRun(id=log_id)
        self.test_run.metadata.log_file_path = str(self.log_path)

        # Parse sections
        self._parse_metadata()
        self._parse_plan()
        self._parse_steps()
        self._parse_available_tools()
        self._calculate_summary()

        return self.test_run

    def _parse_metadata(self):
        """Extract metadata from the log header."""
        meta = self.test_run.metadata

        # QAI Version
        match = PATTERNS["qai_version"].search(self.content)
        if match:
            meta.qai_version = match.group(1)

        # AI Provider
        match = PATTERNS["ai_provider"].search(self.content)
        if match:
            meta.ai_provider = match.group(1)

        # AI Model
        match = PATTERNS["ai_model"].search(self.content)
        if match:
            meta.ai_model = match.group(1)

        # Session ID (as device identifier)
        match = PATTERNS["session_id"].search(self.content)
        if match:
            meta.device_name = match.group(1)[:8]  # First 8 chars

        # Objective
        match = PATTERNS["objective"].search(self.content)
        if match:
            meta.objective = match.group(1)

        # Extract timestamp from filename
        # Format: pytest_YYYYMMDD_HHMMSS
        parts = self.test_run.id.split("_")
        if len(parts) >= 3:
            date_str = parts[1]
            time_str = parts[2]
            try:
                dt = datetime.strptime(f"{date_str}_{time_str}", "%Y%m%d_%H%M%S")
                meta.timestamp_start = dt.isoformat()
            except ValueError:
                pass

    def _parse_plan(self):
        """Extract test plan from the log."""
        plan = self.test_run.plan

        # Total steps
        match = PATTERNS["total_steps"].search(self.content)
        if match:
            plan.total_steps = int(match.group(1))

        # Objective
        match = PATTERNS["objective"].search(self.content)
        if match:
            plan.objective = match.group(1)
            self.test_run.metadata.objective = match.group(1)

        # Individual steps from plan listing
        # Look for the plan section - format is "INFO -   1. Step description"
        plan_section_match = re.search(
            r"Plan de prueba:(.*?)(?=\n\n|\n.*════)",
            self.content,
            re.DOTALL
        )
        if plan_section_match:
            plan_text = plan_section_match.group(1)
            for match in PATTERNS["plan_step"].finditer(plan_text):
                step_index = int(match.group(1))
                step_desc = match.group(2).strip()
                plan.steps.append({
                    "index": step_index,
                    "description": step_desc
                })

    def _parse_steps(self):
        """Parse step executions."""
        # Find all step starts
        step_starts = list(PATTERNS["step_start"].finditer(self.content))

        for i, step_match in enumerate(step_starts):
            step_index = int(step_match.group(1))
            total_steps = int(step_match.group(2))
            step_desc = step_match.group(3)

            # Determine end position (next step start or end of file)
            start_pos = step_match.start()
            if i + 1 < len(step_starts):
                end_pos = step_starts[i + 1].start()
            else:
                end_pos = len(self.content)

            step_content = self.content[start_pos:end_pos]

            # Parse step
            step = self._parse_single_step(step_index, step_desc, step_content)
            self.test_run.steps.append(step)

        # Determine overall status
        if self.test_run.steps:
            failed_count = sum(1 for s in self.test_run.steps if s["status"] == "failed")
            self.test_run.metadata.status = "failed" if failed_count > 0 else "passed"

    def _parse_single_step(self, index: int, description: str, content: str) -> dict:
        """Parse a single step's content."""
        step = StepExecution(index=index, description=description)

        # Check if completed or failed
        complete_match = PATTERNS["step_complete"].search(content)
        failed_match = PATTERNS["step_failed"].search(content)

        if complete_match:
            step.status = "passed"
            step.duration_ms = int(float(complete_match.group(2)) * 1000)
        elif failed_match:
            step.status = "failed"

        # Count warnings
        step.warnings_count = len(PATTERNS["warning"].findall(content))

        # Parse loop iterations
        loop_matches = list(PATTERNS["loop_iteration"].finditer(content))
        for j, loop_match in enumerate(loop_matches):
            loop_num = int(loop_match.group(1))

            # Determine loop content boundaries
            loop_start = loop_match.start()
            if j + 1 < len(loop_matches):
                loop_end = loop_matches[j + 1].start()
            else:
                loop_end = len(content)

            loop_content = content[loop_start:loop_end]
            iteration = self._parse_loop_iteration(loop_num, loop_content)
            step.loop_iterations.append(asdict(iteration))

        return asdict(step)

    def _parse_loop_iteration(self, iteration_num: int, content: str) -> LoopIteration:
        """Parse a single loop iteration."""
        iteration = LoopIteration(iteration_number=iteration_num)

        # UI elements count
        ui_match = PATTERNS["ui_elements"].search(content)
        if ui_match:
            iteration.ui_elements_count = int(ui_match.group(1))

        # UI stability time
        stable_match = PATTERNS["ui_stable"].search(content)
        if stable_match:
            iteration.ui_stability_ms = int(float(stable_match.group(1)) * 1000)

        # Parse AI calls
        iteration.ai_calls = self._parse_ai_calls(content)

        # Parse tool calls
        iteration.tool_calls = self._parse_tool_calls(content)

        return iteration

    def _parse_ai_calls(self, content: str) -> list:
        """Parse AI orchestrator calls from content."""
        ai_calls = []

        # Find decision calls (Llamada #N)
        for match in PATTERNS["ai_call_number"].finditer(content):
            call_num = int(match.group(1))
            call_start = match.start()

            # Find the section for this call (until next call or end)
            next_call = PATTERNS["ai_call_number"].search(content, call_start + 1)
            next_completitud = PATTERNS["ai_call_completitud"].search(content, call_start + 1)

            if next_call and next_completitud:
                call_end = min(next_call.start(), next_completitud.start())
            elif next_call:
                call_end = next_call.start()
            elif next_completitud:
                call_end = next_completitud.start()
            else:
                call_end = len(content)

            call_content = content[call_start:call_end]
            ai_call = self._parse_single_ai_call(call_num, "decide_action", call_content)
            ai_calls.append(asdict(ai_call))

        # Find completitud calls
        for match in PATTERNS["ai_call_completitud"].finditer(content):
            call_num = int(match.group(1))
            call_start = match.start()

            # Find end of this call section
            next_match = PATTERNS["ai_call_completitud"].search(content, call_start + 1)
            call_end = next_match.start() if next_match else len(content)

            call_content = content[call_start:call_end]
            ai_call = self._parse_single_ai_call(call_num, "check_completion", call_content)
            ai_calls.append(asdict(ai_call))

        return ai_calls

    def _parse_single_ai_call(self, call_num: int, call_type: str, content: str) -> AICall:
        """Parse a single AI call."""
        ai_call = AICall(call_number=call_num, call_type=call_type)

        # Tokens
        tokens_match = PATTERNS["tokens"].search(content)
        if tokens_match:
            ai_call.tokens = TokenUsage(
                prompt=int(tokens_match.group(1)),
                completion=int(tokens_match.group(2)),
                total=int(tokens_match.group(3))
            )

        # Duration
        duration_match = PATTERNS["ai_duration"].search(content)
        if duration_match:
            ai_call.duration_ms = int(duration_match.group(1))

        # Context sizes
        sys_prompt_match = PATTERNS["system_prompt_chars"].search(content)
        if sys_prompt_match:
            ai_call.system_prompt_chars = int(sys_prompt_match.group(1))

        ctx_match = PATTERNS["context_chars"].search(content)
        if ctx_match:
            ai_call.context_chars = int(ctx_match.group(1))

        # Decision
        decision_match = PATTERNS["ai_decision"].search(content)
        if decision_match:
            tool_name = decision_match.group(1)
            args_str = decision_match.group(2)
            try:
                # Try to parse args as dict
                args = eval(f"dict({args_str})")
            except:
                args = {"raw": args_str}
            ai_call.decision = {"tool": tool_name, "args": args}

        return ai_call

    def _parse_tool_calls(self, content: str) -> list:
        """Parse tool calls from content."""
        tool_calls = []

        # Find tool call blocks
        tool_starts = list(PATTERNS["tool_call_start"].finditer(content))

        for i, match in enumerate(tool_starts):
            start_pos = match.start()
            # Find end (next tool call or reasonable boundary)
            if i + 1 < len(tool_starts):
                end_pos = tool_starts[i + 1].start()
            else:
                # Look for closing box or next section
                end_pos = start_pos + 2000  # Reasonable limit
                if end_pos > len(content):
                    end_pos = len(content)

            tool_content = content[start_pos:end_pos]
            tool_call = self._parse_single_tool_call(tool_content)
            if tool_call:
                tool_calls.append(asdict(tool_call))

        return tool_calls

    def _parse_single_tool_call(self, content: str) -> Optional[ToolCall]:
        """Parse a single tool call block."""
        name_match = PATTERNS["tool_name"].search(content)
        if not name_match:
            return None

        tool_call = ToolCall(tool=name_match.group(1))

        # Tool ID
        id_match = PATTERNS["tool_id"].search(content)
        if id_match:
            tool_call.tool_id = id_match.group(1)

        # Args
        args_match = PATTERNS["tool_args"].search(content)
        if args_match:
            try:
                tool_call.args = json.loads(args_match.group(1).replace("'", '"'))
            except:
                tool_call.args = {"raw": args_match.group(1)}

        # Status (get the last one, which is the final status)
        status_matches = list(PATTERNS["tool_status"].finditer(content))
        if status_matches:
            final_status = status_matches[-1].group(1).lower()
            tool_call.status = final_status

        # Result
        result_match = PATTERNS["tool_result"].search(content)
        if result_match:
            tool_call.result = result_match.group(1)

        # Duration
        duration_match = PATTERNS["tool_duration"].search(content)
        if duration_match:
            tool_call.duration_ms = int(duration_match.group(1))

        return tool_call

    def _parse_available_tools(self):
        """Extract the list of available tools."""
        match = PATTERNS["available_tools"].search(self.content)
        if match:
            tools_str = match.group(1)
            # Parse the list of tool names
            tools = re.findall(r"'(\w+)'", tools_str)
            self.test_run.available_tools = tools

    def _calculate_summary(self):
        """Calculate summary statistics."""
        summary = self.test_run.summary
        summary.total_steps = len(self.test_run.steps)

        total_tokens = 0
        total_tokens_prompt = 0
        total_tokens_completion = 0
        total_ai_calls = 0
        total_tool_calls = 0

        for step in self.test_run.steps:
            if step["status"] == "passed":
                summary.completed_steps += 1
            elif step["status"] == "failed":
                summary.failed_steps += 1

            for iteration in step.get("loop_iterations", []):
                for ai_call in iteration.get("ai_calls", []):
                    total_ai_calls += 1
                    tokens = ai_call.get("tokens", {})
                    total_tokens += tokens.get("total", 0)
                    total_tokens_prompt += tokens.get("prompt", 0)
                    total_tokens_completion += tokens.get("completion", 0)

                total_tool_calls += len(iteration.get("tool_calls", []))

        summary.total_ai_calls = total_ai_calls
        summary.total_tokens = total_tokens
        summary.total_tokens_prompt = total_tokens_prompt
        summary.total_tokens_completion = total_tokens_completion
        summary.total_actions = total_tool_calls

        # Calculate duration
        if self.test_run.steps:
            total_duration_ms = sum(s.get("duration_ms", 0) for s in self.test_run.steps)
            self.test_run.metadata.duration_seconds = total_duration_ms / 1000


# =============================================================================
# Cost Calculator
# =============================================================================

def load_config(config_path: Path) -> dict:
    """Load configuration from JSON file."""
    if config_path.exists():
        return json.loads(config_path.read_text(encoding="utf-8"))
    return {}


def calculate_costs(test_run: TestRun, config: dict) -> None:
    """Calculate token costs based on config."""
    costs = test_run.costs

    # Get pricing for the provider/model
    provider = test_run.metadata.ai_provider.lower()
    model = test_run.metadata.ai_model

    prices = config.get("token_prices", {}).get(provider, {}).get(model, {})
    if not prices:
        # Default prices
        prices = {
            "input_per_million": 0.14,
            "output_per_million": 0.28,
            "price_date": datetime.now().strftime("%Y-%m-%d")
        }

    costs.token_prices = prices

    # TRM
    trm = config.get("trm", {"usd_to_cop": 4150, "date": datetime.now().strftime("%Y-%m-%d")})
    costs.trm = trm

    # Calculate costs
    summary = test_run.summary
    input_cost = (summary.total_tokens_prompt / 1_000_000) * prices.get("input_per_million", 0)
    output_cost = (summary.total_tokens_completion / 1_000_000) * prices.get("output_per_million", 0)

    costs.total_usd = round(input_cost + output_cost, 6)
    costs.total_cop = round(costs.total_usd * trm.get("usd_to_cop", 4150), 2)

    # Per-step costs
    for step in test_run.steps:
        step_tokens = 0
        for iteration in step.get("loop_iterations", []):
            for ai_call in iteration.get("ai_calls", []):
                step_tokens += ai_call.get("tokens", {}).get("total", 0)

        step_input_cost = (step_tokens * 0.6 / 1_000_000) * prices.get("input_per_million", 0)  # Approx 60% prompt
        step_output_cost = (step_tokens * 0.4 / 1_000_000) * prices.get("output_per_million", 0)  # Approx 40% completion

        costs.per_step_costs.append({
            "step_index": step["index"],
            "tokens": step_tokens,
            "cost_usd": round(step_input_cost + step_output_cost, 6)
        })


# =============================================================================
# Main Functions
# =============================================================================

def dataclass_to_dict(obj):
    """Recursively convert dataclass to dict."""
    if hasattr(obj, "__dataclass_fields__"):
        return {k: dataclass_to_dict(v) for k, v in asdict(obj).items()}
    elif isinstance(obj, list):
        return [dataclass_to_dict(i) for i in obj]
    elif isinstance(obj, dict):
        return {k: dataclass_to_dict(v) for k, v in obj.items()}
    return obj


def generate_dashboard(log_path: Path, output_dir: Path, config: dict) -> dict:
    """Generate dashboard data from a log file."""
    print(f"Parsing: {log_path}")

    parser = LogParser(log_path)
    test_run = parser.parse()

    # Calculate costs
    calculate_costs(test_run, config)

    # Convert to dict
    run_data = dataclass_to_dict(test_run)

    # Save to runs directory
    runs_dir = output_dir / "data" / "runs"
    runs_dir.mkdir(parents=True, exist_ok=True)

    run_file = runs_dir / f"{test_run.id}.json"
    run_file.write_text(json.dumps(run_data, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"  Saved: {run_file}")

    return run_data


def update_index(output_dir: Path, runs: list) -> None:
    """Update the index.json file with all runs."""
    index_data = {
        "generated_at": datetime.now().isoformat(),
        "total_runs": len(runs),
        "runs": [
            {
                "id": r["id"],
                "status": r["metadata"]["status"],
                "timestamp": r["metadata"]["timestamp_start"],
                "duration_seconds": r["metadata"]["duration_seconds"],
                "objective": r["metadata"]["objective"][:100] + "..." if len(r["metadata"].get("objective", "")) > 100 else r["metadata"].get("objective", ""),
                "ai_provider": r["metadata"]["ai_provider"],
                "ai_model": r["metadata"]["ai_model"],
                "total_steps": r["summary"]["total_steps"],
                "completed_steps": r["summary"]["completed_steps"],
                "total_tokens": r["summary"]["total_tokens"],
                "cost_usd": r["costs"]["total_usd"],
            }
            for r in runs
        ]
    }

    index_file = output_dir / "data" / "index.json"
    index_file.parent.mkdir(parents=True, exist_ok=True)
    index_file.write_text(json.dumps(index_data, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Updated index: {index_file}")


def create_default_config(output_dir: Path) -> dict:
    """Create default config.json if it doesn't exist."""
    config_file = output_dir / "data" / "config.json"

    if config_file.exists():
        return json.loads(config_file.read_text(encoding="utf-8"))

    config = {
        "token_prices": {
            "openai": {
                "gpt-4o": {"input_per_million": 2.50, "output_per_million": 10.00, "price_date": "2026-01-20"},
                "gpt-4o-mini": {"input_per_million": 0.15, "output_per_million": 0.60, "price_date": "2026-01-20"}
            },
            "anthropic": {
                "claude-3-5-sonnet-20241022": {"input_per_million": 3.00, "output_per_million": 15.00, "price_date": "2026-01-20"}
            },
            "deepseek": {
                "deepseek-chat": {"input_per_million": 0.14, "output_per_million": 0.28, "price_date": "2026-01-20"}
            }
        },
        "trm": {
            "usd_to_cop": 4150.00,
            "date": "2026-01-20"
        }
    }

    config_file.parent.mkdir(parents=True, exist_ok=True)
    config_file.write_text(json.dumps(config, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Created default config: {config_file}")

    return config


def main():
    parser = argparse.ArgumentParser(description="Generate dashboard data from pytest logs")
    parser.add_argument("--log", type=str, help="Specific log file to parse")
    parser.add_argument("--all", action="store_true", help="Parse all logs in reports/logs/")
    args = parser.parse_args()

    # Paths
    project_root = Path(__file__).parent.parent
    logs_dir = project_root / "reports" / "logs"
    output_dir = project_root / "reports" / "dashboard"

    # Ensure output directory exists
    output_dir.mkdir(parents=True, exist_ok=True)

    # Load or create config
    config = create_default_config(output_dir)

    # Determine which logs to parse
    if args.log:
        log_files = [Path(args.log)]
    elif args.all:
        log_files = list(logs_dir.glob("pytest_*.log"))
    else:
        # Parse only the most recent log by default
        log_files = sorted(logs_dir.glob("pytest_*.log"), reverse=True)[:1]

    if not log_files:
        print("No log files found!")
        return

    # Parse logs
    runs = []
    for log_file in log_files:
        if log_file.exists():
            try:
                run_data = generate_dashboard(log_file, output_dir, config)
                runs.append(run_data)
            except Exception as e:
                print(f"  Error parsing {log_file}: {e}")

    # Update index
    if runs:
        update_index(output_dir, runs)

    print(f"\nDashboard data generated in: {output_dir}")
    print(f"Open reports/dashboard/index.html in a browser to view")


if __name__ == "__main__":
    main()
