#!/usr/bin/env python3
"""
Dummy Coolify Python App
Fetches PostgreSQL table structures and returns them as text via HTTP.
"""

import os
import psycopg2
from flask import Flask, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # Enable CORS for cross-origin requests

# Database connection parameters from environment
DB_HOST = os.getenv('POSTGRES_HOST', 'localhost')
DB_PORT = os.getenv('POSTGRES_PORT', '5432')
DB_NAME = os.getenv('POSTGRES_DB', 'postgres')
DB_USER = os.getenv('POSTGRES_USER', 'postgres')
DB_PASSWORD = os.getenv('POSTGRES_PASSWORD', '')


def get_db_connection():
    """Create and return a database connection."""
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD
        )
        return conn
    except psycopg2.Error as e:
        raise Exception(f"Database connection error: {e}")


def get_table_structures():
    """
    Fetch structure of all PostgreSQL tables.
    Returns a formatted string with table information.
    """
    conn = get_db_connection()
    result = []
    
    try:
        with conn.cursor() as cur:
            # Get all schemas and tables
            cur.execute("""
                SELECT 
                    table_schema,
                    table_name
                FROM information_schema.tables
                WHERE table_schema NOT IN ('pg_catalog', 'information_schema')
                ORDER BY table_schema, table_name
            """)
            
            tables = cur.fetchall()
            
            for schema, table in tables:
                result.append(f"\n{'='*60}")
                result.append(f"Schema: {schema}")
                result.append(f"Table: {table}")
                result.append(f"{'='*60}")
                
                # Get column information
                cur.execute("""
                    SELECT 
                        column_name,
                        data_type,
                        character_maximum_length,
                        is_nullable,
                        column_default
                    FROM information_schema.columns
                    WHERE table_schema = %s AND table_name = %s
                    ORDER BY ordinal_position
                """, (schema, table))
                
                columns = cur.fetchall()
                
                if columns:
                    result.append(f"\nColumns:")
                    result.append(f"{'-'*60}")
                    result.append(f"{'Column Name':<30} {'Type':<20} {'Nullable':<10}")
                    result.append(f"{'-'*60}")
                    
                    for col_name, data_type, max_length, nullable, default in columns:
                        type_str = data_type
                        if max_length:
                            type_str = f"{data_type}({max_length})"
                        
                        nullable_str = "YES" if nullable == "YES" else "NO"
                        result.append(f"{col_name:<30} {type_str:<20} {nullable_str:<10}")
                else:
                    result.append("No columns found")
                
                result.append("")
            
            if not tables:
                result.append("No tables found in database")
                
    except psycopg2.Error as e:
        raise Exception(f"Error fetching table structures: {e}")
    finally:
        conn.close()
    
    return "\n".join(result)


@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint."""
    return jsonify({'status': 'healthy', 'service': 'dummy-app'})


@app.route('/get_tables', methods=['GET'])
def get_tables():
    """
    Main endpoint to fetch and return table structures.
    Returns plain text for easy display in Django interface.
    """
    try:
        structures = get_table_structures()
        return structures, 200, {'Content-Type': 'text/plain; charset=utf-8'}
    except Exception as e:
        error_msg = f"Error: {str(e)}"
        return error_msg, 500, {'Content-Type': 'text/plain; charset=utf-8'}


@app.route('/', methods=['GET'])
def index():
    """Root endpoint with basic info."""
    return jsonify({
        'service': 'dummy-coolify-app',
        'endpoints': {
            '/health': 'Health check',
            '/get_tables': 'Get PostgreSQL table structures'
        }
    })


if __name__ == '__main__':
    port = int(os.getenv('PORT', 8001))
    host = os.getenv('HOST', '0.0.0.0')
    app.run(host=host, port=port, debug=os.getenv('DEBUG', 'False').lower() == 'true')
