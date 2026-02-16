import logging
import os
import dotenv
import neo4j
#from langchain_openai import OpenAIEmbeddings
from langchain_openai import AzureOpenAIEmbeddings
from neo4j_graphrag.indexes import create_vector_index, upsert_vectors, drop_index_if_exists
from random import random
from langchain_community.vectorstores import Neo4jVector
import src.utils.driver as driver
import time
from openai import RateLimitError

# setup logger config
logger = logging.getLogger("neo4j_graphrag")
logging.basicConfig(format="%(asctime)s - %(message)s")
logger.setLevel(logging.DEBUG)

def create_index(neo4jdriver, INDEX_NAME, l):

    logger.info(f'Creating index for {l}')

    create_vector_index(
        neo4jdriver.driver,
        INDEX_NAME,
        label=l, # node label to be indexed
        embedding_property="_embedding", # property key of a node which contains embedding values
        dimensions=neo4jdriver.INDEX_DIMENSION, 
        similarity_fn="cosine", # vector similarity function: euclidean or cosine
    )

def properties_embedding(l, properties: list, index_name, neo4jdriver, attempt):

    logger.info(f'Attempt #{attempt} at embedding properties of {l}')

    query = f'''
        MATCH (n:{l}) WHERE n._embedding IS null 
        RETURN n
    '''
    to_embed = len(neo4jdriver.driver.execute_query(query).records)

    while to_embed != 0:
        logger.info(f'{to_embed} {l} nodes to embed!')
        try:
            p_e = Neo4jVector.from_existing_graph(
                embedding = neo4jdriver.embedder,
                url = neo4jdriver.URI,
                username = neo4jdriver.USERNAME,
                password = neo4jdriver.PASSWORD,
                node_label = l,
                text_node_properties = properties,
                embedding_node_property = '_embedding'
            )
            to_embed = len(neo4jdriver.driver.execute_query(query).records)
            logger.info('Sleeping 30s...')
            time.sleep(30)

        except RateLimitError as e:
            if attempt <= 2:
                print('RateLimitError, sleeping 60 seconds')
                time.sleep(60)
                properties_embedding(l, properties, index_name, neo4jdriver, attempt+1)
            else:
                raise(e)

def query_neo4j(l, neo4jdriver):

    records, summary, keys = neo4jdriver.driver.execute_query(
        f"""
        MATCH (n:{l})
        RETURN keys(n) LIMIT 1
        """,
        database_='neo4j'
    )

    return records

def init_index(neo4jdriver):
    #labels = ['Document', 'InflectedWord', 'Lemma', 'Occupation', 'Person', 'Sense', 'Quotation', 'Entity', 'Language', 'PartOfSpeech','Taxonomy', 'TemporalInterval', 'TimePoint']
    #labels = ['Document', 'InflectedWord', 'Lemma', 'Occupation', 'Person', 'Sense']
    labels = ['Quotation']
    propertiesToSkip = ['gbID', 'wikidata', 'hash']

    for l in labels:
        INDEX_NAME = l.upper()+'_INDEX'
        drop_index_if_exists(neo4jdriver.driver, INDEX_NAME)
        records = query_neo4j(l, neo4jdriver)
       
        for record in records:
            properties = [p for p in list(record.data().values())[0] if p not in propertiesToSkip]      
            try: 
                properties_embedding(l=l, properties=properties, index_name=INDEX_NAME, neo4jdriver=neo4jdriver, attempt=0)
                create_index(neo4jdriver, INDEX_NAME, l)
            except RateLimitError as e:
                print(e)

if __name__ == '__main__':

    driver.load_environment()
    neo4jdriver = driver.init_driver()
    init_index(neo4jdriver)