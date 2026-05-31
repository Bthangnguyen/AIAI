# -*- coding: utf-8 -*-
"""Script to seed tags_vector embedding for all POIs in Database.
Uses OpenAI text-embedding-3-small via EmbeddingService.
Run inside travel-gateway container.
"""

import os
import sys
import logging
import psycopg

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("seed_tags_vector")

# Add app to path to import services
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

try:
    from app.services.embedding_service import EmbeddingService
except ImportError as e:
    # Try alternate import
    try:
        from services.embedding_service import EmbeddingService
    except ImportError:
        logger.error(f"Failed to import EmbeddingService. Ensure python path is correct: {e}")
        sys.exit(1)

def get_db_connection():
    """Connect to database using env variables."""
    sql_db = os.getenv("SQL_DB", "travel")
    sql_user = os.getenv("SQL_USER", "travel")
    sql_password = os.getenv("SQL_PASSWORD", "")
    sql_host = os.getenv("SQL_HOST", "travel-db")
    sql_port = os.getenv("SQL_PORT", "5432")
    
    conn_str = f"dbname={sql_db} user={sql_user} password={sql_password} host={sql_host} port={sql_port}"
    logger.info(f"Connecting to database {sql_db} on {sql_host}...")
    return psycopg.connect(conn_str)

def main():
    logger.info("Starting tags_vector seeding process...")
    
    # Initialize EmbeddingService (will automatically pick up shopaikey/openai configuration from env)
    api_key = os.getenv("OPENAI_API_KEY", "")
    if not api_key:
        logger.error("OPENAI_API_KEY not found in environment variables!")
        sys.exit(1)
        
    embed_service = EmbeddingService()
    logger.info(f"EmbeddingService initialized with provider={os.getenv('LLM_PROVIDER', 'openai')}")
    
    try:
        conn = get_db_connection()
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        sys.exit(1)
        
    try:
        with conn.cursor() as cur:
            # 1. Count empty tags_vector records
            cur.execute("SELECT count(*) FROM travel.poi WHERE tags_vector IS NULL;")
            empty_count = cur.fetchone()[0]
            
            cur.execute("SELECT count(*) FROM travel.poi;")
            total_count = cur.fetchone()[0]
            
            logger.info(f"Found {empty_count} POIs out of {total_count} total POIs with empty tags_vector.")
            
            if empty_count == 0:
                logger.info("All POIs already have vector embeddings! Nothing to do.")
                return
                
            # 2. Fetch all POIs with empty tags_vector
            cur.execute("SELECT uuid, name, category, tags, description FROM travel.poi WHERE tags_vector IS NULL;")
            pois = cur.fetchall()
            
            # 3. Prepare texts for batch embedding
            pois_data = []
            texts_to_embed = []
            
            for uuid, name, category, tags, description in pois:
                # Convert tags from list if necessary
                tag_list = tags if isinstance(tags, list) else []
                desc_str = description or ""
                
                text = embed_service.build_poi_text(name, category, tag_list, desc_str)
                texts_to_embed.append(text)
                pois_data.append({
                    "uuid": uuid,
                    "name": name
                })
                
            logger.info(f"Prepared {len(texts_to_embed)} texts for embedding. Generating embeddings in batches...")
            
            # 4. Generate embeddings in batches of 100 to optimize API calls
            batch_size = 100
            all_vectors = []
            
            for i in range(0, len(texts_to_embed), batch_size):
                batch_texts = texts_to_embed[i : i + batch_size]
                logger.info(f"Generating embeddings for batch {i // batch_size + 1} ({len(batch_texts)} items)...")
                
                try:
                    # Call OpenAI batch embedding
                    vectors = embed_service.embed_batch(batch_texts, batch_size=batch_size)
                    all_vectors.extend(vectors)
                except Exception as e:
                    logger.error(f"Failed to generate embeddings for batch {i // batch_size + 1}: {e}")
                    sys.exit(1)
                    
            logger.info(f"Successfully generated {len(all_vectors)} vector embeddings. Starting database update...")
            
            # 5. Update DB records
            updated = 0
            for idx, poi in enumerate(pois_data):
                vector = all_vectors[idx]
                # Convert vector list to PostgreSQL pgvector string format: '[0.1, 0.2, ...]'
                vector_str = "[" + ",".join(map(str, vector)) + "]"
                
                cur.execute(
                    "UPDATE travel.poi SET tags_vector = %s::vector WHERE uuid = %s;",
                    (vector_str, poi["uuid"])
                )
                updated += 1
                if updated % 100 == 0:
                    logger.info(f"Updated {updated}/{len(pois_data)} POIs...")
                    
            conn.commit()
            logger.info(f"Seeding completed successfully! Committed {updated} tags_vector updates to DB.")
            
    except Exception as e:
        conn.rollback()
        logger.error(f"Seeding process encountered an error: {e}")
        sys.exit(1)
    finally:
        conn.close()

if __name__ == "__main__":
    main()
