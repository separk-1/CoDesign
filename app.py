import os
from flask import Flask, request, jsonify, send_from_directory
from calculator import compute_ebct

# Initialize the Flask app
app = Flask(__name__, static_folder='.')

# Route to serve the main index.html file
@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

# Route to serve other static files (like ebct.js)
@app.route('/<path:path>')
def static_files(path):
    # To prevent directory traversal attacks, ensure the path is safe
    if '..' in path or path.startswith('/'):
        return "Not Found", 404
    return send_from_directory('.', path)

# API endpoint for the EBCT calculation
@app.route('/api/calculate', methods=['POST'])
def calculate_api():
    # Ensure the request is JSON
    if not request.is_json:
        return jsonify({"error": "Request must be JSON"}), 415
        
    data = request.get_json()
    # Validate the input
    if not data or 'query' not in data:
        return jsonify({'error': 'Invalid input', 'need': ['"query" field is required']}), 400

    query = data['query']
    # Call the core calculation logic
    result = compute_ebct(query)

    # If calculation is not successful, return an error response
    if not result['ok']:
        return jsonify({'error': 'Calculation failed', 'need': result.get('need', [])}), 400

    # Return the successful result
    return jsonify(result)

# Main entry point for running the app
if __name__ == '__main__':
    # Use the PORT environment variable if available, otherwise default to 5000
    port = int(os.environ.get('PORT', 5000))
    # Run the app, accessible from any network interface
    app.run(host='0.0.0.0', port=port, debug=True)
