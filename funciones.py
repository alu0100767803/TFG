#! /usr/bin/env python
# -*- coding: utf-8 -*-

import re
import nltk

def preprocess(text):
    # Limpieza básica
    # Limpia de espacios y signos de puntuación, y convierte en minúscula
    text = text.strip()
    text = re.sub(r'[^\w\s]','',text)
    text = text.lower()

    # Divide en tokens
    tokens = nltk.word_tokenize(text) 

    return(tokens,)

# Obtiene los hastags de los mensajes
def get_hashtags(text):
    hashtags = re.findall(r"#(\w+)", text)
    return(hashtags,)

# Etiqueta los tokens preprocesados
def tag_tokens(preprocessed_tokens):
    pos = nltk.pos_tag(preprocessed_tokens)
    return(pos,)

# Obtiene las palabras clave
def get_keywords(tagged_tokens, pos='all'):

    if(pos == 'all'):
        lst_pos = ('NN','JJ','VB')
    elif(pos == 'nouns'):
        lst_pos = 'NN' #Filtra por sustantivos
    elif(pos == 'verbs'):
        lst_pos = 'VB' #Filtra por verbos
    elif(pos == 'adjectives'):
        lst_pos = 'JJ' #Filtra por adjetivos
    else:
        lst_pos = ('NN','JJ','VB')

    keywords = [tup[0] for tup in tagged_tokens if tup[1].startswith(lst_pos)]
    return(keywords,)


def get_noun_phrases(tagged_tokens):

    grammar = "NP: {<DT>?<JJ>*<NN>}"
    cp = nltk.RegexpParser(grammar)
    tree = cp.parse(tagged_tokens)

    result = []
    for subtree in tree.subtrees(filter=lambda t: t.label() == 'NP'):
        #Solo tomamos frases, no palabras sueltas
        if(len(subtree.leaves()) > 1):
            outputs = [tup[0] for tup in subtree.leaves()]
            outputs = " ".join(outputs)
            result.append(outputs)
    return(result,)

def execute_pipeline(dataframe):
    
    # Obtiene hashtags
    dataframe['hashtags'] = dataframe.apply(lambda x: get_hashtags(x['message']), axis=1)
    
    # Preprocesamiento
    dataframe['preprocessed'] = dataframe.apply(lambda x: preprocess(x['message']), axis=1)
    
    # Etiquetado
    dataframe['tagged'] = dataframe.apply(lambda x: tag_tokens(x['preprocessed'][0]), axis=1)

    #Obtiene palabras clave
    dataframe['keywords'] = dataframe.apply(lambda x: get_keywords(x['tagged'][0], 'all'), axis=1)
    
    # Obtiene frases nominales
    dataframe['noun_phrases'] = dataframe.apply(lambda x: get_noun_phrases(x['tagged'][0]), axis=1)

    return(dataframe)