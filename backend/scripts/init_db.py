#!/usr/bin/env python3
"""Initialize ACG database with sample data."""
import asyncio
import uuid
from datetime import UTC, datetime

import structlog

from app.config import settings
from app.core.services.auth_service import hash_password
from app.db.models import User
from app.db.session import build_session_factory

logger = structlog.get_logger()


async def create_admin_user(session) -> User:
    """Create default admin user."""
    admin_email = "admin@acg.local"
    admin_password = "admin123"  # Change in production!

    # Check if admin exists
    from sqlalchemy import select

    result = await session.execute(select(User).where(User.email == admin_email))
    existing = result.scalar_one_or_none()

    if existing:
        logger.info("admin_user_exists", email=admin_email)
        return existing

    # Create admin user
    admin = User(
        id=uuid.uuid4(),
        email=admin_email,
        hashed_password=hash_password(admin_password),
        name="Administrator",
        role="owner",
        notification_settings={
            "email_enabled": True,
            "in_app_enabled": True,
            "digest_frequency": "daily",
        },
    )

    session.add(admin)
    await session.commit()
    await session.refresh(admin)

    logger.info("admin_user_created", email=admin_email, user_id=str(admin.id))
    return admin


async def create_sample_escalation_rules(session, user_id: uuid.UUID) -> None:
    """Create sample escalation rules."""
    from app.db.models import EscalationRule

    rules = [
        {
            "name": "Scadenza Fiscale Standard",
            "deadline_type": "fiscale",
            "steps": [
                {
                    "delay_seconds": 14400,  # 4 hours
                    "channel": "in_app",
                    "recipient": str(user_id),
                    "message_template": "Promemoria: scadenza fiscale in arrivo",
                },
                {
                    "delay_seconds": 86400,  # 24 hours
                    "channel": "email",
                    "recipient": "admin@acg.local",
                    "message_template": "URGENTE: Scadenza fiscale non gestita",
                },
            ],
        },
        {
            "name": "Pagamento Fornitore",
            "deadline_type": "pagamento",
            "steps": [
                {
                    "delay_seconds": 28800,  # 8 hours
                    "channel": "in_app",
                    "recipient": str(user_id),
                    "message_template": "Promemoria: pagamento fornitore in scadenza",
                },
                {
                    "delay_seconds": 172800,  # 48 hours
                    "channel": "email",
                    "recipient": "admin@acg.local",
                    "message_template": "Pagamento fornitore non effettuato",
                },
            ],
        },
    ]

    for rule_data in rules:
        # Check if exists
        from sqlalchemy import select

        result = await session.execute(
            select(EscalationRule).where(
                EscalationRule.user_id == user_id,
                EscalationRule.name == rule_data["name"],
            )
        )
        if result.scalar_one_or_none():
            logger.info("escalation_rule_exists", name=rule_data["name"])
            continue

        rule = EscalationRule(
            id=uuid.uuid4(),
            user_id=user_id,
            name=rule_data["name"],
            deadline_type=rule_data["deadline_type"],
            steps=rule_data["steps"],
            is_active=True,
        )
        session.add(rule)
        logger.info("escalation_rule_created", name=rule_data["name"])

    await session.commit()


async def main() -> None:
    """Initialize database with sample data."""
    print("\n🗄️  ACG Database Initialization\n")
    print("=" * 50)

    try:
        factory = build_session_factory(settings.database_url)
        async with factory() as session:
            # Create admin user
            print("\n1. Creating admin user...")
            admin = await create_admin_user(session)
            print(f"   ✅ Admin user: {admin.email}")
            print(f"   🔑 Password: admin123 (change in production!)")

            # Create sample escalation rules
            print("\n2. Creating sample escalation rules...")
            await create_sample_escalation_rules(session, admin.id)
            print("   ✅ Escalation rules created")

        print("\n" + "=" * 50)
        print("\n✅ Database initialized successfully!")
        print("\n📝 Next steps:")
        print("   1. Login with admin@acg.local / admin123")
        print("   2. Change admin password in Settings")
        print("   3. Configure Google OAuth in Settings > Sorgenti")
        print("   4. Upload your first document")

    except Exception as e:
        logger.error("database_init_failed", error=str(e))
        print(f"\n❌ Database initialization failed: {e}")
        print("\nMake sure:")
        print("   1. PostgreSQL is running")
        print("   2. Database exists (createdb acg)")
        print("   3. Migrations are up to date (alembic upgrade head)")
        raise


if __name__ == "__main__":
    asyncio.run(main())
