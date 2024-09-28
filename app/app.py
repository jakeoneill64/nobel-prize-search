import urllib

import requests
from pymongo import MongoClient
from flask import Flask, request, jsonify
import re

if __name__ == '__main__':
    # obviously this is terrible. I'm trying to save a bit of time here
    mongo_client = MongoClient(f'mongodb://adminuser:password123@mongo-service:27017')
    db = mongo_client['nobel_prize_db']
    collection = db['prizes']
    url = "https://api.nobelprize.org/v1/prize.json"
    response = requests.get(url)
    data = response.json()
    searchable_laureates = []
    for prize in data['prizes']:
        if 'laureates' in prize and prize['laureates']:
            for laureate in prize['laureates']:
                # augment and transform the dataset for ease of search and add some additional fields
                laureate['fullname'] = ' '.join(filter(None, [laureate.get('firstname'), laureate.get('surname')]))
                laureate['category'] = prize['category']
                laureate['year'] = prize['year']
                searchable_laureates.append(laureate)
    collection.insert_many(searchable_laureates)
    app = Flask(__name__)


@app.route('/search', methods=['GET'])
def search_by_category():
    category = request.args.get('category', '').lower()
    name = request.args.get('name', '')
    # this is actually denoted as 'motivation' in the json schema, but using the task description here.
    description = request.args.get('description', '')
    query = {}

    if description:
        query["motivation"] = {"$regex": description, "$options": 'i'}

    if name:
        query["fullname"] = {"$regex": name, "$options": 'i'}

    if category:
        query["category"] = category

    results = list(collection.find(query, {'_id': False}))
    return jsonify([result for result in results])

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80)
