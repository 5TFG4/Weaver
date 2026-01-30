"""
WallE - Persistence Layer

Centralized data persistence for Weaver:
- Database session management
- SQLAlchemy models (runs, orders, fills, candles)
- Repository pattern for data access
- Event-driven write handlers

All business data writes go through WallE.
Every table has: id, created_at (UTC), updated_at (UTC)
"""
