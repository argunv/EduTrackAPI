#!/usr/bin/env python3
"""Скрипт для создания суперпользователя."""

import asyncio
import getpass
import sys
import uuid
from datetime import datetime
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from edutrack.config.settings import Settings
from edutrack.infrastructure.services.security import hash_password


def get_local_database_url() -> str:
    settings = Settings()
    return settings.database_url.replace("@postgres:", "@localhost:").replace("postgres:5432", "localhost:5432")


async def create_superuser():
    print("Создание суперпользователя")
    print("=" * 50)
    
    engine = create_async_engine(get_local_database_url(), echo=False)
    
    try:
        email = input("Email: ").strip()
        full_name = input("Полное имя: ").strip()
        password = getpass.getpass("Пароль: ")
        
        if getpass.getpass("Повторите пароль: ") != password:
            print("Ошибка: Пароли не совпадают")
            sys.exit(1)
        
        async with engine.begin() as conn:
            if await conn.scalar(text("SELECT id FROM users WHERE email = :email"), {"email": email}):
                print(f"Ошибка: Пользователь с email '{email}' уже существует")
                sys.exit(1)
            
            await conn.execute(
                text("""
                    INSERT INTO users (id, email, full_name, password_hash, role, created_at)
                    VALUES (:id, :email, :full_name, :password_hash, 'admin', :created_at)
                """),
                {
                    "id": uuid.uuid4(),
                    "email": email,
                    "full_name": full_name,
                    "password_hash": hash_password(password),
                    "created_at": datetime.utcnow(),
                }
            )
        
        print(f"\n✓ Суперпользователь '{email}' успешно создан!")
    
    except Exception as e:
        print(f"\n✗ Ошибка: {e}")
        sys.exit(1)
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(create_superuser())
