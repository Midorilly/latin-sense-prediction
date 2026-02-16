import json
import sys
from sklearn.metrics import classification_report, mean_squared_error,  mean_absolute_error, balanced_accuracy_score, f1_score, precision_score, recall_score, confusion_matrix, ConfusionMatrixDisplay
import re
import os
import logging
from termcolor import colored
import matplotlib.pyplot as plt
import numpy as np
import src.utils.driver as driver
import pandas as pd
from src.utils.utils import jsonl2csv

# setup logger config
logger = logging.getLogger("latin-mt")
logging.basicConfig(format="%(asctime)s - %(message)s")
logger.setLevel(logging.DEBUG)

def load_per_word(filename, mode, word):
    gold = []
    sys = []
    with open(filename) as file:
        for line in file:
            o = json.loads(line)
            if o['lemma'] == word:
                if mode == 'binary':
                    gold.append(str(o['gold']))
                    sys.append(str(o['system']))
                elif mode == 'regression':
                    gold.append(float(o['gold']))
                    sys.append(float(re.sub("[^0-9\\.]+", '', str(o['system']))))
    file.close()
    return gold, sys

def load(filename, mode):
    gold = []
    sys = []
    with open(filename) as file:
        for line in file:
            o = json.loads(line)
            if mode == 'binary':
                gold.append(str(o['gold']))
                sys.append(str(o['system']))
            elif mode == 'regression':
                gold.append(float(o['gold']))
                sys.append(float(re.sub("[^0-9\\.]+", '', str(o['system']))))
    file.close()
    return gold, sys

def binary(f, gold, sys):

    f.write(f'Precision: {precision_score(gold, sys, average=None, zero_division=0.0)}\n')
    average = 'weighted'
    f.write(f'Weighted precision: {precision_score(gold, sys, average=average, zero_division=0.0)}\n')
    f.write(f'Recall: {recall_score(gold, sys, average=None, zero_division=0.0)}\n')
    f.write(f'Weighted recall: {recall_score(gold, sys, average=average, zero_division=0.0)}\n')            
    f.write(f'Balanced accuracy: {balanced_accuracy_score(gold,sys)}\n')

    #f.write(f'F1: {f1_score(gold, sys, average=None)}\n')
    f.write(f'F1: {f1_score(gold, sys, average=average)}\n')
    average = 'macro'
    f.write(f'F1-macro: {f1_score(gold, sys, average=average)}\n')
    average = 'micro'
    f.write(f'F1-micro: {f1_score(gold, sys, average=average)}\n')
    f.write(f'Classification report:\n {classification_report(gold, sys, zero_division=0.0)}')

def evaluate_per_word(file, output):

    df = pd.read_csv('data/groundtruth.csv', header=0)
    targets = df['word'].values.tolist()
    overview = open(os.path.join(output, 'overview.jsonl'), 'w+')

    x = {}
    for word in targets:
        gold, sys = load_per_word(file, 'binary', word)
        f = open(os.path.join(output, word+'.txt'), 'w') 
        binary(f, gold, sys)    
        f.close()
        x['word'] = word
        x['f1'] = f1_score(gold, sys, average='weighted')
        json.dump(x, overview)
        overview.write('\n')
        logger.info(colored('{} evaluated!'.format(word), 'green'))

    overview.close()
    jsonl2csv(os.path.join(output, 'overview.jsonl'), os.path.join(output, 'overview.csv'), ['word', 'f1'])

def evaluate(input, output):

    gold, sys = load(input, 'binary')
    f = open(output, 'w')
    binary(f, gold, sys)
    f.close()

if __name__ == '__main__':

    driver.load_environment()
    model_name = sys.argv[1]
    
    exps_file = os.path.join('exps', 'llm-only', 'senses', os.getenv(model_name)+'.jsonl')
    evaluate(input=exps_file, output=os.path.join('exps', 'llm-only', 'senses', os.getenv(model_name)+'-eval.txt'))
    evaluate_per_word(exps_file, os.path.join('appendix', 'llm-only', 'sense-metadata', os.getenv(model_name)))

