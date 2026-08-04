import argparse
import json
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path


def post(url: str, question: str) -> dict:
    request = urllib.request.Request(
        url, data=json.dumps({"message": question}).encode(),
        headers={"Content-Type": "application/json"}, method="POST"
    )
    with urllib.request.urlopen(request, timeout=70) as response:
        return json.load(response)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--api", default="http://localhost:8000")
    args = parser.parse_args()
    cases = json.loads(Path("data/evaluation/questions.json").read_text(encoding="utf-8"))
    results = []
    for case in cases:
        started = time.perf_counter()
        try:
            payload = post(args.api.rstrip("/") + "/chat", case["question"])
            answer = payload["answer"].lower()
            passed = any(x.lower() in answer for x in case["expect_any"])
            passed = passed and not any(x.lower() in answer for x in case.get("reject_any", []))
            error = None
        except Exception as exc:
            answer, passed, error = "", False, str(exc)
        results.append({**case, "passed": passed, "answer": answer,
                        "elapsed_ms": round((time.perf_counter()-started)*1000), "error": error})
        print(("PASS" if passed else "FAIL"), case["question"])
    rag = [x for x in results if x["kind"] == "rag"]
    report = {
        "run_at": datetime.now(timezone.utc).isoformat(), "api": args.api,
        "total": len(results), "passed": sum(x["passed"] for x in results),
        "rag_accuracy": round(sum(x["passed"] for x in rag) / len(rag), 3),
        "results": results,
    }
    Path("docs/evaluation-results.json").write_text(json.dumps(report, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    print(json.dumps({k: report[k] for k in ("total", "passed", "rag_accuracy")}, ensure_ascii=False))


if __name__ == "__main__":
    main()

