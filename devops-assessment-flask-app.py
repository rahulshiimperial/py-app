# app.py
import os
import json
import logging
from datetime import datetime
from flask import Flask, request, jsonify, render_template
import boto3
from botocore.exceptions import ClientError
import pymongo
from pymongo.errors import ConnectionFailure
import redis
import requests
from prometheus_client import Counter, Gauge, generate_latest, REGISTRY

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("app.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Prometheus metrics
API_REQUESTS = Counter('api_requests_total', 'Total API requests', ['endpoint', 'method', 'status'])
DB_CONNECTIONS = Gauge('db_connections', 'Database connections', ['db_type'])
S3_OPERATIONS = Counter('s3_operations_total', 'S3 operations', ['operation', 'status'])

# Configuration - In a real app, use environment variables or a config file
app.config.update(
    MONGO_URI=os.environ.get('MONGO_URI', 'mongodb://localhost:27017/'),
    MONGO_DB=os.environ.get('MONGO_DB', 'devops_test'),
    REDIS_HOST=os.environ.get('REDIS_HOST', 'localhost'),
    REDIS_PORT=os.environ.get('REDIS_PORT', 6379),
    AWS_ACCESS_KEY=os.environ.get('AWS_ACCESS_KEY', ''),
    AWS_SECRET_KEY=os.environ.get('AWS_SECRET_KEY', ''),
    AWS_REGION=os.environ.get('AWS_REGION', 'us-east-1'),
    S3_BUCKET=os.environ.get('S3_BUCKET', 'devops-test-bucket')
)

# Initialize S3 client
def get_s3_client():
    try:
        s3_client = boto3.client(
            's3',
            aws_access_key_id=app.config['AWS_ACCESS_KEY'],
            aws_secret_access_key=app.config['AWS_SECRET_KEY'],
            region_name=app.config['AWS_REGION']
        )
        return s3_client
    except Exception as e:
        logger.error(f"Failed to initialize S3 client: {str(e)}")
        return None

# Initialize MongoDB client
def get_mongo_client():
    try:
        client = pymongo.MongoClient(app.config['MONGO_URI'], serverSelectionTimeoutMS=5000)
        # Validate connection
        client.admin.command('ismaster')
        DB_CONNECTIONS.labels(db_type='mongodb').set(1)
        return client
    except ConnectionFailure:
        logger.error("MongoDB server not available")
        DB_CONNECTIONS.labels(db_type='mongodb').set(0)
        return None
    except Exception as e:
        logger.error(f"Failed to initialize MongoDB client: {str(e)}")
        DB_CONNECTIONS.labels(db_type='mongodb').set(0)
        return None

# Initialize Redis client
def get_redis_client():
    try:
        client = redis.Redis(
            host=app.config['REDIS_HOST'],
            port=app.config['REDIS_PORT'],
            db=0
        )
        # Check connection
        client.ping()
        DB_CONNECTIONS.labels(db_type='redis').set(1)
        return client
    except Exception as e:
        logger.error(f"Failed to initialize Redis client: {str(e)}")
        DB_CONNECTIONS.labels(db_type='redis').set(0)
        return None

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/health')
def health():
    """Health check endpoint for load balancers and monitoring."""
    status = {
        'status': 'ok',
        'timestamp': datetime.utcnow().isoformat(),
        'checks': {
            'mongodb': False,
            's3': False,
            'redis': False
        }
    }
    
    # MongoDB check
    mongo_client = get_mongo_client()
    if mongo_client:
        status['checks']['mongodb'] = True
        mongo_client.close()
    
    # S3 check
    s3_client = get_s3_client()
    if s3_client:
        try:
            s3_client.head_bucket(Bucket=app.config['S3_BUCKET'])
            status['checks']['s3'] = True
        except ClientError as e:
            logger.warning(f"S3 bucket check failed: {str(e)}")
    
    # Redis check
    redis_client = get_redis_client()
    if redis_client:
        status['checks']['redis'] = True
    
    # Determine overall status
    if not all(status['checks'].values()):
        status['status'] = 'degraded'
    
    return jsonify(status)

@app.route('/metrics')
def metrics():
    """Expose Prometheus metrics."""
    return generate_latest(REGISTRY)

@app.route('/api/data', methods=['GET'])
def get_data():
    """API endpoint to get data from MongoDB."""
    API_REQUESTS.labels(endpoint='/api/data', method='GET', status='attempt').inc()
    
    mongo_client = get_mongo_client()
    if not mongo_client:
        API_REQUESTS.labels(endpoint='/api/data', method='GET', status='error').inc()
        return jsonify({'error': 'Database connection failed'}), 500
    
    try:
        db = mongo_client[app.config['MONGO_DB']]
        collection = db.test_data
        
        # Get query parameters
        limit = int(request.args.get('limit', 10))
        skip = int(request.args.get('skip', 0))
        
        # Query the database
        data = list(collection.find({}, {'_id': False}).limit(limit).skip(skip))
        
        # Close the connection
        mongo_client.close()
        
        API_REQUESTS.labels(endpoint='/api/data', method='GET', status='success').inc()
        return jsonify(data)
    
    except Exception as e:
        logger.error(f"Database error: {str(e)}")
        API_REQUESTS.labels(endpoint='/api/data', method='GET', status='error').inc()
        return jsonify({'error': str(e)}), 500
    finally:
        if mongo_client:
            mongo_client.close()

@app.route('/api/data', methods=['POST'])
def post_data():
    """API endpoint to add data to MongoDB."""
    API_REQUESTS.labels(endpoint='/api/data', method='POST', status='attempt').inc()
    
    if not request.json:
        API_REQUESTS.labels(endpoint='/api/data', method='POST', status='error').inc()
        return jsonify({'error': 'Invalid request, JSON required'}), 400
    
    mongo_client = get_mongo_client()
    if not mongo_client:
        API_REQUESTS.labels(endpoint='/api/data', method='POST', status='error').inc()
        return jsonify({'error': 'Database connection failed'}), 500
    
    try:
        db = mongo_client[app.config['MONGO_DB']]
        collection = db.test_data
        
        # Add timestamp to the data
        data = request.json
        data['timestamp'] = datetime.utcnow().isoformat()
        
        # Insert into database
        result = collection.insert_one(data)
        
        # Cache in Redis
        redis_client = get_redis_client()
        if redis_client:
            redis_key = f"data:{str(result.inserted_id)}"
            redis_client.setex(redis_key, 3600, json.dumps(data))
        
        API_REQUESTS.labels(endpoint='/api/data', method='POST', status='success').inc()
        return jsonify({'success': True, 'id': str(result.inserted_id)}), 201
    
    except Exception as e:
        logger.error(f"Database error: {str(e)}")
        API_REQUESTS.labels(endpoint='/api/data', method='POST', status='error').inc()
        return jsonify({'error': str(e)}), 500
    finally:
        if mongo_client:
            mongo_client.close()

@app.route('/api/files', methods=['GET'])
def list_files():
    """List files in S3 bucket."""
    API_REQUESTS.labels(endpoint='/api/files', method='GET', status='attempt').inc()
    
    s3_client = get_s3_client()
    if not s3_client:
        API_REQUESTS.labels(endpoint='/api/files', method='GET', status='error').inc()
        return jsonify({'error': 'S3 client initialization failed'}), 500
    
    try:
        response = s3_client.list_objects_v2(Bucket=app.config['S3_BUCKET'])
        files = []
        
        if 'Contents' in response:
            for item in response['Contents']:
                files.append({
                    'key': item['Key'],
                    'size': item['Size'],
                    'last_modified': item['LastModified'].isoformat()
                })
        
        S3_OPERATIONS.labels(operation='list_objects', status='success').inc()
        API_REQUESTS.labels(endpoint='/api/files', method='GET', status='success').inc()
        return jsonify(files)
    
    except ClientError as e:
        logger.error(f"S3 error: {str(e)}")
        S3_OPERATIONS.labels(operation='list_objects', status='error').inc()
        API_REQUESTS.labels(endpoint='/api/files', method='GET', status='error').inc()
        return jsonify({'error': str(e)}), 500

@app.route('/api/files/<key>', methods=['GET'])
def get_file(key):
    """Get download URL for a file in S3."""
    API_REQUESTS.labels(endpoint='/api/files/<key>', method='GET', status='attempt').inc()
    
    s3_client = get_s3_client()
    if not s3_client:
        API_REQUESTS.labels(endpoint='/api/files/<key>', method='GET', status='error').inc()
        return jsonify({'error': 'S3 client initialization failed'}), 500
    
    try:
        # Generate a pre-signed URL for downloading
        url = s3_client.generate_presigned_url(
            'get_object',
            Params={'Bucket': app.config['S3_BUCKET'], 'Key': key},
            ExpiresIn=3600
        )
        
        S3_OPERATIONS.labels(operation='generate_presigned_url', status='success').inc()
        API_REQUESTS.labels(endpoint='/api/files/<key>', method='GET', status='success').inc()
        return jsonify({'url': url})
    
    except ClientError as e:
        logger.error(f"S3 error: {str(e)}")
        S3_OPERATIONS.labels(operation='generate_presigned_url', status='error').inc()
        API_REQUESTS.labels(endpoint='/api/files/<key>', method='GET', status='error').inc()
        return jsonify({'error': str(e)}), 500

@app.route('/api/files', methods=['POST'])
def upload_file():
    """Upload a file to S3."""
    API_REQUESTS.labels(endpoint='/api/files', method='POST', status='attempt').inc()
    
    if 'file' not in request.files:
        API_REQUESTS.labels(endpoint='/api/files', method='POST', status='error').inc()
        return jsonify({'error': 'No file part'}), 400
    
    file = request.files['file']
    if file.filename == '':
        API_REQUESTS.labels(endpoint='/api/files', method='POST', status='error').inc()
        return jsonify({'error': 'No selected file'}), 400
    
    s3_client = get_s3_client()
    if not s3_client:
        API_REQUESTS.labels(endpoint='/api/files', method='POST', status='error').inc()
        return jsonify({'error': 'S3 client initialization failed'}), 500
    
    try:
        # Generate a unique key for the file
        filename = file.filename
        key = f"uploads/{datetime.utcnow().strftime('%Y%m%d%H%M%S')}-{filename}"
        
        # Upload the file
        s3_client.upload_fileobj(
            file,
            app.config['S3_BUCKET'],
            key,
            ExtraArgs={'ContentType': file.content_type}
        )
        
        # Record the upload in MongoDB
        mongo_client = get_mongo_client()
        if mongo_client:
            db = mongo_client[app.config['MONGO_DB']]
            collection = db.file_uploads
            collection.insert_one({
                'filename': filename,
                'key': key,
                'content_type': file.content_type,
                'timestamp': datetime.utcnow().isoformat()
            })
            mongo_client.close()
        
        S3_OPERATIONS.labels(operation='upload_fileobj', status='success').inc()
        API_REQUESTS.labels(endpoint='/api/files', method='POST', status='success').inc()
        return jsonify({
            'success': True,
            'key': key,
            'url': f"/api/files/{key}"
        })
    
    except ClientError as e:
        logger.error(f"S3 error: {str(e)}")
        S3_OPERATIONS.labels(operation='upload_fileobj', status='error').inc()
        API_REQUESTS.labels(endpoint='/api/files', method='POST', status='error').inc()
        return jsonify({'error': str(e)}), 500

@app.route('/api/simulate-load', methods=['GET'])
def simulate_load():
    """Endpoint to simulate CPU load for monitoring tests."""
    API_REQUESTS.labels(endpoint='/api/simulate-load', method='GET', status='attempt').inc()
    
    duration = int(request.args.get('duration', 10))  # seconds
    # Cap the duration to avoid server overload
    duration = min(duration, 30)
    
    start_time = datetime.now()
    count = 0
    
    # Simple CPU-bound task
    while (datetime.now() - start_time).total_seconds() < duration:
        count += 1
        _ = [i**2 for i in range(10000)]
    
    API_REQUESTS.labels(endpoint='/api/simulate-load', method='GET', status='success').inc()
    return jsonify({
        'duration': duration,
        'iterations': count,
        'message': f"Load test completed with {count} iterations over {duration} seconds"
    })

@app.errorhandler(404)
def not_found(error):
    API_REQUESTS.labels(endpoint='404', method=request.method, status='error').inc()
    return jsonify({'error': 'Not found'}), 404

@app.errorhandler(500)
def server_error(error):
    API_REQUESTS.labels(endpoint='500', method=request.method, status='error').inc()
    return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    # Enable debug for development
    debug_mode = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    port = int(os.environ.get('PORT', 5050))
    
    logger.info(f"Starting application on port {port} with debug={debug_mode}")
    app.run(host='0.0.0.0', port=port, debug=debug_mode)
