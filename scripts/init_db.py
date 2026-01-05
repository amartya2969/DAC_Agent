"""Initialize database with tables and default data."""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.models import Base, Scope, BaseModel
from src.utils.config import Config
from datetime import datetime


def create_default_scopes(session):
    """Create default scopes."""
    default_scopes = [
        {
            'scope_id': BaseModel.generate_id('scope'),
            'scope_name': 'read:profile',
            'display_name': 'Read Profile',
            'description': 'View your profile information including name, email, and basic details',
            'category': 'profile',
            'sensitive': False
        },
        {
            'scope_id': BaseModel.generate_id('scope'),
            'scope_name': 'write:profile',
            'display_name': 'Update Profile',
            'description': 'Update your profile information',
            'category': 'profile',
            'sensitive': False
        },
        {
            'scope_id': BaseModel.generate_id('scope'),
            'scope_name': 'delete:account',
            'display_name': 'Delete Account',
            'description': 'Permanently delete your account and all associated data',
            'category': 'profile',
            'sensitive': True
        },
        {
            'scope_id': BaseModel.generate_id('scope'),
            'scope_name': 'read:documents',
            'display_name': 'Read Documents',
            'description': 'View your documents and files',
            'category': 'documents',
            'sensitive': False
        },
        {
            'scope_id': BaseModel.generate_id('scope'),
            'scope_name': 'write:documents',
            'display_name': 'Manage Documents',
            'description': 'Create, update, and modify your documents',
            'category': 'documents',
            'sensitive': False
        },
        {
            'scope_id': BaseModel.generate_id('scope'),
            'scope_name': 'delete:documents',
            'display_name': 'Delete Documents',
            'description': 'Permanently delete your documents',
            'category': 'documents',
            'sensitive': True
        },
        {
            'scope_id': BaseModel.generate_id('scope'),
            'scope_name': 'read:email',
            'display_name': 'Read Emails',
            'description': 'Read your emails and messages',
            'category': 'email',
            'sensitive': False
        },
        {
            'scope_id': BaseModel.generate_id('scope'),
            'scope_name': 'send:email',
            'display_name': 'Send Emails',
            'description': 'Send emails on your behalf',
            'category': 'email',
            'sensitive': True
        },
        {
            'scope_id': BaseModel.generate_id('scope'),
            'scope_name': 'read:calendar',
            'display_name': 'Read Calendar',
            'description': 'View your calendar events and appointments',
            'category': 'calendar',
            'sensitive': False
        },
        {
            'scope_id': BaseModel.generate_id('scope'),
            'scope_name': 'write:calendar',
            'display_name': 'Manage Calendar',
            'description': 'Create, update, and delete calendar events',
            'category': 'calendar',
            'sensitive': False
        }
    ]

    for scope_data in default_scopes:
        scope = Scope(
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            **scope_data
        )
        session.add(scope)

    print(f"✓ Created {len(default_scopes)} default scopes")


def init_database():
    """Initialize database with tables and default data."""
    print("Initializing OAuth 2.1 Agent Authentication Flow database...")
    print(f"Database URL: {Config.DATABASE_URL}")

    # Create data directory if using SQLite
    if Config.DATABASE_URL.startswith('sqlite:'):
        os.makedirs('data', exist_ok=True)

    # Create engine and session
    engine = create_engine(Config.DATABASE_URL, echo=False)
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        # Drop all tables if they exist (for clean setup)
        print("\n1. Dropping existing tables (if any)...")
        Base.metadata.drop_all(engine)
        print("✓ Dropped existing tables")

        # Create all tables
        print("\n2. Creating database tables...")
        Base.metadata.create_all(engine)
        print("✓ Created all tables:")
        for table in Base.metadata.tables.keys():
            print(f"   - {table}")

        # Insert default data
        print("\n3. Inserting default data...")
        create_default_scopes(session)

        # Commit changes
        session.commit()
        print("\n✓ Database initialization completed successfully!")

        # Print summary
        print("\n" + "=" * 60)
        print("Database is ready to use!")
        print("=" * 60)
        print("\nNext steps:")
        print("1. Generate RSA keys: python scripts/generate_keys.py")
        print("2. Create .env file: cp .env.example .env")
        print("3. Start authorization server: python -m src.auth_server.app")
        print("=" * 60)

    except Exception as e:
        session.rollback()
        print(f"\n✗ Error initializing database: {str(e)}")
        raise
    finally:
        session.close()


if __name__ == '__main__':
    init_database()
