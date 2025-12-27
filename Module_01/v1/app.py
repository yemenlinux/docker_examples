from flask import Flask, jsonify, request
import redis
import os
import socket

app = Flask(__name__)

# Connect to Redis
redis_host = os.getenv('REDIS_HOST', 'localhost')
redis_port = int(os.getenv('REDIS_PORT', 6379))
redis_client = redis.Redis(host=redis_host, port=redis_port, decode_responses=True)

@app.route('/')
def hello():
    return "<h1>مرحباً بك في مقرر مادة الحوسبة السحابية</h1>"
#     hostname = socket.gethostname()
#     visitor_count = redis_client.incr('visitors')
#     
#     return jsonify({
#         'message': 'Hello from Dockerized Flask App!',
#         'container_id': hostname,
#         'visitor_count': visitor_count,
#         'environment': os.getenv('ENVIRONMENT', 'development')
#     })

@app.route('/health')
def health():
    return jsonify({'status': 'healthy', 'service': 'flask-app'})

@app.route('/keys', methods=['GET', 'POST'])
def keys():
    if request.method == 'POST':
        data = request.json
        key = data.get('key')
        value = data.get('value')
        if key and value:
            redis_client.set(key, value)
            return jsonify({'message': f'Key {key} set successfully'})
    
    # GET request - list all keys
    keys = redis_client.keys('*')
    return jsonify({'keys': keys})

@app.route('/key/<key_name>')
def get_key(key_name):
    value = redis_client.get(key_name)
    return jsonify({'key': key_name, 'value': value})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True) 
