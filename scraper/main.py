import sys
import os
from datetime import datetime

# Fix the import path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

# Import your modules
from scraper.maps_scraper import GoogleMapsScraper
from config.db_handler import DatabaseHandler

def get_user_input():
    """Get search parameters from user"""
    print("\n" + "="*50)
    print("🗺️  GOOGLE MAPS SCRAPER")
    print("="*50)
    
    category = input("Enter category (e.g., restaurants, hotels): ").strip()
    location = input("Enter location (e.g., New York, Chennai): ").strip()
    max_results = input("Max results (default 20): ").strip()
    
    max_results = int(max_results) if max_results.isdigit() else 20
    return category, location, max_results

def scrape_and_store(scraper, db, category, location, max_results):
    """Scrape and store results in database"""
    print(f"\n🔍 Searching for {category} in {location}...")
    print(f"📊 Max results: {max_results}")
    print("-" * 40)
    
    results = scraper.search_and_scrape(category, location, max_results=max_results)

    if not results:
        print("❌ No results found or scraping failed.")
        return

    # print(f"\n💾 Storing {len(results)} results in database...")
    # stored_count = 0

    # for i, place_data in enumerate(results, 1):
    #     try:
    #         if 'category' not in place_data or not place_data['category']:
    #             place_data['category'] = 'Unknown'


    #         # Optional: store categories if needed
    #         place_id = db.get_place_id_by_name(place_data['name'])  # You may need to add this method
    #         if place_id:
    #             db.insert_categories(place_id, [place_data['category']])
    #             db.commit()

    #     except Exception as e:
    #         print(f"❌ Error post-processing {place_data['name']}: {e}")

    #         try:
    #             db.conn.rollback()
    #         except:
    #             pass

    #     time.sleep(0.5)

    # print(f"\n🎉 Successfully stored {stored_count} new places!")


def query_data(db):
    """Query stored data with reviews and media"""
    print("\n" + "=" * 40)
    print("📊 QUERY STORED DATA")
    print("=" * 40)
    print("1. Search by category")
    print("2. Search by location")
    print("3. Search by rating (minimum)")
    print("4. Search by name")
    print("5. Show all places")
    print("-" * 40)

    choice = input("Enter your choice (1-5): ").strip()
    results = []

    try:
        if choice == "1":
            category = input("Enter category: ").strip()
            results = db.get_places_by_category(category)
        elif choice == "2":
            location = input("Enter location: ").strip()
            results = db.get_places_by_location(location)
        elif choice == "3":
            min_rating = float(input("Enter minimum rating (1-5): ").strip())
            results = db.get_places_by_min_rating(min_rating)
        elif choice == "4":
            name = input("Enter name to search: ").strip()
            results = db.search_places(name)
        elif choice == "5":
            results = db.get_all_places()
        else:
            print("❌ Invalid choice")
            return

    except ValueError:
        print("❌ Invalid input format")
        return
    except Exception as e:
        print(f"❌ Query error: {str(e)}")
        return

    # Display results
    if not results:
        print("\n❌ No results found")
        return

    print(f"\n📋 Found {len(results)} results:")
    print("=" * 60)

    for i, place in enumerate(results, 1):
        print(f"\n{i}. {place['name']}")
        if place.get('address'):
            print(f"   📍 {place['address']}")
        if place.get('phone'):
            print(f"   📞 {place['phone']}")
        if place.get('rating'):
            print(f"   ⭐ {place['rating']} ({place.get('review_count', 0)} reviews)")
        if place.get('category'):
            print(f"   🏷️  {place['category']}")

        place_id = place.get('id')
        if place_id:
            # Fetch and display reviews
            reviews = db.get_reviews_by_place_id(place_id)
            if reviews:
                print(f"\n   📝 Reviews:")
                for review in reviews:
                    print(f"      • {review['author']} - {review['rating']}⭐")
                    print(f"        {review['text']}")
                    print(f"        📅 {review['date']}")
                    if review['images']:
                        print(f"        🖼️ Review Images: {', '.join(review['images'][:3])}")
                    print("      -" * 10)
            else:
                print(f"\n   📝 No reviews found.")

            # Fetch and display media
            media = db.get_media_by_place_id(place_id)
            if media['images']:
                print(f"   📸 Place Images: {', '.join(media['images'][:5])}")
            if media['videos']:
                print(f"   🎥 Place Videos: {', '.join(media['videos'][:3])}")

        print("-" * 40)

    print("\n✅ Query complete.")

def main():
    """Main application loop"""
    print("🚀 Initializing Google Maps Scraper...")
    
    # Initialize components
    try:
        db = DatabaseHandler()
        print("✅ Database connected")
        
        scraper = GoogleMapsScraper(headless=False)  # Set True for headless mode
        print("✅ Scraper initialized")
        
    except Exception as e:
        print(f"❌ Initialization error: {str(e)}")
        return
    
    # Main loop
    while True:
        try:
            print("\n" + "="*50)
            print("🎯 MAIN MENU")
            print("="*50)
            print("1. 🔍 Scrape new data")
            print("2. 📊 Query existing data") 
            print("3. 🚪 Exit")
            print("-" * 50)
            
            choice = input("Enter your choice (1-3): ").strip()
            
            if choice == "1":
                category, location, max_results = get_user_input()
                scrape_and_store(scraper, db, category, location, max_results)
                
            elif choice == "2":
                query_data(db)
                
            elif choice == "3":
                print("\n👋 Goodbye!")
                break
                
            else:
                print("❌ Invalid choice. Please try again.")
            
            # Pause before showing menu again
            input("\nPress Enter to continue...")
            
        except KeyboardInterrupt:
            print("\n\n⚠️  Interrupted by user")
            break
        except Exception as e:
            print(f"\n❌ Unexpected error: {str(e)}")
            input("Press Enter to continue...")
    
    # Cleanup
    try:
        scraper.close()
        db.close()
        print("✅ Cleanup completed")
    except:
        pass

if __name__ == "__main__":
    main()