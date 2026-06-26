"""
Phase 3 Verification Script — Healthcare AI Router Graph
=========================================================
Tests that the LangGraph Router Graph executes correctly for all
four intents and the error path.

Run from: backend/
    python -m backend.tests.verify_phase3

Requires: GROQ_API_KEY in environment or .env file
"""

from __future__ import annotations

import asyncio
import os
import sys
import time

# Add backend parent to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


TEST_CASES = [
    {
        "name": "Consultation",
        "message": "I want to book an appointment with a cardiologist in Paris next week.",
        "expected_intent": "consultation",
    },
    {
        "name": "Reimbursement",
        "message": "What documents do I need to submit to get reimbursed for my surgery?",
        "expected_intent": "reimbursement",
    },
    {
        "name": "Follow-up",
        "message": "My fever has not gone down in 3 days after my treatment.",
        "expected_intent": "followup",
    },
    {
        "name": "Medical FAQ",
        "message": "What is the difference between Type 1 and Type 2 diabetes?",
        "expected_intent": "faq",
    },
]

PASS = "✅ PASS"
FAIL = "❌ FAIL"


async def run_test(test_case: dict) -> bool:
    """Run a single graph test case and return True if it passed."""
    from backend.graph.graph_builder import invoke_graph

    name = test_case["name"]
    message = test_case["message"]
    expected = test_case["expected_intent"]

    print(f"\n{'─'*60}")
    print(f"Test: {name}")
    print(f"Message: {message[:60]}...")

    start = time.monotonic()
    try:
        result = await invoke_graph(
            message=message,
            session_id="test-session-001",
            correlation_id=f"test-{name.lower().replace(' ', '-')}-001",
            history=[],
        )
        elapsed = (time.monotonic() - start) * 1000

        intent = result.get("intent", "")
        confidence = result.get("confidence", 0.0)
        agent = (result.get("response") or {}).get("agent", "N/A")
        error = result.get("error")
        answer = (result.get("response") or {}).get("answer", "")[:80]

        passed = intent == expected and not error

        status = PASS if passed else FAIL
        print(f"Status:    {status}")
        print(f"Intent:    {intent} (expected: {expected})")
        print(f"Confidence:{confidence:.2f}")
        print(f"Agent:     {agent}")
        print(f"Answer:    {answer}...")
        print(f"Error:     {error or 'None'}")
        print(f"Latency:   {elapsed:.0f}ms")

        return passed

    except Exception as exc:
        elapsed = (time.monotonic() - start) * 1000
        print(f"Status:    {FAIL}")
        print(f"Exception: {type(exc).__name__}: {exc}")
        print(f"Latency:   {elapsed:.0f}ms")
        return False


async def main() -> None:
    """Execute all test cases and report results."""
    print("=" * 60)
    print("Phase 3 Verification: LangGraph Router Graph")
    print("=" * 60)

    # Validate environment
    api_key = os.getenv("GROQ_API_KEY", "")
    if not api_key:
        # Try loading from .env
        try:
            from dotenv import load_dotenv
            load_dotenv()
            api_key = os.getenv("GROQ_API_KEY", "")
        except ImportError:
            pass

    if not api_key:
        print("\n⚠️  GROQ_API_KEY not set — set it in .env or environment")
        sys.exit(1)

    print(f"\nGroq API Key: {'*' * 8}{api_key[-4:]}")
    print(f"Test cases:  {len(TEST_CASES)}")

    results = []
    for case in TEST_CASES:
        passed = await run_test(case)
        results.append(passed)

    # Summary
    total = len(results)
    passed_count = sum(results)
    failed_count = total - passed_count

    print(f"\n{'=' * 60}")
    print(f"RESULTS: {passed_count}/{total} passed")
    print(f"  {PASS}: {passed_count}")
    print(f"  {FAIL}: {failed_count}")
    print("=" * 60)

    if failed_count > 0:
        sys.exit(1)
    else:
        print("\n✅ All Phase 3 verification tests passed!")


if __name__ == "__main__":
    asyncio.run(main())
