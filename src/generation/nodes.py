from rdflib import Namespace, Literal, URIRef, BNode
from rdflib.namespace import RDF, RDFS, OWL, XSD, DCTERMS
from urllib.parse import quote
import urllib.error
import nltk
nltk.download('wordnet')
nltk.download('wordnet31')
from nltk.corpus import wordnet as wn30
from nltk.corpus import wordnet31 as wn31
import re
import logging
from SPARQLWrapper import SPARQLExceptions
import hashlib
import src.utils.utils as utils
import src.utils.driver as driver
from namespaces import LILA, LEXINFO, SKOS08, LVONT
from relations import *
import queries

logging.basicConfig(format='%(asctime)s %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

driver.load_environment()
neo4jdriver = driver.init_driver()

lilaPosMapping = {'N' : LILA.noun, 'ADJ' : LILA.adjective, 'V' : LILA.verb}
lexinfoPosMapping = {'N' : LEXINFO.noun , 'ADJ' : LEXINFO.adjective, 'V' : LEXINFO.verb}

# pos da rivedere
def addTaxonomyNode():
    query = '''
        CREATE (WordNet30:Taxonomy {name: 'WordNet30'})
        CREATE (WordNet31:Taxonomy {name: 'WordNet31'})
        CREATE (LewisShort:Taxonomy {name: 'LewisShort'})
        CREATE (PartOfSpeech:Taxonomy {name: 'PartOfSpeech'}) 
    '''
    insertion = neo4jdriver.driver.execute_query(query).summary
    x = ['WordNet30', 'WordNet31', 'LewisShort']
    for p in x:
        query = f'''
            MATCH (n:Entity) WHERE n.name = 'Taxonomy'
            MATCH (i:Taxonomy) WHERE i.name = '{p}'
            MERGE (i)-[:IS_A]->(n)
            RETURN *
        '''
    insertion = neo4jdriver.driver.execute_query(query).summary

def addPoSTagNode():

    query = '''
        CREATE (noun:PartOfSpeech {pos: 'noun', value: 'N'})
        CREATE (adjective:PartOfSpeech {pos: 'adjective', value: 'ADJ'})
        CREATE (verb:PartOfSpeech {pos: 'verb', value: 'V'})
    '''
    insertion = neo4jdriver.driver.execute_query(query).summary

    x = ['noun', 'adjective', 'verb']
    for p in x:
        query = f'''
            MATCH (n:Entity) WHERE n.name = 'PartOfSpeech'
            MATCH (i:PartOfSpeech) WHERE i.pos = '{p}'
            MERGE (i)-[:IS_A]->(n)
            RETURN *
        '''
        insertion = neo4jdriver.driver.execute_query(query).summary

        addBelongsToRelation(subjID=p, objID='PartOfSpeech', taxonomyID='PartOfSpeechTaxonomy') # da rivedere

def addLemmaNode(writtenRep, pos, mwe, id):
    if mwe == 0.0: mweBool = False
    else: mweBool = True

    query = f'''
        CREATE ({writtenRep}:Lemma {{name: '{writtenRep}', multiWordExpression: '{mweBool}', gbID: '{id}'}})
    '''
    insertion = neo4jdriver.driver.execute_query(query).summary

    addIsA(entity='Lemma', gbID=id)
    addHasPosTag(subjID=id, tag=pos)
    addUsedInRelation('Latin', id, 'Lemma')
    addLexicalEntryNode(writtenRep, id, 'Latin') 
    addLemmaRelation(id,id)

def addLexicalEntryNode(entry, id, language):
    if bool(re.search(r'\s', entry)): mweBool = True
    else: mweBool = False

    create = f'''
        CREATE ({entry}:InflectedWord {{name: '{entry}', gbID: '{id}'}})
    '''
    insertion = neo4jdriver.driver.execute_query(create).summary

    addIsA(entity='InflectedWord', gbID=id)
    addUsedInRelation(language, id, 'InflectedWord')

def addLexicalSenseNode(resource, sense, gloss, id):

    sense_clean = re.sub('[-+.\"\']', '_', sense.lower())
    gloss_clean = re.sub('[\"\'+]', '', gloss.strip())
    gloss_clean = re.sub('/', '-', gloss_clean.lower())
    if resource == 'Lewis-Short Dictionary':
        gloss_clean = re.sub(',(?!\s)', ', ', gloss_clean)

    query = f'''
        CREATE ({sense_clean}:Sense {{name: '{sense}', gloss: '{gloss_clean}', gbID: '{id}'}})
    '''
    insertion = neo4jdriver.driver.execute_query(query).summary

    addIsA(entity='Sense', gbID=id)
    if resource == 'Latin WordNet':
        wn30sense = wn30.synset(sense)
        wn30offset = str(wn30sense.offset())
        wn30pos = str(wn30sense.pos())
        wn30id = '{}-{}'.format(wn30offset.zfill(8),wn30pos)
        addBelongsToRelation(subjID=id, objID='WordNet30', taxonomyID=wn30id)

        wn31sense = wn31.synset(sense)
        wn31offset = str(wn31sense.offset())
        wn31pos = str(wn31sense.pos())
        wn31id = '{}-{}'.format(wn31offset.zfill(8),wn31pos)
        addBelongsToRelation(subjID=id, objID='WordNet31', taxonomyID=wn31id)

    elif resource == 'Lewis-Short Dictionary':
        addBelongsToRelation(subjID=id, objID='LewisShort', taxonomyID=sense_clean)


def addLexicalConceptNode(concept, id):

    query = f'''
        CREATE ({concept}:Concept {{value: '{concept}', gbID: '{id}'}})
    '''
    insertion = neo4jdriver.driver.execute_query(query).summary

    addIsA(entity='Concept', gbID=id)

def addPersonNode(firstname, lastname, id, df):
    # sistema nome x cercarlo nel dataframe
    if lastname != None: fullname = '{} {}'.format(firstname, lastname)
    else: fullname = firstname + ' '

    if fullname[-1] == ' ': label = fullname[:-1]
    else: label = fullname

    wikiEntity = []    
    try: 
        if fullname in df['fullname'].values.tolist():
            authorEntity = df.loc[(df['fullname'] == fullname), 'id'].values[0]
            authorURI = WIKIENTITY+authorEntity
        else:
            wikiEntity = queries.query(queries.authorQuery.format(label))
    except urllib.error.HTTPError or SPARQLExceptions.EndPointInternalError or urllib.error.URLError as e:
        logger.info('{}'.format(e))
    finally:  
        if len(wikiEntity) > 0:
            authorURI = wikiEntity[0]['authorURI']

    label = re.sub('[\s\(\)\.\'\:\;]', '_', label)

    query = f'''
        CREATE ({label}:Person {{fullname: '{label}', wikidata: '{authorURI}', gbID: '{id}'}})
    '''
    insertion = neo4jdriver.driver.execute_query(query).summary

    addIsA(entity='Person', gbID=id)

def addOccupationNode(occupation, id, dict):
    occupationURI = WIKIENTITY+dict[occupation]
    occupation = re.sub('\s', '_', occupation)
    occupation = re.sub('\'', '_', occupation)
    query = f'''
        CREATE ({occupation}:Occupation {{name: '{occupation}', wikidata: '{occupationURI}', gbID: '{id}'}})
    '''
    insertion = neo4jdriver.driver.execute_query(query).summary

    addIsA(entity='Occupation', gbID=id)

def addQuotationNode(quotation: str, language: str, id, start=None, end=None):
    text = f'quotation_{id}'

    quotation = re.sub('[-+\"\']', '', quotation.lower())
    quotation = re.sub('(?:\[target\]|\[/target\]|target|</line>|<line>|</section>|<section>|</p>|<p>|</book>|<book>)', '', quotation)    #quotation = re.sub('"', '', quotation)
    quotation = re.sub(' +', ' ', quotation)
    strippedQuotation = quotation.strip()
    quotationHash = utils.getSentenceHash(strippedQuotation)
    #quotation = re.sub('\'', '', quotation)

    query = f'''
        CREATE ({text}:Quotation {{value: '{strippedQuotation}', gbID: '{id}', hash: '{quotationHash}'}})
    '''
    insertion = neo4jdriver.driver.execute_query(query).summary

    addIsA(entity='Quotation', gbID=id)
    addUsedInRelation('Latin', id, 'Quotation')

def addDocumentNode(title, id):

    title = re.sub('[\s\(\)\.\'\:\;\*\,]', '_', title)

    query = f'''
        CREATE ({title}:Document {{title: '{title}', gbID: '{id}'}})
    '''
    insertion = neo4jdriver.driver.execute_query(query).summary

    addIsA(entity='Document', gbID=id)
    addUsedInRelation('Latin', id, 'Document')

def addCorpusNode(title, id):

    query = f'''
        CREATE ({title}:Corpus {{name: '{title}', gbID: '{id}'}})
    '''
    insertion = neo4jdriver.driver.execute_query(query).summary

    addIsA(entity='Corpus', gbID=id)
    addUsedInRelation('Latin', id, 'Corpus')

def addLanguageNode(language, l: Graph):
    try:
        nameEnglish = Literal(l.value(subject=language, predicate=SKOS08.prefLabel, object=None), lang='en')
        nameEnglish = re.sub('[-\s\(\)\.\'\:\;\*\,]', '_', nameEnglish)
        if nameEnglish == 'Latin':
            iso63911 = l.value(subject=language, predicate=LVONT.iso639P1Code, object=None, any=False)
            iso63921 = l.value(subject=language, predicate=LVONT.iso6392TCode, object=None, any=False)
            iso63931 = l.value(subject=language, predicate=LVONT.iso639P3PCode, object=None, any=False)
            query = f'''
                CREATE ({nameEnglish}:Language {{nameEnglish: '{nameEnglish}', iso63911: '{iso63911}', iso63921: '{iso63921}', iso63931: '{iso63931}'}})
            '''
            insertion = neo4jdriver.driver.execute_query(query).summary
            addIsA(entity='Language', nameEnglish=nameEnglish)
    except neo4j.exceptions.CypherSyntaxError as e:
        print(e)

def addTimeIntervalNode(name, description, id):

    name = name.split(' ')
    century = utils.roman(name[1])
    name = century + '_' + name[2]
    
    query = f'''
       CREATE ({name}:TemporalInterval {{name: '{name}', description: '{description}', gbID: '{id}'}})
    '''
    insertion = neo4jdriver.driver.execute_query(query).summary
    addIsA(entity='TemporalInterval', gbID=id)

def addTimePointNode(pointsDict):

    for year, ids in pointsDict.items():
        date, period = utils.convertDate(year)
        name = utils.roman(date)+'_'+period
        description = date+'_'+period

        query = f'''
            CREATE ({name}:TimePoint {{name: '{name}', description: '{description}', gbID: {ids}}})
        '''
        insertion = neo4jdriver.driver.execute_query(query).summary
        addIsA(entity='TimePoint', gbID=ids)

    