import requests
import json
import pymongo
import pandas

from pymongo import MongoClient
from requests_oauthlib import OAuth2

#Base de datos 
client = MongoClient('localhost:27017')
db = client.db_analyzer
db_analyzer = db.analyzer
collection_posts = db_analyzer.posts
collection_comments = db_analyzer.comments

id = "tenerifevacanze"              # id de la página que va a ser analizada

url = 'https://graph.facebook.com/v2.12/'
page_url = 'https://graph.facebook.com/v2.12/%s/feed?fields=id,message,reactions,shares,from,caption,created_time,likes.summary(true)' %id
print(page_url)
# Todos los campos deben de ser especificados
comments_url = 'https://graph.facebook.com/v2.12/{post_id}/comments?filter=stream&limit=100'

#Variable con el token de acceso de Facebook
params = {'access_token' : 'EAACQFfa9JeIBAKK0ZCX9x7vGxtDjfDjLLo5W8qVz5REnvqr30DSEy4EgrZAU0RLG0AxYo2UFdfU3hUqtm3T3dEys1eZC1BDq1IRnfpZAKwDDVi6n0LqAYKgOazNbj26FOD7zPGhZCz3RlFw4ADrqIHLC3yc1m7EEZD'}
posts = requests.get(page_url, params = params)
posts = posts.json()

#Data extraction

while True:
    try:
        print("Recopilando datos...")
    ### Recupera un post
        for element in posts['data']:
            collection_posts.insert(element)
            #### Recupera todos los comentarios de ese post
            this_comment_url = comments_url.replace("{post_id}", element['id'])
            comments = requests.get(this_comment_url, params = params).json()
            # Recorre todos los comentarios hasta que la respuesta esté vacía, que no haya más comentarios
            while ('paging' in comments and 'cursors' in comments['paging'] and 'after' in comments['paging']['cursors']):
                ### Itera a través de todos los comentarios
                for comment in comments['data']:
                    comment['post_id'] = element['id']
                    collection_comments.insert(comment)
                comments = requests.get(this_comment_url + '&after=' + comments['paging']['cursors']['after'], params = params).json()
        ####Vamos a la siguiente página en feed
        posts = requests.get(posts['paging']['next']).json()
    except KeyError:
        break

print("Datos recopilados")

# Data pull

posts_data = []
comments_data = []

for doc in collection_posts.find({}):
    try:
        posts_data.append((doc['message'], doc['created_time'], doc['likes']['summary']['total_count'], doc['shares']['count'], doc['id']))
    except:
        #print("No message")
        pass
    
for comment in collection_comments.find({}):
    try:
        comments_data.append((comment['message'], comment['created_time'], comment['post_id']))
    except:
        pass

df_posts = pandas.DataFrame(posts_data)
df_posts.columns = ['message', 'created_time', 'likes', 'shares', 'post_id']
df_comments = pandas.DataFrame(comments_data)
df_comments.columns = ['message', 'creates_time', 'post_id']

#Feature extraction
