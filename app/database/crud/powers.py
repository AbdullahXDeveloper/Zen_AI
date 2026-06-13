"""
ZenAI — CRUD: Powers
"""

from sqlalchemy.orm import Session
from app.database.models import Power


def create_power(
    session: Session,
    name: str,
    description: str = None,
    rules: str = None,
    scope: str = "local",
) -> Power:
    """scope: 'universal' | 'local'"""
    power = Power(
        name=name,
        description=description,
        rules=rules,
        scope=scope,
    )
    session.add(power)
    session.commit()
    session.refresh(power)
    return power


def get_power(session: Session, power_id: int) -> Power | None:
    return session.query(Power).filter(Power.id == power_id).first()


def list_powers(
    session: Session,
    scope: str = None,
    name_contains: str = None,
) -> list[Power]:
    q = session.query(Power)
    if scope:
        q = q.filter(Power.scope == scope)
    if name_contains:
        q = q.filter(Power.name.ilike(f"%{name_contains}%"))
    return q.order_by(Power.name.asc()).all()


def update_power(
    session: Session,
    power_id: int,
    **kwargs,
) -> Power | None:
    power = get_power(session, power_id)
    if not power:
        return None

    allowed = {"name", "description", "rules", "scope"}
    for key, val in kwargs.items():
        if key in allowed:
            setattr(power, key, val)

    session.commit()
    session.refresh(power)
    return power


def delete_power(session: Session, power_id: int) -> bool:
    power = get_power(session, power_id)
    if not power:
        return False
    session.delete(power)
    session.commit()
    return True
