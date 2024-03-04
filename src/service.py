from flask import Flask, jsonify, request
from bson.objectid import ObjectId
from config import *
from pymongo import MongoClient
from item import *
import redis
import json
import os  # Add this import statement

# Change the SQLALCHEMY_DATABASE_URI to use the environment variables for Docker service

app = Flask(__name__)

# Configure SQL Alchemy


app.config['SQLALCHEMY_DATABASE_URI'] = f"mssql+pyodbc://{os.environ['MSSQL_DB_USERNAME']}:{os.environ['MSSQL_DB_PASSWORD']}@{os.environ['MSSQL_DB_SERVER']}/{os.environ['MSSQL_DB_NAME']}?driver={os.environ['MSSQL_DRIVER']}"
#app.config['SQLALCHEMY_DATABASE_URI'] = f"mssql+pyodbc://{MSSQL_DB_USERNAME}:{MSSQL_DB_PASSWORD}@{MSSQL_DB_SERVER}/{MSSQL_DB_NAME}?driver={MSSQL_DRIVER}"
db_item.init_app(app)

# Connect to MongoDB
client = MongoClient(MONGO_CLIENT)
mongo_db = client.products
collection = mongo_db[MONGO_COLLECTION]

# Connect to Redis
redis_client = redis.StrictRedis(host='redis', port=6379, decode_responses=True)

# Helper function to fetch items from the database or Redis cache
def get_items():
    items_data = redis_client.get('items')
    if items_data:
        return json.loads(items_data)
    else:
        items = Item.query.all()
        items_list = [{'id': item.id, 'name': item.name, 'price': item.price} for item in items]
        redis_client.set('items', json.dumps(items_list))
        return items_list

# Helper function to fetch products from the database or Redis cache
def get_products():
    products_data = None
    products_data = redis_client.get('products')
    if products_data:
        return json.loads(products_data)
    else:
        products = list(collection.find({}, {'_id': 0}))
        redis_client.set('products', json.dumps(products))
        return products

@app.route('/items', methods=['GET'])
def get_items_route():
    items = get_items()
    return jsonify({'items': items})

@app.route('/items/<int:item_id>', methods=['PUT'])
def update_item(item_id):
    item = Item.query.get_or_404(item_id)
    data = request.get_json()
    if 'name' in data:
        item.name = data['name']
    if 'price' in data:
        item.price = data['price']
    db_item.session.commit()
    redis_client.delete('items')  # Invalidate cache
    return jsonify({'message': 'Item updated successfully'})

@app.route('/items', methods=['POST'])
def create_item():
    data = request.get_json()
    new_item = Item(name=data['name'], price=data['price'])
    db_item.session.add(new_item)
    db_item.session.commit()
    redis_client.delete('items')  # Invalidate cache
    return jsonify({'message': 'Item created successfully'})

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
        with db_item.session.begin():
            result = collection.insert_one(data)
            new_item = Item(name=data['name'], price=data['price'])
            db_item.session.add(new_item) 
            db_item.session.commit()  

        # Invalidate cache
        redis_client.delete('items')
        redis_client.delete('products')
        
        return True, {'item_id': new_item.id, 'product_id': str(result.inserted_id)}
    except Exception as e:
        db_item.session.rollback() 
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
