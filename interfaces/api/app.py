"""HTTP API и локальный веб-интерфейс проекта."""

from pathlib import Path
from typing import Any
from uuid import uuid4

from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import FileResponse, JSONResponse
from starlette.routing import Mount, Route
from starlette.staticfiles import StaticFiles

from domain.investigation.entities import Investigation
from infrastructure.bootstrap import create_investigation_runtime
from infrastructure.observability.run_metrics import RunMetrics


WEB_DIRECTORY = Path(__file__).resolve().parents[1] / "web"
STATIC_DIRECTORY = WEB_DIRECTORY / "static"
MAX_HISTORY_MESSAGES = 10
MAX_HISTORY_CONTENT_LENGTH = 4000


async def homepage(request: Request) -> FileResponse:
    """Показать основную страницу интерфейса."""
    return FileResponse(WEB_DIRECTORY / "index.html")


async def create_investigation(request: Request) -> JSONResponse:
    """Выполнить исследование пользовательского вопроса."""

    try:
        payload = await request.json()
    except Exception:
        return JSONResponse(
            {"error": "Тело запроса должно содержать JSON"},
            status_code=400,
        )

    question = payload.get("question") if isinstance(payload, dict) else None

    if not isinstance(question, str) or not question.strip():
        return JSONResponse(
            {"error": "Поле question обязательно"},
            status_code=400,
        )

    try:
        history = parse_history(payload.get("history", []))
    except ValueError as error:
        return JSONResponse(
            {"error": str(error)},
            status_code=400,
        )

    try:
        session_id = parse_session_id(payload.get("session_id"))
    except ValueError as error:
        return JSONResponse(
            {"error": str(error)},
            status_code=400,
        )

    display_question = question.strip()

    try:
        runtime = await create_investigation_runtime()
        investigation = await runtime.use_case.execute(
            display_question,
            session_id=session_id,
            history=history,
        )
        runtime.metrics.finish()
    except Exception as error:
        return JSONResponse(
            {"error": f"Не удалось запустить исследование: {error}"},
            status_code=500,
        )

    return JSONResponse(
        serialize_investigation(
            investigation=investigation,
            metrics=runtime.metrics,
            display_question=display_question,
            session_id=session_id,
        )
    )


def parse_session_id(value: Any) -> str:
    """Проверить идентификатор диалога или создать новый."""

    if value is None:
        return str(uuid4())
    if not isinstance(value, str):
        raise ValueError("Поле session_id должно быть строкой")

    session_id = value.strip()
    if not session_id:
        raise ValueError("Поле session_id не должно быть пустым")
    if len(session_id) > 200:
        raise ValueError("Поле session_id не должно быть длиннее 200 символов")

    return session_id


def parse_history(history: Any) -> list[dict[str, str]]:
    """Проверить и ограничить историю, полученную от веб-клиента."""

    if history is None:
        return []
    if not isinstance(history, list):
        raise ValueError("Поле history должно быть списком сообщений")

    parsed: list[dict[str, str]] = []
    for message in history[-MAX_HISTORY_MESSAGES:]:
        if not isinstance(message, dict):
            raise ValueError("Каждое сообщение history должно быть объектом")

        role = message.get("role")
        content = message.get("content")
        if role not in {"user", "assistant"}:
            raise ValueError("Роль сообщения должна быть user или assistant")
        if not isinstance(content, str):
            raise ValueError("Текст сообщения history должен быть строкой")

        content = content.strip()
        if not content:
            continue

        parsed.append(
            {
                "role": role,
                "content": content[:MAX_HISTORY_CONTENT_LENGTH],
            }
        )

    return parsed


def serialize_investigation(
    investigation: Investigation,
    metrics: RunMetrics,
    display_question: str | None = None,
    session_id: str | None = None,
) -> dict[str, Any]:
    """Преобразовать доменные сущности в ответ HTTP API."""

    return {
        "session_id": session_id,
        "investigation_id": investigation.investigation_id,
        "question": display_question or investigation.question,
        "status": investigation.status.value,
        "final_answer": investigation.final_answer,
        "structured_answer": {
            "short_summary": investigation.short_summary,
            "main_factors": investigation.main_factors,
            "conclusion": investigation.conclusion,
            "next_checks": investigation.next_checks,
        },
        "error_message": investigation.error_message,
        "steps": [
            {
                "step_id": step.step_id,
                "description": step.description,
                "agent_name": step.agent_name,
                "tool_name": step.tool_name,
                "arguments": step.arguments,
                "status": step.status.value,
                "result": step.result,
                "error_message": step.error_message,
            }
            for step in investigation.steps
        ],
        "evidence": [
            {
                "evidence_id": item.evidence_id,
                "source": item.source,
                "tool_name": item.tool_name,
                "data": item.data,
                "collected_at": item.collected_at.isoformat(),
            }
            for item in investigation.evidence
        ],
        "findings": [
            {
                "finding_id": finding.finding_id,
                "statement": finding.statement,
                "evidence_ids": finding.evidence_ids,
                "confidence": finding.confidence.value,
                "is_hypothesis": finding.is_hypothesis,
            }
            for finding in investigation.findings
        ],
        "metrics": {
            "llm_calls": metrics.llm_calls,
            "planning_calls": metrics.planning_calls,
            "tool_calls": metrics.tool_calls,
            "duration_seconds": round(metrics.duration_seconds, 2),
        },
    }


routes = [
    Route("/", homepage, methods=["GET"]),
    Route(
        "/api/investigations",
        create_investigation,
        methods=["POST"],
    ),
    Mount(
        "/static",
        app=StaticFiles(directory=STATIC_DIRECTORY),
        name="static",
    ),
]

app = Starlette(
    debug=True,
    routes=routes,
)
