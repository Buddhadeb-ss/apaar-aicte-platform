"""
Database Initialization & Synthetic Seed Script for SIH26263 APAAR Platform
"""
import os
from app.database.session import engine, Base, SessionLocal
from app.database.seed_data import seed_database

def main():
    print("Dropping existing tables to ensure clean schema sync...")
    Base.metadata.drop_all(bind=engine)
    print("Creating new relational schema...")
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    print("Seeding database with statutory institutions, programmes, courses, intakes, and students...")
    seed_database(db, force_reset=True)
    db.close()
    print("Database initialization complete! Persistent SQLite file is ready.")

if __name__ == "__main__":
    main()
