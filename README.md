# ai-interview-backend

```
ai-interview-backend/
├── app/
│   ├── __init__.py
│   ├── main.py
│   ├── api/
│   │   ├── __init__.py
│   │   └── v1/
│   │       ├── __init__.py
│   │       └── endpoints/
│   │           ├── __init__.py
│   │           └── example.py
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py
│   │   ├── security.py
│   │   └── exceptions.py
│   ├── models/
│   │   ├── __init__.py
│   │   └── user.py
│   ├── schemas/
│   │   ├── __init__.py
│   │   └── user.py
│   ├── crud/
│   │   ├── __init__.py
│   │   └── user.py
│   ├── db/
│   │   ├── __init__.py
│   │   ├── base.py
│   │   └── session.py
│   ├── services/
│   │   ├── __init__.py
│   │   └── user_service.py
│   ├── utils/
│   │   ├── __init__.py
│   │   └── helpers.py
│   ├── tests/
│   │   ├── __init__.py
│   │   └── test_example.py
├── alembic/
│   ├── versions/
│   ├── env.py
│   └── alembic.ini
├── scripts/
│   ├── __init__.py
│   └── data_migration.py
├── docs/
│   ├── __init__.py
│   └── api_documentation.md
├── .env
├── .env.example
├── requirements/
│   ├── base.txt
│   ├── dev.txt
│   └── prod.txt
├── Dockerfile
├── docker-compose.yml
└── README.md
```