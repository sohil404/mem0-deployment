# Mem0 Server

This directory contains the Mem0 REST API server, configured for deployment on Railway with Neon PostgreSQL and OpenRouter.

## Configuration

The server is configured via environment variables:

```
OPENROUTER_API_KEY=your_openrouter_api_key
OPENROUTER_MODEL=mistralai/mistral-small

POSTGRES_HOST=your_neon_pg_host
POSTGRES_PORT=5432
POSTGRES_DB=neondb
POSTGRES_USER=your_neon_pg_user
POSTGRES_PASSWORD=your_neon_pg_password
POSTGRES_COLLECTION_NAME=memories
```

## Local Development

1. Create a `.env` file with your configuration (see `.env.example`)
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Run the server:
   ```bash
   uvicorn main:app --reload
   ```
4. Visit http://localhost:8000/docs to view the API documentation

## API Endpoints

- `POST /memories` - Create new memories
- `GET /memories` - Retrieve memories
- `POST /search` - Search for memories
- `GET /memories/{memory_id}` - Retrieve a specific memory
- `PUT /memories/{memory_id}` - Update a memory
- `DELETE /memories/{memory_id}` - Delete a memory
- `DELETE /memories` - Delete all memories for a user
- `POST /reset` - Reset all stored memories

## Deployment

This server is configured for deployment on Railway. The `Dockerfile` provides the containerization, and Railway's environment variables can be used to set the configuration.
