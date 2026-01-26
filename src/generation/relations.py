
import urllib.error
import logging
from SPARQLWrapper import SPARQLExceptions
import utils
from driver import *
import nltk
nltk.download('wordnet')
nltk.download('wordnet31')
from nltk.corpus import wordnet as wn30
from nltk.corpus import wordnet31 as wn31
import re


logging.basicConfig(format='%(asctime)s %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

load_environment()
neo4jdriver = init_driver()

def addLemmaRelation(subjID, objID):

    query = f'''
        MATCH (l:Lemma) WHERE l.gbID = '{objID}'
        MATCH (i:InflectedWord) WHERE i.gbID = '{subjID}'
        MERGE (i)-[:LEMMA]->(l)
        RETURN *
    '''
    insertion = neo4jdriver.driver.execute_query(query).summary

def addSemanticRelation(subjID, objID):
    
    query = f'''
        MATCH (s1:Sense)-[:BELONGS_TO]->(t1:Taxonomy) WHERE s1.gbID = '{subjID}'
        MATCH (s2:Sense)-[:BELONGS_TO]->(t2:Taxonomy) WHERE s2.gbID = '{objID}'
        RETURN s1.name, s2.name, t1.name, t2.name
    '''
    records, summary, keys = neo4jdriver.driver.execute_query(query)
    
    for record in records:
        sense1 = record.data()['s1.name']
        taxonomy1 = record.data()['t1.name']
        sense2 = record.data()['s2.name']
        taxonomy2 = record.data()['t2.name']

        if taxonomy1 == 'WordNet31' and taxonomy2 == 'WordNet31':
            subjSyn = wn31.synset(sense1)
            objSyn = wn31.synset(sense2)
        elif taxonomy1 == 'WordNet30' and taxonomy2 == 'WordNet30':
            subjSyn = wn30.synset(sense1)
            objSyn = wn30.synset(sense2)

        if objSyn in subjSyn.hypernyms():
            query = f'''
                MATCH (s1:Sense) WHERE s1.gbID = '{subjID}'
                MATCH (s2:Sense) WHERE s2.gbID = '{objID}'
                MERGE (s1)-[:HYPONYM]->(s2)
                MERGE (s2)-[:HYPERNYM]->(s1)
                RETURN *            
            '''
        elif objSyn in subjSyn.hyponyms():
            query = f'''
                MATCH (s1:Sense) WHERE s1.gbID = '{subjID}'
                MATCH (s2:Sense) WHERE s2.gbID = '{objID}'
                MERGE (s1)-[:HYPERNYM]->(s2)
                MERGE (s2)-[:HYPONYM]->(s1)
                RETURN *            
            '''      
        request = neo4jdriver.driver.execute_query(query).summary

def addSenseRelation(subjID, objID):
    query = f'''
        MATCH (i:InflectedWord) WHERE i.gbID = '{subjID}'
        MATCH (s:Sense) WHERE s.gbID = '{objID}'
        MERGE (i)-[:SENSE]->(s)
        MERGE (s)-[:IS_SENSE_OF]->(i)
        RETURN *
    '''    
    insertion = neo4jdriver.driver.execute_query(query).summary

def addExampleDescribesRelation(subjID, objID, role, grade): 

    if grade >= 3.0: binary = 'yes'
    elif grade <= 2.0: binary = 'no'

    query = f'''
        MATCH (s1:Sense) WHERE s1.gbID = '{subjID}'
        MATCH (s2:Quotation) WHERE s2.gbID = '{objID}'
        MERGE (s2)-[:DESCRIBES {{role: '{role}', grade: {grade}, binary:'{binary}'}}]->(s1)
        RETURN *
    '''
    insertion = neo4jdriver.driver.execute_query(query).summary

def dropBinaryProperty(quotation, gloss, lemma):

    quotationHash = utils.cleanQuotation(quotation)
    gloss = utils.cleanGloss(gloss)

    query = f'''
        MATCH (l:Lemma) WHERE l.name = '{lemma}'
        RETURN l.gbID LIMIT 1
    '''
    records, _, _ = neo4jdriver.driver.execute_query(query)
    lemmaID = records[0].data()['l.gbID']

    query = f'''
        MATCH (s:Sense) WHERE s.gloss = '{gloss}' 
        MATCH (l:Lemma) WHERE l.gbID = '{lemmaID}'
        MATCH (s)-[:IS_SENSE_OF]->(x)-[:LEMMA]->(l)
        RETURN s.gbID LIMIT 1
    '''
    records, _, _ = neo4jdriver.driver.execute_query(query)
    senseID = records[0].data()['s.gbID']

    query = f'''
        MATCH (q:Quotation) WHERE q.hash = '{quotationHash}'
        MATCH (s:Sense) WHERE s.gbID = '{senseID}'
        MATCH (q)-[r:DESCRIBES]->(s)
        DELETE r
        RETURN q, s
    '''
    records, _, _ = neo4jdriver.driver.execute_query(query)

    query = f'''
        MATCH (q:Quotation) WHERE q.hash = '{quotationHash}'
        MATCH (s:Sense) WHERE s.gbID = '{senseID}'
        MERGE (q)-[:DESCRIBES {{role: 'example', grade: 'None', binary: 'None'}}]->(s)
        RETURN q, s
    '''
    records, _, _ = neo4jdriver.driver.execute_query(query)

    y = len(records)
    if y==0:
        print(f'{y} / {quotationHash} / {senseID}')
    elif y>1:
        print(f'{y} / {quotationHash} / {senseID}')

def addSameAsRelation(subjID, objID):

    query = f'''
        MATCH (s1:Sense) WHERE s1.gbID = '{subjID}'
        MATCH (s2:Sense) WHERE s2.gbID = '{objID}'
        MERGE (s1)-[:SAME_AS]->(s2)
        RETURN *
    '''
    insertion = neo4jdriver.driver.execute_query(query).summary

def addOccursInRelation(subjID, objID):

    query = f'''
        MATCH (s1:InflectedWord) WHERE s1.gbID = '{subjID}'
        MATCH (s2:Quotation) WHERE s2.gbID = '{objID}'
        MERGE (s1)-[:OCCURS_IN]->(s2)
        RETURN *
    '''
    insertion = neo4jdriver.driver.execute_query(query).summary

def addDevelopedRelation(subjID, objID, role):

    query = f'''
        MATCH (s1) WHERE s1.gbID = '{subjID}'
        MATCH (s2:Person) WHERE s2.gbID = '{objID}'
        MERGE (s2)-[:DEVELOPED {{role: '{role}'}}]->(s1)
        RETURN *
    '''
    insertion = neo4jdriver.driver.execute_query(query).summary

def addDateRelation(subjID, objID):

    query = f'''
        MATCH (i) WHERE i.gbID = '{subjID}'
        MATCH (n) WHERE n.gbID = '{objID}' OR ({objID} IN n.gbID)
        MERGE (i)-[:DATE]->(n)
        RETURN *
    '''
    insertion = neo4jdriver.driver.execute_query(query).summary

# Text, Document, Corpus, or Taxonomy
def addBelongsToRelation(subjID, objID, taxonomyID=None):

    if taxonomyID:
        query = f'''
            MATCH (s1) WHERE s1.gbID = '{subjID}' OR s1.pos = '{subjID}'
            MATCH (s2:Taxonomy) WHERE s2.name = '{objID}'
            MERGE (s1)-[:BELONGS_TO {{taxonomyID: '{taxonomyID}'}}]->(s2)
            RETURN *
        '''
        insertion = neo4jdriver.driver.execute_query(query).summary
    else:
        query = f'''
            MATCH (s1) WHERE s1.gbID = '{subjID}'
            MATCH (s2) WHERE s2.gbID = '{objID}'
            MERGE (s1)-[:BELONGS_TO]->(s2)
            RETURN *
        '''
        insertion = neo4jdriver.driver.execute_query(query).summary

def addStartEndTimeRelation(subjID, objID, relType):

    relType = relType.upper()

    query = f'''
        MATCH (i:TemporalInterval) WHERE i.gbID = '{subjID}'
        MATCH (n:TimePoint) WHERE ({objID} IN n.gbID)
        MERGE (i)-[:{relType}]->(n)
        RETURN *
    '''
    insertion = neo4jdriver.driver.execute_query(query).summary

def addOccupationRelation(subjID, objID):

    query = f'''
        MATCH (i:Person) WHERE i.gbID = '{subjID}'
        MATCH (n:Occupation) WHERE n.gbID = '{objID}' 
        MERGE (i)-[:OCCUPATION]->(n)
        MERGE (n)-[:DESCRIBES {{role: 'occupation'}}]->(i)
        RETURN *
    '''
    insertion = neo4jdriver.driver.execute_query(query).summary
    

#########################

def addIsA(entity, gbID=None, nameEnglish=None):

    if isinstance(gbID, list):
        query = f'''
            MATCH (n:Entity) WHERE n.name = '{entity}'
            MATCH (i:{entity}) WHERE ANY (id IN i.gbID WHERE id IN {gbID})
            MERGE (i)-[:IS_A]->(n)
            RETURN *
        '''
    elif nameEnglish:
        query = f'''
            MATCH (n:Entity) WHERE n.name = '{entity}'
            MATCH (i:{entity}) WHERE i.nameEnglish = '{nameEnglish}'
            MERGE (i)-[:IS_A]->(n)
            RETURN *
        '''
    else:
        query = f'''
            MATCH (n:Entity) WHERE n.name = '{entity}'
            MATCH (i:{entity}) WHERE i.gbID = '{gbID}'
            MERGE (i)-[:IS_A]->(n)
            RETURN *
        '''

    insertion = neo4jdriver.driver.execute_query(query).summary

def addHasPosTag(subjID, tag):
    query = f'''
        MATCH (l:Lemma) WHERE l.gbID = '{subjID}'
        MATCH (p:PartOfSpeech) WHERE p.value = '{tag}'
        MERGE (l)-[:HAS_POS_TAG]->(p)
        RETURN *
    '''
    insertion = neo4jdriver.driver.execute_query(query).summary

# to external links
def addSeeAlso(subjID, objID):

    query = f'''
        MATCH (s1:Sense) WHERE s1.gbID = '{subjID}'
        MATCH (s2:Sense) WHERE s2.gbID = '{objID}'
        MERGE (s1)-[:SAME_AS]->(s2)
        RETURN *
    '''
    insertion = neo4jdriver.driver.execute_query(query).summary

#objEntity can be Text, Quotation, Corpus, Document, usato per Language
def addUsedInRelation(nameEnglish, objID, objEntity):

    query = f'''
        MATCH (i:Language) WHERE i.nameEnglish = '{nameEnglish}'
        MATCH (n:{objEntity}) WHERE n.gbID = '{objID}'
        MERGE (i)-[:USED_IN]->(n)
        RETURN *
    '''
    insertion = neo4jdriver.driver.execute_query(query).summary
