"""Obsidian vault ingestion service for Neo4j graph database.

This module provides functionality to parse, chunk, embed, and ingest Obsidian markdown
notes into a Neo4j graph database. It extracts notes, chunks them for vector search,
generates embeddings, and stores them with relationships (folders, tags, links) in Neo4j.

The service supports:
- Parsing Obsidian markdown files with frontmatter
- Character-based chunking with overlap
- Embedding generation using configured models
- Graph storage with Note, Chunk, Folder, Tag, and Link relationships
- Vector similarity search via Neo4j vector indexes
"""

import logging
import os
import re
import hashlib
import yaml
from typing import TypedDict, List, Optional
from pathlib import Path
from neo4j import GraphDatabase, Driver
from advanced_omi_backend.services.memory.providers.llm_providers import _get_openai_client
from advanced_omi_backend.services.memory.config import load_config_yml as load_root_config

logger = logging.getLogger(__name__)

class NoteData(TypedDict):
    path: str
    name: str
    folder: str
    content: str
    wordcount: int
    links: List[str]
    tags: List[str]

class ChunkPayload(TypedDict):
    text: str
    embedding: List[float]

def load_env_file(filepath: Path) -> dict[str, str]:
    """Load environment variables from a .env file.
    
    Args:
        filepath: Path to the .env file to load.
    
    Returns:
        Dictionary of key-value pairs from the .env file.
    """
    env_vars = {}
    if filepath.exists():
        with open(filepath, 'r') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                if '=' in line:
                    parts = line.split('=', 1)
                    key = parts[0].strip()
                    value = parts[1].strip() if len(parts) > 1 else ""
                    # Handle quotes
                    if (value.startswith("'") and value.endswith("'")) or (value.startswith('"') and value.endswith('"')):
                        value = value[1:-1]
                    env_vars[key] = value
    return env_vars

def resolve_value(value: str | int | float) -> str | int | float:
    """Resolve environment variable references in configuration values.
    
    Supports ${VAR} and ${VAR:-default} syntax. Returns the original value
    if it's not a string or doesn't match the pattern.
    """
    if isinstance(value, str) and value.startswith("${") and value.endswith("}"):
        content = value[2:-1]
        if ":-" in content:
            var_name, default_val = content.split(":-", 1)
            # Try to get from real environment first, then default
            return os.getenv(var_name, default_val)
        else:
            return os.getenv(content, "")
    return value

class ObsidianService:
    """Service for ingesting Obsidian vaults into Neo4j graph database."""
    
    def __init__(self):
        """Initialize the Obsidian service with configuration from config.yml and environment."""
        # Resolve paths relative to this file
        # backends/advanced/src/advanced_omi_backend/services/obsidian_service.py
        self.CURRENT_DIR = Path(__file__).parent.resolve()

        # Load configuration strictly from standard locations
        # Prefer /app/config.yml inside containers (mounted by docker-compose)
        # Fallbacks handled by shared utility
        config_data = load_root_config()

        # Helper to get model config
        def get_model_config(model_role: str):
            default_name = config_data.get('defaults', {}).get(model_role)
            if not default_name:
                raise ValueError(f"Configuration for 'defaults.{model_role}' not found in config.yml")
            for model in config_data.get('models', []):
                if model.get('name') == default_name:
                    return model
            raise ValueError(f"Configuration for 'defaults.{model_role}' not found in config.yml")

        llm_config = get_model_config('llm')
        if not llm_config:
            raise ValueError("Configuration for 'defaults.llm' not found in config.yml")

        embed_config = get_model_config('embedding')
        if not embed_config:
            raise ValueError("Configuration for 'defaults.embedding' not found in config.yml")

        # Neo4j Connection - Prefer environment variables passed by Docker Compose
        neo4j_host = os.getenv("NEO4J_HOST")
        # Load .env file as fallback (for local dev or if env vars not set)
        candidate_env_files = [
            Path("/app/.env"),
            self.CURRENT_DIR.parent.parent.parent.parent / ".env",          # /app/.env when running in container
            self.CURRENT_DIR.parent.parent.parent.parent / "backends" / "advanced" / ".env",  # repo path
        ]
        env_data = {}
        for p in candidate_env_files:
            if p.exists():
                env_data.update(load_env_file(p))
        
        # Use env var first, then fallback to .env file
        if not neo4j_host:
            neo4j_host = env_data.get("NEO4J_HOST")

        if not neo4j_host:
            raise KeyError("NEO4J_HOST not found in environment or .env")

        self.neo4j_uri = f"bolt://{neo4j_host}:7687"
        self.neo4j_user = os.getenv("NEO4J_USER") or env_data.get("NEO4J_USER", "neo4j")
        self.neo4j_password = os.getenv("NEO4J_PASSWORD") or env_data.get("NEO4J_PASSWORD", "")

        # Models / API - Loaded strictly from config.yml
        self.embedding_model = str(resolve_value(embed_config['model_name']))
        self.embedding_dimensions = int(resolve_value(embed_config['embedding_dimensions']))
        self.openai_base_url = str(resolve_value(llm_config['model_url']))
        self.openai_api_key = str(resolve_value(llm_config['api_key']))

        # Chunking - can have defaults
        self.chunk_char_limit = 1000
        self.chunk_overlap = 200
        
        self.client = _get_openai_client(
            api_key=self.openai_api_key,
            base_url=self.openai_base_url,
            is_async=False
        )
        
        self.driver: Optional[Driver] = None

    def _get_driver(self) -> Driver:
        """Get or create Neo4j driver connection.
        
        Returns:
            Neo4j driver instance, creating it if it doesn't exist.
        """
        if not self.driver:
            # Use basic auth when both user and password are provided; otherwise connect without auth
            self.driver = GraphDatabase.driver(
                    self.neo4j_uri, 
                    auth=(self.neo4j_user, self.neo4j_password)
                )
        return self.driver

    def close(self):
        """Close the Neo4j driver connection and clean up resources."""
        if self.driver:
            self.driver.close()
            self.driver = None

    def reset_driver(self):
        """Reset the driver connection, forcing it to be recreated with current credentials."""
        self.close()

    def setup_database(self) -> None:
        """Create database constraints and vector index for notes and chunks."""
        # Reset driver to ensure we use current credentials
        self.reset_driver()
        driver = self._get_driver()
        with driver.session() as session:
            session.run("CREATE CONSTRAINT note_path IF NOT EXISTS FOR (n:Note) REQUIRE n.path IS UNIQUE")
            session.run("CREATE CONSTRAINT chunk_id IF NOT EXISTS FOR (c:Chunk) REQUIRE c.id IS UNIQUE")
            index_query = f"""
            CREATE VECTOR INDEX chunk_embeddings IF NOT EXISTS
            FOR (c:Chunk) ON (c.embedding)
            OPTIONS {{indexConfig: {{
             `vector.dimensions`: {self.embedding_dimensions},
             `vector.similarity_function`: 'cosine'
            }}}}
            """
            session.run(index_query)

    def get_embedding(self, text: str) -> Optional[List[float]]:
        """Generate embedding vector for text using the configured embedding model.
        
        Args:
            text: Text to generate embedding for.
        
        Returns:
            Embedding vector as list of floats, or None if generation fails.
        """
        try:
            clean_text = re.sub(r'\s+', ' ', text).strip()
            if not clean_text: return None
            
            response = self.client.embeddings.create(input=[clean_text], model=self.embedding_model)
            return response.data[0].embedding
        except Exception as e:
            logger.error(f"Embedding failed for text length {len(text)}: {e}")
            return None

    def character_chunker(self, text: str) -> List[str]:
        """Split text into overlapping character-based chunks.
        
        Args:
            text: Text to chunk.
        
        Returns:
            List of text chunks with configured overlap.
        """
        chunks = []
        start = 0
        limit = self.chunk_char_limit
        overlap = self.chunk_overlap
        while start < len(text):
            end = start + limit
            chunk = text[start:end]
            chunks.append(chunk)
            if end >= len(text):
                break
            start += (limit - overlap)
        return chunks

    def parse_obsidian_note(self, root: str, filename: str, vault_path: str) -> NoteData:
        """Parse an Obsidian markdown file and extract metadata.
        
        Args:
            root: Directory containing the file.
            filename: Name of the markdown file.
            vault_path: Root path of the Obsidian vault.
        
        Returns:
            NoteData dictionary with parsed content, links, tags, and metadata.
        """
        full_path = os.path.join(root, filename)
        # Vault path might be relative or absolute, handle it
        try:
            rel_path = os.path.relpath(full_path, vault_path)
        except ValueError:
            rel_path = filename # Fallback if paths on different drives (Windows)
            
        # Robust reading with encoding fallbacks
        raw_text = None
        for enc in ("utf-8", "utf-8-sig", "latin-1"):
            try:
                with open(full_path, 'r', encoding=enc, errors='strict') as f:
                    raw_text = f.read()
                break
            except UnicodeDecodeError:
                continue
        if raw_text is None:
            with open(full_path, 'r', encoding='utf-8', errors='replace') as f:
                raw_text = f.read()

        fm_match = re.match(r'^---\s*\n(.*?)\n---\s*\n', raw_text, re.DOTALL)
        content = raw_text[fm_match.end():] if fm_match else raw_text
        
        links = re.findall(r'\[\[([^\]|]+)(?:\|[^\]]+)?\]\]', content)
        tags = re.findall(r'#([a-zA-Z0-9_\-/]+)', content)
        
        return {
            "path": rel_path,
            "name": filename.replace(".md", ""),
            "folder": os.path.basename(root),
            "content": content.strip(),
            "wordcount": len(content.split()),
            "links": links,
            "tags": tags
        }

    def chunking_and_embedding(self, note_data: NoteData) -> List[ChunkPayload]:
        """Chunk note content and generate embeddings for each chunk.
        
        Args:
            note_data: Parsed note data to process.
        
        Returns:
            List of chunk payloads with text and embedding vectors.
        """
        text_chunks = self.character_chunker(note_data["content"])
        logger.info(
            f"Processing: {note_data['path']} ({len(note_data['content'])} chars -> {len(text_chunks)} chunks)"
        )

        chunk_payloads: List[ChunkPayload] = []
        for i, txt in enumerate(text_chunks):
            vector = self.get_embedding(txt)
            if vector:
                chunk_payloads.append({"text": txt, "embedding": vector})
            else:
                logger.warning(f"Failed to embed chunk {i} for {note_data['path']}")

        return chunk_payloads

    def ingest_note_and_chunks(self, note_data: NoteData, chunks: List[ChunkPayload]) -> None:
        """Store note and chunks in Neo4j with relationships to folders, tags, and links.
        
        Args:
            note_data: Parsed note data to store.
            chunks: List of chunks with embeddings to store.
        """
        driver = self._get_driver()
        with driver.session() as session:
            session.run("""
                MERGE (f:Folder {name: $folder})
                MERGE (n:Note {path: $path})
                SET n.name = $name, n.wordcount = $wordcount
                MERGE (n)-[:IN_FOLDER]->(f)
            """, path=note_data['path'], name=note_data['name'],
                 folder=note_data['folder'], wordcount=note_data['wordcount'])

            for i, chunk in enumerate(chunks):
                chunk_id = hashlib.md5(f"{note_data['path']}_{i}".encode()).hexdigest()
                session.run("""
                    MATCH (n:Note {path: $path})
                    MERGE (c:Chunk {id: $chunk_id})
                    SET c.text = $text, c.embedding = $embedding, c.index = $index
                    MERGE (n)-[:HAS_CHUNK]->(c)
                """, path=note_data['path'], chunk_id=chunk_id,
                     text=chunk['text'], embedding=chunk['embedding'], index=i)

            for tag in note_data['tags']:
                session.run("MATCH (n:Note {path: $path}) MERGE (t:Tag {name: $tag}) MERGE (n)-[:HAS_TAG]->(t)",
                            path=note_data['path'], tag=tag)
            for link in note_data['links']:
                session.run("MATCH (source:Note {path: $path}) MERGE (target:Note {name: $link}) "
                            "ON CREATE SET target.path = $link + '.md' MERGE (source)-[:LINKS_TO]->(target)",
                            path=note_data['path'], link=link)

    def ingest_vault(self, vault_path: str) -> dict:
        """Ingest an entire Obsidian vault into Neo4j.
        
        Processes all markdown files in the vault, chunks them, generates embeddings,
        and stores them in Neo4j with relationships.
        
        Args:
            vault_path: Path to the Obsidian vault directory.
        
        Returns:
            Dictionary with status, processed count, and any errors.
        
        Raises:
            FileNotFoundError: If vault path doesn't exist.
        """
        if not os.path.exists(vault_path):
            raise FileNotFoundError(f"Vault path not found: {vault_path}")

        self.setup_database()
        
        processed = 0
        errors = []
        
        for root, dirs, files in os.walk(vault_path):
            dirs[:] = [d for d in dirs if not d.startswith('.')]
            for file in files:
                if file.endswith(".md"):
                    try:
                        note_data = self.parse_obsidian_note(root, file, vault_path)
                        chunk_payloads = self.chunking_and_embedding(note_data)

                        if chunk_payloads:
                            self.ingest_note_and_chunks(note_data, chunk_payloads)
                            processed += 1
                    except Exception as e:
                        logger.exception(f"Processing {file} failed")
                        errors.append(f"{file}: {str(e)}")

        return {"status": "success", "processed": processed, "errors": errors}

# Lazy initialization to avoid startup failures
_obsidian_service: Optional[ObsidianService] = None

def get_obsidian_service() -> ObsidianService:
    """Get or create the Obsidian service singleton.
    
    Returns:
        ObsidianService instance, creating it on first access.
    """
    global _obsidian_service
    if _obsidian_service is None:
        _obsidian_service = ObsidianService()
    return _obsidian_service

# Backward compatibility: module-level access uses lazy initialization
# This property-like access ensures the service is only created when first used
class _ObsidianServiceProxy:
    """Proxy for lazy access to obsidian_service."""
    def __getattr__(self, name):
        return getattr(get_obsidian_service(), name)

obsidian_service = _ObsidianServiceProxy()
