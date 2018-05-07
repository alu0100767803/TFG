#! /usr/bin/env python
# -*- coding: utf-8 -*-

import requests
import json
import pymongo
import pandas
import re
import nltk
import numpy
import itertools
import datetime 


from ggplot import *
from matplotlib import pyplot as plt
from wordcloud import WordCloud
from pymongo import MongoClient
from requests_oauthlib import OAuth2
from tqdm import tqdm

#Base de datos 
client = MongoClient('localhost:27017')
db = client.db_analyzer
db_analyzer = db.analyzer
collection_posts = db_analyzer.posts
collection_comments = db_analyzer.comments

#Limpiamos la base de datos para que no se repliquen los datos o interfieran con los de otras páginas
collection_posts.delete_many({})
collection_comments.delete_many({})

id = "tenerifevacanze"              # id de la página que va a ser analizada
"""Páginas usadas
 * tenerifevacanze
 * VisitTenerifeES"""



url = 'https://graph.facebook.com/v2.12/'
page_url = 'https://graph.facebook.com/v2.12/%s/feed?fields=id,message,reactions,shares,from,caption,created_time,likes.summary(true)' %id
print(page_url)
# Todos los campos deben de ser especificados
comments_url = 'https://graph.facebook.com/v2.12/{post_id}/comments?filter=stream&limit=100'

# Variable con el token de acceso de Facebook
params = {'access_token' : 'EAACQFfa9JeIBAKK0ZCX9x7vGxtDjfDjLLo5W8qVz5REnvqr30DSEy4EgrZAU0RLG0AxYo2UFdfU3hUqtm3T3dEys1eZC1BDq1IRnfpZAKwDDVi6n0LqAYKgOazNbj26FOD7zPGhZCz3RlFw4ADrqIHLC3yc1m7EEZD'}
posts = requests.get(page_url, params = params)
posts = posts.json()

# Data extraction

while True:
    try:
        print("Recopilando datos...")
        ### Recupera un post
        for element in posts['data']:
            collection_posts.insert_one(element)
            #### Recupera todos los comentarios de ese post
            this_comment_url = comments_url.replace("{post_id}", element['id'])
            comments = requests.get(this_comment_url, params = params).json()
            # Recorre todos los comentarios hasta que la respuesta esté vacía, que no haya más comentarios
            while ('paging' in comments and 'cursors' in comments['paging'] and 'after' in comments['paging']['cursors']):
                ### Itera a través de todos los comentarios
                for comment in comments['data']:
                    comment['post_id'] = element['id']
                    collection_comments.insert_one(comment)
                comments = requests.get(this_comment_url + '&after=' + comments['paging']['cursors']['after'], params = params).json()
        #### Vamos a la siguiente página en feed
        posts = requests.get(posts['paging']['next']).json()
    except KeyError as e:
        print(e)
        break

print("Datos recopilados")

# Data pull

posts_data = []
comments_data = []

for doc in collection_posts.find({}):
    if 'message' in doc.keys():
        posts_data.append((doc['message'], doc['created_time'], doc['likes']['summary']['total_count'], doc.get('shares', {'count': 0})['count'], doc['id']))
    else:
        pass
        #print("No message")
        
print(len(posts_data))
    
for comment in collection_comments.find({}):
    if 'message' in comment.keys():
        comments_data.append((comment['message'], comment['created_time'], comment['post_id']))
    else:
        pass

print(len(comments_data))

df_posts = pandas.DataFrame(posts_data)
df_posts.columns = ['message', 'created_time', 'likes', 'shares', 'post_id']
df_comments = pandas.DataFrame(comments_data)
df_comments.columns = ['message', 'created_time', 'post_id']
print(df_comments)

# Feature extraction


# Funciones

# Limpia comentarios y posts
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

# 
def tag_tokens(preprocessed_tokens):
    pos = nltk.pos_tag(preprocessed_tokens)
    return(pos,)

# 
def get_keywords(tagged_tokens, pos='all'):

    if(pos == 'all'):
        lst_pos = ('NN','JJ','VB')
    elif(pos == 'nouns'):
        lst_pos = 'NN'
    elif(pos == 'verbs'):
        lst_pos = 'VB'
    elif(pos == 'adjectives'):
        lst_pos = 'JJ'
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
    print("Entro execute pipeline")
    #Obtener hashtags
    dataframe['hashtags'] = dataframe.apply(lambda x: get_hashtags(x['message']), axis=1)
    print("Paso 1")
    #
    dataframe['preprocessed'] = dataframe.apply(lambda x: preprocess(x['message']), axis=1, reduce=True)
    print("Paso 2")
    #
    dataframe['tagged'] = dataframe.apply(lambda x: tag_tokens(x['preprocessed'][0]), axis=1)
    print("Paso 3") 
    #Extraer palabras clave
    dataframe['keywords'] = dataframe.apply(lambda x: get_keywords(x['tagged'][0], 'all'), axis=1)
    print("Paso 4")
    #
    dataframe['noun_phrases'] = dataframe.apply(lambda x: get_noun_phrases(x['tagged'][0]), axis=1)
    print("Paso 5")
    print("Salgo execute pipeline")
    return(dataframe)


df_posts = execute_pipeline(df_posts)
df_comments = execute_pipeline(df_comments)

#Content analysis
 
def viz_wordcloud(dataframe, column_name):
    lst_tokens = list(itertools.chain.from_iterable(dataframe[column_name][0]))
    lst_phrases = [phrase.replace(" ", "_") for phrase in lst_tokens]

    CLEANING_LIST = [] # Lista con palabras que consideraremos como ruido
    lst_phrases = [phrase.replace("","_") for phrase in lst_phrases if not any(spam in phrase.lower() for spam in CLEANING_LIST)] # Quitamos los keywords considerados como ruido
    lst_phrases = [phrase.replace("","_") for phrase in lst_phrases if len(phrase) > 1] # Eliminamos los tokens que son de una sola letra

    wordcloud = WordCloud(font_path='./Font/Verdana.ttf', background_color="White", max_words=2000, max_font_size=40, random_state=42).generate(" ".join(lst_phrases))

    plt.figure()
    plt.imshow(wordcloud)
    plt.axis("off")
    plt.show()

def print_verbatims(df, nb_verbatim, keywords):
    verbatims = df[df['message'].str.contains(keywords)]
    for i, text in verbatims.head(nb_verbatim).iterrows():
        print(text['message'])

"""viz_wordcloud(df_posts, 'keywords')
viz_wordcloud(df_comments, 'keywords')"""

df_comments['date'] = df_comments['created_time'].apply(pandas.to_datetime)
df_comments_ts = df_comments.set_index(['date'])
df_comments_ts = df_comments_ts['2015-01-01':]

df_posts['date'] = df_posts['created_time'].apply(pandas.to_datetime)
df_posts_ts = df_posts.set_index(['date'])
df_posts_ts = df_posts_ts['2015-01-01':]

#Creamos un data frame que contiene la cantidad promedio de likes y shares por semana
dx = df_posts_ts.resample('W').mean()
dx.index.name = 'date'
dx = dx.reset_index()

#Mostramos el progreso de likes
p = ggplot(dx, aes(x = 'date', y = 'likes')) + geom_line()
p = p + xlab("Date") + ylab("Number of likes") + ggtitle("Facebook vacanzeTenerife Page")
print(p)

#Mostramos el progreso de shares
p = ggplot(dx, aes(x = 'date', y = 'shares')) + geom_line()
p = p + xlab("Date") + ylab("Number of shares") + ggtitle("Facebook VacanzeTenerife Page")
print(p)

# criterium 
def max_wordcloud(ts_df_posts, ts_df_comments, columnname, criterium):
    mean_week = ts_df_posts.resample('W').mean()
    start_week = (mean_week[criterium].idxmax() - datetime.timedelta(days=7)).strftime('%Y-%m-%d')
    end_week = mean_week[criterium].idxmax().strftime('%Y-%m-%d')
    viz_wordcloud(ts_df_posts[start_week:end_week], columnname)
    viz_wordcloud(ts_df_comments[start_week:end_week], columnname)
