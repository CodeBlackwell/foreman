#!/usr/bin/env python3
"""
Ralph - Autonomous Coding Agent Runner

Runs Claude CLI in a loop to complete tasks from a PRD file.
"""

import argparse
import re
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

try:
    from tqdm import tqdm
except ImportError:
    print("Error: tqdm is required. Install with: pip install tqdm")
    sys.exit(1)


@dataclass
class TaskProgress:
    """Track task completion status."""
    total: int
    completed: int

    @property
    def remaining(self) -> int:
        return self.total - self.completed

    @property
    def percentage(self) -> float:
        return (self.completed / self.total * 100) if self.total > 0 else 0.0


def format_duration(seconds: float) -> str:
    """Format seconds as HH:MM:SS."""
    hours, remainder = divmod(int(seconds), 3600)
    minutes, secs = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


class Ralph:
    """Autonomous coding agent runner."""

    # Three-layer completion tags (distinct per layer to prevent false positives)
    COMPLETION_MARKER = "<promise>COMPLETE</promise>"  # Legacy (solo mode stdout)
    DELIVERED_TAG = "<delivered>COMPLETE</delivered>"   # Agent self-report
    VERIFIED_TAG = "<verified>COMPLETE</verified>"      # Reviewer-confirmed

    def __init__(self, target: Path, max_iterations: int, sleep_seconds: int,
                 army: bool = False):
        self.max_iterations = max_iterations
        self.sleep_seconds = sleep_seconds
        self.army_mode = army
        self.start_time = time.time()

        # Resolve paths
        self.prd_file, self.progress_file, self.target_dir = self._resolve_paths(target)
        self.timing_log = self.target_dir / "ralph_timing.log"

        # Ensure progress file exists (army agents have individual files)
        if not self.army_mode:
            self._ensure_progress_file()

        # Track initial state
        self.initial_progress = self.count_tasks()

    def _resolve_paths(self, target: Path) -> tuple[Path, Path, Path]:
        """Resolve PRD file, progress file, and target directory from input."""
        target = target.resolve()

        if target.is_file():
            target_dir = target.parent
            if target.name == "PRD.md":
                prd_file = target
                progress_file = target_dir / "progress.txt"
            elif target.name == "progress.txt":
                prd_file = target_dir / "PRD.md"
                progress_file = target
            else:
                # Assume it's a PRD-like file
                prd_file = target
                progress_file = target_dir / "progress.txt"
        elif target.is_dir():
            target_dir = target
            prd_file = target_dir / "PRD.md"
            progress_file = target_dir / "progress.txt"
        else:
            print(f"Error: '{target}' is not a valid file or directory")
            sys.exit(1)

        if not prd_file.exists():
            print(f"Error: PRD file not found at {prd_file}")
            sys.exit(1)

        return prd_file, progress_file, target_dir

    def _ensure_progress_file(self) -> None:
        """Create progress.txt from PRD gate structure if it doesn't exist."""
        if not self.progress_file.exists():
            print(f"Note: Creating progress.txt at {self.progress_file}")
            self.progress_file.write_text(self._build_progress_from_prd(), encoding="utf-8")

    def _build_progress_from_prd(self) -> str:
        """Parse PRD gate/story structure and generate a pre-populated progress.txt."""
        content = self.prd_file.read_text(encoding="utf-8")

        # Extract stories: ### US-NNN: Title lines, with optional **Agent:** on next line
        story_pattern = re.compile(
            r"^### (US-\d+): (.+)$\n\*\*Agent:\*\* `([^`]+)`",
            re.MULTILINE,
        )
        # Extract gate headers: ## GATE N — Name
        gate_pattern = re.compile(r"^## (GATE \d+)\s*[—–-]\s*(.+)$", re.MULTILINE)

        gates = list(gate_pattern.finditer(content))
        stories = list(story_pattern.finditer(content))

        if not gates or not stories:
            # Fallback for non-gated PRDs
            return (
                "# Progress Log\n\n"
                "## Learnings\n"
                "(Patterns discovered during implementation)\n\n"
                "---\n"
            )

        # Build story tracker grouped by gate
        lines = [
            "# Progress Log\n",
            "## Summary",
            f"- **Total Stories:** {len(stories)} (US-001 through US-{len(stories):03d})",
            "- **Completed:** 0",
            "- **In Progress:** 0",
            "- **Status:** NOT STARTED\n",
            "## Story Tracker\n",
        ]

        # Map each story to its gate by position in file
        for gi, gate_match in enumerate(gates):
            gate_id = gate_match.group(1)
            gate_name = gate_match.group(2).strip()
            gate_start = gate_match.start()
            gate_end = gates[gi + 1].start() if gi + 1 < len(gates) else len(content)

            lines.append(f"### {gate_id} — {gate_name}")
            for story in stories:
                if gate_start <= story.start() < gate_end:
                    sid, title, agent = story.group(1), story.group(2).strip(), story.group(3)
                    lines.append(f"- [ ] {sid}: {title} (`{agent}`)")
            lines.append("")

        lines.extend([
            "---\n",
            "## Gate Completion Log",
            "(Appended by Ralph as gates complete)\n",
            "---\n",
            "## Learnings",
            "(Patterns discovered during implementation)\n",
            "---\n",
        ])
        return "\n".join(lines)

    def count_tasks(self) -> TaskProgress:
        """Count completed and total tasks from PRD file (or progress files in army mode)."""
        if self.army_mode:
            return self._count_army_tasks()
        content = self.prd_file.read_text(encoding="utf-8")
        total = len(re.findall(r"- \[ \]|- \[x\]", content))
        completed = len(re.findall(r"- \[x\]", content))
        return TaskProgress(total=total, completed=completed)

    def _count_army_tasks(self) -> TaskProgress:
        """Count tasks across all agent progress files."""
        progress_dir = self.target_dir / "progress"
        total = completed = 0
        for pf in progress_dir.glob("progress-*.txt"):
            content = pf.read_text(encoding="utf-8")
            total += len(re.findall(r"- \[ \]|- \[x\]", content))
            completed += len(re.findall(r"- \[x\]", content))
        return TaskProgress(total=total, completed=completed)

    def detect_current_gate(self) -> str | None:
        """Detect the current gate being worked on from the PRD."""
        content = self.prd_file.read_text(encoding="utf-8")
        gate_pattern = re.compile(r"^## (GATE \d+)\s*[—–-]\s*(.+)$", re.MULTILINE)

        for match in gate_pattern.finditer(content):
            gate_id = match.group(1)
            gate_name = match.group(2).strip()
            # Find the next gate or end of file
            remaining = content[match.end():]
            next_gate = gate_pattern.search(remaining)
            section = remaining[:next_gate.start()] if next_gate else remaining
            # If this section has any incomplete criteria, this is the current gate
            if re.search(r"- \[ \]", section):
                return f"{gate_id} — {gate_name}"
        return None

    def _build_prompt(self) -> str:
        """Build the prompt for Claude."""
        return f"""You are Ralph, an autonomous coding agent. Do exactly ONE task per iteration.

## Target Files
- PRD: {self.prd_file}
- Progress: {self.progress_file}

## Steps

1. Read {self.prd_file} and find the first task that is NOT complete (marked [ ]).
2. Read {self.progress_file} - check Learnings first for patterns from previous iterations.
3. Implement that ONE task only.
4. Run tests/typecheck to verify it works.

## Critical: Only Complete If Tests Pass

- If tests PASS:
  - Update {self.prd_file} to mark the task complete (change [ ] to [x])
  - Commit your changes with message: feat: [task description]
  - Append what worked to {self.progress_file}

- If tests FAIL:
  - Do NOT mark the task complete
  - Do NOT commit broken code
  - Append what went wrong to {self.progress_file} (so next iteration can learn)

## Progress Notes Format

Append to {self.progress_file} using this format:

## Iteration [N] - [Task Name]
- What was implemented
- Files changed
- Learnings for future iterations:
  - Patterns discovered
  - Gotchas encountered
  - Useful context
---

## Update AGENTS.md (If Applicable)

If you discover a reusable pattern that future work should know about:
- Check if AGENTS.md exists in the project root
- Add patterns like: 'This codebase uses X for Y' or 'Always do Z when changing W'
- Only add genuinely reusable knowledge, not task-specific details

## End Condition

After completing your task, just end your response. Ralph tracks progress automatically."""

    def _run_claude(self, prompt: str) -> str:
        """Run Claude CLI, streaming output in real-time and returning it."""
        try:
            process = subprocess.Popen(
                ["claude", "--dangerously-skip-permissions", "-p", prompt],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
            )
            output_lines: list[str] = []
            for line in process.stdout:
                print(line, end="", flush=True)
                output_lines.append(line)
            process.wait()
            return "".join(output_lines)
        except FileNotFoundError:
            print("Error: 'claude' command not found. Is Claude CLI installed?")
            sys.exit(1)

    def _init_timing_log(self) -> None:
        """Initialize the timing log file."""
        mode = "Army" if self.army_mode else "Sequential"
        with open(self.timing_log, "w", encoding="utf-8") as f:
            f.write(f"Ralph Timing Log - Started {datetime.now()}\n")
            f.write(f"Target: {self.target_dir}\n")
            f.write(f"Mode: {mode}\n")
            f.write(f"Max Iterations: {self.max_iterations}\n")
            initial = self.initial_progress
            f.write(f"Initial Progress: {initial.completed}/{initial.total} tasks\n")
            f.write("---\n")

    def _log_iteration(self, iteration: int, iter_duration: float, total_elapsed: float) -> None:
        """Log iteration timing to file."""
        with open(self.timing_log, "a", encoding="utf-8") as f:
            f.write(f"Iteration {iteration}: {format_duration(iter_duration)} | "
                    f"Total: {format_duration(total_elapsed)}\n")

    def _log_summary(self, status: str, iterations: int, total_time: float,
                     tasks_done: int, final_progress: TaskProgress) -> None:
        """Log final summary to file."""
        with open(self.timing_log, "a", encoding="utf-8") as f:
            f.write("---\n")
            f.write(f"SUMMARY ({status})\n")
            f.write(f"Total Time: {format_duration(total_time)}\n")
            f.write(f"Iterations Completed: {iterations}\n")
            avg = format_duration(total_time / iterations) if iterations > 0 else "00:00:00"
            f.write(f"Average per Iteration: {avg}\n")
            f.write(f"Tasks Completed This Run: {tasks_done}\n")
            f.write(f"Final Progress: {final_progress.completed}/{final_progress.total}")
            if final_progress.remaining > 0:
                f.write(f" ({final_progress.remaining} remaining)")
            f.write("\n")

    def _show_task_progress(self, progress: TaskProgress) -> None:
        """Display task progress bar."""
        bar_width = 40
        filled = int(progress.percentage * bar_width / 100)
        bar = "█" * filled + "░" * (bar_width - filled)

        # Color based on progress
        if progress.percentage < 25:
            color = "\033[31m"  # Red
        elif progress.percentage < 50:
            color = "\033[33m"  # Yellow
        elif progress.percentage < 75:
            color = "\033[34m"  # Blue
        else:
            color = "\033[32m"  # Green
        reset = "\033[0m"

        print(f"\n  {color}{bar}{reset} {progress.percentage:5.1f}% "
              f"({progress.completed}/{progress.total} tasks)")
        print(f"  Remaining: {progress.remaining} tasks\n")

    def _print_summary(self, title: str, iterations: int, total_time: float,
                       tasks_done: int, progress: TaskProgress) -> None:
        """Print final summary."""
        print("=" * 43)
        print(f"  {title}")
        print("=" * 43)
        self._show_task_progress(progress)
        print("=" * 43)
        print("  Summary")
        print("=" * 43)
        print(f"  Total Time:    {format_duration(total_time)}")
        print(f"  Iterations:    {iterations}")
        avg = format_duration(total_time / iterations) if iterations > 0 else "00:00:00"
        print(f"  Avg/Iter:      {avg}")
        print(f"  Tasks Done:    {tasks_done} (this run)")
        if progress.remaining > 0:
            print(f"  Remaining:     {progress.remaining} tasks")
        else:
            print(f"  Total Tasks:   {progress.completed}/{progress.total}")
        print("=" * 43)

    # ─── Army Mode ────────────────────────────────────────────

    def _parse_wave_gates(self) -> dict[int, str]:
        """Parse WAVE_N_GATE="command" from PRD."""
        content = self.prd_file.read_text(encoding="utf-8")
        gates: dict[int, str] = {}
        for match in re.finditer(r'WAVE_(\d+)_GATE="([^"]+)"', content):
            gates[int(match.group(1))] = match.group(2)
        return gates

    def _run_wave_gate(self, wave_num: int, command: str) -> bool:
        """Run gate command, return pass/fail."""
        print(f"\n  Gate {wave_num}: {command[:60]}...")
        result = subprocess.run(command, shell=True, executable="/bin/bash",
                                capture_output=True, text=True)
        if result.returncode == 0:
            print(f"  Gate {wave_num}: PASSED")
            return True
        print(f"  Gate {wave_num}: FAILED (exit {result.returncode})")
        if result.stderr:
            for line in result.stderr.strip().splitlines()[:10]:
                print(f"    {line}")
        return False

    def _get_gate_error(self, wave_num: int, command: str) -> str:
        """Run gate and capture error output."""
        result = subprocess.run(command, shell=True, executable="/bin/bash",
                                capture_output=True, text=True)
        return (result.stderr or result.stdout or "unknown error").strip()

    def _append_gate_failure(self, agent_name: str, wave_num: int,
                             attempt: int, error: str) -> None:
        """Write gate failure context to agent's progress file and clear completion marker."""
        pf = self.target_dir / "progress" / f"progress-{agent_name}.txt"
        if not pf.exists():
            return
        content = pf.read_text(encoding="utf-8")
        content = content.replace(self.COMPLETION_MARKER, "")
        content = content.replace(self.DELIVERED_TAG, "")
        content = content.replace(self.VERIFIED_TAG, "")
        content += (
            f"\n\n## Wave {wave_num} Gate FAILED (attempt {attempt})\n"
            f"The validation gate failed after your work completed. Fix the errors below:\n"
            f"```\n{error[:2000]}\n```\n"
            f"Re-read your stories and fix the issues, then re-signal completion.\n"
        )
        pf.write_text(content, encoding="utf-8")

    def _parse_army_waves(self) -> dict[int, list[str]]:
        """Parse wave assignments from PRD Orchestrator Config block."""
        content = self.prd_file.read_text(encoding="utf-8")
        # Match: WAVE_0_AGENTS=("foundation" "feature-a")
        waves: dict[int, list[str]] = {}
        for match in re.finditer(r'WAVE_(\d+)_AGENTS=\(([^)]+)\)', content):
            wn = int(match.group(1))
            agents = re.findall(r'"([^"]+)"', match.group(2))
            if agents:
                waves[wn] = agents
        if not waves:
            # Fallback: parse Agent Roster table (| agent | wave | ...)
            for match in re.finditer(r'\|\s*(\w[\w-]*)\s*\|\s*(\d+)\s*\|', content):
                agent, wn = match.group(1), int(match.group(2))
                if agent.lower() not in ('agent', '---'):
                    waves.setdefault(wn, []).append(agent)
        if not waves:
            print("Error: No wave config in PRD. Need Orchestrator Config or Agent Roster table.")
            sys.exit(1)
        return waves

    def _check_agent_complete(self, agent_name: str) -> bool:
        """Check for verified completion (or legacy marker with all tasks checked)."""
        pf = self.target_dir / "progress" / f"progress-{agent_name}.txt"
        if not pf.exists():
            return False
        content = pf.read_text(encoding="utf-8")
        if self.VERIFIED_TAG in content:
            return True
        # Legacy compat: old <promise> tag + all tasks actually checked
        if self.COMPLETION_MARKER in content:
            unchecked = len(re.findall(r"- \[ \]", content))
            checked = len(re.findall(r"- \[x\]", content))
            return unchecked == 0 and checked > 0
        return False

    def _check_agent_delivered(self, agent_name: str) -> bool:
        """Check if agent claims completion (needs verification)."""
        pf = self.target_dir / "progress" / f"progress-{agent_name}.txt"
        if not pf.exists():
            return False
        content = pf.read_text(encoding="utf-8")
        return self.DELIVERED_TAG in content and self.VERIFIED_TAG not in content

    def _build_verify_prompt(self, agent_name: str) -> str:
        """Build prompt for verification Claude."""
        pf = self.target_dir / "progress" / f"progress-{agent_name}.txt"
        agent_file = self.target_dir / "agents" / f"{agent_name}-agent.md"
        return (
            f"You are a code reviewer verifying {agent_name}-agent's work.\n\n"
            f"## Steps\n"
            f"1. Read {pf} — every sub-task must be [x], none [ ]\n"
            f"2. Read {agent_file} — find the Owned Paths section\n"
            f"3. Verify each owned file exists and contains the expected changes\n"
            f"4. Run any typecheck/test commands mentioned in the agent spec\n\n"
            f"## Verdict\n"
            f"If ALL criteria are genuinely complete and files exist with correct content:\n"
            f"  Append this exact line to {pf}: {self.VERIFIED_TAG}\n\n"
            f"If anything is missing, broken, or incomplete:\n"
            f"  Do NOT write the verified tag.\n"
            f"  Append a '## Verification FAILED' section to {pf} listing what's wrong.\n"
        )

    def _verify_agent(self, agent_name: str) -> bool:
        """Run verification Claude to confirm agent's work. Returns True if verified."""
        pf = self.target_dir / "progress" / f"progress-{agent_name}.txt"
        content = pf.read_text(encoding="utf-8")

        # Quick pre-check: any unchecked tasks?
        unchecked = len(re.findall(r"- \[ \]", content))
        if unchecked:
            content = content.replace(self.DELIVERED_TAG, "")
            content += (
                f"\n\n## Verification FAILED (auto-check)\n"
                f"{unchecked} tasks still unchecked. Complete all tasks before signaling.\n"
            )
            pf.write_text(content, encoding="utf-8")
            return False

        # Launch verification Claude
        print(f"  🔍 Verifying {agent_name}-agent...")
        prompt = self._build_verify_prompt(agent_name)
        log_path = self.target_dir / "logs" / f"{agent_name}-verify.log"
        with open(log_path, "w", encoding="utf-8") as log_fh:
            subprocess.run(
                ["claude", "--dangerously-skip-permissions", "-p", prompt],
                stdout=log_fh, stderr=subprocess.STDOUT, text=True, timeout=600,
            )

        # Check if verifier wrote the verified tag
        new_content = pf.read_text(encoding="utf-8")
        if self.VERIFIED_TAG in new_content:
            return True

        # Verification failed — strip delivered tag so agent must re-signal
        new_content = new_content.replace(self.DELIVERED_TAG, "")
        pf.write_text(new_content, encoding="utf-8")
        return False

    def _build_agent_prompt(self, agent_name: str, wave: int) -> str:
        """Build prompt for an army agent from its spec file."""
        agent_file = self.target_dir / "agents" / f"{agent_name}-agent.md"
        progress_file = self.target_dir / "progress" / f"progress-{agent_name}.txt"
        if not agent_file.exists():
            print(f"Error: Agent spec not found: {agent_file}")
            sys.exit(1)
        spec = agent_file.read_text(encoding="utf-8")
        return (
            f"You are {agent_name}-agent (Wave {wave}). Implement ALL your assigned stories.\n\n"
            f"## Your Specification\n{spec}\n\n"
            f"## Rules\n"
            f"1. Read {progress_file} first for any prior learnings\n"
            f"2. ONLY modify files listed in your Owned Paths\n"
            f"3. Commit after each story: feat: US-NNN — [title]\n"
            f"4. Mark criteria [x] in {progress_file} as you complete them\n"
            f"5. Run typecheck/tests before marking any story complete\n"
            f"6. When ALL stories done, signal completion per your Verification Checklist\n\n"
            f"Start now: read your progress file, then implement stories in order."
        )

    def _launch_agent(self, agent_name: str, wave: int):
        """Launch a Claude CLI process for one agent, logging to file."""
        prompt = self._build_agent_prompt(agent_name, wave)
        log_path = self.target_dir / "logs" / f"{agent_name}-agent.log"
        log_fh = open(log_path, "w", encoding="utf-8")
        try:
            proc = subprocess.Popen(
                ["claude", "--dangerously-skip-permissions", "-p", prompt],
                stdout=log_fh, stderr=subprocess.STDOUT, text=True,
            )
        except Exception:
            log_fh.close()
            raise
        print(f"  Launched {agent_name}-agent (PID {proc.pid}) → logs/{agent_name}-agent.log")
        return proc, log_fh

    def _cleanup_agents(self, active: dict) -> None:
        """Terminate all active agent processes and close file handles."""
        for _agent, (proc, fh) in active.items():
            if proc.poll() is None:
                proc.terminate()
            fh.close()
        active.clear()

    def _poll_wave(self, active: dict, wave_num: int) -> None:
        """Poll progress files until all agents in wave complete or exit."""
        try:
            while active:
                time.sleep(15)
                done = []
                for agent, (proc, fh) in list(active.items()):
                    if self._check_agent_complete(agent):
                        print(f"  ✓ {agent}-agent verified complete")
                        done.append(agent)
                    elif self._check_agent_delivered(agent) and proc.poll() is not None:
                        # Agent claims done and exited — run verification
                        fh.close()
                        if self._verify_agent(agent):
                            print(f"  ✓ {agent}-agent verified complete")
                            done.append(agent)
                        else:
                            print(f"  ↻ Re-launching {agent}-agent after failed verification")
                            new_proc, new_fh = self._launch_agent(agent, wave_num)
                            active[agent] = (new_proc, new_fh)
                    elif proc.poll() is not None:
                        print(f"  ✗ {agent}-agent exited (code {proc.returncode}) "
                              "without completion signal")
                        done.append(agent)
                for agent in done:
                    if agent in active:
                        proc, fh = active.pop(agent)
                        fh.close()
                        if proc.poll() is None:
                            proc.terminate()
                if active:
                    print(f"  ⏳ Waiting: {', '.join(active.keys())}")
        except KeyboardInterrupt:
            print("\n  Interrupted — terminating agents...")
            self._cleanup_agents(active)
            raise

    def run_army(self) -> int:
        """Run Army mode — parallel agents in sequential waves."""
        waves = self._parse_army_waves()
        gates = self._parse_wave_gates()
        max_wave = max(waves.keys())
        (self.target_dir / "logs").mkdir(exist_ok=True)
        (self.target_dir / "progress").mkdir(exist_ok=True)

        agent_count = sum(len(a) for a in waves.values())
        print(f"Starting Ralph's Army — {agent_count} agents across {len(waves)} waves")
        print(f"Target: {self.target_dir}")
        for wn in sorted(waves.keys()):
            gate_tag = " [gated]" if wn in gates else ""
            print(f"  Wave {wn}: {', '.join(waves[wn])}{gate_tag}")
        self._show_task_progress(self.initial_progress)
        self._init_timing_log()

        for wave_num in sorted(waves.keys()):
            agents = waves[wave_num]
            wave_start = time.time()
            print(f"\n{'=' * 43}")
            print(f"  Wave {wave_num}: {', '.join(agents)}")
            print(f"{'=' * 43}")

            # Launch incomplete agents in parallel
            active = {}
            for agent in agents:
                if self._check_agent_complete(agent):
                    print(f"  ✓ {agent}-agent already complete")
                    continue
                proc, fh = self._launch_agent(agent, wave_num)
                active[agent] = (proc, fh)

            if active:
                self._poll_wave(active, wave_num)

            wave_dur = time.time() - wave_start
            total_elapsed = time.time() - self.start_time
            print(f"\n  Wave {wave_num}: {format_duration(wave_dur)} | "
                  f"Total: {format_duration(total_elapsed)}")
            with open(self.timing_log, "a", encoding="utf-8") as f:
                f.write(f"Wave {wave_num}: {format_duration(wave_dur)} | "
                        f"Total: {format_duration(total_elapsed)}\n")
            self._show_task_progress(self.count_tasks())

            # Wave gate validation with retry
            if wave_num in gates:
                gate_cmd = gates[wave_num]
                is_final = wave_num == max_wave
                for attempt in range(1, 4):
                    if self._run_wave_gate(wave_num, gate_cmd):
                        break
                    if is_final:
                        print("\n  WARNING: Final wave gate failed (advisory only)")
                        break
                    if attempt == 3:
                        print(f"\n  BLOCKED: Wave {wave_num} gate failed after 3 attempts.")
                        return 1
                    print(f"\n  Retrying wave {wave_num} (attempt {attempt + 1}/3)...")
                    gate_error = self._get_gate_error(wave_num, gate_cmd)
                    for agent in agents:
                        self._append_gate_failure(agent, wave_num, attempt, gate_error)
                    active = {}
                    for agent in agents:
                        proc, fh = self._launch_agent(agent, wave_num)
                        active[agent] = (proc, fh)
                    if active:
                        self._poll_wave(active, wave_num)

        # Final summary
        total_elapsed = time.time() - self.start_time
        final = self.count_tasks()
        tasks_done = final.completed - self.initial_progress.completed
        title = ("Army complete!" if final.remaining == 0
                 else f"Army done — {final.remaining} tasks remaining")
        self._print_summary(title, len(waves), total_elapsed, tasks_done, final)
        self._log_summary(
            "COMPLETED" if final.remaining == 0 else "PARTIAL",
            len(waves), total_elapsed, tasks_done, final,
        )
        return 0 if final.remaining == 0 else 1

    # ─── Main Entry ───────────────────────────────────────────

    def run(self) -> int:
        """Run the main loop. Returns exit code (0 = complete, 1 = max iterations reached)."""
        if self.army_mode:
            return self.run_army()
        print(f"Starting Ralph - Max {self.max_iterations} iterations")
        print(f"Target directory: {self.target_dir}")
        print(f"PRD file: {self.prd_file}")
        print(f"Progress file: {self.progress_file}")
        print(f"Timing log: {self.timing_log}")

        self._show_task_progress(self.initial_progress)
        self._init_timing_log()

        prompt = self._build_prompt()
        print("Mode: Sequential (one task per iteration)")

        # Main iteration loop with tqdm
        pbar = tqdm(
            range(1, self.max_iterations + 1),
            desc="Iterations",
            unit="iter",
            ncols=80,
            bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}]"
        )

        for i in pbar:
            print("\n" + "=" * 43)
            print(f"  Iteration {i} of {self.max_iterations}")

            current_gate = self.detect_current_gate()
            if current_gate:
                print(f"  {current_gate}")

            print("=" * 43)

            iter_start = time.time()
            self._run_claude(prompt)

            # Calculate timings
            iter_end = time.time()
            iter_duration = iter_end - iter_start
            total_elapsed = iter_end - self.start_time

            # Log iteration
            self._log_iteration(i, iter_duration, total_elapsed)

            # Show timing
            print()
            print(f"⏱  Iter {i}: {format_duration(iter_duration)} | "
                  f"Total: {format_duration(total_elapsed)} | "
                  f"Avg: {format_duration(total_elapsed / i)}/iter")

            # Show updated progress
            current_progress = self.count_tasks()
            self._show_task_progress(current_progress)

            # Update tqdm description with task count
            pbar.set_postfix({"tasks": f"{current_progress.completed}/{current_progress.total}"})

            # Check for completion via PRD task state
            if current_progress.remaining == 0:
                tasks_done = current_progress.completed - self.initial_progress.completed
                self._print_summary(
                    f"All tasks complete after {i} iterations!",
                    i, total_elapsed, tasks_done, current_progress
                )
                self._log_summary("COMPLETED", i, total_elapsed, tasks_done, current_progress)
                pbar.close()
                return 0

            # Sleep between iterations
            if i < self.max_iterations:
                time.sleep(self.sleep_seconds)

        # Max iterations reached
        pbar.close()
        final_elapsed = time.time() - self.start_time
        final_progress = self.count_tasks()
        tasks_done = final_progress.completed - self.initial_progress.completed

        self._print_summary(
            f"Reached max iterations ({self.max_iterations})",
            self.max_iterations, final_elapsed, tasks_done, final_progress
        )
        self._log_summary("MAX ITERATIONS", self.max_iterations, final_elapsed,
                          tasks_done, final_progress)
        return 1


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Ralph - Autonomous Coding Agent Runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s PRDs/07-session-transparency           # Target directory
  %(prog)s PRDs/07-session-transparency/PRD.md    # Target PRD file
  %(prog)s PRDs/07-session-transparency 50        # 50 iterations
  %(prog)s -t PRDs/07-session-transparency -n 300 # Named arguments
        """
    )
    parser.add_argument(
        "target",
        nargs="?",
        default=".",
        help="Target directory, PRD.md, or progress.txt (default: current directory)"
    )
    parser.add_argument(
        "max_iterations",
        nargs="?",
        type=int,
        default=None,
        help="Maximum iterations (default: 10)"
    )
    parser.add_argument(
        "sleep",
        nargs="?",
        type=int,
        default=None,
        help="Sleep seconds between iterations (default: 2)"
    )
    parser.add_argument(
        "-t", "--target",
        dest="target_named",
        help="Target directory or file"
    )
    parser.add_argument(
        "-n", "--max-iterations",
        dest="max_iterations_named",
        type=int,
        help="Maximum iterations"
    )
    parser.add_argument(
        "-s", "--sleep",
        dest="sleep_named",
        type=int,
        help="Sleep seconds between iterations"
    )
    parser.add_argument(
        "-a", "--army",
        action="store_true",
        help="Army mode: parallel agents per wave with file isolation "
             "(requires agents/ and progress/ dirs)"
    )

    args = parser.parse_args()

    # Resolve arguments (named args take precedence)
    target = Path(args.target_named or args.target)
    max_iterations = args.max_iterations_named or args.max_iterations or 10
    sleep_seconds = args.sleep_named or args.sleep or 2

    try:
        ralph = Ralph(target, max_iterations, sleep_seconds, army=args.army)
        return ralph.run()
    except KeyboardInterrupt:
        print("\n\nInterrupted by user.")
        return 130


if __name__ == "__main__":
    sys.exit(main())
