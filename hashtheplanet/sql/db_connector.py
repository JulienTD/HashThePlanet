"""
This module handles connections and requests to the database
"""
# standard imports
from json import JSONEncoder, loads

# third party imports
from loguru import logger
from sqlalchemy import Column, Text, JSON
from sqlalchemy import select, update
from sqlalchemy.ext.declarative import declarative_base, declared_attr


Base = declarative_base()

class Version(Base):
    """
    This class is a model for version table
    """
    @declared_attr
    def __tablename__(cls): # pylint: disable=no-self-argument
        return cls.__name__.lower()

    technology = Column(Text, nullable=False, primary_key=True)
    version = Column(Text, nullable=False, primary_key=True)

    def __repr__(self):
        return f"Version (technology={self.technology}, version={self.version})"

class File(Base):
    """
    This class is a model for file table
    """
    @declared_attr
    def __tablename__(cls): # pylint: disable=no-self-argument
        return cls.__name__.lower()

    technology = Column(Text, nullable=False, primary_key=True)
    path = Column(Text, nullable=False, primary_key=True)

    def __repr__(self):
        return f"File (technology={self.technology}, path={self.path})"

class Hash(Base):
    """
    This class is a model for hash table
    """
    @declared_attr
    def __tablename__(cls): # pylint: disable=no-self-argument
        return cls.__name__.lower()

    hash = Column(Text, nullable=False, primary_key=True)
    technology = Column(Text, nullable=False)
    versions = Column(JSON, nullable=False)

    def __repr__(self):
        return f"Hash (hash={self.hash}, technology={self.technology}, versions={self.versions})"

class DbConnector():
    """
    This class implements method to connect to and request the database.
    """
    @staticmethod
    def insert_version(session, technology, version):
        """
        Insert a new version related to technology in version table if it does not exist yet.
        """
        stmt = select(Version).filter_by(technology=technology, version=str(version))
        entry = session.execute(stmt).scalar_one_or_none()

        if not entry:
            new_version = Version(technology=technology, version=str(version))
            session.add(new_version)
            logger.info(f"Entry {new_version} added to version database")
        else:
            logger.debug(f"Entry {entry} already exists in versions database")

    def insert_versions(self, session, technology, versions):
        """
        Insert a list of versions related to technology.
        """
        for _, version in enumerate(versions):
            self.insert_version(session, technology, version)

    @staticmethod
    def get_versions(session, technology):
        """
        Returns all the versions related to technology.
        """
        stmt = select(Version).filter_by(technology=technology)
        versions = session.execute(stmt).scalars().all()
        return versions

    @staticmethod
    def insert_file(session, technology, path):
        """
        Insert a new file related to technology in file table if it does not exist yet.
        """
        stmt = select(File).filter_by(technology=technology, path=path)
        entry = session.execute(stmt).scalar_one_or_none()

        if not entry:
            new_file = File(technology=technology, path=path)
            session.add(new_file)
            logger.info(f"Entry {new_file} added to file database")
        else:
            logger.debug(f"Entry {entry} already exists in files database")

    @staticmethod
    def insert_or_update_hash(session, hash_value, technology, version):
        """
        Insert a new hash related to technology and version in hash table if it does not exist yet.
        If it already exists, update related versions.
        """
        stmt = select(Hash).filter_by(hash=hash_value)
        entry = session.execute(stmt).scalar_one_or_none()

        if not entry:
            new_hash = Hash(hash=hash_value, technology=technology, versions=JSONEncoder() \
                .encode({"versions": [version]}))
            session.add(new_hash)
            logger.info(f"Entry {new_hash} added to hash database")
        else:
            existing_versions = loads(entry.versions)["versions"]

            if version not in existing_versions:
                existing_versions.append(version)
                new_versions = existing_versions
                stmt = update(Hash).where(Hash.hash==hash_value) \
                    .values(versions=JSONEncoder().encode({"versions": new_versions})) \
                        .execution_options(synchronize_session="fetch")
                session.execute(stmt)
                logger.debug(f"Entry {entry} updated with new versions {new_versions}")
            else:
                logger.debug(f"Version {version} already registered for hash {entry.hash}")

    @staticmethod
    def get_all_hashs(session):
        """
        Returns all the hashs already computed.
        """
        stmt = select(Hash)
        hashs = session.execute(stmt).scalars().all()
        return hashs

    @staticmethod
    def find_hash(session, hash_str: str):
        """
        Returns the technology and its versions from a hash.
        """
        return session.query(Hash.technology, Hash.versions).filter(Hash.hash == hash_str).first()

    @staticmethod
    def get_static_files(session):
        """
        Returns all files ending with .html, .md or .txt
        """
        static_files_query = session \
                            .query(File.path) \
                            .filter(File.path.regexp_match(r"([a-zA-Z0-9\s_\\.\-\(\):])+(.html|.md|.txt)$"))
        return [path for path, in static_files_query]