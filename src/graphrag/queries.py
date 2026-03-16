author_metadata_limit_1 = '''
        OPTIONAL MATCH (da)<-[:DATE]-(q:Quotation)-[:BELONGS_TO]->(d:Document)<-[:DEVELOPED]-(p:Person)-[:OCCUPATION]->(o:Occupation)
        WHERE q.gbID = '{}'
        RETURN q.value, d.title, collect(da.description), p.fullname, collect(o.name) LIMIT 1
    '''

author_metadata = '''
        OPTIONAL MATCH (da)<-[:DATE]-(q:Quotation)-[:BELONGS_TO]->(d:Document)<-[:DEVELOPED]-(p:Person)-[:OCCUPATION]->(o:Occupation)
        WHERE q.gbID = '{}'
        RETURN q.value, d.title, collect(da.description), p.fullname, collect(o.name)
    '''

author_prompt = '''
        Sentence "{}" 
        belongs to work {} 
        written in {}. 
        Its author is {} and was a {}.\n
    '''

hypernym_metadata = '''
        MATCH (s:Sense)-[:SAME_AS]-(x)-[:HYPERNYM]-(y)
        WHERE s.gloss = '{}'
        RETURN x.gloss, y.gloss LIMIT 1
'''

hyponym_metadata = '''
        MATCH (s:Sense)-[:SAME_AS]-(x)-[:HYPONYM]-(y)
        WHERE s.gloss = '{}'
        RETURN x.gloss, y.gloss LIMIT 1
'''

similarity_query = '''
        MATCH (q:Quotation) WHERE q.hash = '{}'
        CALL db.index.vector.queryNodes('QUOTATION_INDEX', {}, q._embedding)
        YIELD node AS quotation, score
        RETURN quotation.gbID AS gbID, score, q.gbID
    '''

negative_example = '''
        MATCH (q:Quotation)-[r:DESCRIBES]->(s:Sense)
        WHERE r.binary = 'no' and s.gloss = '{}'
        RETURN q.value, r.binary LIMIT 1
'''

positive_example = '''
        MATCH (q:Quotation)-[r:DESCRIBES]->(s:Sense)
        WHERE r.binary = 'yes' and s.gloss = '{}'
        RETURN q.value, r.binary LIMIT 1
'''