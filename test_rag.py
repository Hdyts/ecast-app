import asyncio
from app.rag_manager import RAGManager
import numpy as np

def test_rag():
    rag = RAGManager()
    
    text = """
    This is paragraph one about Islamic history. It happened a long time ago.
    
    This is paragraph two about the prophet. He was a great man.
    
    This is paragraph three about prayer. It is performed five times a day.
    
    This is paragraph four about fasting. It is done during Ramadan.
    """
    
    index = rag.build_index(text)
    print(f"Index built with {len(index['chunks'])} chunks.")
    
    query = "When is fasting done?"
    print(f"Query: {query}")
    
    results = rag.search(query, index, top_k=1)
    print(f"Results: {results}")
    
    if "Ramadan" in results[0]:
        print("Test Passed!")
    else:
        print("Test Failed!")

if __name__ == "__main__":
    test_rag()
