from urllib.parse import quote
import urllib.error
#import nltk
#nltk.download('wordnet')
#nltk.download('wordnet31')
#from nltk.corpus import wordnet as wn30
#from nltk.corpus import wordnet31 as wn31
import re
#from namespaces import *
import logging
from SPARQLWrapper import SPARQLExceptions
#import relations
import hashlib
from utils import *
from driver import *

load_environment()
neo4jdriver = init_driver()

def createSchemaNodes():

    # volendo si può inserire un attributo che spieghi il nodo (description)
    hierarchy = neo4jdriver.driver.execute_query("""
        CREATE (InflectedWord:Entity {name: 'InflectedWord'})
        CREATE (Lemma:Entity {name: 'Lemma'})
        CREATE (Word:Entity {name: 'Word'})
        CREATE (Stem:Entity {name: 'Stem'})
        CREATE (ContentDescription:Entity {name: 'ContentDescritption'})
        CREATE (Text:Entity {name: 'Text'})
        CREATE (Concept:Entity {name: 'Concept'})
        CREATE (Language:Entity {name: 'Language'})
        CREATE (Sense:Entity {name: 'Sense'})
        CREATE (Sentence:Entity {name: 'Sentence'})
        CREATE (Document:Entity {name: 'Document'})
        CREATE (Corpus:Entity {name: 'Corpus'})
        CREATE (TemporalSpecification:Entity {name: 'TemporalSpecification'})
        CREATE (TimePoint:Entity {name: 'TimePoint'})
        CREATE (TemporalInterval:Entity {name: 'TemporalInterval'})
        CREATE (Agent:Entity {name: 'Agent'})
        CREATE (Person:Entity {name: 'Person'})
        CREATE (Occupation:Entity {name: 'Occupation'})
        CREATE (Organization:Entity {name: 'Organization'})
        CREATE (Quotation:Entity {name: 'Quotation'})
        CREATE (PartOfSpeech:Entity {name: 'PartOfSpeech'})
        CREATE (Taxonomy:Entity {name: 'Taxonomy'})

        CREATE (InflectedWord)-[:HAS_SUBCLASS]->(Lemma)
        CREATE (InflectedWord)<-[:IS_A]-(Lemma)
        CREATE (Word)-[:HAS_SUBCLASS]->(Stem)
        CREATE (Word)<-[:IS_A]-(Stem)
        CREATE (ContentDescription)-[:HAS_SUBCLASS]->(Concept)
        CREATE (ContentDescription)<-[:IS_A]-(Concept) 
        CREATE (ContentDescription)-[:HAS_SUBCLASS]->(Text)
        CREATE (ContentDescription)<-[:IS_A]-(Text)
        CREATE (ContentDescription)-[:HAS_SUBCLASS]->(Language)
        CREATE (ContentDescription)<-[:IS_A]-(Language)
        CREATE (TemporalSpecification)-[:HAS_SUBCLASS]->(TimePoint)
        CREATE (TemporalSpecification)<-[:IS_A]-(TimePoint)
        CREATE (TemporalSpecification)-[:HAS_SUBCLASS]->(TemporalInterval)
        CREATE (TemporalSpecification)<-[:IS_A]-(TemporalInterval)
        CREATE (Agent)-[:HAS_SUBCLASS]->(Person)
        CREATE (Agent)<-[:IS_A]-(Person)
        CREATE (Occupation)-[:IS_A]->(Concept)
        CREATE (Concept)-[:HAS_SUBCLASS]->(Occupation)
        CREATE (Agent)-[:HAS_SUBCLASS]->(Organization)
        CREATE (Agent)<-[:IS_A]-(Organization)
        CREATE (Text)-[:HAS_SUBCLASS]->(Quotation)
        CREATE (Text)<-[:IS_A]-(Quotation)
    """
    ).summary

    print(hierarchy)

if __name__ == '__main__':

    createSchemaNodes()


