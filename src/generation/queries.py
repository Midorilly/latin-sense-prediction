from SPARQLWrapper import SPARQLWrapper, JSON, SPARQLExceptions
from rdflib import Graph
from namespaces import WIKIENTITY, WIKIPROP, SKOS04, BIGDATA, WIKIBASE
import rdflib.query
import urllib.error
import time
import logging
import socket

q = Graph()

q.bind("wd", WIKIENTITY)
q.bind("wdt", WIKIPROP)
q.bind("skos", SKOS04)
q.bind("bd", BIGDATA)
q.bind("wikibase", WIKIBASE)

logging.basicConfig(format='%(asctime)s %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

authorQuery = '''SELECT ?authorURI 
    WHERE {{
        ?authorURI wdt:P31 wd:Q5 .
        {{ ?authorURI skos:altLabel ?label .}}
        UNION
        {{ ?authorURI rdfs:label ?label . }}
    FILTER (regex(str(?label), "{}", "i"))
    SERVICE wikibase:label {{ bd:serviceParam wikibase:language "[AUTO_LANGUAGE],en". }}
    }} LIMIT 1
'''

MAXRETRY = 5
def queryRetry(query: str, initNs, initBindings) -> rdflib.query.Result:
    backoff = 2
    connectionBackoff = 5
    for i in range(MAXRETRY):
        try:
            result = q.query(query, initNs = initNs, initBindings = initBindings)
            print(result.bindings)
            #result.bindings
            return result
        except urllib.error.URLError or TimeoutError or json.decoder.JSONDecodeError as e:
            if i == MAXRETRY-1:
                raise e
            backoffS = 2 ** backoff
            backoff += 1
            logger.info('{} \nwaiting for {}s and retrying'.format(e, backoffS))
            time.sleep(backoffS)
        except ConnectionError as c: 
            if i == MAXRETRY-1:
                raise e
            backoffS = 2 ** connectionBackoff
            connectionBackoff += 1
            logger.info('{} \nwaiting for {}s and retrying'.format(c, backoffS))
            time.sleep(backoffS)

def transform2dicts(results):
    new_results = []
    for result in results:
        new_result = {}
        for key in result:
            new_result[key] = result[key]['value']
        new_results.append(new_result)
    return new_results

def query(query: str):
    socket.getaddrinfo('localhost',8080)
    endpoint = "https://query.wikidata.org/sparql"
    sparql = SPARQLWrapper(endpoint)
    sparql.setQuery(query)
    sparql.setReturnFormat(JSON)
    results = []
    n = 2
    logger.info('Querying...')
    for i in range(MAXRETRY):
        try:
            results = sparql.queryAndConvert()['results']['bindings']
            results = transform2dicts(results)
            return results
        except urllib.error.HTTPError or SPARQLExceptions.EndPointInternalError or urllib.error.URLError as e:
            if i == MAXRETRY-1:
                raise e
            else:
                logger.info('{}, waiting 60s'.format(e))
                backoffS = n * 61
                n += 1
                time.sleep(backoffS)        

    


