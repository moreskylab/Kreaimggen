from fastapi import APIRouter, Depends, HTTPException, Request, status
from celery.result import AsyncResult

from app.auth import get_current_user
from app.db_models import User
from app.models import GenerateRequest, GenerateResponse, TaskStatusResponse
from app.tasks import generate_image
from app.celery_app import celery_app

router = APIRouter(prefix="/generate", tags=["generate"])


@router.post("", response_model=GenerateResponse, status_code=status.HTTP_202_ACCEPTED)
async def submit_generation(
    request: Request,
    body: GenerateRequest,
    current_user: User = Depends(get_current_user),
):
    """
    Enqueue an image-generation Celery task and immediately return the task ID.
    Clients should poll /generate/status/{task_id} to retrieve the result.
    """
    task: AsyncResult = generate_image.apply_async(
        kwargs={
            "prompt": body.prompt,
            "negative_prompt": body.negative_prompt,
            "width": body.width,
            "height": body.height,
            "num_inference_steps": body.num_inference_steps,
            "guidance_scale": body.guidance_scale,
            "user": current_user.username,
        },
        queue="image_generation",
    )
    return GenerateResponse(task_id=task.id)


@router.get("/status/{task_id}", response_model=TaskStatusResponse)
async def task_status(
    task_id: str,
    current_user: User = Depends(get_current_user),
):
    """
    Return the current status / result of a previously submitted task.
    """
    result = AsyncResult(task_id, app=celery_app)

    state = result.state.lower()
    response = TaskStatusResponse(task_id=task_id, status=state)

    if state == "success":
        response.result = result.get(timeout=1)
    elif state == "failure":
        response.error = str(result.info)
    elif state == "progress":
        response.result = result.info   # meta dict from update_state

    return response
