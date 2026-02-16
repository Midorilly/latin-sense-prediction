import logging
import pandas as pd
import csv
import jsonlines
import os
import relations
import nodes
import importlib
import schema
#import src.utils.driver
from namespaces import *
from rdflib import Graph
import src.utils.utils as utils


from urllib.parse import quote

logging.basicConfig(format='%(asctime)s %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

lkgDataset = '../data/full-dataset-v3.jsonl'
wikidataMap = '../data/wikidata_metadata/'
languagesFolder = '../data/languages/'

def languageNodes():
    l = Graph()
    l.bind('skos', SKOS08)
    l.parse(os.path.join(languagesFolder, 'lexvo_2013-02-09.nt'))
    logger.info('Generating language nodes...')
    
    for item in l.subjects(predicate=RDF.type, object=LVONT.Language):
        try:
            nodes.addLanguageNode(language=item, l=l)
        except neo4j.exceptions.CypherSyntaxError as e:
            print(e)
    
def lemmaNodes():
    logger.info('Generating lemma nodes...')
    with jsonlines.open(lkgDataset, 'r') as lkg:   
        lemmas = (line for line in lkg if line['jtype'] == 'node' and line['label'] == 'Lemma')
        for line in lemmas:     
            nodes.addLemmaNode(writtenRep=line['properties']['value'], pos=line['properties']['posTag'], mwe=line['properties']['mwe'], id=line['identity'])      
    
def entryNodes():
    logger.info('Generating entries nodes...')
    with jsonlines.open(lkgDataset, 'r') as lkg:
        lexicalEntries = (line for line in lkg if line['jtype'] == 'node' and line['label'] == 'InflectedWord')  
        for line in lexicalEntries:
            nodes.addLexicalEntryNode(entry=line['properties']['value'], id=line['identity'], language='Latin')

def senseNodes(): 
    logger.info('Generating lexical sense nodes...')
    with jsonlines.open(lkgDataset, 'r') as lkg:
        lexicalSenses = (line for line in lkg if line['jtype'] == 'node' and line['label'] == 'LexiconConcept')
        for line in lexicalSenses:
            resource = line['properties']['resource']
            if resource == 'Lewis-Short Dictionary':
                nodes.addLexicalSenseNode(resource=resource, sense=line['properties']['id'], gloss=line['properties']['alias'], id=line['identity']) 
            elif resource == 'Latin WordNet':
                nodes.addLexicalSenseNode(resource=resource, sense=line['properties']['alias'], gloss=line['properties']['gloss'], id=line['identity']) 

def authorNodes():
    logger.info('Generating author nodes...')
    #authors_df = pd.read_csv(os.path.join(wikidataMap, 'annotation.csv'), header=0, usecols=[2,3,4,5], names=['name', 'lastname', 'title', 'id'])
    authors_df = pd.read_csv(os.path.join(wikidataMap, 'annotation.csv'), header=0, usecols=['lastname', 'name', 'work', 'id'])
    authors_df = authors_df.drop_duplicates(subset=['lastname', 'name', 'id'])
    logger.info('{} unique authors'.format(authors_df['id'].nunique()))
    authors_df = authors_df.fillna('')
    authors_df['fullname'] = authors_df['lastname'] + ' ' + authors_df['name']
    #print(authors_df['fullname'].values.tolist())
    with jsonlines.open(lkgDataset, 'r') as lkg:
        authors = [line for line in lkg if line['jtype'] == 'node' and line['label'] == 'Person']     
        for line in authors:
           nodes.addPersonNode(firstname=line['properties']['name'], lastname=line['properties']['lastname'], id=line['identity'], df=authors_df)

def quotationNodes():
    logger.info('Generating text nodes...')
    with jsonlines.open(lkgDataset, 'r') as lkg:
        occurrences = [line for line in lkg if line['jtype'] == 'node' and line['label'] == 'Text']
        for line in occurrences:
            nodes.addQuotationNode(quotation=line['properties']['value'], language='Latin', id=line['identity'], start=None, end=None)

def occupationNodes():
    file = open(os.path.join(wikidataMap, 'occupations_map.tsv'), encoding='utf-8', mode='r')
    reader = csv.reader(file, delimiter='\t')
    occupationDict = {}
    for row in reader:
        occupationDict[row[1]] = row[0]
    file.close()

    logger.info('Generating occupation nodes...')
    with jsonlines.open(lkgDataset, 'r') as lkg:
        occupations = [line for line in lkg if line['jtype']=='node' and line['label']=='Occupation']        
        for line in occupations:
           nodes.addOccupationNode(occupation=line['properties']['value'], id=line['identity'], dict=occupationDict)

def documentNodes():
    logger.info('Generating document nodes...')
    with jsonlines.open(lkgDataset, 'r') as lkg:
        documents = [line for line in lkg if line['jtype'] == 'node' and line['label'] == 'Document']
        for line in documents: # adds dummy nodes
            nodes.addDocumentNode(title=line['properties']['title'], id=line['identity'])

def corpusNodes():
    logger.info('Generating corpora nodes...')
    with jsonlines.open(lkgDataset, 'r') as lkg:
        corpora = [line for line in lkg if line['jtype'] == 'node' and line['label'] == 'Corpus']
        for line in corpora:
            nodes.addCorpusNode(title=line['properties']['name'], id=line['identity'])    

def timeNodes():
    logger.info('Generating corpora nodes...')
    with jsonlines.open(lkgDataset, 'r') as lkg:
        intervals = [line for line in lkg if line['jtype'] == 'node' and line['label'] == 'TimeInterval']
        for line in intervals:
            nodes.addTimeIntervalNode(name=line['properties']['name'], description=line['properties']['name'], id=line['identity'])

    with jsonlines.open(lkgDataset, 'r') as lkg:
        points = [line for line in lkg if line['jtype'] == 'node' and line['label'] == 'TimePoint']
        pointsDict = generateTimePointsDictionary(points)
        
    nodes.addTimePointNode(pointsDict)   

    with jsonlines.open(lkgDataset, 'r') as lkg:
        relationships = [line for line in lkg if line['jtype'] == 'relationship']
        for line in relationships:
            property = line['name']
            if property == 'startTime' or property == 'endTime':  
                subjID = line['subject']
                objID = line['object']
                relations.addStartEndTimeRelation(subjID, objID, property) 
    
def lkgRelations():
    
    with jsonlines.open(lkgDataset, 'r') as lkg:
        relationships = [line for line in lkg if line['jtype'] == 'relationship']
        logger.info('Connecting nodes...')
        for line in relationships:
            property = line['name']
            subjID = line['subject']
            objID = line['object']

            if property == 'HAS_LEMMA':
                relations.addLemmaRelation(subjID, objID)            
            elif property == 'HAS_SUBCLASS':
                relations.addSemanticRelation(subjID, objID)
            if property == 'HAS_CONCEPT':
                relations.addSenseRelation(subjID, objID)
            elif property == 'SAME_AS':
                relations.addSameAsRelation(subjID, objID)      
            elif property == 'HAS_OCCURRENCE':
                relations.addOccursInRelation(subjID, objID)
            elif property == 'HAS_AUTHOR':
                relations.addDevelopedRelation(subjID, objID, 'author')
            elif property == 'PUBLISHED_IN':
                relations.addDateRelation(subjID, objID)
            elif property == 'HAS_CORPUS' or property == 'BELONG_TO':
                relations.addBelongsToRelation(subjID, objID)
            elif property == 'HAS_EXAMPLE':
                relations.addExampleDescribesRelation(subjID, objID, 'example', line['properties']['grade'])
            elif property == 'startTime' or property == 'endTime':
                relations.addStartEndTimeRelation(subjID, objID, property)
            elif property == 'HAS_OCCUPATION':
                relations.addOccupationRelation(subjID, objID)


    logger.info('Nodes successfully connected!')

def lkgNodes():
    
    schema.createSchemaNodes()
    nodes.addTaxonomyNode()
    nodes.addPoSTagNode() 
    languageNodes()
    lemmaNodes()
    entryNodes()
    senseNodes()
    corpusNodes()
    documentNodes()
    quotationNodes()
    timeNodes()
    authorNodes()
    occupationNodes()

testFile = 'data/graphrag/test_latin_wsd_binary.jsonl'

def removeTestInstances():
    removed = 0
    with jsonlines.open(testFile, 'r') as test:
        for line in test:
            quotation = line['input']
            sense = line['sense']
            lemma = line['lemma']
            relations.dropBinaryProperty(quotation, sense, lemma)

if __name__ == '__main__':

    importlib.reload(nodes)
    importlib.reload(relations)

    lkgNodes()
    lkgRelations()
    removeTestInstances()
  
    