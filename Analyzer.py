#! /usr/bin/env python
# -*- coding: utf-8 -*-

import requests
import json
import pymongo
import pandas
import re
import nltk
import numpy
import matplotlib
import itertools
import datetime 
import ggplot
import wordcloud
import plotly
import plotly.plotly as py
import plotly.graph_objs as go


from ggplot import *
from matplotlib import pyplot as plt
from wordcloud import WordCloud
from pymongo import MongoClient

from watson_developer_cloud import NaturalLanguageUnderstandingV1
from watson_developer_cloud.natural_language_understanding_v1 \
  import Features, EmotionOptions, SentimentOptions

#Base de datos 
client = MongoClient('localhost:27017')
db = client.db_analyzer
db_analyzer = db.analyzer
collection_posts = db_analyzer.posts
collection_comments = db_analyzer.comments

#Limpiamos la base de datos para que no se repliquen los datos o interfieran con los de otras páginas
collection_posts.delete_many({})
collection_comments.delete_many({})

id = "turismoTenerife"              # id de la página que va a ser analizada


url = 'https://graph.facebook.com/v2.12/'
page_url = 'https://graph.facebook.com/v2.12/%s/feed?fields=id,message,shares,created_time,likes.summary(true)' %id
print(page_url)
# Todos los campos deben de ser especificados
comments_url = 'https://graph.facebook.com/v2.12/{post_id}/comments?filter=stream&limit=100'

# Variable con el token de acceso de Facebook
params = {'access_token' : 'EAACQFfa9JeIBAI1wRhKxGmFTvH5BJ6GhmhrrPrWkvkh0iG29oiSGPocYWgxIYaDgkFapkxmn4ZB7bz0nVb6D0DQ2VynIZAT7gegZCkixBaXlcRZBvpCfArZB0Yfyr3HRUUJ3Epc4CJHsgNRnmlqQZCRt5QCDzU7ioZD'}
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
        posts_data.append((doc['message'], doc['created_time'], doc['likes']['summary']['total_count'], 
            doc.get('shares', {'count': 0})['count'], doc['id']))
    else:
        pass
        
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


df_posts = execute_pipeline(df_posts)
df_comments = execute_pipeline(df_comments)

#Content analysis
 
def viz_wordcloud(dataframe, column_name, title):
    lst_tokens = list(itertools.chain.from_iterable(dataframe[column_name]))
    lst_p = []
    for phrase in lst_tokens:
        lst_p.extend(phrase)
    lst_phrases = [phrase.replace(" ", "_") for phrase in lst_p]
    if column_name == 'keywords':
        CLEANING_LIST = ['que', 'el', 'la', 'un', 'lo', 'del', 'para', 'en', 'al', 'por'] # Lista con palabras que consideraremos como ruido
    else:
        CLEANING_LIST = []
    # Quitamos los elementos considerados como ruido
    lst_phrases = [phrase.replace(" ","_") for phrase in lst_phrases if not any(spam in phrase.lower() for spam in CLEANING_LIST)] 
    # Eliminamos los tokens que son de una sola letra
    lst_phrases = [phrase.replace(" ","_") for phrase in lst_phrases if len(phrase) > 1] 

    wordcloud = WordCloud(font_path='./Fonts/Verdana.ttf', background_color="White", max_words=2000
                                        , max_font_size=40, random_state=42).generate(" ".join(lst_phrases))

    plt.figure()
    plt.imshow(wordcloud)
    plt.axis("off")
    plt.title(title)
    plt.show()

def print_verbatims(df, nb_verbatim, keywords):
    verbatims = df[df['message'].str.contains(keywords)]
    for i, text in verbatims.head(nb_verbatim).iterrows():
        print(text['message'])

#Mostrando las nubes de palabras
#Keywords
viz_wordcloud(df_posts, 'keywords', 'Palabras clave en publicaciones')
viz_wordcloud(df_comments, 'keywords', 'Palabras clave en comentarios')

#Hashtaggs
viz_wordcloud(df_posts, 'hashtags', 'Hashtags en publicaciones')
viz_wordcloud(df_comments, 'hashtags', 'Hashtags en comentarios')

#Noun Phrases
viz_wordcloud(df_posts, 'noun_phrases', 'Frases nominales en publicaciones')
viz_wordcloud(df_comments, 'noun_phrases', 'Frases nominales en comentarios')

df_comments['date'] = df_comments['created_time'].apply(pandas.to_datetime)
df_comments_ts = df_comments.set_index(['date'])
df_comments_ts = df_comments_ts['2015-01-01':]

df_posts['date'] = df_posts['created_time'].apply(pandas.to_datetime)
df_posts_ts = df_posts.set_index(['date'])
df_posts_ts = df_posts_ts[:'2015-01-01']

#Creamos un data frame que contiene la cantidad promedio de likes y shares por semana
dx = df_posts_ts.resample('D').mean() #.seample('W')
dx.index.name = 'date'
dx = dx.reset_index()

#Mostramos el progreso de likes
p = ggplot(dx, aes(x = 'date', y = 'likes')) + geom_line()
p = p + xlab("Fecha") + ylab("Número de me gustas") + ggtitle("Página de Facebook Turismo Tenerife")
print(p)

#Mostramos el progreso de shares
p = ggplot(dx, aes(x = 'date', y = 'shares')) + geom_line()
p = p + xlab("Fecha") + ylab("Número de comparticiones") + ggtitle("Página de Facebook Turismo Tenerife")
print(p)


def max_wordcloud(ts_df_posts, ts_df_comments, columnname, criterium, title):
    mean_week = ts_df_posts.resample('D').mean() #.resample('W')
    #start_week = (mean_week[criterium].idxmax() - datetime.timedelta(days=7)).strftime('%Y-%m-%d')
    end_week = mean_week[criterium].idxmax().strftime('%Y-%m-%d')

    viz_wordcloud(ts_df_posts[end_week], columnname, title + ' en publicaciones')
    viz_wordcloud(ts_df_comments[end_week], columnname, title + ' en comentarios')

# Palabras clave
max_wordcloud(df_posts_ts, df_comments_ts, 'keywords', 'likes', 'Palabras clave en máximo de me gustas')
max_wordcloud(df_posts_ts, df_comments_ts, 'keywords','shares', 'Palabras clave en máximo de comparticiones')

#Hashtags
max_wordcloud(df_posts_ts, df_comments_ts, 'hashtags', 'likes', 'Hashtags en máximo de me gustas')
max_wordcloud(df_posts_ts, df_comments_ts, 'hashtags','shares', 'Hashtags en máximo de comparticiones')

#Frases nominales
max_wordcloud(df_posts_ts, df_comments_ts, 'noun_phrases', 'likes', 'Frases nominales en máximo de me gustas')
max_wordcloud(df_posts_ts, df_comments_ts, 'noun_phrases','shares', 'Frases nominales en máximo de comparticiones')


url_api = "https://gateway.watsonplatform.net/natural-language-understanding/api"

def get_sentiment(text):
    try:
        natural_language_understanding = NaturalLanguageUnderstandingV1(
            username="209d9a26-cca5-4bef-9690-33f5e8ee66da",
            password="SpWglqCnrHqD",
            version='2018-03-16')
        response = natural_language_understanding.analyze(
            text=text,
            features=Features(
                emotion=EmotionOptions(),
                sentiment=SentimentOptions()))
        
        return json.dumps(response, indent=2)
    except:
        return None

print("Iniciando Análisis de sentiminetos")

df_nlu = df_comments
df_nlu['nlu'] = df_nlu.apply(lambda x: get_sentiment(x['message']), axis=1)
print("Terminado análisis de sentimientos")
emotions = []
sentiments = []
languages = []

for index, p in enumerate(df_nlu['nlu']):
    if not p == None:
        fichero = json.loads(p)
        languages.append(fichero['language'])
        sentiments.append((df_nlu['message'][index], fichero['sentiment']['document']['label'], fichero['sentiment']['document']['score']))
        if 'emotion' in fichero.keys():
            emotions.append( fichero['emotion']['document']['emotion'])

df_emotions = pandas.DataFrame(emotions)
df_sentiments = pandas.DataFrame(sentiments)
df_sentiments.columns = ['message', 'label', 'score']
df_languages = pandas.DataFrame(languages)
df_languages.columns = ['languages']

positive = []
negative = []

for index, i in enumerate(df_sentiments['score']):
    if i > 0:
        positive.append((df_sentiments['message'][index], i))
    elif i < 0:
        negative.append((df_sentiments['message'][index], i))

df_positive = pandas.DataFrame(positive)
df_positive.columns = ['message', 'score']
df_negative = pandas.DataFrame(negative)
df_negative.columns = ['message', 'score']

df_positive = execute_pipeline(df_positive)
df_negative = execute_pipeline(df_negative)

median_positive = df_positive['score'].median()
median_negative = df_negative['score'].median()

# Mostrando la gráfica de las emociones
df_emotions = df_emotions.apply(pandas.to_numeric, errors='ignore')
df_emotions_means = df_emotions.transpose().apply(numpy.mean, axis=1)
df_emotions_means.plot(kind='bar', legend=False, title='Emociones')
plt.show()

#Mostrando gráfica de lenguajes
df_languages['languages'].value_counts().plot(kind='bar', title='Idiomas')
plt.show()

#Mostrando gráfica de sentimientos
df_sentiments['label'].value_counts().plot(kind='bar', title="Sentimientos")
plt.show()

#Métodos para mostrar datos usando plotly
def bar_plotly(x, y, title):
    plotly.offline.init_notebook_mode(connected=True)
    x = x
    y = y

    trace = go.Bar(
                x=x,
                y=y,)

    data = [trace]
    layout = go.Layout(title=title,height=1 )
    fig = go.Figure(data=data, layout=layout)
    
    plotly.offline.iplot(fig)
    
def bar_plotly_file(x, y, title, filename):
    x = x
    y = y

    trace = go.Bar(
                x=x,
                y=y)

    data = [trace]
    layout = go.Layout(
        title=title,
        )
    fig = go.Figure(data=data, layout=layout)
    
    plotly.offline.plot(fig, filename=+ filename + '.html')

def cir_plotly_file(labels, values, title, filename):
    
    fig = {
    'data': [{'labels': labels,
              'values': values,
              'type': 'pie'}],
    'layout': {'title': title}
     }

    plotly.offline.plot(fig, filename=filename + '.html')
    
def cir_plotly(labels, values, title):
    plotly.offline.init_notebook_mode(connected=True)
    
    fig = {
    'data': [{'labels': labels,
              'values': values,
              'type': 'pie'}],
    'layout': {'title': title}
     }

    plotly.offline.iplot(fig)
    

#Mostrando lenguajes con plotly 
labels_languages = df_languages['languages'].value_counts().keys().tolist()
values_languages = df_languages['languages'].value_counts().tolist()

cir_plotly_file(labels_languages, values_languages, 'Gráfico idiomas', 'c_lenguajes')
bar_plotly_file(labels_languages, values_languages, 'Idiomas', 'b_lenguajes')


#Mostrando emociones con plotly
labels_emotions = df_emotions_means.keys().tolist()
values_emotions = df_emotions_means.tolist()

cir_plotly_file(labels_emotions, values_emotions, 'Gráfico emociones', 'c_emociones')
bar_plotly_file(labels_emotions, values_emotions,'Emociones', 'b_emociones')


#Mostrando sentimientos con plotly
labels_sentiments = df_sentiments['label'].value_counts().keys().tolist()
values_sentiments = df_sentiments['label'].value_counts().tolist()

cir_plotly_file(labels_sentiments, values_sentiments, 'Gráfico sentimientos', 'c_sentimientos')
bar_plotly_file(labels_sentiments, values_sentiments,'Sentimientos', 'b_sentimientos')

labels_median = ['positive', 'negative']
values_median = [median_positive, median_negative]

bar_plotly_file(labels_median, values_median, 'Puntuación sentimientos', 'score_sentiments')

# Mostrando palabras clave, hashtags y frases nominales de los mensajes con sentimientos positivos
viz_wordcloud(df_positive, 'keywords', 'Palabras clave en comentarios positivos')
viz_wordcloud(df_positive, 'hashtags', 'Hashtags en comentarios positivos')
viz_wordcloud(df_positive, 'noun_phrases', 'Frases nominales en comentarios positivos')

# Mostrando palabras clave, hashtags y frases nominales de los mensajes con sentimientos negativos
viz_wordcloud(df_negative, 'keywords', 'Palabras clave en comentarios negativos')
viz_wordcloud(df_negative, 'hashtags', 'Hashtags en comentarios negativos')
viz_wordcloud(df_negative, 'noun_phrases', 'Frases nominales en comentarios negativos')