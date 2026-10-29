"""
测试公共 fixture

设计要点：
1. 用临时 SQLite 文件（不是 :memory:）让多线程后台任务可访问同一个 DB
2. 覆盖 engine / SessionLocal / get_db，让 app 和后台任务都走测试 DB
3. 提供两个测试用户（alice / bob） + JWT token
4. 提供 client fixture（FastAPI TestClient）
"""
import os
import sys
from pathlib import Path
from datetime import datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# 让 app.* 可被 import
BACKEND_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_ROOT))


# ==================== 1. 临时 DB & 上传目录 ====================

@pytest.fixture(scope="session")
def test_db_file(tmp_path_factory):
    """整个测试 session 共享一个临时 SQLite 文件。"""
    db_dir = tmp_path_factory.mktemp("test_db")
    db_path = db_dir / "test_hr_saas.db"
    yield f"sqlite:///{db_path}"
    if db_path.exists():
        try:
            db_path.unlink()
        except Exception:
            pass


@pytest.fixture(scope="session")
def test_upload_dir(tmp_path_factory):
    """临时上传目录。"""
    upload_dir = tmp_path_factory.mktemp("test_uploads")
    yield str(upload_dir)


# ==================== 2. 重新装配 app 的 engine / DB ====================

@pytest.fixture(scope="session")
def app_module(test_db_file, test_upload_dir):
    """
    加载 app 并把所有数据库相关对象替换为测试版本。

    - engine 指向测试 DB
    - SessionLocal 指向测试 engine
    - settings.UPLOAD_DIR 指向临时目录
    - Base.metadata.create_all 建表
    """
    from app.core import config as cfg
    from app.core import database as db
    from app.models import models as models_mod

    cfg.settings.UPLOAD_DIR = test_upload_dir

    test_engine = create_engine(
        test_db_file,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    db.engine = test_engine
    db.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

    models_mod.Base.metadata.create_all(bind=test_engine)

    from app import main as app_main
    return app_main


@pytest.fixture(scope="session")
def client(app_module):
    """FastAPI TestClient（session 级共享）。"""
    with TestClient(app_module.app) as c:
        yield c


# ==================== 3. 测试用户 + Token ====================

@pytest.fixture(scope="session")
def test_users(app_module):
    """创建两个测试用户（alice / bob），返回 dict。"""
    from app.core.database import SessionLocal
    from app.core.security import get_password_hash
    from app.models.models import User, UserRole

    db = SessionLocal()
    try:
        alice = db.query(User).filter(User.username == "alice").first()
        if not alice:
            alice = User(
                username="alice",
                real_name="Alice 测试",
                email="alice@test.local",
                phone="13800000001",
                role=UserRole.RECRUITER,
                password_hash=get_password_hash("alice123"),
                status=1,
                is_deleted=0,
            )
            db.add(alice)
        bob = db.query(User).filter(User.username == "bob").first()
        if not bob:
            bob = User(
                username="bob",
                real_name="Bob 测试",
                email="bob@test.local",
                phone="13800000002",
                role=UserRole.RECRUITER,
                password_hash=get_password_hash("bob123"),
                status=1,
                is_deleted=0,
            )
            db.add(bob)
        db.commit()
        alice = db.query(User).filter(User.username == "alice").first()
        bob = db.query(User).filter(User.username == "bob").first()
        return {
            "alice": {"id": alice.id, "username": "alice", "real_name": alice.real_name},
            "bob": {"id": bob.id, "username": "bob", "real_name": bob.real_name},
        }
    finally:
        db.close()


@pytest.fixture(scope="session")
def alice_token(app_module, test_users):
    """alice 的 JWT token。"""
    from app.core.security import create_access_token
    return create_access_token(subject={"sub": "alice"})


@pytest.fixture(scope="session")
def bob_token(app_module, test_users):
    """bob 的 JWT token。"""
    from app.core.security import create_access_token
    return create_access_token(subject={"sub": "bob"})


@pytest.fixture
def alice_headers(alice_token):
    """alice 的请求头。"""
    return {"Authorization": f"Bearer {alice_token}"}


@pytest.fixture
def bob_headers(bob_token):
    """bob 的请求头。"""
    return {"Authorization": f"Bearer {bob_token}"}


# ==================== 4. 工具 fixture ====================

@pytest.fixture
def fresh_db(app_module):
    """
    每个用例前后清理：清空操作日志（保留用户）。
    """
    from app.core.database import SessionLocal
    from app.models.models import OperationLog

    db = SessionLocal()
    try:
        db.query(OperationLog).delete()
        db.commit()
    finally:
        db.close()
    yield
    db = SessionLocal()
    try:
        db.query(OperationLog).delete()
        db.commit()
    finally:
        db.close()
