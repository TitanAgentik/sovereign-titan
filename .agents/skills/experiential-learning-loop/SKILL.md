---
name: experiential-learning-loop
description: Closed-loop ACE, ExpeL, Reflexion, Voyager, and FinMem self-improving skill bundle for auditing 6-stage Solana memecoin execution trajectories, generating verbal critiques, and applying incremental rule deltas.
---

# Experiential Learning Loop (`experiential-learning-loop`)

## Overview
Implements the closed-loop self-improvement cycle combining:
1. **Stanford-SambaNova ACE (Generator / Reflector / Curator)**: Modular role separation with incremental delta updates to prevent brevity bias and context collapse.
2. **Reflexion (Verbal Reinforcement)**: Immediate episodic verbal self-critique (`memory/episodic_failures.jsonl` and `episodic_reflections` table in `memory/telemetry.db`).
3. **ExpeL (Experiential Learning)**: Cross-task heuristic extraction (`ADD`, `EDIT`, `UPVOTE`, `DOWNVOTE`) + vector similarity recall of $k$-nearest winning trajectories.
4. **Voyager (Executable Skill Library)**: Self-contained CLI scripts in `scripts/` invoked as black boxes via `--help`.
5. **FinMem (Two-Mode Execution Gate)**: Validates candidate heuristics in `train` (shadow/replay) mode before promoting to `active` (`test` live capital mode).

## Black-Box CLI Scripts
- **Evaluate Trajectory & Validate Shadow Rules**:
  ```bash
  python3 .agents/skills/experiential-learning-loop/scripts/evaluate_trajectory.py --help
  ```
- **Curate ExpeL Rule Deltas (`ADD`, `EDIT`, `UPVOTE`, `DOWNVOTE`)**:
  ```bash
  python3 .agents/skills/experiential-learning-loop/scripts/curate_rules.py --help
  ```

## Reference Documentation
- Archived low-utility heuristics (`<= 0` utility score) are stored on demand in [`references/archived-heuristics.md`](references/archived-heuristics.md) (`<= 60,000` characters).
