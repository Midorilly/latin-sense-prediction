from rdflib import Namespace, Graph
from rdflib.namespace import RDF, RDFS, OWL, XSD, DCTERMS

SCHEMA = Namespace("https://schema.org/")
ONTOLEX = Namespace("http://www.w3.org/ns/lemon/ontolex#")
VARTRANS = Namespace("http://www.w3.org/ns/lemon/vartrans#")
LEXINFO = Namespace("http://www.lexinfo.net/ontology/2.0/lexinfo#")
LIME = Namespace("http://www.w3.org/ns/lemon/lime#")
LEXVO = Namespace("http://lexvo.org/id/term/")
LVONT = Namespace("http://lexvo.org/ontology#")
SKOS04 = Namespace("http://www.w3.org/2004/02/skos/core#")
SKOS08 = Namespace("http://www.w3.org/2008/05/skos#")
WIKIENTITY = Namespace("http://www.wikidata.org/entity/")
WIKIPROP = Namespace("http://www.wikidata.org/prop/direct/")
WIKIBASE = Namespace("http://wikiba.se/ontology#")
BIGDATA = Namespace("http://www.bigdata.com/rdf#")
LLKG = Namespace("http://llkg.com/")
LEMONETY = Namespace("http://lari-datasets.ilc.cnr.it/lemonEty#")
CC = Namespace("https://creativecommons.org/ns#")
POWLA = Namespace("https://raw.githubusercontent.com/acoli-repo/powla/main/owl/powla.owl#")

# RESOURCES
WORDNET = Namespace("https://globalwordnet.github.io/schemas/wn#")
UWN = Namespace("http://www.lexvo.org/uwn/entity/s/")
LILA = Namespace("http://lila-erc.eu/ontologies/lila/")
INTRATEXT = Namespace("http://www.intratext.com/IXT/")
MQDQ = Namespace("https://www.mqdq.it/texts/")
LC = Namespace("http://penelope.uchicago.edu/Thayer/E/Roman/home.html")

llkgSchema = Graph()

llkgSchema.bind("rdf", RDF)
llkgSchema.bind("rdfs", RDFS)
llkgSchema.bind("xsd", XSD)
llkgSchema.bind("dct", DCTERMS)
llkgSchema.bind("owl", OWL)

llkgSchema.bind("schema", SCHEMA)
llkgSchema.bind("ontolex", ONTOLEX)
llkgSchema.bind("vartrans", VARTRANS)
llkgSchema.bind("lexinfo", LEXINFO)
llkgSchema.bind("lime", LIME)
llkgSchema.bind("wn", WORDNET)
llkgSchema.bind("llkg", LLKG)
llkgSchema.bind("powla", POWLA)

llkgSchema.bind('intratext', INTRATEXT)
llkgSchema.bind('mqdq', MQDQ)
llkgSchema.bind('lc', LC)

schemaFile = '/home/ghizzotae/knowledge-graph/schema/llkg-schema.ttl'

llkgSchema.parse(schemaFile, format='ttl')
