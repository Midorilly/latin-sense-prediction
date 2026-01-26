import logging
import os
import dotenv
import neo4j
import sys
import json
from langchain_openai import OpenAIEmbeddings
from neo4j_graphrag.llm import OpenAILLM, AzureOpenAILLM
from neo4j_graphrag.generation import GraphRAG, RagTemplate
from neo4j_graphrag.retrievers import VectorCypherRetriever
from random import random
from langchain_community.vectorstores import Neo4jVector
from neo4j.exceptions import CypherSyntaxError, GqlError
from neo4j_graphrag.exceptions import SearchValidationError, Text2CypherRetrievalError
from termcolor import colored
import time
from openai import BadRequestError
from compute_wsd_score import evaluate, evaluate_per_word

import driver
from graphrag import *
from utils import cleanGloss, cleanQuotation,
from client import client_setup, query_client
import client
import re
import hashlib
import queries 

# setup logger config
logger = logging.getLogger("neo4j_graphrag")
logging.basicConfig(format="%(asctime)s - %(message)s")
logger.setLevel(logging.DEBUG)

test = open('data/graphrag/test_latin_wsd_binary.jsonl', 'r')

class Quotation:
    def __init__(self, l):
        self.quotation = l['input']
        self.gloss = cleanGloss(l['sense'])
        self.lemma = l['lemma'].lower()
        self.instruction = l['instruction']
        self.target_word = re.sub('TARGET', '', l['instruction'].split('\"')[1]).strip().lower()
        self.quotation_hash = cleanQuotation(l['input'])

def write_sense_context(item, neo4jdriver):

    augmented_prompt = f'''Consider the following information and examples about the target sense '{item.gloss}':\n'''

    records, _, _ = neo4jdriver.driver.execute_query(queries.hypernym_metadata.format(item.gloss))
    for record in records:
        if len(records)>0:
            augmented_prompt = augmented_prompt + f'''It has the same meaning as {record.data()['x.gloss']} and its hypernym is {record.data()['y.gloss']}'''

    records, _, _ = neo4jdriver.driver.execute_query(queries.positive_example.format(item.gloss))
    if len(records)>0:
        for record in records:
            augmented_prompt = augmented_prompt + f'''The following sentence is a positive example of the target sense and was labelled with 'yes': {record.data()['q.value']}'''

    records, _, _ = neo4jdriver.driver.execute_query(queries.negative_example.format(item.gloss))
    if len(records)>0:
        for record in records:
            augmented_prompt = augmented_prompt + f'''The following sentence is a negative example of the target sense and was labelled with 'no': {record.data()['q.value']} '''

    instr = item.instruction
    augmented_prompt = augmented_prompt + instr + f'''\nThe sentence to label is: \"{item.quotation}\"'''

    return augmented_prompt

def write_author_context(similar_quotations_ids, item, neo4jdriver):

    augmented_prompt = f'''Consider the following {len(similar_quotations_ids)} sentences and their metadata as examples for the task:\n'''

    for id in similar_quotations_ids:
        similar_quotations_metadata_query = queries.author_metadata.format(id)      
        records, _, _ = neo4jdriver.driver.execute_query(similar_quotations_metadata_query)

        for record in records:
            if record.data()['q.value'] != None:
                augmented_prompt = augmented_prompt + queries.author_metadata.format(record.data()['q.value'], record.data()['d.title'], 
                        set(record.data()['collect(da.description)']), record.data()['p.fullname'], set(record.data()['collect(o.name)']))
    
    instr = item.instruction
    augmented_prompt = augmented_prompt + instr + f'''\nThe sentence to label is: \"{item.quotation}\"'''

    return augmented_prompt

def retrieve_top_k(k, quotation_hash, neo4jdriver):
    records, _, _ = neo4jdriver.driver.execute_query(queries.similarity_query.format(quotation_hash, k))
    quotation_id = records[0].data()['q.gbID']
    similar_quotations_ids = [record.data()['gbID'] for record in records if record.data()['gbID'] != quotation_id]

    return similar_quotations_ids, quotation_id

def run_author_experiment(model_name, neo4jdriver):

    client = client_setup(os.getenv(model_name))

    exps_file = os.path.join('exps', 'author-metatata', os.getenv(model_name)+'.jsonl')
    exps = open(exps_file, 'w+')
    test = open('data/graphrag/test_latin_wsd_binary.jsonl', 'r')
    log = open(os.path.join('exps', 'author-metatata', os.getenv(model_name)+'-LOG.txt'), 'w+')
    for idx, line in enumerate(test):
        if idx%100 == 0:
            logger.info(colored(f'Prompt {idx}', 'green'))
        l = json.loads(line)
        item = Quotation(l)

        similar_quotations_ids, quotation_id = retrieve_top_k(5, item.quotation_hash, neo4jdriver)
        augmented_prompt = write_author_context(similar_quotations_ids, item, neo4jdriver)

        skipped = {}
        try:
            answer = query_client(augmented_prompt, os.getenv(model_name), client)
            if answer is None:
                answer = 'null'
        except BadRequestError as e:
            logger.error(colored('Error 400: {}\nSkipping sentence {}'.format(e,idx), 'red'))
            answer = 'null'
        finally:
            l['system'] = answer
            json.dump(l, exps)
            exps.write('\n')
            if answer == 'null':
                skipped['id'] = idx
                skipped['prompt'] = augmented_prompt
                json.dump(skipped, log)
            
    exps.close()
    test.close()
    logger.info
    evaluate(exps_file, os.path.join('exps', 'author-metatata', os.getenv(model_name)+'-eval.txt'))

def run_sense_experiment(model_name, neo4jdriver):

    client = client_setup(os.getenv(model_name))
    senses = ['Related to "Christian virtue"', 'Related to "Virtue, personified as a deity"', 'a space marked out, an open place for observation', 
        'the military oath of allegiance', 'municipial official', 'An epithet of Jupiter', 'consul']
    senses_to_skip = [cleanGloss(sense) for sense in senses]
    exps_file = os.path.join('exps', 'sense-metadata', os.getenv(model_name)+'.jsonl')
    exps = open(exps_file, 'w+')
    log = open(os.path.join('exps', 'sense-metadata', os.getenv(model_name)+'-LOG.txt'), 'w+')
    for idx, line in enumerate(test):
        if idx%100 == 0:
            logger.info(colored(f'Prompt {idx}', 'green'))
        l = json.loads(line)
        if cleanGloss(l['sense']) not in senses_to_skip:
            item = Quotation(l)
            augmented_prompt = write_sense_context(item, neo4jdriver)

            skipped = {}
            try:
                answer = query_client(augmented_prompt, os.getenv(model_name), client)
                if answer is None:
                    answer = 'null'
            except BadRequestError as e:
                logger.error(colored('Error 400: {}\nSkipping sentence {}'.format(e,idx), 'red'))
                answer = 'null'
            finally:
                l['system'] = answer
                l['prompt'] = augmented_prompt
                json.dump(l, exps)
                exps.write('\n')
                if answer == 'null':
                    skipped['id'] = idx
                    skipped['prompt'] = augmented_prompt
                    json.dump(skipped, log)
            
    exps.close()
    test.close()
    logger.info(colored('Evaluating...', 'green'))
    #evaluate(exps_file, os.path.join('exps', 'sense-metadata', os.getenv(model_name)+'-eval.txt'))
    #evaluate_per_word(exps_file, os.path.join('appendix', 'sense-metadata', os.getenv(model_name)))


def missing_evaluation(model_name, neo4jdriver):

    exps = open(os.path.join('exps', os.getenv(model_name)+'.jsonl'), 'r')
    prompts = open(os.path.join('exps', os.getenv(model_name)+'-LOG.jsonl'), 'w+')
    for idx, line in enumerate(exps):
        l = json.loads(line)
        if l['system'] == 'null':
            x = {}
            item = Quotation(l)
            similar_quotations_ids, quotation_id = retrieve_top_k(5, item.quotation_hash, neo4jdriver)
            augmented_prompt = write_context(similar_quotations_ids, item, neo4jdriver)
            x['id'] = idx 
            x['prompt'] = augmented_prompt
            json.dump(x, prompts, indent=2)
    
    exps.close()
    prompts.close()

#python3 src/graphrag/experiment.py GPT_4O_MINI_MODEL_NAME

if __name__ == '__main__':

    driver.load_environment()
    neo4jdriver = driver.init_driver()
    model_name = sys.argv[1]
    run_author_experiment(model_name, neo4jdriver)
    run_sense_experiment(model_name, neo4jdriver)
    #missing_evaluation(model_name, neo4jdriver)
    #exps_file = os.path.join('exps', 'sense-metadata', os.getenv(model_name)+'.jsonl')
    #evaluate(exps_file, os.path.join('exps', 'sense-metadata', os.getenv(model_name)+'-eval.txt'))
    #evaluate_per_word(exps_file, os.path.join('appendix', 'sense-metadata', os.getenv(model_name)))
    neo4jdriver.driver.close()
    logger.info("Connection closed.")

    #llm = AzureOpenAILLM(model_name=os.getenv("LLAMA_8B_MODEL_NAME"), azure_endpoint=os.getenv("LLAMA_ENDPOINT"), api_key=os.getenv("LLAMA_API_KEY"))
    
    

