import os
from dotenv import load_dotenv
from typing import Any, List, Optional, Type, TypeVar, Iterable, Union
from neo4j import GraphDatabase
from driver import *
import hashlib
import re
import pickle
import pandas as pd
import csv
import json

def cleanQuotation(quotation):

    quotation = re.sub('[-+\"\']', '', quotation.lower())
    quotation = re.sub('(?:\[target\]|\[/target\]|target|</line>|<line>|</section>|<section>|</p>|<p>|</book>|<book>)', '', quotation)    #quotation = re.sub('"', '', quotation)
    quotation = re.sub(' +', ' ', quotation)
    quotationHash = getSentenceHash(quotation.strip())
    return quotationHash

def getSentenceHash(sentence: str) -> str:
    splitSentence = sentence.split(' ')
    startJoin = ' '.join(splitSentence[:5]).encode('utf-8')
    x = len(splitSentence)-5
    endJoin = ' '.join(splitSentence[x:]).encode('utf-8')
    sentenceHash = int(hashlib.md5(startJoin+endJoin).hexdigest(), 16)

    return sentenceHash

def cleanGloss(gloss):
    gloss = re.sub('[\"\'+]', '', gloss.lower())
    gloss = gloss.strip()
    return gloss

def deserialize(file):
    f = open(file, 'rb')
    obj = pickle.load(f)
    return obj

def serialize(file, item):
    pkl = open(file, 'wb')
    pickle.dump(item, pkl)
    pkl.close
    logger.info(colored('Object serialized at {}'.format(file), 'green'))

def jsonl2csv(jsonl_path, csv_path, fieldnames=None):
    with open(jsonl_path, 'r') as jsonl, open(csv_path, 'w') as csvfile:
        if fieldnames:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        else:
            writer = csv.writer(csvfile)
        for x in jsonl:
            row = json.loads(x)
            writer.writerow(row)

def add_lemma(lemma_path, results_path, output_path):

    output_file = open(output_path, 'w')
    with open(lemma_path) as lemma, open(results_path) as results:
        output = {}
        for l, r in zip(lemma, results):
            x = json.loads(l)
            y = json.loads(r)
            output['lemma'] = x['lemma']
            output['sense'] = x['sense']
            output['gold'] = y['gold']
            output['system'] = y['system']
            json.dump(output, output_file)
            output_file.write('\n')
    
    output_file.close()

def x(llm, output):

    senses = ['related to "christian virtue"', 'related to "virtue, personified as a deity"', 'a space marked out, an open place for observation',
                'the military oath of allegiance', 'municipial official', 'an epithet of jupiter', 'consul']

    output_file = open(output, 'w')
    with open(llm) as lm:
        for l in lm:
            y = json.loads(l)
            if y['sense'] not in senses:             
                json.dump(y, output_file)
                output_file.write('\n')

    output_file.close()
    
if __name__ == '__main__':

    add_lemma('exps/llm-only/Llama-3.3-70B-Instruct.jsonl', 'exps/llm-only/Meta-Llama-3.1-8B-Instruct.jsonl', 'exps/llm-only/senses/Meta-Llama-3.1-8B-Instruct-senses.jsonl')
    x('exps/llm-only/senses/Meta-Llama-3.1-8B-Instruct-senses.jsonl', 'exps/llm-only/senses/Meta-Llama-3.1-8B-Instruct.jsonl')
    #jsonl2csv('exps/sense-metadata/Llama-3.3-70B-Instruct.jsonl', 'exps/sense-metadata/Llama-3.3-70B-Instruct.csv', fieldnames=['lemma', 'sense', 'instruction', 'input', 'gold', 'system', 'prompt'])
    #add_lemma('exps/llm-only/Llama-3.3-70B-Instruct.jsonl', 'exps/llm-only/Meta-Llama-3.1-8B-Instruct.jsonl', 'exps/llm-only/Meta-Llama-3.1-8B-Instruct-new.jsonl')