"""
Background Evaluation Worker
=============================
Continuously pops evaluation job IDs from the Redis `eval_queue` list
and processes them:

1. Mark evaluation as "processing"
2. Simulate evaluation work (stub — replace with real LLM call)
3. Mark as "completed" with a generated score and feedback

Run with:
    python -m app.worker.evaluation_worker
"""

import asyncio
import logging
import random
import uuid
from datetime import timezone

from sqlalchemy import select

from app.database import AsyncSessionLocal
from app.models.evaluation import Evaluation, EvaluationStatus
from app.redis_client import dequeue_evaluation, get_redis

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("evaluation_worker")


async def process_evaluation(evaluation_id_str: str) -> None:
    try:
        eval_id = uuid.UUID(evaluation_id_str)
    except ValueError:
        logger.error("Invalid evaluation UUID: %s", evaluation_id_str)
        return

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Evaluation).where(Evaluation.id == eval_id))
        evaluation = result.scalar_one_or_none()

        if not evaluation:
            logger.warning("Evaluation %s not found in DB", eval_id)
            return

        # ── Mark as processing ──────────────────────────────────────────────
        evaluation.status = EvaluationStatus.processing
        await db.commit()
        logger.info("Processing evaluation %s …", eval_id)

        # ── Simulate evaluation work ────────────────────────────────────────
        await asyncio.sleep(2)  # stub for async LLM / grading pipeline

        try:
            score = round(random.uniform(60.0, 100.0), 2)
            feedback_options = [
                "Excellent understanding of core concepts.",
                "Good progress. Focus on problem-solving speed.",
                "Strong performance with minor gaps in advanced topics.",
                "Solid foundation. Review session notes for improvement.",
            ]
            feedback = random.choice(feedback_options)

            evaluation.status = EvaluationStatus.completed
            evaluation.score = score
            evaluation.feedback = feedback
            logger.info("Evaluation %s completed — score: %.2f", eval_id, score)

        except Exception as exc:
            evaluation.status = EvaluationStatus.failed
            evaluation.feedback = f"Worker error: {exc}"
            logger.exception("Evaluation %s failed", eval_id)

        await db.commit()


async def run_worker() -> None:
    logger.info("Evaluation worker started. Listening on Redis queue …")
    await get_redis()  # warm up Redis connection

    while True:
        evaluation_id = await dequeue_evaluation(timeout=5)
        if evaluation_id:
            asyncio.create_task(process_evaluation(evaluation_id))


if __name__ == "__main__":
    asyncio.run(run_worker())
