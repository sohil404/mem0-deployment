import os
from fastapi import FastAPI, HTTPException, Query, Path
from fastapi.responses import JSONResponse, RedirectResponse
from pydantic import BaseModel, Field
from typing import Optional, List, Any, Dict
from mem0 import Memory
from dotenv import load_dotenv
import psycopg2

import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Load environment variables
load_dotenv()

# Database configuration - read from environment variables
POSTGRES_HOST = os.environ.get("POSTGRES_HOST", "postgres")
POSTGRES_PORT = os.environ.get("POSTGRES_PORT", "5432")
POSTGRES_DB = os.environ.get("POSTGRES_DB", "postgres")
POSTGRES_USER = os.environ.get("POSTGRES_USER", "postgres")
POSTGRES_PASSWORD = os.environ.get("POSTGRES_PASSWORD", "postgres")
POSTGRES_COLLECTION_NAME = os.environ.get("POSTGRES_COLLECTION_NAME", "memories")

# Get model configuration
TOGETHER_API_KEY = os.environ.get("TOGETHER_API_KEY")
LLM_MODEL = os.environ.get("LLM_MODEL", "mistralai/Mistral-7B-Instruct-v0.2")
EMBEDDING_MODEL = os.environ.get("EMBEDDING_MODEL", "togethercomputer/m2-bert-80M-8k-retrieval")
HISTORY_DB_PATH = os.environ.get("HISTORY_DB_PATH", "/app/history/history.db")

# Set environment variables that mem0ai uses internally
os.environ["TOGETHER_API_KEY"] = TOGETHER_API_KEY
# OpenAI API key is still needed for some fallback functionality
os.environ["OPENAI_API_KEY"] = TOGETHER_API_KEY

# Initialize database with pgvector extension and required tables
def setup_database():
    try:
        conn = psycopg2.connect(
            host=POSTGRES_HOST,
            port=POSTGRES_PORT,
            dbname=POSTGRES_DB,
            user=POSTGRES_USER,
            password=POSTGRES_PASSWORD
        )
        conn.autocommit = True
        cursor = conn.cursor()
        
        # Create pgvector extension if it doesn't exist
        cursor.execute("SELECT EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'vector')")
        extension_exists = cursor.fetchone()[0]
        
        if not extension_exists:
            logging.info("Creating pgvector extension...")
            cursor.execute("CREATE EXTENSION IF NOT EXISTS vector")
            logging.info("pgvector extension created successfully")
        
        # Check if memories table exists and create it if needed
        cursor.execute(f"""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = '{POSTGRES_COLLECTION_NAME}'
            )
        """)
        table_exists = cursor.fetchone()[0]
        
        if not table_exists:
            logging.info(f"Creating {POSTGRES_COLLECTION_NAME} table...")
            
            # Create the memories table with pgvector support
            # This is a basic schema - mem0ai will typically handle this,
            # but we're creating it just in case
            cursor.execute(f"""
                CREATE TABLE IF NOT EXISTS {POSTGRES_COLLECTION_NAME} (
                    id UUID PRIMARY KEY,
                    content TEXT NOT NULL,
                    metadata JSONB,
                    user_id TEXT,
                    agent_id TEXT,
                    run_id TEXT,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    embedding vector(1536)
                )
            """)
            
            # Add indices for faster queries
            cursor.execute(f"""
                CREATE INDEX IF NOT EXISTS idx_{POSTGRES_COLLECTION_NAME}_user_id ON {POSTGRES_COLLECTION_NAME}(user_id);
                CREATE INDEX IF NOT EXISTS idx_{POSTGRES_COLLECTION_NAME}_agent_id ON {POSTGRES_COLLECTION_NAME}(agent_id);
                CREATE INDEX IF NOT EXISTS idx_{POSTGRES_COLLECTION_NAME}_run_id ON {POSTGRES_COLLECTION_NAME}(run_id);
                CREATE INDEX IF NOT EXISTS idx_{POSTGRES_COLLECTION_NAME}_embedding ON {POSTGRES_COLLECTION_NAME} USING ivfflat (embedding vector_cosine_ops);
            """)
            
            logging.info(f"{POSTGRES_COLLECTION_NAME} table created successfully")
            
        cursor.close()
        conn.close()
        return True
    except Exception as e:
        logging.error(f"Error setting up database: {str(e)}")
        return False

# Make sure the database is properly set up
setup_result = setup_database()
logging.info(f"Database setup result: {setup_result}")

DEFAULT_CONFIG = {
    "version": "v1.1",
    "vector_store": {
        "provider": "pgvector",
        "config": {
            "host": POSTGRES_HOST,
            "port": int(POSTGRES_PORT),
            "dbname": POSTGRES_DB,
            "user": POSTGRES_USER,
            "password": POSTGRES_PASSWORD,
            "collection_name": POSTGRES_COLLECTION_NAME
        }
    },
    "llm": {
        "provider": "together",
        "config": {
            "model": LLM_MODEL,
            "temperature": 0.2,
            "max_tokens": 2000
        }
    },
    "embedder": {
        "provider": "together",
        "config": {
            "model": EMBEDDING_MODEL
        }
    },
    "history_db_path": HISTORY_DB_PATH,
}

# Initialize memory instance with default configuration
try:
    logging.info("Initializing memory with config: %s", DEFAULT_CONFIG)
    MEMORY_INSTANCE = Memory.from_config(DEFAULT_CONFIG)
    logging.info("Memory initialization successful")
except Exception as e:
    logging.error(f"Configuration validation error: {str(e)}")
    raise

app = FastAPI(
    title="Mem0 REST APIs",
    description="A REST API for managing and searching memories for your AI Agents and Apps.",
    version="1.0.0",
)


class Message(BaseModel):
    role: str = Field(..., description="Role of the message (user or assistant).")
    content: str = Field(..., description="Message content.")


class MemoryCreate(BaseModel):
    messages: List[Message] = Field(..., description="List of messages to store.")
    user_id: Optional[str] = None
    agent_id: Optional[str] = None
    run_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class SearchRequest(BaseModel):
    query: str = Field(..., description="Search query.")
    user_id: Optional[str] = None
    run_id: Optional[str] = None
    agent_id: Optional[str] = None
    filters: Optional[Dict[str, Any]] = None


@app.post("/configure", summary="Configure Mem0")
def set_config(config: Dict[str, Any]):
    """Set memory configuration."""
    global MEMORY_INSTANCE
    MEMORY_INSTANCE = Memory.from_config(config)
    return {"message": "Configuration set successfully"}


@app.post("/memories", summary="Create memories")
def add_memory(memory_create: MemoryCreate):
    """Store new memories."""
    if not any([memory_create.user_id, memory_create.agent_id, memory_create.run_id]):
        raise HTTPException(
            status_code=400, detail="At least one identifier (user_id, agent_id, run_id) is required."
        )

    params = {k: v for k, v in memory_create.model_dump().items() if v is not None and k != "messages"}
    try:
        response = MEMORY_INSTANCE.add(messages=[m.model_dump() for m in memory_create.messages], **params)
        return JSONResponse(content=response)
    except Exception as e:
        logging.exception("Error in add_memory:")  # This will log the full traceback
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/memories", summary="Get memories")
def get_all_memories(
    user_id: Optional[str] = None,
    run_id: Optional[str] = None,
    agent_id: Optional[str] = None,
):
    """Retrieve stored memories."""
    if not any([user_id, run_id, agent_id]):
        raise HTTPException(status_code=400, detail="At least one identifier is required.")
    try:
        params = {k: v for k, v in {"user_id": user_id, "run_id": run_id, "agent_id": agent_id}.items() if v is not None}
        return MEMORY_INSTANCE.get_all(**params)
    except Exception as e:
        logging.exception("Error in get_all_memories:")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/memories/{memory_id}", summary="Get a memory")
def get_memory(memory_id: str):
    """Retrieve a specific memory by ID."""
    try:
        return MEMORY_INSTANCE.get(memory_id)
    except Exception as e:
        logging.exception("Error in get_memory:")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/search", summary="Search memories")
def search_memories(search_req: SearchRequest):
    """Search for memories based on a query."""
    try:
        params = {k: v for k, v in search_req.model_dump().items() if v is not None and k != "query"}
        return MEMORY_INSTANCE.search(query=search_req.query, **params)
    except Exception as e:
        logging.exception("Error in search_memories:")
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/memories/{memory_id}", summary="Update a memory")
def update_memory(memory_id: str, updated_memory: Dict[str, Any]):
    """Update an existing memory."""
    try:
        return MEMORY_INSTANCE.update(memory_id=memory_id, data=updated_memory)
    except Exception as e:
        logging.exception("Error in update_memory:")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/memories/{memory_id}/history", summary="Get memory history")
def memory_history(memory_id: str):
    """Retrieve memory history."""
    try:
        return MEMORY_INSTANCE.history(memory_id=memory_id)
    except Exception as e:
        logging.exception("Error in memory_history:")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/memories/{memory_id}", summary="Delete a memory")
def delete_memory(memory_id: str):
    """Delete a specific memory by ID."""
    try:
        MEMORY_INSTANCE.delete(memory_id=memory_id)
        return {"message": "Memory deleted successfully"}
    except Exception as e:
        logging.exception("Error in delete_memory:")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/memories", summary="Delete all memories")
def delete_all_memories(
    user_id: Optional[str] = None,
    run_id: Optional[str] = None,
    agent_id: Optional[str] = None,
):
    """Delete all memories for a given identifier."""
    if not any([user_id, run_id, agent_id]):
        raise HTTPException(status_code=400, detail="At least one identifier is required.")
    try:
        params = {k: v for k, v in {"user_id": user_id, "run_id": run_id, "agent_id": agent_id}.items() if v is not None}
        MEMORY_INSTANCE.delete_all(**params)
        return {"message": "All relevant memories deleted"}
    except Exception as e:
        logging.exception("Error in delete_all_memories:")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/reset", summary="Reset all memories")
def reset_memory():
    """Completely reset stored memories."""
    try:
        MEMORY_INSTANCE.reset()
        return {"message": "All memories reset"}
    except Exception as e:
        logging.exception("Error in reset_memory:")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/", summary="Redirect to the OpenAPI documentation", include_in_schema=False)
def home():
    """Redirect to the OpenAPI documentation."""
    return RedirectResponse(url='/docs')
