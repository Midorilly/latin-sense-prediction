import logging
import os
import dotenv
import neo4j
from langchain_openai import AzureOpenAIEmbeddings
from termcolor import colored

# setup logger config
logger = logging.getLogger("neo4j_graphrag")
logging.basicConfig(format="%(asctime)s - %(message)s")
logger.setLevel(logging.DEBUG)

class Neo4jDriver:
    def __init__(self, URI, USERNAME, PASSWORD, AUTH, driver, index_dimension, embedder=None, schema=None):
        self.URI = URI
        self.USERNAME = USERNAME
        self.PASSWORD = PASSWORD
        self.AUTH = AUTH
        self.driver = driver
        self.embedder = embedder
        self.schema = schema
        self.INDEX_DIMENSION = index_dimension

    def execute_cypher_query(self, query):
        self.driver.execute_query(query)

def load_environment():
    load_status = dotenv.load_dotenv("env-rag/graphrag.env")
    if load_status is False:
        raise RuntimeError('Environment variables not loaded.')

def init_driver():
    
    URI = os.getenv("NEO4J_URI")
    USERNAME = os.getenv("NEO4J_USERNAME")
    PASSWORD = os.getenv("NEO4J_PASSWORD")
    AUTH = (USERNAME, PASSWORD)
    driver = neo4j.GraphDatabase.driver(URI, auth=AUTH)
    if driver.verify_connectivity():
        logger.info("Connection established.")

    EMBEDDER_MODEL_NAME = os.getenv("EMBEDDING_MODEL_NAME")
    EMBEDDER_API_KEY = os.getenv("OPENAI_API_KEY")
    EMBEDDER_API_VERSION = os.getenv("OPENAI_API_VERSION")
    AZURE_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")

    embedding_dimension = 1536
    embedder = AzureOpenAIEmbeddings(model=EMBEDDER_MODEL_NAME, api_key=EMBEDDER_API_KEY, api_version=EMBEDDER_API_VERSION, 
        azure_endpoint=AZURE_ENDPOINT, retry_min_seconds=30, retry_max_seconds=60, show_progress_bar=True, dimensions=embedding_dimension)
    schema = ""

    neo4jdriver = Neo4jDriver(URI, USERNAME, PASSWORD, AUTH, driver, embedding_dimension, embedder, schema)

    return neo4jdriver


if __name__ == '__main__':
    load_environment()
    neo4jdriver = init_driver()