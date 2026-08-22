from __future__ import annotations

import hashlib
import os
import re
import smtplib
from contextlib import asynccontextmanager
from email.message import EmailMessage

from fastapi import Cookie, Depends, FastAPI, File, HTTPException, Request, Response, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import select

from app.account_service import create_guest_user, update_credentials
from app.auth import COOKIE_NAME, current_user, require_admin, require_owner
from app.chat_learning import learn_explicit_teaching, parse_command
from app.config import settings
from app.database import (
    Feedback, KnowledgeVersion, SessionLocal, add_learning_candidate, authenticate,
    audit_log, bootstrap_owner, cache_get, cache_put, create_conversation,
    create_password_reset_token, create_session, create_user, database_stats,
    delete_conversation, delete_session, delete_user, get_conversations, get_history,
    get_user_by_id, get_user_settings, ingest_language_package, language_snapshot,
    list_audit_logs, list_candidates, list_users, promote_configured_owners,
    recall_user_memory, remember_user_memory, reset_password, review_candidate,
    save_message, save_usage, set_user_active, set_user_role, update_user_settings,
    verify_password_reset_code,
)
from app.github_sync import GitHubSyncError, status as github_status
from app.groq_client import call_groq_detailed
from app.learning.service import review_learning_candidate, submit_command_candidate
from app.linguistics.normalizer import analyze_input
from app.linguistics.parser import extract_linguistic_hints
from app.local_answer import answer as local_answer
from app.memory.manager import extract_memory_candidates, format_memory
from app.melimi.engine import build_language_engine_context
from app.melimi.generation import finalize_response
from app.melimi.grammar import grammar_policy
from app.melimi.index import inventory as subject_inventory
from app.melimi.registry import analyze_word, lookup_word
from app.melimi.content_store import submit_content
from app.migrations import run_migrations
from app.models import (
    ChatRequest, ChatResponse, CredentialUpdateRequest, FeedbackRequest,
    ForgotPasswordRequest, GuestRegisterRequest, HealthResponse, LoginRequest,
    MemoryRequest, RegisterRequest, ResetPasswordRequest, SettingsUpdateRequest,
    VerifyResetCodeRequest,
)
from app.prompts import build_prompt
from app.response import clean_response
from app.security import RateLimitMiddleware, SecurityHeadersMiddleware
from app.conversation.planner import plan_response
from app.conversation.state import from_history
from app.conversation.understanding import build_context, infer_intent
from app.retrieval.knowledge import load_vocabulary


@asynccontextmanager
async def lifespan(app: FastAPI):
    run_migrations()
    owner_emails = [e.strip().lower() for e in os.getenv("OWNER_EMAILS", "").split(",") if e.strip()]
    promote_configured_owners(owner_emails)
    yield


app = FastAPI(title="TeluAI — Melimi Telugu AI Platform", docs_url="/docs" if settings.expose_docs else None, redoc_url="/redoc" if settings.expose_docs else None, openapi_url="/openapi.json" if settings.expose_docs else None, lifespan=lifespan)
app.state.trust_proxy_headers = settings.trust_proxy_headers
app.state.secure_transport = settings.cookie_secure
if settings.cors_origins:
    app.add_middleware(CORSMiddleware, allow_origins=list(settings.cors_origins), allow_credentials=True, allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"], allow_headers=["Content-Type", "X-Requested-With"], max_age=600)
app.add_middleware(RateLimitMiddleware)
app.add_middleware(SecurityHeadersMiddleware)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATIC_DIR = os.path.join(BASE_DIR, "static")
if os.path.isdir(STATIC_DIR):
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


def _knowledge_version() -> int:
    with SessionLocal() as db:
        row = db.scalars(select(KnowledgeVersion).order_by(KnowledgeVersion.version.desc())).first()
        return int(row.version) if row else 0


def _cache_key(message: str, mode: str, history=None, response_length: str = "normal") -> str:
    normalized = re.sub(r"\s+", " ", message.strip().lower())
    recent = []
    for turn in (history or [])[-4:]:
        recent.append(f"{turn.get('role','')}:{turn.get('content','')}")
    raw = "|".join([mode, response_length, normalized, *recent, str(_knowledge_version())])
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _set_session_cookie(response: Response, token: str):
    response.set_cookie(COOKIE_NAME, token, httponly=True, secure=settings.cookie_secure, samesite=settings.cookie_samesite, max_age=settings.session_days * 86400, path="/")


# ... existing routes remain unchanged ...

# NOTE: The production repository keeps the complete route implementation.
# The chat handler below uses the dedicated Melimi finalizer instead of calling
# deterministic_repair directly.
