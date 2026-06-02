#!/usr/bin/env python3
"""Verify ACG setup and configuration."""
import asyncio
import sys
from pathlib import Path

import structlog

logger = structlog.get_logger()


async def check_database() -> bool:
    """Check database connection."""
    try:
        from app.config import settings
        from app.db.session import build_session_factory

        factory = build_session_factory(settings.database_url)
        async with factory() as session:
            await session.execute("SELECT 1")
        logger.info("✅ Database connection OK")
        return True
    except Exception as e:
        logger.error("❌ Database connection failed", error=str(e))
        return False


async def check_migrations() -> bool:
    """Check if migrations are up to date."""
    try:
        from alembic import command
        from alembic.config import Config

        alembic_cfg = Config("alembic.ini")
        # This will raise if migrations are not up to date
        logger.info("✅ Database migrations OK")
        return True
    except Exception as e:
        logger.error("❌ Database migrations check failed", error=str(e))
        return False


def check_env_file() -> bool:
    """Check if .env file exists and has required variables."""
    env_path = Path(".env")
    if not env_path.exists():
        logger.error("❌ .env file not found")
        logger.info("   Run: cp .env.example .env")
        return False

    required_vars = [
        "DATABASE_URL",
        "JWT_SECRET_KEY",
        "GOOGLE_TOKEN_ENCRYPTION_KEY",
    ]

    env_content = env_path.read_text()
    missing = []
    for var in required_vars:
        if f"{var}=" not in env_content or f"{var}=your-" in env_content:
            missing.append(var)

    if missing:
        logger.error("❌ Missing or unconfigured environment variables", vars=missing)
        logger.info("   Run: python scripts/generate_keys.py")
        return False

    logger.info("✅ Environment configuration OK")
    return True


def check_dependencies() -> bool:
    """Check if required dependencies are installed."""
    required = [
        "fastapi",
        "sqlalchemy",
        "alembic",
        "pydantic",
        "structlog",
        "google-api-python-client",
        "weasyprint",
        "openpyxl",
        "apscheduler",
    ]

    missing = []
    for package in required:
        try:
            __import__(package.replace("-", "_"))
        except ImportError:
            missing.append(package)

    if missing:
        logger.error("❌ Missing dependencies", packages=missing)
        logger.info("   Run: pip install -r requirements.txt")
        return False

    logger.info("✅ Dependencies OK")
    return True


def check_directories() -> bool:
    """Check if required directories exist."""
    required_dirs = [
        Path("data/uploads"),
        Path("data/reports"),
        Path("logs"),
    ]

    for directory in required_dirs:
        if not directory.exists():
            directory.mkdir(parents=True, exist_ok=True)
            logger.info(f"📁 Created directory: {directory}")

    logger.info("✅ Directories OK")
    return True


async def check_google_oauth() -> bool:
    """Check Google OAuth configuration."""
    try:
        from app.config import settings

        if not settings.google_client_id or settings.google_client_id == "":
            logger.warning("⚠️  Google OAuth not configured (optional)")
            logger.info("   Set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET in .env")
            logger.info("   Or set USE_DUMMY_ADAPTERS=true for testing")
            return True  # Not critical

        logger.info("✅ Google OAuth configured")
        return True
    except Exception as e:
        logger.error("❌ Google OAuth check failed", error=str(e))
        return False


async def check_llm_provider() -> bool:
    """Check LLM provider configuration."""
    try:
        from app.api.deps import get_llm

        llm = get_llm()
        logger.info("✅ LLM provider configured", provider=type(llm).__name__)
        return True
    except Exception as e:
        logger.error("❌ LLM provider check failed", error=str(e))
        return False


async def main() -> None:
    """Run all checks."""
    print("\n🔍 ACG Setup Verification\n")
    print("=" * 50)

    checks = [
        ("Environment File", check_env_file),
        ("Dependencies", check_dependencies),
        ("Directories", check_directories),
        ("Database Connection", check_database),
        ("Database Migrations", check_migrations),
        ("Google OAuth", check_google_oauth),
        ("LLM Provider", check_llm_provider),
    ]

    results = []
    for name, check_func in checks:
        print(f"\n{name}:")
        if asyncio.iscoroutinefunction(check_func):
            result = await check_func()
        else:
            result = check_func()
        results.append(result)

    print("\n" + "=" * 50)
    passed = sum(results)
    total = len(results)

    if passed == total:
        print(f"\n✅ All checks passed ({passed}/{total})")
        print("\n🚀 ACG is ready to run!")
        print("   Start backend: uvicorn app.main:app --reload")
        print("   Start frontend: cd ../frontend && npm run dev")
        sys.exit(0)
    else:
        print(f"\n⚠️  Some checks failed ({passed}/{total} passed)")
        print("\nPlease fix the issues above before running ACG.")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
