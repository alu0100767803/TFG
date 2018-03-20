import requests
import json
import pymongo

from pymongo import MongoClient
from requests_oauthlib import OAuth2

#Base de datos 
client = MongoClient('localhost:27017')
db = client.db_analyzer
db_analyzer = db.analyzer
collection_posts = db_analyzer.posts
collection_comments = db_analyzer.comments 

url = 'https://graph.facebook.com/v2.12/'
page_url = 'https://graph.facebook.com/v2.12/Google/feed?fields=id,message,reactions,shares,from,caption,created_time,likes.summary(true)'
# Todos los campos deben de ser especificados
comments_url = 'https://graph.facebook.com/v2.12/{post_id}/comments?filter=stream&limit=100'

#Variable con el token de acceso de Facebook
params = {'access_token' : 'EAACQFfa9JeIBAKK0ZCX9x7vGxtDjfDjLLo5W8qVz5REnvqr30DSEy4EgrZAU0RLG0AxYo2UFdfU3hUqtm3T3dEys1eZC1BDq1IRnfpZAKwDDVi6n0LqAYKgOazNbj26FOD7zPGhZCz3RlFw4ADrqIHLC3yc1m7EEZD'}
posts = requests.get(page_url, params = params)
posts = posts.json()

("""print(data)
for element in data['data']:
   print(element['message'])""")