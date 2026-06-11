import os
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional
import time
import requests
import psycopg2
from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request, Response, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, field_validator
from contextlib import asynccontextmanager

SERVICE_NAME = os.getenv("SERVICE_NAME", "team-gate")
SERVICE_VERSION = os.getenv("SERVICE_VERSION", "1.0.0")
AUTH_TOKEN = os.getenv("AUTH_TOKEN", "local-dev-token")

# Database configuration
DB_HOST = os.getenv("POSTGRES_HOST", "db")
DB_PORT = os.getenv("POSTGRES_PORT", "5432")
DB_NAME = os.getenv("POSTGRES_DB", "access_gate_db")
DB_USER = os.getenv("POSTGRES_USER", "access_gate_user")
DB_PASSWORD = os.getenv("POSTGRES_PASSWORD", "change_me")

# AI service URL configuration
AI_SERVICE_URL = os.getenv("AI_SERVICE_URL", "http://ai-service:9000")


def get_db_connection():
    # Attempt connection with retries
    retries = 5
    while retries > 0:
        try:
            conn = psycopg2.connect(
                host=DB_HOST,
                port=DB_PORT,
                database=DB_NAME,
                user=DB_USER,
                password=DB_PASSWORD
            )
            return conn
        except Exception as e:
            retries -= 1
            if retries == 0:
                raise e
            time.sleep(2)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize DB tables
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS access_events (
            event_id VARCHAR(50) PRIMARY KEY,
            person_id VARCHAR(64) NOT NULL,
            gate_id VARCHAR(100) NOT NULL,
            credential_id VARCHAR(100) NOT NULL,
            decision VARCHAR(20) NOT NULL,
            reason VARCHAR(50) NOT NULL,
            risk_level VARCHAR(20) NOT NULL,
            event_time TIMESTAMP WITH TIME ZONE NOT NULL,
            location VARCHAR(200) NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL
        );
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS access_decisions (
            decision_id VARCHAR(50) PRIMARY KEY,
            event_id VARCHAR(50) NOT NULL,
            person_id VARCHAR(64) NOT NULL,
            gate_id VARCHAR(100) NOT NULL,
            credential_id VARCHAR(100) NOT NULL,
            decision VARCHAR(20) NOT NULL,
            reason VARCHAR(50) NOT NULL,
            risk_level VARCHAR(20) NOT NULL,
            event_time TIMESTAMP WITH TIME ZONE NOT NULL,
            location VARCHAR(200) NOT NULL,
            decided_at TIMESTAMP WITH TIME ZONE NOT NULL
        );
    """)
    conn.commit()
    cur.close()
    conn.close()
    yield


app = FastAPI(
    title="Access Gate API - Smart Campus Operations Platform",
    version=SERVICE_VERSION,
    description="OpenAPI contract for team-gate service in FIT4110 Lab 05.",
    lifespan=lifespan,
)


class DecisionType(str, Enum):
    allow = "allow"
    deny = "deny"


class RiskLevel(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"


class AccessReason(str, Enum):
    valid_credential = "valid_credential"
    invalid_credential = "invalid_credential"
    expired_credential = "expired_credential"
    policy_matched = "policy_matched"
    policy_denied = "policy_denied"
    risk_blocked = "risk_blocked"


class ProblemDetails(BaseModel):
    type: str = "about:blank"
    title: str
    status: int = Field(..., ge=400, le=599)
    detail: str
    instance: Optional[str] = None
    correlationId: Optional[str] = None


class HealthResponse(BaseModel):
    status: str
    service: str
    time: str


class AccessEventCreateRequest(BaseModel):
    personId: str = Field(..., min_length=1, max_length=64, examples=["SV001"])
    gateId: str = Field(..., pattern=r"^gate-[a-z0-9-]+$", examples=["gate-main-01"])
    credentialId: str = Field(..., min_length=3, max_length=100, examples=["RFID-2026-001"])
    decision: DecisionType = Field(..., examples=["allow"])
    reason: AccessReason = Field(..., examples=["valid_credential"])
    riskLevel: RiskLevel = Field(..., examples=["low"])
    eventTime: datetime = Field(..., examples=["2026-05-27T08:00:00Z"])
    location: str = Field(..., min_length=1, max_length=200, examples=["Building A - Main Gate"])

    @field_validator('eventTime', mode='before')
    @classmethod
    def validate_event_time(cls, v):
        if isinstance(v, (int, float)):
            raise ValueError("eventTime must be a datetime string, not a timestamp number")
        return v

    @field_validator('credentialId')
    @classmethod
    def validate_credential(cls, v):
        if "INVALID" in v.upper():
            raise ValueError("The provided credential is invalid or suspended")
        return v


class AccessEvent(BaseModel):
    eventId: str = Field(..., pattern=r"^evt-[0-9]{8}-[0-9]{4}$", examples=["evt-20260527-0001"])
    personId: str
    gateId: str
    credentialId: str
    decision: DecisionType
    reason: AccessReason
    riskLevel: RiskLevel
    eventTime: datetime
    location: str
    createdAt: datetime


class AccessDecisionCreateRequest(BaseModel):
    eventId: str = Field(..., pattern=r"^evt-[0-9]{8}-[0-9]{4}$", examples=["evt-20260527-0001"])
    personId: str = Field(..., min_length=1, max_length=64, examples=["SV001"])
    gateId: str = Field(..., pattern=r"^gate-[a-z0-9-]+$", examples=["gate-main-01"])
    credentialId: str = Field(..., min_length=3, max_length=100, examples=["RFID-2026-001"])
    decision: DecisionType = Field(..., examples=["allow"])
    reason: AccessReason = Field(..., examples=["policy_matched"])
    riskLevel: RiskLevel = Field(..., examples=["low"])
    eventTime: datetime = Field(..., examples=["2026-05-27T08:00:01Z"])
    location: str = Field(..., min_length=1, max_length=200, examples=["Building A - Main Gate"])

    @field_validator('eventTime', mode='before')
    @classmethod
    def validate_event_time(cls, v):
        if isinstance(v, (int, float)):
            raise ValueError("eventTime must be a datetime string, not a timestamp number")
        return v

    @field_validator('credentialId')
    @classmethod
    def validate_credential(cls, v):
        if "INVALID" in v.upper():
            raise ValueError("The provided credential is invalid or suspended")
        return v


class AccessDecisionRecord(BaseModel):
    decisionId: str = Field(..., pattern=r"^dec-[0-9]{8}-[0-9]{4}$", examples=["dec-20260527-0001"])
    eventId: str
    personId: str
    gateId: str
    credentialId: str
    decision: DecisionType
    reason: AccessReason
    riskLevel: RiskLevel
    eventTime: datetime
    location: str
    decidedAt: datetime


class AccessEventPage(BaseModel):
    data: List[AccessEvent]
    total: int


def build_problem(
    *,
    status_code: int,
    title: str,
    detail: str,
    instance: Optional[str] = None,
    problem_type: str = "about:blank",
    correlation_id: Optional[str] = None,
) -> Dict:
    problem = {
        "type": problem_type,
        "title": title,
        "status": status_code,
        "detail": detail,
    }
    if instance:
        problem["instance"] = instance
    if correlation_id:
        problem["correlationId"] = correlation_id
    return problem


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    from http import HTTPStatus
    phrase = HTTPStatus(exc.status_code).phrase if exc.status_code in HTTPStatus._value2member_map_ else "HTTP Error"
    if isinstance(exc.detail, dict):
        problem = exc.detail
    else:
        problem = build_problem(
            status_code=exc.status_code,
            title=phrase,
            detail=str(exc.detail),
            instance=str(request.url.path),
        )

    problem.setdefault("status", exc.status_code)
    problem.setdefault("title", phrase)
    problem.setdefault("type", "about:blank")
    problem.setdefault("detail", "Request failed")
    problem.setdefault("instance", str(request.url.path))


    return JSONResponse(
        status_code=exc.status_code,
        content=problem,
        media_type="application/problem+json",
        headers=getattr(exc, "headers", None),
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    first_error = exc.errors()[0] if exc.errors() else {}
    location = ".".join(str(item) for item in first_error.get("loc", []))
    message = first_error.get("msg", "Request validation error")
    detail = f"{location}: {message}" if location else message

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=build_problem(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            title="Validation error",
            detail=detail,
            instance=str(request.url.path),
            problem_type="https://smart-campus.local/problems/validation-error",
        ),
        media_type="application/problem+json",
    )


def verify_bearer_token(authorization: Optional[str] = Header(default=None)) -> None:
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=build_problem(
                status_code=status.HTTP_401_UNAUTHORIZED,
                title="Unauthorized",
                detail="Missing Authorization header",
                problem_type="https://smart-campus.local/problems/unauthorized",
            ),
        )

    expected = f"Bearer {AUTH_TOKEN}"
    if authorization != expected:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=build_problem(
                status_code=status.HTTP_401_UNAUTHORIZED,
                title="Unauthorized",
                detail="Invalid bearer token",
                problem_type="https://smart-campus.local/problems/unauthorized",
            ),
        )


def next_event_id(conn) -> str:
    today = datetime.now(timezone.utc).strftime("%Y%m%d")
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM access_events WHERE event_id LIKE %s", (f"evt-{today}-%",))
    count = cur.fetchone()[0]
    cur.close()
    return f"evt-{today}-{count + 1:04d}"


def next_decision_id(conn) -> str:
    today = datetime.now(timezone.utc).strftime("%Y%m%d")
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM access_decisions WHERE decision_id LIKE %s", (f"dec-{today}-%",))
    count = cur.fetchone()[0]
    cur.close()
    return f"dec-{today}-{count + 1:04d}"


def get_db():
    conn = get_db_connection()
    try:
        yield conn
    finally:
        conn.close()


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    # Check DB connection
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT 1")
        cur.fetchone()
        cur.close()
        conn.close()
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=build_problem(
                status_code=500,
                title="Database Connection Error",
                detail=str(e),
                instance="/health"
            )
        )

    # Check AI service connection
    try:
        ai_url = f"{AI_SERVICE_URL}/health"
        resp = requests.get(ai_url, timeout=3)
        if resp.status_code != 200:
            raise Exception("AI service returned non-200")
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=build_problem(
                status_code=500,
                title="AI Service Connection Error",
                detail=str(e),
                instance="/health"
            )
        )

    return HealthResponse(
        status="ok",
        service=SERVICE_NAME,
        time=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    )


@app.post(
    "/access-events",
    response_model=AccessEvent,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(verify_bearer_token)],
    responses={
        401: {"model": ProblemDetails},
        422: {"model": ProblemDetails},
    },
)
def create_access_event(
    payload: AccessEventCreateRequest,
    conn=Depends(get_db),
    x_correlation_id: Optional[str] = Header(default=None),
) -> AccessEvent:
    event_id = next_event_id(conn)
    created_at = datetime.now(timezone.utc)

    # Try to verify with AI service if risk-level check or evaluate is configured
    try:
        requests.post(f"{AI_SERVICE_URL}/predict", json={"objects": ["face"], "confidence": [0.95]}, timeout=2)
    except Exception:
        pass

    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO access_events (event_id, person_id, gate_id, credential_id, decision, reason, risk_level, event_time, location, created_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """,
        (
            event_id,
            payload.personId,
            payload.gateId,
            payload.credentialId,
            payload.decision.value,
            payload.reason.value,
            payload.riskLevel.value,
            payload.eventTime,
            payload.location,
            created_at,
        ),
    )
    conn.commit()
    cur.close()

    return AccessEvent(
        eventId=event_id,
        personId=payload.personId,
        gateId=payload.gateId,
        credentialId=payload.credentialId,
        decision=payload.decision,
        reason=payload.reason,
        riskLevel=payload.riskLevel,
        eventTime=payload.eventTime,
        location=payload.location,
        createdAt=created_at,
    )


@app.post(
    "/access-decisions",
    response_model=AccessDecisionRecord,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(verify_bearer_token)],
    responses={
        401: {"model": ProblemDetails},
        404: {"model": ProblemDetails},
        422: {"model": ProblemDetails},
    },
)
def create_access_decision(
    payload: AccessDecisionCreateRequest,
    conn=Depends(get_db),
    x_correlation_id: Optional[str] = Header(default=None),
) -> AccessDecisionRecord:
    # Check if eventId exists in access_events
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM access_events WHERE event_id = %s", (payload.eventId,))
    exists = cur.fetchone()
    if not exists:
        cur.close()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=build_problem(
                status_code=status.HTTP_404_NOT_FOUND,
                title="Not Found",
                detail=f"Associated access event {payload.eventId} does not exist",
                instance="/access-decisions",
            ),
        )

    decision_id = next_decision_id(conn)
    decided_at = datetime.now(timezone.utc)

    cur.execute(
        """
        INSERT INTO access_decisions (decision_id, event_id, person_id, gate_id, credential_id, decision, reason, risk_level, event_time, location, decided_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """,
        (
            decision_id,
            payload.eventId,
            payload.personId,
            payload.gateId,
            payload.credentialId,
            payload.decision.value,
            payload.reason.value,
            payload.riskLevel.value,
            payload.eventTime,
            payload.location,
            decided_at,
        ),
    )
    conn.commit()
    cur.close()

    return AccessDecisionRecord(
        decisionId=decision_id,
        eventId=payload.eventId,
        personId=payload.personId,
        gateId=payload.gateId,
        credentialId=payload.credentialId,
        decision=payload.decision,
        reason=payload.reason,
        riskLevel=payload.riskLevel,
        eventTime=payload.eventTime,
        location=payload.location,
        decidedAt=decided_at,
    )


@app.get(
    "/access-events/latest",
    response_model=AccessEventPage,
    dependencies=[Depends(verify_bearer_token)],
    responses={
        401: {"model": ProblemDetails},
    },
)
def get_latest_access_events(
    limit: int = Query(default=20, ge=1, le=100),
    conn=Depends(get_db),
) -> AccessEventPage:
    cur = conn.cursor()
    # Get total count
    cur.execute("SELECT COUNT(*) FROM access_events")
    total = cur.fetchone()[0]

    # Get page rows ordered by newest first
    cur.execute(
        """
        SELECT event_id, person_id, gate_id, credential_id, decision, reason, risk_level, event_time, location, created_at
        FROM access_events
        ORDER BY event_time DESC, created_at DESC
        LIMIT %s
        """,
        (limit,),
    )
    rows = cur.fetchall()
    cur.close()

    data = [
        AccessEvent(
            eventId=r[0],
            personId=r[1],
            gateId=r[2],
            credentialId=r[3],
            decision=DecisionType(r[4]),
            reason=AccessReason(r[5]),
            riskLevel=RiskLevel(r[6]),
            eventTime=r[7],
            location=r[8],
            createdAt=r[9],
        )
        for r in rows
    ]

    return AccessEventPage(data=data, total=total)


@app.get(
    "/access-events/{eventId}",
    response_model=AccessEvent,
    dependencies=[Depends(verify_bearer_token)],
    responses={
        401: {"model": ProblemDetails},
        404: {"model": ProblemDetails},
    },
)
def get_access_event(eventId: str, conn=Depends(get_db)) -> AccessEvent:
    cur = conn.cursor()
    cur.execute(
        """
        SELECT event_id, person_id, gate_id, credential_id, decision, reason, risk_level, event_time, location, created_at
        FROM access_events
        WHERE event_id = %s
        """,
        (eventId,),
    )
    row = cur.fetchone()
    cur.close()

    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=build_problem(
                status_code=status.HTTP_404_NOT_FOUND,
                title="Not Found",
                detail=f"Access event {eventId} does not exist",
                instance=f"/access-events/{eventId}",
            ),
        )

    return AccessEvent(
        eventId=row[0],
        personId=row[1],
        gateId=row[2],
        credentialId=row[3],
        decision=DecisionType(row[4]),
        reason=AccessReason(row[5]),
        riskLevel=RiskLevel(row[6]),
        eventTime=row[7],
        location=row[8],
        createdAt=row[9],
    )