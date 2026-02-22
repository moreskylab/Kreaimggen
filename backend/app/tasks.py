"""
Celery tasks – image generation via the Krea AI REST API.
"""
import logging
import time
from typing import Any

import httpx
from celery import Task
from celery.utils.log import get_task_logger

from app.celery_app import celery_app
from app.config import get_settings

settings = get_settings()
logger = get_task_logger(__name__)


class KreaBaseTask(Task):
    """Abstract base task that holds a shared httpx client."""

    abstract = True
    _client: httpx.Client | None = None

    @property
    def client(self) -> httpx.Client:
        if self._client is None:
            self._client = httpx.Client(
                base_url=settings.KREA_API_BASE_URL,
                headers={
                    "Authorization": f"Bearer {settings.KREA_API_KEY}",
                    "Content-Type": "application/json",
                },
                timeout=120.0,
            )
        return self._client


# ---------------------------------------------------------------------------
# Helper: poll Krea AI for a completed generation
# ---------------------------------------------------------------------------

def _poll_for_result(client: httpx.Client, job_id: str, max_wait: int = 300) -> dict:
    """Poll the Krea AI /jobs/{job_id} endpoint until completed or timeout."""
    deadline = time.monotonic() + max_wait
    while time.monotonic() < deadline:
        resp = client.get(f"/jobs/{job_id}")
        resp.raise_for_status()
        data = resp.json()
        if data.get("completed_at"):
            if data.get("status") == "completed":
                return data
            raise RuntimeError(f"Krea AI job {job_id} ended with status: {data.get('status')}")
        time.sleep(2)
    raise TimeoutError(f"Krea AI job {job_id} did not finish within {max_wait}s")


# ---------------------------------------------------------------------------
# Task
# ---------------------------------------------------------------------------

@celery_app.task(
    bind=True,
    base=KreaBaseTask,
    name="app.tasks.generate_image",
    max_retries=3,
    default_retry_delay=10,
    acks_late=True,
    track_started=True,
)
def generate_image(
    self: KreaBaseTask,
    prompt: str,
    negative_prompt: str | None = None,
    width: int = 512,
    height: int = 512,
    num_inference_steps: int = 30,
    guidance_scale: float = 7.5,
    user: str = "anonymous",
) -> dict[str, Any]:
    """
    Submit an image-generation job to Krea AI and return the result URLs.

    Krea AI uses an async job model:
      1. POST /generate/image/{model}  → returns { job_id, status: "queued" }
      2. Poll GET /jobs/{job_id} until completed_at is set and status == "completed"
    """
    logger.info("Starting image generation | user=%s prompt=%.80s", user, prompt)

    payload: dict[str, Any] = {
        "prompt": prompt,
        "width": width,
        "height": height,
        "steps": num_inference_steps,
        "guidance_scale": guidance_scale,
    }
    if negative_prompt:
        payload["negative_prompt"] = negative_prompt

    try:
        # ── Step 1: submit ──────────────────────────────────────────────────
        endpoint = f"/generate/image/{settings.KREA_MODEL}"
        submit_resp = self.client.post(endpoint, json=payload)
        submit_resp.raise_for_status()
        job = submit_resp.json()
        job_id: str = job["job_id"]
        logger.info("Job submitted | id=%s", job_id)

        # Update Celery task state so callers can track progress
        self.update_state(
            state="PROGRESS",
            meta={"job_id": job_id, "status": "submitted"},
        )

        # ── Step 2: poll ────────────────────────────────────────────────────
        result = _poll_for_result(self.client, job_id)

        output_urls: list[str] = result.get("result", {}).get("urls", [])
        logger.info("Generation succeeded | id=%s urls=%s", job_id, output_urls)

        return {
            "job_id": job_id,
            "image_urls": output_urls,
            "prompt": prompt,
            "user": user,
        }

    except httpx.HTTPStatusError as exc:
        logger.error("Krea AI HTTP error: %s %s", exc.response.status_code, exc.response.text)
        raise self.retry(exc=exc)
    except (TimeoutError, RuntimeError) as exc:
        logger.error("Generation failed: %s", exc)
        raise self.retry(exc=exc)
    except Exception as exc:
        logger.exception("Unexpected error during image generation")
        raise self.retry(exc=exc)
