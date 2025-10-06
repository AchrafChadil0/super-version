# vector_store.py

import hashlib
import json
import logging
import re
from typing import Any

import chromadb
from chromadb.config import Settings
from chromadb.utils import embedding_functions

from src.core.config import Config
from src.schemas.products import VectorProductFormat, VectorProductSearchResult

logger = logging.getLogger(__name__)


class VectorStore:
    """Manages ChromaDB vector database for product search"""

    def __init__(
        self,
        collection_name: str = Config.CHROMA_COLLECTION_NAME,
        persist_directory: str = Config.CHROMA_PERSIST_DIRECTORY,
        openai_api_key: str | None = None,
    ):
        """
        Initialize ChromaDB with OpenAI embeddings

        Args:
            collection_name: Name of the ChromaDB collection
            persist_directory: Directory to persist the database
            openai_api_key: OpenAI API key for embeddings
        """
        self.collection_name = collection_name
        self.persist_directory = persist_directory
        self.openai_api_key = Config.OPENAI_API_KEY

        # Initialize ChromaDB client with persistence
        self.client = chromadb.PersistentClient(
            path=persist_directory,
            settings=Settings(anonymized_telemetry=False, allow_reset=True),
        )

        # Initialize OpenAI embedding function
        if openai_api_key:
            self.embedding_function = embedding_functions.OpenAIEmbeddingFunction(
                api_key=Config.OPENAI_API_KEY,
                model_name="text-embedding-3-large",  # Cheaper and faster model
            )
        else:
            # Fallback to default embedding if no API key
            logger.warning("No OpenAI API key provided, using default embeddings")
            self.embedding_function = embedding_functions.DefaultEmbeddingFunction()

        # Get or create collection
        self._init_collection()

    def _init_collection(self):
        """Initialize or get the products collection"""
        try:
            # Try to get existing collection
            self.collection = self.client.get_collection(
                name=self.collection_name, embedding_function=self.embedding_function
            )
            logger.info(
                f"✅ Loaded existing collection '{self.collection_name}' with {self.collection.count()} items"
            )
        except Exception:
            # Create new collection if it doesn't exist
            self.collection = self.client.create_collection(
                name=self.collection_name,
                embedding_function=self.embedding_function,
                metadata={"description": "Product catalog for semantic search"},
            )
            logger.info(f"📦 Created new collection '{self.collection_name}'")

    def generate_product_id(self, product: dict) -> str:
        """Generate a unique ID for a product based on its content"""
        # Use the product ID if available, otherwise generate from content
        if "id" in product:
            return str(product["id"])

        # Fallback: Create ID from redirect URL to ensure uniqueness
        unique_string = product.get("metadata", {}).get("redirect_url", "")
        return hashlib.md5(unique_string.encode()).hexdigest()[:16]

    def prepare_product_for_storage(self, product: dict) -> dict[str, Any]:
        """
        Prepare product data for ChromaDB storage with new format

        Returns:
            Dict with document, metadata, and id
        """
        # Use the document field directly as searchable text
        document = product.get("document", "")

        # Extract metadata
        product_metadata = product.get("metadata", {})

        # Prepare metadata for ChromaDB (requires specific types)
        metadata = {
            # Store categories as JSON string since ChromaDB doesn't support arrays directly
            "categories_json": json.dumps(product_metadata.get("categories", [])),
            "brand": product_metadata.get("brand", ""),
            "product_type": product_metadata.get("product_type", "basic"),
            "redirect_url": product_metadata.get("redirect_url", ""),
            "details_url": product_metadata.get("details_url", ""),
            # Store full product as JSON for retrieval
            "full_product": json.dumps(product),
        }

        return {
            "document": document,
            "metadata": metadata,
            "id": self.generate_product_id(product),
        }

    def add_products(
        self, products: list[VectorProductFormat], batch_size: int = 100
    ) -> dict[str, Any]:
        """
        Add multiple products to the vector store

        Args:
            products: List of product dictionaries in new format
            batch_size: Number of products to add in each batch

        Returns:
            Dict with success status and statistics
        """
        try:
            total_products = len(products)
            added_count = 0
            skipped_count = 0

            # Process in batches for better performance
            for i in range(0, total_products, batch_size):
                batch = products[i : i + batch_size]

                documents = []
                metadatas = []
                ids = []

                for product in batch:
                    prepared = self.prepare_product_for_storage(product)

                    # Check if product already exists
                    product_id = prepared["id"]
                    existing = self.collection.get(ids=[product_id])

                    if existing and existing["ids"]:
                        skipped_count += 1
                        logger.debug(f"Skipping existing product ID: {product_id}")
                        continue

                    documents.append(prepared["document"])
                    metadatas.append(prepared["metadata"])
                    ids.append(product_id)

                # Add batch to collection
                if documents:
                    self.collection.add(
                        documents=documents, metadatas=metadatas, ids=ids
                    )
                    added_count += len(documents)
                    logger.info(
                        f"Added batch of {len(documents)} products ({i + len(batch)}/{total_products})"
                    )

            return {
                "success": True,
                "total_products": total_products,
                "added": added_count,
                "skipped": skipped_count,
                "total_in_db": self.collection.count(),
            }

        except Exception as e:
            logger.error(f"Error adding products to vector store: {e}")
            return {"success": False, "error": str(e)}

    def search_products(
        self,
        query: str,
        n_results: int = 5,
    ) -> list[VectorProductSearchResult]:
        """
        Search for products using semantic similarity

        Args:
            query: Search query text
            n_results: Number of results to return

        Returns:
            List of matching products with scores
        """
        try:
            # Perform semantic search without any filters
            results = self.collection.query(
                query_texts=[query],
                n_results=min(n_results, self.collection.count()),
                include=["metadatas", "distances", "documents"],
            )

            # Process results
            products = []
            if results and results["metadatas"] and results["metadatas"][0]:
                for i, metadata in enumerate(results["metadatas"][0]):
                    # Parse full product from metadata
                    value = metadata.get("full_product", "{}")
                    if not isinstance(value, str):
                        value = "{}"
                    full_product = json.loads(value)

                    # Parse categories from JSON string
                    value = metadata.get("categories_json", "[]")
                    if not isinstance(value, str):
                        value = "[]"
                    categories = json.loads(value)

                    # Add similarity score (convert distance to similarity)
                    distance = (
                        results["distances"][0][i] if results["distances"] else 1.0
                    )
                    similarity_score = 1.0 / (1.0 + distance)  # Convert to 0-1 scale

                    # Add parsed categories back to product
                    if "metadata" in full_product:
                        full_product["metadata"]["categories"] = categories

                    products.append(
                        {
                            **full_product,
                            "similarity_score": similarity_score,
                            "search_rank": i + 1,
                        }
                    )

            logger.info(f"Found {len(products)} products for query: '{query}'")
            return products[:n_results]  # Ensure we don't return more than requested

        except Exception as e:
            logger.error(f"Error searching products: {e}")
            return []

    def get_product_by_id(self, product_id: str) -> dict | None:
        """Get a specific product by its ID"""
        try:
            result = self.collection.get(ids=[product_id], include=["metadatas"])

            if result and result["metadatas"]:
                metadata = result["metadatas"][0]
                full_product = json.loads(metadata.get("full_product", "{}"))

                # Parse categories
                categories = json.loads(metadata.get("categories_json", "[]"))
                if "metadata" in full_product:
                    full_product["metadata"]["categories"] = categories

                return full_product

            return None

        except Exception as e:
            logger.error(f"Error getting product by ID: {e}")
            return None

    def update_product(self, product: dict) -> bool:
        """Update an existing product in the vector store"""
        try:
            prepared = self.prepare_product_for_storage(product)

            self.collection.update(
                ids=[prepared["id"]],
                documents=[prepared["document"]],
                metadatas=[prepared["metadata"]],
            )

            logger.info(f"Updated product ID: {product.get('id')}")
            return True

        except Exception as e:
            logger.error(f"Error updating product: {e}")
            return False

    def delete_product(self, product_id: str) -> bool:
        """Delete a product from the vector store"""
        try:
            self.collection.delete(ids=[product_id])
            logger.info(f"Deleted product with ID: {product_id}")
            return True

        except Exception as e:
            logger.error(f"Error deleting product: {e}")
            return False

    def clear_collection(self) -> bool:
        """Clear all products from the collection"""
        try:
            # Delete the collection
            self.client.delete_collection(name=self.collection_name)
            logger.info(f"Cleared collection '{self.collection_name}'")

            # Reinitialize the collection
            self._init_collection()
            return True

        except Exception as e:
            logger.error(f"Error clearing collection: {e}")
            return False

    def get_statistics(self) -> dict[str, Any]:
        """Get statistics about the vector store"""
        try:
            # Get all products to analyze
            all_products = self.collection.get(include=["metadatas"])
            categories = set()
            brands = set()
            product_types = {"customizable": 0, "basic": 0}

            if all_products and all_products["metadatas"]:
                for metadata in all_products["metadatas"]:
                    # Parse categories from JSON
                    categories_json = metadata.get("categories_json", "[]")
                    try:
                        product_categories = json.loads(categories_json)
                        categories.update(product_categories)
                    except (json.JSONDecodeError, TypeError, ValueError):
                        pass

                    # Collect brands
                    brand = metadata.get("brand", "")
                    if brand:
                        brands.add(brand)

                    # Count product types
                    product_type = metadata.get("product_type", "basic")
                    if product_type in product_types:
                        product_types[product_type] += 1

            return {
                "total_products": self.collection.count(),
                "collection_name": self.collection_name,
                "unique_categories": len(categories),
                "categories": sorted(categories),
                "unique_brands": len(brands),
                "brands": sorted(brands),
                "product_types": product_types,
                "persist_directory": self.persist_directory,
            }

        except Exception as e:
            logger.error(f"Error getting statistics: {e}")
            return {"error": str(e), "total_products": 0}


def sanitize_dir(name: str) -> str:
    """this will just sanitize the website name so we can use it folder"""
    # Replace spaces with underscores, remove bad chars
    return re.sub(r"[^a-zA-Z0-9_\-]", "_", name.strip())


def sanitize_add_parent_dir(website_name: str, parent_dir_name: str = "vdbs") -> str:
    """this will sanitize website so we use it as dir name and and add to it  parent_dir_name"""
    clean_website_name = sanitize_dir(website_name)
    return f"{parent_dir_name}/{clean_website_name}"
