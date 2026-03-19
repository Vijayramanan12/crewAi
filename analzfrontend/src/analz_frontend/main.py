#!/usr/bin/env python
"""
Frontend Digest — Daily Runner
──────────────────────────────
Run manually:       python -m my_project.main
Run with scheduler: python -m my_project.main --schedule
"""
import argparse
import os
import sys
from datetime import date, datetime
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# ── Fix: merge consecutive same-role messages for local LLMs ──────────────
# Local models (LM Studio) use strict Jinja templates that require user and
# assistant turns to strictly alternate. CrewAI can send consecutive same-role
# messages during tool calls. This hook merges them before the LLM sees them.
import litellm

def _fix_role_alternation(kwargs, completion_response=None, start_time=None, end_time=None):
    pass  # only used as pre-call hook


def _pre_call_fix(kwargs):
    """Merge consecutive messages with the same role before sending to LLM."""
    messages = kwargs.get("messages", [])
    if not messages:
        return kwargs

    fixed = [messages[0]]
    for msg in messages[1:]:
        if msg.get("role") == fixed[-1].get("role"):
            # Merge content
            prev_content = fixed[-1].get("content") or ""
            new_content = msg.get("content") or ""
            if isinstance(prev_content, list) or isinstance(new_content, list):
                # If either is a list (multimodal), just concatenate as strings
                fixed[-1]["content"] = str(prev_content) + "\n" + str(new_content)
            else:
                fixed[-1]["content"] = prev_content + "\n" + new_content
        else:
            fixed.append(dict(msg))

    kwargs["messages"] = fixed
    return kwargs


litellm.callbacks = []
litellm.input_callback = [_pre_call_fix]
# ──────────────────────────────────────────────────────────────────────────────



def validate_env():
    """Check required environment variables before running."""
    required = {
        "OPENAI_API_KEY": "LLM provider (OpenAI)",
        "SERPER_API_KEY": "Web search (SerperDev)",
    }
    missing = [f"  • {var} — {desc}" for var, desc in required.items() if not os.getenv(var)]
    if missing:
        print("❌  Missing environment variables:\n" + "\n".join(missing))
        print("\nAdd them to your .env file and retry.")
        sys.exit(1)


def ensure_knowledge_dir():
    """Make sure the knowledge/ output directory exists."""
    Path("knowledge").mkdir(exist_ok=True)


from analz_frontend.crew import get_daily_category

def already_ran_today() -> bool:
    """Check if today's report already exists (prevents double-runs)."""
    today = date.today().strftime("%Y-%m-%d")
    category = get_daily_category()
    report_path = Path(f"knowledge/frontend_digest_{category}_{today}.md")
    return report_path.exists()


def run():
    """Execute one full daily digest run."""
    from analz_frontend.crew import FrontendDigestCrew

    today = date.today().strftime("%Y-%m-%d")
    day_name = datetime.now().strftime("%A")

    print(f"\n{'═' * 55}")
    print(f"  🌐  Frontend Digest — {today} ({day_name})")
    print(f"{'═' * 55}\n")

    validate_env()
    ensure_knowledge_dir()

    if already_ran_today():
        print(f"✅  Today's report already exists: knowledge/frontend_digest_{today}.md")
        print("    Delete it to force a re-run.\n")
        return

    print("🔍  Starting crew...\n")

    try:
        result = FrontendDigestCrew().crew().kickoff(
            inputs={"today": today, "category": get_daily_category()},  # category can be used for future expansion (e.g. "mobile", "ecommerce")
        )

        category = get_daily_category()
        report_path = f"knowledge/frontend_digest_{category}_{today}.md"
        print(f"\n{'═' * 55}")
        print(f"  ✅  Report saved → {report_path}")
        print(f"{'═' * 55}\n")
        return result

    except Exception as e:
        print(f"\n❌  Crew run failed: {e}")
        raise


def run_scheduled():
    """
    Run the digest on a daily schedule using the `schedule` library.
    Fires at 08:00 every morning.
    
    Install: pip install schedule
    """
    try:
        import schedule
        import time
    except ImportError:
        print("❌  Install `schedule` to use --schedule mode: pip install schedule")
        sys.exit(1)

    RUN_AT = "08:00"

    print(f"⏰  Scheduler active — will run daily at {RUN_AT}")
    print("    Press Ctrl+C to stop.\n")

    schedule.every().day.at(RUN_AT).do(run)

    # Run immediately on start too
    run()

    while True:
        schedule.run_pending()
        time.sleep(60)


def train():
    """Train the crew for a number of iterations (CrewAI built-in)."""
    from analz_frontend.crew import FrontendDigestCrew

    try:
        n_iterations = int(sys.argv[2]) if len(sys.argv) > 2 else 3
        filename = sys.argv[3] if len(sys.argv) > 3 else "training_data.pkl"
        FrontendDigestCrew().crew().train(
            n_iterations=n_iterations,
            filename=filename,
            inputs={"today": date.today().strftime("%Y-%m-%d")},
        )
    except Exception as e:
        raise Exception(f"Training failed: {e}") from e


def replay(task_id: str):
    """Replay a specific task by ID."""
    from analz_frontend.crew import FrontendDigestCrew

    try:
        FrontendDigestCrew().crew().replay(task_id=task_id)
    except Exception as e:
        raise Exception(f"Replay failed: {e}") from e


def test():
    """Test the crew with a small number of iterations."""
    from analz_frontend.crew import FrontendDigestCrew

    try:
        FrontendDigestCrew().crew().test(
            n_iterations=1,
            inputs={"today": date.today().strftime("%Y-%m-%d")},
        )
    except Exception as e:
        raise Exception(f"Test failed: {e}") from e


# ──────────────────────────────────────────────────────────────
# CLI Entry Point
# ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Frontend Digest — Daily AI-powered frontend trend tracker"
    )
    parser.add_argument(
        "--schedule",
        action="store_true",
        help="Run on a daily schedule (08:00 every morning)",
    )
    parser.add_argument(
        "--train",
        action="store_true",
        help="Train the crew",
    )
    parser.add_argument(
        "--test",
        action="store_true",
        help="Run a quick test iteration",
    )
    parser.add_argument(
        "--replay",
        type=str,
        metavar="TASK_ID",
        help="Replay a specific task by ID",
    )

    args = parser.parse_args()

    if args.schedule:
        run_scheduled()
    elif args.train:
        train()
    elif args.test:
        test()
    elif args.replay:
        replay(args.replay)
    else:
        run()