#!/usr/bin/env python3
"""
Water Kiosk Hardware Server - Python Flask Version
Converted from Node.js WebSocket server to HTTP for better scalability
Handles kiosk hardware requests for user verification and database operations
"""

import json
import os
import logging
import random
from datetime import datetime
import urllib.request
import urllib.parse
import urllib.error
from flask import Flask, request, jsonify

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration Constants - Environment Variables with Fallbacks (UPDATED FOR UNIFIED SCHEMA)
APPWRITE_PROJECT_ID = os.environ.get('APPWRITE_PROJECT_ID', '689107c288885e90c039')  # Same as SMS
APPWRITE_DATABASE_ID = os.environ.get('APPWRITE_DATABASE_ID', '6864aed388d20c69a461')  # Same as SMS  
APPWRITE_API_KEY = os.environ.get('APPWRITE_API_KEY', '0f3a08c2c4fc98480980cbe59cd2db6b8522734081f42db3480ab2e7a8ffd7c46e8476a62257e429ff11c1d6616e814ae8753fb07e7058d1b669c641012941092ddcd585df802eb2313bfba49bf3ec3f776f529c09a7f5efef2988e4b4821244bbd25b3cd16669885c173ac023b5b8a90e4801f3584eef607506362c6ae01c94')  # Same as SMS
CUSTOMERS_COLLECTION_ID = os.environ.get('CUSTOMERS_COLLECTION_ID', 'customers')  # Same as SMS
APPWRITE_ENDPOINT = os.environ.get('APPWRITE_ENDPOINT', 'http://192.168.1.126/v1')

# Flask app
app = Flask(__name__)

@app.route('/', methods=['GET'])
def status():
    """Status endpoint"""
    return jsonify({
        'status': 'Water Kiosk Hardware Server Active',
        'message': 'Python Flask application for kiosk hardware integration',
        'timestamp': datetime.now().isoformat(),
        'features': ['dispense_verification', 'database_query', 'database_create', 'database_update'],
        'endpoints': {
            'status': 'GET / - This status page',
            'dispense_verification': 'POST /dispense-verification - Verify user for water dispensing',
            'database_query': 'POST /database/query - Query database documents',
            'database_create': 'POST /database/create - Create database documents',
            'database_update': 'POST /database/update - Update database documents',
            'test_database': 'POST /test-database - Test database connection'
        }
    })

@app.route('/dispense-verification', methods=['POST'])
def dispense_verification():
    """Main endpoint for kiosk hardware - verify user credentials for water dispensing"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No JSON data provided'}), 400
        
        logger.info(f"🔍 Processing dispense verification: {data}")
        
        # Extract required fields (UPDATED: user_id is now phone_number)
        kiosk_id = data.get('kiosk_id')
        phone_number = data.get('user_id')  # Kiosk sends user_id, but it's phone_number
        pin = data.get('pin')
        volume_ml = data.get('volume_ml')
        timestamp = data.get('timestamp')
        
        if not all([kiosk_id, phone_number, pin]):
            return jsonify({
                'error': 'Missing required fields: kiosk_id, user_id (phone_number), pin',
                'approved': False,
                'reason': 'Invalid request format'
            }), 400
        
        approved = False
        reason = ''
        user_data = None
        
        try:
            # First, try to verify user in the database (UPDATED FOR UNIFIED SCHEMA)
            logger.info('📡 Checking user credentials in database...')
            user_lookup = lookup_customer_by_phone(phone_number, pin)
            
            if user_lookup['found']:
                if not user_lookup['is_registered']:
                    approved = False
                    reason = 'Customer not fully registered'
                    logger.info(f"❌ Customer {phone_number} not fully registered")
                elif not user_lookup['active']:
                    approved = False
                    reason = 'Subscription inactive'
                    logger.info(f"❌ Customer {phone_number} subscription inactive")
                elif not user_lookup['valid_pin']:
                    approved = False
                    reason = 'Invalid PIN'
                    logger.info(f"❌ Invalid PIN for customer {phone_number}")
                else:
                    approved = True
                    reason = 'Customer verified in database'
                    user_data = user_lookup['customer_data']
                    logger.info(f"✅ Customer {phone_number} verified successfully")
            else:
                approved = False
                reason = 'Customer not found in database'
                logger.info(f"❌ Customer {phone_number} not found in database")
                
        except Exception as error:
            logger.error(f"❌ Database lookup failed: {str(error)}")
            logger.info('🔄 Falling back to random approval logic...')
            
            # Fall back to original 90% approval rate if database is unavailable
            approved = random.random() < 0.9
            reason = ('Database unavailable - approved by fallback (90% chance)' if approved 
                     else 'Database unavailable - denied by fallback (10% chance)')
        
        # Prepare response (same format as Node.js version, but user_id = phone_number)
        response = {
            'type': 'dispense_response',
            'user_id': phone_number,  # Kiosk expects user_id field
            'pin': pin,
            'volume_ml': volume_ml,
            'approved': approved,
            'reason': reason,
            'timestamp': datetime.now().isoformat(),
            'kiosk_id': kiosk_id
        }
        
        # Add user data if available
        if user_data:
            response['user_data'] = user_data
        
        # Add user data if available
        if user_data:
            response['user_data'] = user_data
        
        logger.info(f"📤 Sent response: {'✅ APPROVED' if approved else '❌ DENIED'} - {reason}")
        
        return jsonify(response)
        
    except Exception as e:
        logger.error(f'Dispense verification error: {str(e)}')
        return jsonify({
            'error': str(e),
            'type': 'server_error',
            'approved': False,
            'reason': 'Server error occurred',
            'timestamp': datetime.now().isoformat()
        }), 500

@app.route('/database/query', methods=['POST'])
def database_query():
    """Handle database query requests"""
    try:
        data = request.get_json()
        logger.info(f'🔍 Processing database query: {data}')
        
        database = data.get('database', APPWRITE_DATABASE_ID)
        collection = data.get('collection')
        queries = data.get('queries', [])
        request_id = data.get('request_id')
        
        if not collection:
            return jsonify({
                'type': 'query_response',
                'request_id': request_id,
                'success': False,
                'error': 'Collection ID is required',
                'timestamp': datetime.now().isoformat()
            }), 400
        
        # Build query path
        path = f'/v1/databases/{database}/collections/{collection}/documents'
        if queries:
            query_params = '&'.join([f'queries[]={urllib.parse.quote(q)}' for q in queries])
            path += f'?{query_params}'
        
        result = make_appwrite_request('GET', path)
        
        response = {
            'type': 'query_response',
            'request_id': request_id,
            'success': True,
            'data': result['data'],
            'total': result['data'].get('total', 0),
            'timestamp': datetime.now().isoformat()
        }
        
        logger.info(f"✅ Database query successful: {result['data'].get('total', 0)} documents")
        return jsonify(response)
        
    except Exception as error:
        logger.error(f"❌ Database query failed: {str(error)}")
        response = {
            'type': 'query_response',
            'request_id': data.get('request_id') if 'data' in locals() else None,
            'success': False,
            'error': str(error),
            'timestamp': datetime.now().isoformat()
        }
        return jsonify(response), 500

@app.route('/database/create', methods=['POST'])
def database_create():
    """Handle database document creation"""
    try:
        data = request.get_json()
        logger.info(f'🔍 Processing database create: {data}')
        
        database = data.get('database', APPWRITE_DATABASE_ID)
        collection = data.get('collection')
        document_id = data.get('document_id', 'unique()')
        document_data = data.get('document_data')
        request_id = data.get('request_id')
        
        if not collection or not document_data:
            return jsonify({
                'type': 'create_response',
                'request_id': request_id,
                'success': False,
                'error': 'Collection ID and document_data are required',
                'timestamp': datetime.now().isoformat()
            }), 400
        
        path = f'/v1/databases/{database}/collections/{collection}/documents'
        body = {
            'documentId': document_id,
            'data': document_data
        }
        
        result = make_appwrite_request('POST', path, body)
        
        response = {
            'type': 'create_response',
            'request_id': request_id,
            'success': True,
            'data': result['data'],
            'timestamp': datetime.now().isoformat()
        }
        
        logger.info(f"✅ Document created successfully: {result['data']['$id']}")
        return jsonify(response)
        
    except Exception as error:
        logger.error(f"❌ Document creation failed: {str(error)}")
        response = {
            'type': 'create_response',
            'request_id': data.get('request_id') if 'data' in locals() else None,
            'success': False,
            'error': str(error),
            'timestamp': datetime.now().isoformat()
        }
        return jsonify(response), 500

@app.route('/database/update', methods=['POST'])
def database_update():
    """Handle database document updates"""
    try:
        data = request.get_json()
        logger.info(f'🔍 Processing database update: {data}')
        
        database = data.get('database', APPWRITE_DATABASE_ID)
        collection = data.get('collection')
        document_id = data.get('document_id')
        document_data = data.get('document_data')
        request_id = data.get('request_id')
        
        if not all([collection, document_id, document_data]):
            return jsonify({
                'type': 'update_response',
                'request_id': request_id,
                'success': False,
                'error': 'Collection ID, document_id, and document_data are required',
                'timestamp': datetime.now().isoformat()
            }), 400
        
        path = f'/v1/databases/{database}/collections/{collection}/documents/{document_id}'
        body = {'data': document_data}
        
        result = make_appwrite_request('PATCH', path, body)
        
        response = {
            'type': 'update_response',
            'request_id': request_id,
            'success': True,
            'data': result['data'],
            'timestamp': datetime.now().isoformat()
        }
        
        logger.info(f"✅ Document updated successfully: {document_id}")
        return jsonify(response)
        
    except Exception as error:
        logger.error(f"❌ Document update failed: {str(error)}")
        response = {
            'type': 'update_response',
            'request_id': data.get('request_id') if 'data' in locals() else None,
            'success': False,
            'error': str(error),
            'timestamp': datetime.now().isoformat()
        }
        return jsonify(response), 500

@app.route('/test-database', methods=['POST'])
def test_database():
    """Test database connection"""
    try:
        # Test listing collections
        url = f'{APPWRITE_ENDPOINT}/databases/{APPWRITE_DATABASE_ID}/collections'
        
        headers = {
            'X-Appwrite-Project': APPWRITE_PROJECT_ID,
            'X-Appwrite-Key': APPWRITE_API_KEY,
            'Content-Type': 'application/json'
        }
        
        request_obj = urllib.request.Request(url, headers=headers)
        response = urllib.request.urlopen(request_obj, timeout=10)
        data = json.loads(response.read().decode('utf-8'))
        
        logger.info(f"✅ Database connected! Found {data['total']} collections")
        
        collection_names = [col['name'] for col in data.get('collections', [])]
        
        return jsonify({
            'status': 'DATABASE_SUCCESS',
            'message': 'Database connection working via HTTP!',
            'collections_found': data['total'],
            'collection_names': collection_names,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"❌ Database test failed: {str(e)}")
        return jsonify({
            'status': 'DATABASE_ERROR',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

def lookup_customer_by_phone(phone_number, pin):
    """Look up customer in unified customers collection - updated for SMS/Kiosk integration"""
    try:
        logger.info(f"🔍 Looking up customer {phone_number} in customers database...")
        
        # Try multiple phone number formats (same logic as SMS server)
        phone_variants = [
            phone_number,
            phone_number.replace('+254', '0'),
            phone_number.replace('+254', '254'),
            phone_number.replace('+254', ''),
            f"+254{phone_number.lstrip('0')}" if not phone_number.startswith('+') else phone_number
        ]
        
        for variant in phone_variants:
            query = f'equal("phone_number","{variant}")'
            url = f'{APPWRITE_ENDPOINT}/databases/{APPWRITE_DATABASE_ID}/collections/{CUSTOMERS_COLLECTION_ID}/documents?queries[]={urllib.parse.quote(query)}'
            
            headers = {
                'X-Appwrite-Project': APPWRITE_PROJECT_ID,
                'X-Appwrite-Key': APPWRITE_API_KEY,
                'Content-Type': 'application/json'
            }
            
            request_obj = urllib.request.Request(url, headers=headers)
            response = urllib.request.urlopen(request_obj, timeout=5)
            data = json.loads(response.read().decode('utf-8'))
            
            if data.get('documents') and len(data['documents']) > 0:
                customer = data['documents'][0]
                pin_match = customer.get('pin') == pin
                is_registered = customer.get('is_registered') == True
                active = customer.get('active') == True
                
                logger.info(f"👤 Found customer: {variant}, registered: {is_registered}, active: {active}, PIN match: {pin_match}")
                
                return {
                    'found': True,
                    'valid_pin': pin_match,
                    'is_registered': is_registered,
                    'active': active,
                    'customer_data': {
                        'phone_number': customer.get('phone_number'),
                        'account_id': customer.get('account_id'),
                        'full_name': customer.get('full_name'),
                        'active': customer.get('active'),
                        'credits': customer.get('credits', 0)
                    }
                }
        
        logger.info(f"❌ Customer {phone_number} not found in database")
        return {
            'found': False,
            'valid_pin': False,
            'is_registered': False,
            'active': False
        }
            
    except Exception as e:
        logger.error(f"❌ Database connection error: {str(e)}")
        raise e

def make_appwrite_request(method, path, body=None):
    """Generic Appwrite API request function - converted from Node.js"""
    try:
        body_string = json.dumps(body).encode('utf-8') if body else None
        
        headers = {
            'X-Appwrite-Project': APPWRITE_PROJECT_ID,
            'X-Appwrite-Key': APPWRITE_API_KEY,
            'Content-Type': 'application/json'
        }
        
        if body_string:
            headers['Content-Length'] = str(len(body_string))
        
        url = f'{APPWRITE_ENDPOINT}{path}'
        request_obj = urllib.request.Request(url, data=body_string, headers=headers, method=method)
        response = urllib.request.urlopen(request_obj, timeout=10)
        
        response_data = json.loads(response.read().decode('utf-8'))
        
        if 200 <= response.status < 300:
            return {'status': response.status, 'data': response_data}
        else:
            raise Exception(f"HTTP {response.status}: {response_data.get('message', 'Unknown error')}")
            
    except Exception as e:
        logger.error(f"Appwrite request failed: {str(e)}")
        raise e

if __name__ == '__main__':
    print("🚀 Water Kiosk Hardware Server starting...")
    print(f"📊 Database endpoint: {APPWRITE_ENDPOINT}")
    print(f"🏢 Project ID: {APPWRITE_PROJECT_ID}")
    print(f"🗃️ Database ID: {APPWRITE_DATABASE_ID}")
    print(f"👥 Customers Collection: {CUSTOMERS_COLLECTION_ID}")
    print("📡 Endpoints:")
    print("  - GET  /                     - Status page")
    print("  - POST /dispense-verification - Main kiosk endpoint (phone + PIN verification)")
    print("  - POST /database/query       - Database queries")
    print("  - POST /database/create      - Create database documents")
    print("  - POST /database/update      - Update database documents")
    print("  - POST /test-database        - Test database connection")
    print("")
    print("🔧 UNIFIED SCHEMA: Uses same customers collection as SMS server")
    print("🔧 VERIFICATION: phone_number + pin + active subscription status")
    print("🔧 For 600+ kiosks: Use load balancer with multiple instances of this server")
    print("")
    
    # Start the server
    app.run(host='0.0.0.0', port=8080, debug=True)
