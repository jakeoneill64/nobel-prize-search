import requests
from pymongo import MongoClient
from flask import Flask, request, jsonify
import re

if __name__ == '__main__':
    mongo_client = MongoClient('mongodb://password123:adminuser@localhost:27017')
    db = mongo_client['nobel_prize_db']
    collection = db['prizes']
    url = "https://api.nobelprize.org/v1/prize.json"
    response = requests.get(url)
    data = response.json()
    if 'prizes' in data:
        collection.insert_many(data['prizes'])
    app = Flask(__name__)
    app.run(host='0.0.0.0', port=80)



@app.route('/')
def index():
    return "Welcome to the Nobel Prize Search API!"

@app.route('/search/name=', methods=['GET'])
def search_by_name():
    query = request.args.get('query', '')
    regex_query = re.compile(query, re.IGNORECASE)
    results = collection.find({"laureates.name": regex_query})
    return jsonify([result for result in results])

@app.route('/search/category=', methods=['GET'])
def search_by_category():
    query = request.args.get('query', '')
    regex_query = re.compile(query, re.IGNORECASE)
    results = collection.find({"category": regex_query})
    return jsonify([result for result in results])

@app.route('/search/description=', methods=['GET'])
def search_by_description():
    query = request.args.get('query', '')
    regex_query = re.compile(query, re.IGNORECASE)
    results = collection.find({"laureates.knownName.en": regex_query})
    return jsonify([result for result in results])

