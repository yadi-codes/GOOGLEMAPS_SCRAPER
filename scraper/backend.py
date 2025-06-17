from flask import Flask, jsonify, request
from flask_cors import CORS
import pymysql

app = Flask(__name__)
CORS(app)  # Enable Cross-Origin Resource Sharing

# Database configuration
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': 'ponnarukannan',
    'database': 'google_maps_data'
}

def get_db_connection():
    try:
        return pymysql.connect(**DB_CONFIG)
    except Exception as e:
        return None

@app.route('/api/places', methods=['GET'])
def get_places():
    connection = get_db_connection()
    if not connection:
        return jsonify({'error': 'Database connection failed'}), 500

    try:
        # with connection.cursor(pymysql.cursors.DictCursor) as cursor:
        #     cursor.execute("""
        #         SELECT 
        #             p.id, p.name, p.address, p.phone, p.rating, 
        #             p.review_count, p.scraped_at, p.latitude, p.longitude, 
        #             GROUP_CONCAT(c.name) AS categories
        #         FROM places p
        #         LEFT JOIN place_categories pc ON p.id = pc.place_id
        #         LEFT JOIN categories c ON pc.category_id = c.id
        #         GROUP BY p.id
        #         ORDER BY p.scraped_at DESC
        #     """)
        #     places = cursor.fetchall()

        #     # Process categories
        #     for place in places:
        #         place['categories'] = place['categories'].split(',') if place['categories'] else []

        #     cursor.execute("SELECT DISTINCT name FROM categories ORDER BY name")
        #     categories = [row['name'] for row in cursor.fetchall()]
        
        # return jsonify({'places': places, 'categories': categories})
        with connection.cursor(pymysql.cursors.DictCursor) as cursor:
            cursor.execute("""
                SELECT 
                    p.id, p.name, p.address, p.phone, p.rating, 
                    p.review_count, p.scraped_at, p.latitude, p.longitude, 
                    p.category AS category
                FROM places p
                ORDER BY p.scraped_at DESC
            """)
            places = cursor.fetchall()

            # Process categories (convert string to list for consistency)
            for place in places:
                place['categories'] = [place['category']] if place['category'] else []
                del place['category']  # Optional: remove 'category' key if not needed

            # Fetch distinct categories for dropdown
            cursor.execute("SELECT DISTINCT category FROM places ORDER BY category")
            categories = [row['category'] for row in cursor.fetchall()]

        return jsonify({'places': places, 'categories': categories})


    except Exception as e:
        return jsonify({'error': 'Failed to fetch data'}), 500
    finally:
        connection.close()

if __name__ == '__main__':
    app.run(debug=True)