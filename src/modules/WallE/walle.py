import os

from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import datetime

sql_user = os.getenv('POSTGRES_USER')
sql_password = os.getenv('POSTGRES_PASSWORD')

DATABASE_URL = "postgresql+psycopg2://"+sql_user+":"+sql_password+"@db:5432/weaverdb"

Base = declarative_base()

class TradeRecord(Base):
    __tablename__ = 'trade_records'

    id = Column(Integer, primary_key=True)
    trade_date = Column(DateTime, default=datetime.datetime.utcnow)
    asset = Column(String)
    volume = Column(Float)
    price = Column(Float)


engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    Base.metadata.create_all(bind=engine)

def create_trade_record(asset, volume, price):
    with SessionLocal() as session:
        new_record = TradeRecord(
            asset=asset,
            volume=volume,
            price=price
        )
        session.add(new_record)
        session.commit()

def get_trade_records():
    with SessionLocal() as session:
        records = session.query(TradeRecord).all()
        for record in records:
            print(f"ID: {record.id}, Asset: {record.asset}, Volume: {record.volume}, Price: {record.price}")

if __name__ == "__main__":
    init_db()
    create_trade_record("AAPL", 150, 145.30)
    get_trade_records()
