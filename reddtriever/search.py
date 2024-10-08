from tavily import AsyncTavilyClient
from config import TAVILY_API_KEY
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

class SearchTool:
    def __init__(self):
        self.client = AsyncTavilyClient(api_key=TAVILY_API_KEY)
        self.vectorizer = TfidfVectorizer()
        
    async def initialize(self):
        pass

    async def search(self, query: str) -> list:
        try:
            response = await self.client.search(query=query, include_domains=["reddit.com"])
            documents = self._transform_response(response)
            # return self.re_rank(query, documents) -> not used for now, just adds inference time
            return documents
        except Exception as e:
            return [f"Error performing search: {str(e)}"]

    def _transform_response(self, response: dict) -> list:
        documents = [
            {
                "pageContent": result["content"] if result["content"] else result["title"],
                "metadata": {
                    "title": result["title"],
                    "url": result["url"],
                    "img_src": next((img["url"] for img in response.get("images", []) if img["url"] == result["url"]), None)
                }
            }
            for result in response["results"]
        ]
        return documents

    def re_rank(self, query: str, documents: list) -> list:
        '''not used for now, just adds inference time'''
        if not documents:
            return []

        texts = [doc['pageContent'] for doc in documents]
        
        self.vectorizer.fit(texts)
        doc_vectors = self.vectorizer.transform(texts)
        query_vector = self.vectorizer.transform([query])

        # not working at all, vectors are too long for this kind of comparison. should use something else 
        cosine_similarities = cosine_similarity(query_vector, doc_vectors).flatten() 

        similarity_threshold = 0.5
        filtered_documents = [
            (doc, sim) for doc, sim in zip(documents, cosine_similarities)
            if sim > similarity_threshold
        ]

        ranked_documents = sorted(
            filtered_documents,
            key=lambda x: x[1],
            reverse=True
        )
        result = [doc for doc, _ in ranked_documents]
        return result
