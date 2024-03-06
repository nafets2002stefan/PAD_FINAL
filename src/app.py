from flask import Flask, jsonify, request, make_response
from bson.objectid import ObjectId
from config import *
from pymongo import MongoClient
from flask_sqlalchemy import SQLAlchemy
import redis
import json
from os import environ

app = Flask(__name__)

app.config['SQLALCHEMY_DATABASE_URI'] = environ.get('DATABASE_URL')
db = SQLAlchemy(app)

class Item(db.Model):
    __tablename__ = 'items'

    id = db.Column(db.Integer, primary_key = True)
    name = db.Column(db.String(80), unique=False, nullable=False)
    price = db.Column(db.Integer, unique=False, nullable=False)

    def json(self):
        return {'id': self.id, 'name':self.name, 'price': self.price}
    
#db.create_all()


# Connect to MongoDB
client = MongoClient(MONGO_CLIENT)
mongo_db = client.products
collection = mongo_db[MONGO_COLLECTION]

# Connect to Redis
redis_client = redis.StrictRedis(host='redis', port=6379, decode_responses=True)

def get_products():
    products_data = redis_client.get('products')
    if products_data:
        return json.loads(products_data)
    else:
        products = list(collection.find({}, {'_id': 0}))
        redis_client.set('products', json.dumps(products))
        return products

def get_items():
    items_data = redis_client.get('items')
    if items_data:
        return json.loads(items_data)
    else:
        items = Item.query.all()
        serialized_items = [item.json() for item in items] 
        redis_client.set('items', json.dumps(serialized_items))
        return items
    
@app.route('/initialize', methods=['GET'])
def initialize():
    try:
        db.create_all()
        return make_response(jsonify({'message': 'Db initialized'}), 200)
    except Exception as e:
        return make_response(jsonify({'message': e}), 500)

@app.route('/items', methods=['GET'])
def get_items_route():
    items = get_items()
    return jsonify({'items': items})


@app.route('/items/<int:id>', methods=['PUT'])
def update_item(id):
    try:
        item = Item.query.filter_by(id=id).first()
        if item:
            data = request.get_json()
            item.name = data['name']
            item.price = data['price']
            db.session.commit()
            redis_client.delete('items')  # Invalidate cache
            return make_response(jsonify({'message': 'Item updated successfully'}), 200)
        return make_response(jsonify({'message': 'Item not found'}), 404)
    except Exception as e:
        return make_response(jsonify({'mesage' : 'error updating item'}), 500)

@app.route('/items', methods=['POST'])
def create_item():
    try:
        data = request.get_json()
        new_item = Item(name=data['name'], price=data['price'])
        db.session.add(new_item)
        db.session.commit()
        redis_client.delete('items')  # Invalidate cache
        return make_response(jsonify({'message' : 'Item created successfully'}), 201)
    except Exception as e:
        return make_response(jsonify({'mesage' : 'error creating item'}), 500)

@app.route('/products', methods=['GET'])
def get_products_route():
    products = get_products()
    return jsonify({'products': products})

@app.route('/products/<string:product_id>', methods=['PUT'])
def update_product(product_id):
    data = request.get_json()
    try:
        product_id = ObjectId(product_id)
    except:
        return jsonify({'error': 'Invalid product ID format'}), 400

    result = collection.update_one({'_id': product_id}, {'$set': data})
    if result.modified_count == 1:
        #redis_client.delete('products')  # Invalidate cache
        return jsonify({'message': 'Product updated successfully'})
    else:
        return jsonify({'error': 'Product not found'}), 404
    
@app.route('/products', methods=['POST'])
def create_product():
    data = request.get_json()
    result = collection.insert_one(data)
    if result.inserted_id:
        redis_client.delete('products')  # Invalidate cache
        return jsonify({'message': 'Product created successfully'}), 201
    else:
        return jsonify({'error': 'Failed to create product'}), 500

def two_phase_commit(data, item_id=None, product_id=None):
    try:
        # Start the transaction
        with db.session.begin():
            result = collection.insert_one(data)
            new_item = Item(name=data['name'], price=data['price'])
            db.session.add(new_item) 
            db.session.commit()  

        # Invalidate cache
        redis_client.delete('items')
        redis_client.delete('products')
        
        return True, {'item_id': new_item.id, 'product_id': str(result.inserted_id)}
    except Exception as e:
        db.session.rollback() 
        return False, str(e)

@app.route('/transaction', methods=['POST'])
def two_phase_commit_route():
    data = request.get_json()
    success, response = two_phase_commit(data)
    if success:
        return jsonify({'message': 'Two-phase commit successful', 'data': response}), 201
    else:
        return jsonify({'error': 'Two-phase commit failed', 'message': response}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5003)