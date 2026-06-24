from db2 import engine
from models2 import Base

Base.metadata.create_all(bind=engine)
print("Tables created")