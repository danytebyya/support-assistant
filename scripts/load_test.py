import argparse
import asyncio
import json
import time


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://localhost:8000/chat")
    parser.add_argument("--users", type=int, default=10)
    args = parser.parse_args()
    import httpx
    async with httpx.AsyncClient(timeout=70) as client:
        started = time.perf_counter()
        responses = await asyncio.gather(*[
            client.post(args.url, json={"message": "Почему тормозит видео?", "session_id": f"load-{i}"})
            for i in range(args.users)
        ], return_exceptions=True)
    elapsed = time.perf_counter() - started
    codes = [r.status_code if isinstance(r, httpx.Response) else str(r) for r in responses]
    print(json.dumps({"users": args.users, "wall_seconds": round(elapsed, 2), "results": codes}, ensure_ascii=False))


if __name__ == "__main__":
    asyncio.run(main())

