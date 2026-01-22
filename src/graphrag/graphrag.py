import logging
import os
import sys
import dotenv
import neo4j
from langchain_openai import OpenAIEmbeddings
from neo4j_graphrag.generation import GraphRAG, RagTemplate
from neo4j_graphrag.llm import OpenAILLM, AzureOpenAILLM
from neo4j_graphrag.retrievers import VectorCypherRetriever, VectorRetriever, Text2CypherRetriever, text2cypher
import openai
import re
from termcolor import colored
from neo4j.exceptions import CypherSyntaxError, GqlError
from pydantic import ValidationError
from neo4j_graphrag.exceptions import SearchValidationError, Text2CypherRetrievalError
from neo4j_graphrag.generation.prompts import Text2CypherTemplate
from neo4j_graphrag.schema import get_schema
from neo4j_graphrag.types import Text2CypherSearchModel

import index
import driver
from client import *
import re
import hashlib
from utils import *

# setup logger config
logger = logging.getLogger("neo4j_graphrag")
logging.basicConfig(format="%(asctime)s - %(message)s")
logger.setLevel(logging.DEBUG)


def neo4j_graphrag(nl_query, llm, retriever, prompt_template):

    try:
        rag = GraphRAG(retriever=retriever, llm=llm, prompt_template=prompt_template)
        #response = rag.search(query_text=nl_query, response_fallback="I can not answer this question because I have no relevant context.")
        response = rag.search(query_text=nl_query, retriever_config={'top_k': 3})
        return response
    except Text2CypherRetrievalError or CypherSyntaxError or GqlError or SearchValidationError as e:
        raise e

# Toy example
if __name__ == '__main__':

    driver.load_environment()
    neo4jdriver = driver.init_driver()

    #llm = AzureOpenAILLM(model_name=os.getenv("LLAMA_8B_MODEL_NAME"), azure_endpoint=os.getenv("LLAMA_ENDPOINT"), api_key=os.getenv("LLAMA_API_KEY"))

    client = client_setup(os.getenv('GPT_4O_MINI_MODEL_NAME'))

    instruction = f'''Given the target word \" dolum\" and the sentence in input where the word is enclosed by the [TARGET] tag, 
        and the following meaning \"evil intent, wrongdoing\", assign a label \"yes\" or \"no\". 
        The label meaning is the following:\n
        \"yes\": The sense for the target word occurrence is correct\n
        \"no\": The sense for the target word occurrence is not correct

        To answer, take into account the examples provided in the input after the sentence\n
        
        Answer just with the label.'''

    #prompt_template = RagTemplate(system_instructions=instruction)
    user = f'''Given the target word \" dolum\" and the sentence in input where the word is enclosed by the [TARGET] tag, 
        and the following meaning \"evil intent, wrongdoing\", assign a label \"yes\" or \"no\". 
        The label meaning is the following:\n
        \"yes\": The sense for the target word occurrence is correct\n
        \"no\": The sense for the target word occurrence is not correct

        To answer, take into account the examples provided in the input after the sentence\n
        
        Answer just with the label.'''

    quotation = 'calue, mactassint malo! Si sciam quid uelis, quasi serui comici conmictilis Tergum uarium linguam uafram Age modo: stic garri. particulones producam tibi. Quot laetitias insperatas modo mi inrepsere in sinum! Ego dedita opera te, pater, solum foras Seduxi, ut ne quis esset testis tertius Praeter nos, tibi cum tunderem labeas lubens. ut si quis est Amici, gaudet si cui quid boni Euenit, cuii amicus est germanitus... pater adest. Negato esse hic me. ego operibo caput. Vt nullum ciuem pedicaui per [TARGET] dolum[/TARGET] , Nisi ipsius orans ultro qui oquinisceret. Si ualebit, puls in buccam betet: sic dixin schema? Ego quod comedim quaero, his quaerunt quod cacent: contrariumst. Ego rumorem parui facio, dum sit rumen qui impleam. Continuo ad te centuriatim current qui panem petent. quae peditibus nubere Poterant, equites sperant spurcae. Quis hic est? quam obrem hic prostat? rictum et labeas cum considero Iamne abierunt? iam non tundunt? iamne ego in tuto satis? Nunqui hic restitat, qui nondum labeas lirarit mihi? O hominem'
    # domanda del dataset
    target_word = re.sub('TARGET', '', instruction.split('\"')[1]).strip().lower()
    gloss = cleanGloss("evil intent, wrongdoing")
    quotation_hash = cleanQuotation(quotation)
    print(quotation_hash)
    lemma = 'dolus'
    top_k = 5

    similarity_query = f'''
        MATCH (q:Quotation) WHERE q.hash = '{quotation_hash}'
        CALL db.index.vector.queryNodes('QUOTATION_INDEX', {top_k}, q._embedding)
        YIELD node AS quotation, score
        RETURN quotation.gbID AS gbID, score, q.gbID
    '''
    records, _, _ = neo4jdriver.driver.execute_query(similarity_query)
    quotation_id = records[0].data()['q.gbID']
    similar_quotations_ids = [record.data()['gbID'] for record in records if record.data()['gbID'] != quotation_id]
    #for record in records:
    #    quotations_ids.append(record.data()['gbID'])
    #print(quotations_ids)

    #quotation_query = f'''
    #    MATCH (l:Lemma)<-[:LEMMA]-(e:InflectedWord)-[:OCCURS_IN]->(q:Quotation)-[:DESCRIBES]->(s:Sense)<-[r:DESCRIBES]-(x:Quotation)
    #    WHERE e.name = '{target_word}' AND q.hash = '{quotation_hash}' AND s.gloss = '{gloss}' AND r.binary <> 'None' and r.grade <> 'None' AND l.name = '{lemma}'
    #    RETURN s.gloss, e.name, x.value, r.binary
    #'''

    augmented_prompt = f'''\n
            Consider the following {len(similar_quotations_ids)} similar sentences and their metadata.\n
        '''

    for id in similar_quotations_ids:
        logger.info(colored(id, 'red'))   
        similar_quotations_metadata_query = f'''
            OPTIONAL MATCH (da)<-[:DATE]-(q:Quotation)-[:BELONGS_TO]->(d:Document)<-[:DEVELOPED]-(p:Person)-[:OCCUPATION]->(o:Occupation)
            WHERE q.gbID = '{id}'
            RETURN q.value, d.title, collect(da.description), p.fullname, collect(o.name)
        '''
        records, _, _ = neo4jdriver.driver.execute_query(similar_quotations_metadata_query)

        for record in records:
            if record.data()['q.value'] != None:
                augmented_prompt = augmented_prompt + f'''
                    Sentence "{record.data()['q.value']}" 
                    belongs to work {record.data()['d.title']} 
                    written in {set(record.data()['collect(da.description)'])}. 
                    Its author is {record.data()['p.fullname']} and was a {set(record.data()['collect(o.name)'])}.\n
                '''
    
    augmented_prompt = augmented_prompt + f'''\nAssign a label to the sentence \"{quotation}\"'''

    #logger.info(colored('INSTRUCTION', 'yellow'))
    #logger.info(instruction)
    logger.info(colored('USER', 'yellow'))
    logger.info(augmented_prompt)

    answer = query_client(instruction, augmented_prompt, os.getenv('GPT_4O_MINI_MODEL_NAME'), client)
    logger.info(colored(answer, 'yellow'))


    #quotation_query = f'''
    #    MATCH (l:Lemma)<-[:LEMMA]-(e:InflectedWord)-[:OCCURS_IN]->(q:Quotation)-[:DESCRIBES]->(s:Sense)<-[r:DESCRIBES]-(x:Quotation)
    #    WHERE e.name = '{target_word}' AND q.hash = '{quotation_hash}' AND s.gloss = '{gloss}' AND r.binary <> 'None' and r.grade <> 'None' AND l.name = '{lemma}'
    #    RETURN s.gloss, e.name, x.value, r.binary
    #'''

    #query = f'''
    #    MATCH path = (l:Lemma)<-[:LEMMA]-(i:InflectedWord)-[:OCCURS_IN]->(q:Quotation)-[:DESCRIBES]->(s:Sense)<-[r:DESCRIBES]-(x:Quotation)
    #    WHERE i.name = '{target_word}' AND q.hash = '{quotation_hash}' AND s.gloss = '{gloss}' AND r.binary <> 'None' and r.grade <> 'None' AND l.name = '{lemma}'
    #    OPTIONAL MATCH (s)-[:SAME_AS]->(lw:Sense)
    #    RETURN s.gloss, r.binary, x.value, lw.gloss
    #'''

    #query = f'''
    #    MATCH path = (l:Lemma)<-[:LEMMA]-(i:InflectedWord)-[:OCCURS_IN]->(q:Quotation)-[:BELONGS_TO]->(d:Document)<-[:DEVELOPED]-(p:Person)
    #    WHERE i.name = '{target_word}' AND q.hash = '{quotation_hash}' AND l.name = '{lemma}'
    #    OPTIONAL MATCH (s:Sense)<-[:DESCRIBES]-(q:Quotation)-[:Date]->(date:Date)
    #    WHERE q.hash = '{quotation_hash}' and s.gloss = '{gloss}'
    #    RETURN d.title, p.fullname, date.description


    '''retrievers = {}
    retriever = VectorCypherRetriever(
        driver = neo4jdriver.driver,
        index_name = 'QUOTATION_INDEX', 
        embedder = neo4jdriver.embedder,
        retrieval_query = query,
    )
    retrievers['QUOTATION'] = neo4j_graphrag(quotation, llm, retriever, prompt_template).answer

    for k, v in retrievers.items():
        print(k, v)'''
        

    #print(quotation_hash)

    #model = 

    #query = 
    
    #llmOpenAI = OpenAILLM(model_name="gpt-4o-mini", model_params={"temperature": 0})
    #llmAzure = AzureOpenAILLM(model_name='')

    # provare index su SENSI
    # query usando lexical entry, senso e testo (rimuovendo target)
    # droppare relazioni istanze
    #gloss = re.sub('[\"\']', '_', gloss)
    #quotation = re.sub('[-+.\"\']', '', quotation) #+ RIMUOVERE TARGET
    #query = f'''
    #    MATCH (e:InflectedWord)-[:SENSE]->(s:Sense)<-[:DESCRIBES {{role: 'example'}}]-(q:Quotation) 
    #    WHERE e.name = '{name}' AND s.gloss = '{gloss}' AND q.value = '{quotation}'
    #    RETURN *
    #'''

    neo4jdriver.driver.close()
    logger.info("Connection closed.")





        