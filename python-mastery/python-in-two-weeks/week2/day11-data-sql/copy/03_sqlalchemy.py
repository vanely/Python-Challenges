"""Day 11 — SQLAlchemy 2.0 ORM, minimal. pip install sqlalchemy"""
from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import ForeignKey, String, create_engine, func, select
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, relationship, selectinload


class Base(DeclarativeBase):
    pass


class Note(Base):
    __tablename__ = "notes"
    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(120))
    body: Mapped[str] = mapped_column(default="")
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(UTC))
    tags: Mapped[list[Tag]] = relationship(back_populates="note", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"Note(id={self.id}, title={self.title!r})"


class Tag(Base):
    __tablename__ = "tags"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(40))
    note_id: Mapped[int] = mapped_column(ForeignKey("notes.id"))
    note: Mapped[Note] = relationship(back_populates="tags")


engine = create_engine("sqlite+pysqlite:///:memory:", echo=False)
Base.metadata.create_all(engine)

with Session(engine) as session, session.begin():          # unit of work + transaction
    session.add_all([
        Note(title="A", tags=[Tag(name="x"), Tag(name="y")]),
        Note(title="B", tags=[Tag(name="x")]),
        Note(title="C"),
    ])

with Session(engine) as session:
    # select + where; scalars() unwraps single-entity rows
    notes = session.scalars(select(Note).where(Note.title != "C").order_by(Note.title)).all()
    print(notes)

    # avoid N+1: eager-load the relationship
    stmt = select(Note).options(selectinload(Note.tags))
    for n in session.scalars(stmt):
        print(n.title, [t.name for t in n.tags])

    # aggregate via Core-style expressions
    stmt2 = select(Tag.name, func.count()).group_by(Tag.name).order_by(func.count().desc())
    print(session.execute(stmt2).all())

    # update + delete
    a = session.scalar(select(Note).where(Note.title == "A"))
    assert a is not None
    a.body = "edited"
    session.delete(session.scalar(select(Note).where(Note.title == "C")))
    session.commit()
    print(session.scalar(select(func.count()).select_from(Note)))
