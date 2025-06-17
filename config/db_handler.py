import mysql.connector
from mysql.connector import Error
import os
from dotenv import load_dotenv
import json

load_dotenv()

class DatabaseHandler:
    def __init__(self):
        try:
            self.conn = mysql.connector.connect(
                host=os.getenv('DB_HOST', 'localhost'),
                database=os.getenv('DB_NAME'),
                user=os.getenv('DB_USER'),
                password=os.getenv('DB_PASSWORD'),
                port=int(os.getenv('DB_PORT', 3306))  # MySQL default port
            )
            self.cur = self.conn.cursor(dictionary=True)  # Use dictionary cursor
        except Error as e:
            print(f"Error connecting to MySQL: {e}")
            raise
    
    def place_exists(self, name, latitude, longitude):
        query = "SELECT id FROM places WHERE name = %s AND latitude = %s AND longitude = %s"
        self.cur.execute(query, (name.strip(), latitude, longitude))
        return self.cur.fetchone()


    def clean_address(address):
        return address.replace('\ue0c8', '').replace('\n', '').strip()

    def insert_place(self, place_data):
        """Insert a new place into the database"""

        # ADD THIS VALIDATION:
        # Ensure all string fields are actually strings
        for field in ['name', 'address', 'phone', 'category']:
            if field in place_data and place_data[field] is not None:
                if isinstance(place_data[field], bytes):
                    place_data[field] = place_data[field].decode('utf-8')
                else:
                    place_data[field] = str(place_data[field])
        
        # Ensure numeric fields are proper types
        if 'rating' in place_data and place_data['rating'] is not None:
            place_data['rating'] = float(place_data['rating'])
        if 'review_count' in place_data and place_data['review_count'] is not None:
            place_data['review_count'] = int(place_data['review_count'])


        query = """
        INSERT INTO places (
            name, address, phone, rating, review_count, 
            category, scraped_at, latitude, longitude
        ) VALUES (
            %(name)s, %(address)s, %(phone)s, %(rating)s, %(review_count)s,
            %(category)s, %(scraped_at)s, %(latitude)s, %(longitude)s
        )
        """
        try:
            self.cur.execute(query, place_data)
            return self.cur.lastrowid
        except Exception as e:
            print(f"Database insertion error: {e}")
            print(f"Problematic data: {place_data}")
            raise
    
    def insert_categories(self, place_id, categories):
        """Insert place categories into place_categories table"""
        if not categories:
            return
        
        # First ensure all categories exist in categories table
        for category in categories:
            self.cur.execute(
                "INSERT IGNORE INTO categories (name) VALUES (%s)",
                (category,)
            )
        
        # Get category IDs for the place's categories
        self.cur.execute(
            "SELECT id FROM categories WHERE name IN (%s)" % 
            ','.join(['%s']*len(categories)),
            categories
        )
        category_ids = [row['id'] for row in self.cur.fetchall()]
        
        # Insert into place_categories
        for category_id in category_ids:
            self.cur.execute(
                "INSERT IGNORE INTO place_categories (place_id, category_id) VALUES (%s, %s)",
                (place_id, category_id)
            )
    
    def insert_media(self, place_id, media_data):
        """Insert place media into place_media table"""
        if not media_data:
            return
        
        query = """
        INSERT INTO place_media (
            place_id, images, videos, scraped_at
        ) VALUES (
            %(place_id)s, %(images)s, %(videos)s, %(scraped_at)s
        )
        """
        media_data['place_id'] = place_id
        media_data['images'] = json.dumps(media_data.get('images', []))
        media_data['videos'] = json.dumps(media_data.get('videos', []))
        self.cur.execute(query, media_data)
    
    def insert_reviews(self, place_id, reviews):
        """Insert place reviews into place_reviews table"""
        if not reviews:
            return

        query = """
        INSERT IGNORE INTO place_reviews (
            place_id, author, rating, text, date, images, scraped_at
        ) VALUES (
            %(place_id)s, %(author)s, %(rating)s, %(text)s, %(date)s, %(images)s, %(scraped_at)s
        )
        """

        for review in reviews:
            review_data = {
                'place_id': place_id,
                'author': review.get('author'),
                'rating': review.get('rating'),
                'text': review.get('text'),
                'date': review.get('date'),
                'images': json.dumps(review.get('images', [])),
                'scraped_at': review.get('scraped_at')
            }
            print("blah blah")
            self.cur.execute(query, review_data)
  
    def get_places_by_category(self, category):
        """Retrieve places by category"""
        query = """
        SELECT p.*, GROUP_CONCAT(c.name) as category
        FROM places p
        JOIN place_categories pc ON p.id = pc.place_id
        JOIN categories c ON pc.category_id = c.id
        WHERE c.name LIKE %s
        GROUP BY p.id
        """
        self.cur.execute(query, (f"%{category}%",))
        return self.cur.fetchall()

    def get_places_by_location(self, location):
        """Retrieve places by location (address search)"""
        query = """
        SELECT * FROM places 
        WHERE address LIKE %s
        """
        self.cur.execute(query, (f"%{location}%",))
        return self.cur.fetchall()

    def get_places_by_min_rating(self, min_rating):
        """Retrieve places with minimum rating"""
        query = """
        SELECT * FROM places 
        WHERE rating >= %s
        ORDER BY rating DESC
        """
        self.cur.execute(query, (min_rating,))
        return self.cur.fetchall()

    def search_places(self, search_term):
        """Search places by name or phone"""
        query = """
        SELECT * FROM places 
        WHERE name LIKE %s OR phone LIKE %s
        """
        self.cur.execute(query, (f"%{search_term}%", f"%{search_term}%"))
        return self.cur.fetchall()

    def get_all_places(self):
        """Retrieve all places"""
        query = "SELECT * FROM places"
        self.cur.execute(query)
        return self.cur.fetchall()

    def get_place_id_by_name(self, name):
        query = "SELECT id FROM places WHERE name = %s"
        self.cur.execute(query, (name.strip(),))
        row = self.cur.fetchone()
        return row[0] if row else None
    
    def get_reviews_by_place_id(self, place_id):
        query = "SELECT author, rating, text, date, images FROM place_reviews WHERE place_id = %s"
        self.cur.execute(query, (place_id,))
        rows = self.cur.fetchall()
        return [{
            'author': row[0],
            'rating': row[1],
            'text': row[2],
            'date': row[3],
            'images': json.loads(row[4]) if row[4] else []
        } for row in rows]

    def get_media_by_place_id(self, place_id):
        query = "SELECT images, videos FROM place_media WHERE place_id = %s"
        self.cur.execute(query, (place_id,))
        row = self.cur.fetchone()
        if row:
            return {
                'images': json.loads(row[0]) if row[0] else [],
                'videos': json.loads(row[1]) if row[1] else []
            }
        return {'images': [], 'videos': []}

    def commit(self):
        self.conn.commit()
    
    def close(self):
        self.cur.close()
        self.conn.close()