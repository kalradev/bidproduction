import os
import logging
from typing import List, Dict, Any, Optional
from pinecone import Pinecone
from langchain_pinecone import PineconeVectorStore
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_core.documents import Document as LCDocument
from langchain_community.embeddings import HuggingFaceEmbeddings
from core.config import settings

logger = logging.getLogger(__name__)

def get_embeddings():
    return HuggingFaceEmbeddings(model_name='sentence-transformers/all-MiniLM-L6-v2')

def get_pinecone_client():
    if settings.PINECONE_API_KEY:
        return Pinecone(api_key=settings.PINECONE_API_KEY)
    return None

async def store_rfp_in_pinecone(document_id: str, file_name: str, text: str, metadata: Dict[str, Any] = None):
    try:
        pc = get_pinecone_client()
        if not pc:
            logger.warning("Pinecone API key not set. Skipping storage.")
            return None
            
        index_name = os.getenv("PINECONE_INDEX_NAME", "bid-intelligence-chatbot")
        index = pc.Index(index_name)
        
        splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
        chunks = splitter.split_text(text)
        
        docs = []
        for i, chunk in enumerate(chunks):
            meta = {
                "documentId": document_id,
                "fileName": file_name,
                "chunkIndex": i,
                "totalChunks": len(chunks)
            }
            if metadata:
                meta.update(metadata)
            docs.append(LCDocument(page_content=chunk, metadata=meta))
            
        embeddings = get_embeddings()
        
        vector_store = PineconeVectorStore.from_documents(
            docs,
            embeddings,
            index_name=index_name,
            namespace=document_id
        )
        
        logger.info(f"✅ Stored {len(chunks)} chunks in Pinecone for {file_name} in namespace {document_id}")
        return {"success": True, "chunks": len(chunks)}
    except Exception as e:
        logger.error(f"Error storing in Pinecone: {str(e)}")
        raise e

async def query_rfp_document(document_id: str, query: str, k: int = 3):
    try:
        embeddings = get_embeddings()
        index_name = os.getenv("PINECONE_INDEX_NAME", "bid-intelligence-chatbot")
        
        vector_store = PineconeVectorStore.from_existing_index(
            index_name=index_name,
            embedding=embeddings,
            namespace=document_id
        )
        
        results = vector_store.similarity_search(query, k=k)
        return results
    except Exception as e:
        logger.error(f"Error querying Pinecone: {str(e)}")
        return []
