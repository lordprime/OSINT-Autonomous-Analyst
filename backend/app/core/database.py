"""
Database connection managers for OSINT Autonomous Analyst.
Provides connection pools and clients for all data stores.
"""

from neo4j import GraphDatabase
import psycopg_pool
from elasticsearch import Elasticsearch
import weaviate
import redis
from minio import Minio
import logging

from app.core.config import settings

logger = logging.getLogger(__name__)

# ============================================
# Neo4j Graph Database
# ============================================

class Neo4jConnection:
    """Neo4j connection manager with session pooling"""
    
    def __init__(self):
        self._driver = None
    
    def connect(self):
        """Initialize Neo4j driver"""
        try:
            self._driver = GraphDatabase.driver(
                settings.NEO4J_URI,
                auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD),
                max_connection_pool_size=50,
                connection_timeout=30
            )
            logger.info("Neo4j driver initialized")
        except Exception as e:
            logger.error(f"Failed to connect to Neo4j: {e}")
            raise
    
    def close(self):
        """Close Neo4j driver"""
        if self._driver:
            self._driver.close()
            logger.info("Neo4j driver closed")
    
    @property
    def driver(self):
        """Get Neo4j driver instance"""
        if not self._driver:
            self.connect()
        return self._driver
    
    def session(self, **kwargs):
        """Create a new session"""
        return self.driver.session(database=settings.NEO4J_DATABASE, **kwargs)
    
    def verify_connection(self) -> bool:
        """Verify database connection"""
        try:
            with self.session() as session:
                result = session.run("RETURN 1 AS num")
                record = result.single()
                return record["num"] == 1
        except Exception as e:
            logger.error(f"Neo4j connection verification failed: {e}")
            return False

# Initialize Neo4j connection
neo4j_conn = Neo4jConnection()
neo4j_driver = neo4j_conn.driver

# ============================================
# TimescaleDB (PostgreSQL)
# ============================================

class TimescaleConnection:
    """TimescaleDB connection pool manager"""
    
    def __init__(self):
        self._pool = None
    
    def connect(self):
        """Initialize connection pool"""
        try:
            self._pool = psycopg_pool.ConnectionPool(
                conninfo=settings.timescale_dsn,
                min_size=5,
                max_size=20,
                timeout=30
            )
            logger.info("TimescaleDB connection pool initialized")
        except Exception as e:
            logger.error(f"Failed to connect to TimescaleDB: {e}")
            raise
    
    def close(self):
        """Close connection pool"""
        if self._pool:
            self._pool.close()
            logger.info("TimescaleDB connection pool closed")
    
    @property
    def pool(self):
        """Get connection pool"""
        if not self._pool:
            self.connect()
        return self._pool
    
    def connection(self):
        """Get a connection from the pool"""
        return self.pool.connection()

# Initialize TimescaleDB connection
timescale_conn = TimescaleConnection()
timescale_pool = timescale_conn.pool

# ============================================
# Elasticsearch
# ============================================

class ElasticsearchConnection:
    """Elasticsearch client manager"""
    
    def __init__(self):
        self._client = None
    
    def connect(self):
        """Initialize Elasticsearch client"""
        try:
            self._client = Elasticsearch(
                [settings.ELASTICSEARCH_URL],
                request_timeout=30,
                max_retries=3,
                retry_on_timeout=True
            )
            
            # Verify connection
            if self._client.ping():
                logger.info("Elasticsearch client initialized")
            else:
                raise ConnectionError("Elasticsearch ping failed")
        except Exception as e:
            logger.error(f"Failed to connect to Elasticsearch: {e}")
            raise
    
    def close(self):
        """Close Elasticsearch client"""
        if self._client:
            self._client.close()
            logger.info("Elasticsearch client closed")
    
    @property
    def client(self):
        """Get Elasticsearch client"""
        if not self._client:
            self.connect()
        return self._client

# Initialize Elasticsearch connection
es_conn = ElasticsearchConnection()
elasticsearch_client = es_conn.client

# ============================================
# Weaviate Vector Database
# ============================================

class WeaviateConnection:
    """Weaviate client manager"""
    
    def __init__(self):
        self._client = None
    
    def connect(self):
        """Initialize Weaviate client"""
        try:
            self._client = weaviate.Client(
                url=settings.WEAVIATE_URL,
                timeout_config=(5, 30)  # (connect_timeout, read_timeout)
            )
            
            # Verify connection
            if self._client.is_ready():
                logger.info("Weaviate client initialized")
            else:
                raise ConnectionError("Weaviate not ready")
        except Exception as e:
            logger.error(f"Failed to connect to Weaviate: {e}")
            raise
    
    def close(self):
        """Close Weaviate client"""
        if self._client:
            # Weaviate client doesn't have explicit close
            self._client = None
            logger.info("Weaviate client closed")
    
    @property
    def client(self):
        """Get Weaviate client"""
        if not self._client:
            self.connect()
        return self._client

# Initialize Weaviate connection
weaviate_conn = WeaviateConnection()
weaviate_client = weaviate_conn.client

# ============================================
# Redis Cache & Rate Limiting
# ============================================

class RedisConnection:
    """Redis client manager"""
    
    def __init__(self):
        self._client = None
    
    def connect(self):
        """Initialize Redis client"""
        try:
            self._client = redis.from_url(
                settings.REDIS_URL,
                encoding="utf-8",
                decode_responses=True,
                socket_timeout=5,
                socket_connect_timeout=5
            )
            
            # Verify connection
            self._client.ping()
            logger.info("Redis client initialized")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise
    
    def close(self):
        """Close Redis client"""
        if self._client:
            self._client.close()
            logger.info("Redis client closed")
    
    @property
    def client(self):
        """Get Redis client"""
        if not self._client:
            self.connect()
        return self._client

# Initialize Redis connection
redis_conn = RedisConnection()
redis_client = redis_conn.client

# ============================================
# MinIO Object Storage
# ============================================

class MinIOConnection:
    """MinIO client manager"""
    
    def __init__(self):
        self._client = None
    
    def connect(self):
        """Initialize MinIO client"""
        try:
            self._client = Minio(
                settings.MINIO_ENDPOINT,
                access_key=settings.MINIO_ACCESS_KEY,
                secret_key=settings.MINIO_SECRET_KEY,
                secure=settings.MINIO_SECURE
            )
            
            # Create buckets if they don't exist
            for bucket in [settings.MINIO_BUCKET_RAW_DATA, settings.MINIO_BUCKET_AUDIT]:
                if not self._client.bucket_exists(bucket):
                    self._client.make_bucket(bucket)
                    logger.info(f"Created MinIO bucket: {bucket}")
            
            logger.info("MinIO client initialized")
        except Exception as e:
            logger.error(f"Failed to connect to MinIO: {e}")
            raise
    
    @property
    def client(self):
        """Get MinIO client"""
        if not self._client:
            self.connect()
        return self._client

# Initialize MinIO connection
minio_conn = MinIOConnection()
minio_client = minio_conn.client

# ============================================
# Connection Manager
# ============================================

class DatabaseManager:
    """Central database connection manager"""
    
    @staticmethod
    def initialize_all():
        """Initialize all database connections"""
        logger.info("Initializing all database connections...")
        neo4j_conn.connect()
        timescale_conn.connect()
        es_conn.connect()
        weaviate_conn.connect()
        redis_conn.connect()
        minio_conn.connect()
        logger.info("All database connections initialized")
    
    @staticmethod
    def close_all():
        """Close all database connections"""
        logger.info("Closing all database connections...")
        neo4j_conn.close()
        timescale_conn.close()
        es_conn.close()
        weaviate_conn.close()
        redis_conn.close()
        logger.info("All database connections closed")
    
    @staticmethod
    def health_check() -> dict:
        """Check health of all connections"""
        health = {}
        
        # Neo4j
        try:
            health["neo4j"] = neo4j_conn.verify_connection()
        except:
            health["neo4j"] = False
        
        # TimescaleDB
        try:
            with timescale_pool.connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT 1")
            health["timescaledb"] = True
        except:
            health["timescaledb"] = False
        
        # Elasticsearch
        try:
            health["elasticsearch"] = elasticsearch_client.ping()
        except:
            health["elasticsearch"] = False
        
        # Weaviate
        try:
            health["weaviate"] = weaviate_client.is_ready()
        except:
            health["weaviate"] = False
        
        # Redis
        try:
            redis_client.ping()
            health["redis"] = True
        except:
            health["redis"] = False
        
        return health

# Export manager
db_manager = DatabaseManager()
