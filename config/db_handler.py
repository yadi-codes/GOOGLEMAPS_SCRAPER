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
    
    def place_exists(self, name, address):
        """Check if a place already exists in the database by name and address"""
        query = "SELECT id FROM places WHERE name = %s AND address = %s"
        self.cur.execute(query, (name, address))
        return self.cur.fetchone()
    
    def insert_place(self, place_data):
        """Insert a new place into the database"""
        query = """
        INSERT INTO places (
            name, address, phone, rating, review_count, 
            category, scraped_at, latitude, longitude
        ) VALUES (
            %(name)s, %(address)s, %(phone)s, %(rating)s, %(review_count)s,
            %(category)s, %(scraped_at)s, %(latitude)s, %(longitude)s
        )
        """
        self.cur.execute(query, place_data)
        return self.cur.lastrowid  # Get the auto-incremented ID
    
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
        INSERT INTO place_reviews (
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
                'scraped_at': review.get('timestamp')
            }
            self.cur.execute(query, review_data)
    

    def get_places_by_category(self, category):
        """Retrieve places by category"""
        query = """
        SELECT p.*, GROUP_CONCAT(pc.category) as category
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

    def commit(self):
        self.conn.commit()
    
    def close(self):
        self.cur.close()
        self.conn.close()