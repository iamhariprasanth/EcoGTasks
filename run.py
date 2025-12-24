"""
Application Entry Point
Run with: python run.py
"""
import os
from app import create_app

# Create Flask application instance
app = create_app(os.environ.get('FLASK_CONFIG', 'development'))

if __name__ == '__main__':
    # Run the development server
    # In production, use a WSGI server like Gunicorn
    app.run(host='0.0.0.0', port=5001, debug=True)
