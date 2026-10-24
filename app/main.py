import os
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request, Response
from pydantic import BaseModel, Field
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest
from sqlalchemy import Integer, String, create_engine, select, text
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor


DATABASE_URL = os.environ["DATABASE_URL"]
engine = create_engine(DATABASE_URL, pool_size=20, max_overflow=0, pool_timeout=5, pool_pre_ping=True)


class Base(DeclarativeBase):
    pass


class Student(Base):
    __tablename__ = "students"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    email: Mapped[str] = mapped_column(String(180), unique=True, nullable=False, index=True)
    note: Mapped[str] = mapped_column(String(300), nullable=False, default="")


class StudentInput(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    email: str = Field(min_length=3, max_length=180)
    note: str = Field(default="", max_length=300)


REQUESTS = Counter("crud_requests_total", "CRUD requests", ["operation", "method", "status"])
LATENCY = Histogram(
    "crud_request_duration_seconds", "CRUD request duration in seconds", ["operation"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.2, 0.3, 0.5, 1, 2, 5),
)


def configure_tracing() -> None:
    provider = TracerProvider(resource=Resource.create({"service.name": os.getenv("OTEL_SERVICE_NAME", "taller-crud")}))
    provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))
    trace.set_tracer_provider(provider)
    SQLAlchemyInstrumentor().instrument(engine=engine)


@asynccontextmanager
async def lifespan(_: FastAPI):
    configure_tracing()
    for attempt in range(30):
        try:
            Base.metadata.create_all(engine)
            with Session(engine) as db:
                if db.scalar(select(Student.id).limit(1)) is None:
                    db.add_all([
                        Student(name=f"Estudiante {i}", email=f"estudiante{i}@taller.local", note="Registro semilla")
                        for i in range(1, 101)
                    ])
                    db.commit()
            break
        except Exception:
            if attempt == 29:
                raise
            time.sleep(2)
    yield


app = FastAPI(title="CRUD instrumentado - Taller 4", version="1.0.0", lifespan=lifespan)
FastAPIInstrumentor.instrument_app(app, excluded_urls="health,metrics")


@app.middleware("http")
async def record_metrics(request: Request, call_next):
    path = request.url.path
    operation = "other"
    if path == "/students":
        operation = "list" if request.method == "GET" else "create"
    elif path.startswith("/students/"):
        operation = "read" if request.method == "GET" else "update" if request.method == "PUT" else "delete"
    start = time.perf_counter()
    try:
        response = await call_next(request)
        status = str(response.status_code)
        return response
    except Exception:
        status = "500"
        raise
    finally:
        if operation != "other":
            elapsed = time.perf_counter() - start
            REQUESTS.labels(operation, request.method, status).inc()
            LATENCY.labels(operation).observe(elapsed)


@app.get("/health")
def health():
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))
    return {"status": "ok"}


@app.get("/metrics")
def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.get("/students")
def list_students(limit: int = 100, offset: int = 0):
    with Session(engine) as db:
        rows = db.scalars(select(Student).order_by(Student.id).offset(offset).limit(min(limit, 500))).all()
        return rows


@app.post("/students", status_code=201)
def create_student(payload: StudentInput):
    with Session(engine) as db:
        student = Student(**payload.model_dump())
        db.add(student)
        try:
            db.commit()
            db.refresh(student)
        except Exception as exc:
            db.rollback()
            raise HTTPException(status_code=409, detail="El correo ya existe o el registro no es válido") from exc
        return student


@app.get("/students/{student_id}")
def get_student(student_id: int):
    with Session(engine) as db:
        student = db.get(Student, student_id)
        if student is None:
            raise HTTPException(status_code=404, detail="Estudiante no encontrado")
        return student


@app.put("/students/{student_id}")
def update_student(student_id: int, payload: StudentInput):
    with Session(engine) as db:
        student = db.get(Student, student_id)
        if student is None:
            raise HTTPException(status_code=404, detail="Estudiante no encontrado")
        for key, value in payload.model_dump().items():
            setattr(student, key, value)
        try:
            db.commit()
            db.refresh(student)
        except Exception as exc:
            db.rollback()
            raise HTTPException(status_code=409, detail="El correo ya existe o el registro no es válido") from exc
        return student


@app.delete("/students/{student_id}", status_code=204)
def delete_student(student_id: int):
    with Session(engine) as db:
        student = db.get(Student, student_id)
        if student is None:
            raise HTTPException(status_code=404, detail="Estudiante no encontrado")
        db.delete(student)
        db.commit()

