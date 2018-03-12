#! /usr/bin/env python
# -*- coding: utf-8 -*-

## Identificador de Facebook 
## EAACQFfa9JeIBAA8NXvoQKykmZApPAuoEMMrxD3GhhOslZAkTtAeGG5iGapQsgqO12W3I6VE8CZARsUo5W5NMxs5DtGZA5nXxKKteuJX5rs4rxKZCrylxGZChf6pGj3DsUXpfluw2IKIdZAzmZAxoPcQf7Kitxy8xyLEZD

import requests
import json
from requests_oauthlib import OAuth2

url = 'https://graph.facebook.com/v2.12/'
page_url = 'https://graph.facebook.com/v2.12/MercedesBenzFrance/feed'

#Variable con el token de acceso de Facebook
params = {'acces_token' : 'EAACQFfa9JeIBAKPAQaOS6R5XZBGPebu8J7ZBAWx3wg0PSRRcIBFbiZBL1icoUgcHBLH8aqutyCQA4u8GNcZCueS5Eu55YJ1l5G0XkmCCQbe1HWgy4OKYOiY1cttT8VArxx2CCvPUZC6XRhyCZCbgzZCugq3ecRyKEGNiuo7BHgP4gZDZD'}
result = requests.get(page_url, params = params)
data = result.json()

print(data)
#for element in data['data']:
#   print(element['message'])