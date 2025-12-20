"""
This module is only for CLI use to test if ingested data works correctly.
It provides functions to query the Neo4j graph database and generate answers
using RAG (Retrieval-Augmented Generation) on Obsidian vault data.
"""

from __future__ import annotations

import logging

from neo4j import GraphDatabase

from config import (
    NEO4J_URI,
    NEO4J_USER,
    NEO4J_PASSWORD,
    EMBEDDING_MODEL,
    LLM_MODEL,
    client,
)

logger = logging.getLogger(__name__)

def get_embedding(text: str) -> list[float]:
    """Encodes the question into a vector."""
    response = client.embeddings.create(input=[text], model=EMBEDDING_MODEL)
    return response.data[0].embedding


def generate_answer(question: str, context: str) -> str:
    """Sends the context and question to the LLM for the final answer."""
    prompt = f"""
You are an expert assistant for an Obsidian Vault. Use the following retrieved documents and graph context to answer the user's question.
If the answer is not in the context, say you don't know.

---
CONTEXT FROM GRAPH:
{context}
---

USER QUESTION: {question}

FINAL ANSWER:"""

    response = client.chat.completions.create(
        model=LLM_MODEL,
        messages=[
            {"role": "system", "content": "You are a helpful assistant that answers questions based on provided knowledge graph context."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.2 # Lower temperature for factual accuracy
    )
    return response.choices[0].message.content

def graph_rag_query(question: str) -> str:
    # 1. Embed the question
    question_vector = get_embedding(question)
    
    # 2. Hybrid Cypher Query: Vector Search + Graph Neighbors
    cypher_query = """
    CALL db.index.vector.queryNodes('chunk_embeddings', 5, $vector)
    YIELD node AS chunk, score
    
    // Find the parent Note
    MATCH (note:Note)-[:HAS_CHUNK]->(chunk)
    
    // Get graph context: What tags and linked files are around this note?
    OPTIONAL MATCH (note)-[:HAS_TAG]->(t:Tag)
    OPTIONAL MATCH (note)-[:LINKS_TO]->(linked:Note)
    
    RETURN 
        note.name AS source,
        chunk.text AS content,
        collect(DISTINCT t.name) AS tags,
        collect(DISTINCT linked.name) AS outgoing_links,
        score
    ORDER BY score DESC
    """
    
    context_entries: list[str] = []
    
    # Use context manager to ensure driver is always closed
    with GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD)) as driver:
        with driver.session() as session:
            results = session.run(cypher_query, vector=question_vector)
            
            for record in results:
                # Format each result into a snippet for the LLM
                entry = f"SOURCE: {record['source']}\n"
                entry += f"TAGS: {', '.join(record['tags'])}\n"
                entry += f"RELATED NOTES: {', '.join(record['outgoing_links'])}\n"
                entry += f"CONTENT: {record['content']}\n"
                entry += "---"
                context_entries.append(entry)

    if not context_entries:
        return "No relevant information found in the graph."

    # 3. Combine context and call the LLM
    full_context = "\n".join(context_entries)
    logger.info("Retrieval phase complete. Generating answer...")
    
    answer = generate_answer(question, full_context)
    return answer

if __name__ == "__main__":
    user_query: str = "How do I create a table in dataview?"
    
    final_response = graph_rag_query(user_query)
    
    logger.info("%s", "=" * 50)
    logger.info("QUESTION: %s", user_query)
    logger.info("%s", "-" * 50)
    logger.info("AI ANSWER:\n%s", final_response)
    logger.info("%s", "=" * 50)
