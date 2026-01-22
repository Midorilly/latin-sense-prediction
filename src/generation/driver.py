import logging
import os
import dotenv
import neo4j
#from langchain_openai import OpenAIEmbeddings
#import openai
from termcolor import colored

# setup logger config
logger = logging.getLogger("neo4j_graphrag")
logging.basicConfig(format="%(asctime)s - %(message)s")
logger.setLevel(logging.DEBUG)

class Neo4jDriver:
    def __init__(self, URI, USERNAME, PASSWORD, AUTH, driver, index_dimension, embedder, schema=None):
        self.URI = URI
        self.USERNAME = USERNAME
        self.PASSWORD = PASSWORD
        self.AUTH = AUTH
        self.driver = driver
        self.schema = schema

    def execute_cypher_query(self, query):
        self.driver.execute_query(query)

def load_environment():
    load_status = dotenv.load_dotenv("env/neo4j.env")
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

    #embedder = OpenAIEmbeddings()
    schema = ""

    neo4jdriver = Neo4jDriver(URI, USERNAME, PASSWORD, AUTH, driver, 1536, schema)

    return neo4jdriver


if __name__ == '__main__':
    load_environment()
    neo4jdriver = init_driver()