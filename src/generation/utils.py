import os
from dotenv import load_dotenv
from typing import Any, List, Optional, Type, TypeVar, Iterable, Union
from neo4j import GraphDatabase
from driver import *
import hashlib
import re

load_environment()
neo4jdriver = init_driver()

def generateTimePointsDictionary(points):
    pointsDict = {}
    for line in points:
        year = line['properties']['Year']
        if year in pointsDict.keys():
            pointsDict[year].append(line['identity'])
        else:
            pointsDict[year] = [line['identity']]

    return pointsDict

def convertDate(date): # ISO-8601
    if date < 0:
        period = 'BCE'
        if date == -1 : dateString = '0000'
        else: dateString = str((date+1)*(-1)).zfill(4)
            
    else: 
        dateString = str(date).zfill(4)
        period = 'CE'

    dateString = dateString.split('.')
    return dateString[0], period    
    
def roman(num: int) -> str:

    chlist = "VXLCDM"
    rev = [int(ch) for ch in reversed(str(num))]
    chlist = ["I"] + [chlist[i % len(chlist)] + "\u0304" * (i // len(chlist))
                    for i in range(0, len(rev) * 2)]

    def period(p: int, ten: str, five: str, one: str) -> str:
        if p == 9:
            return one + ten
        elif p >= 5:
            return five + one * (p - 5)
        elif p == 4:
            return one + five
        else:
            return one * p

    return "".join(reversed([period(rev[i], chlist[i * 2 + 2], chlist[i * 2 + 1], chlist[i * 2])
                            for i in range(0, len(rev))]))


def queryReport(summary):

    print("Created {relations_created} relationships and {relations_deleted} deleted in {time} ms.".format(
        nodes_created=summary.counters.nodes_created,
        relations_created=summary.counters.relationships_created,
        relations_deleted=summary.counters.relationships_deleted,
        time=summary.result_available_after
    ))

def getSentenceHash(sentence: str) -> str:
    splitSentence = sentence.split(' ')
    startJoin = ' '.join(splitSentence[:5]).encode('utf-8')
    x = len(splitSentence)-5
    endJoin = ' '.join(splitSentence[x:]).encode('utf-8')
    sentenceHash = int(hashlib.md5(startJoin+endJoin).hexdigest(), 16)

    return sentenceHash

def cleanQuotation(quotation):

    quotation = re.sub('[-+\"\']', '', quotation.lower())
    quotation = re.sub('(?:\[target\]|\[/target\]|target|</line>|<line>|</section>|<section>|</p>|<p>|</book>|<book>)', '', quotation)    #quotation = re.sub('"', '', quotation)
    quotation = re.sub(' +', ' ', quotation)
    quotationHash = getSentenceHash(quotation.strip())
    return quotationHash

def cleanGloss(gloss):
    gloss = re.sub('[\"\'+]', '', gloss.lower())
    gloss = gloss.strip()
    return gloss
