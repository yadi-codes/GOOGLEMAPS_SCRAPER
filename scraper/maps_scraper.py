import time
import random
from datetime import datetime
from playwright.sync_api import sync_playwright
import re
import os
import sys
import time
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from datetime import datetime

# Fix the import path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from config.db_handler import DatabaseHandler

class GoogleMapsScraper:
    
    def __init__(self, headless=True):
        self.user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.1 Safari/605.1.15"
        ]
        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.launch(
            headless=headless,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-infobars',
                '--start-maximized',
                f'--user-agent={random.choice(self.user_agents)}'
            ]
        )
        
    def _accept_cookies(self, page):
        """Handle cookie consent dialogs"""
        try:
            accept_button = page.wait_for_selector('#L2AGLb', timeout=5000)
            if accept_button:
                accept_button.click()
                print("✅ Accepted cookies")
                time.sleep(2)
        except:
            print("⚠️ No cookie dialog found or already accepted")

    def search_and_scrape(self, category, location, max_results=20):
        """Search Google Maps and scrape results"""
        context = self.browser.new_context(
            user_agent=random.choice(self.user_agents),
            viewport={'width': 1366, 'height': 768}
        )
        page = context.new_page()
        
        try:
            print("🌐 Loading Google Maps...")
            page.goto("https://www.google.com/maps", timeout=60000)
            
            # Handle cookies
            self._accept_cookies(page)
            
            # Wait for search box and search
            search_query = f"{category} in {location}"
            print(f"🔍 Searching for: {search_query}")
            
            search_box = page.wait_for_selector('input#searchboxinput', timeout=15000)
            search_box.fill(search_query)
            search_box.press("Enter")
            
            print("✅ Search submitted, waiting for results...")
            time.sleep(5)
            
            # Wait for results panel to load
            try:
                page.wait_for_selector('div[role="main"]', timeout=15000)
                print("✅ Results panel loaded")
            except:
                print("⚠️ Results panel timeout, continuing...")
            
            # Scroll to load more results
            print("🔄 Starting scroll using mouse wheel...")
            final_count = self._scroll_with_mouse_wheel(page, max_results)
            print(f"📊 Final scroll result: {final_count} places found")

            
            # Get all business cards from the sidebar
            results = self._extract_all_businesses(page, max_results, category)
            
            print(f"🎉 Successfully scraped {len(results)} places")
            
            # Store results in database
            if results:
                self._store_results(results)
            
            return results
            
        except Exception as e:
            print(f"❌ Error in search_and_scrape: {str(e)}")
            page.screenshot(path=f'error_{datetime.now().strftime("%Y%m%d_%H%M%S")}.png')
            return []
        finally:
            context.close()

    def _scroll_with_working_container(self, page, working_method, max_results):
        """Scroll using the identified working method"""
        if not working_method:
            print("❌ No working method provided")
            return len(page.query_selector_all('div.Nv2PK'))
        
        initial_count = len(page.query_selector_all('div.Nv2PK'))
        last_count = initial_count
        max_scrolls = 25  # Increase for more results
        
        print(f"🔄 Starting full scroll with {working_method['type']} method...")
        print(f"📊 Initial: {initial_count}, Target: {max_results}")
        
        for i in range(max_scrolls):
            try:
                # Use the working method
                if working_method['type'] == 'document':
                    page.evaluate('window.scrollBy(0, 1000)')
                elif working_method['type'] == 'container':
                    working_method['container'].evaluate('el => el.scrollTop += 1000')
                elif working_method['type'] == 'mouse_wheel':
                    working_method['container'].click()
                    page.mouse.wheel(0, 1000)
                
                time.sleep(random.uniform(2, 3))
                
                current_count = len(page.query_selector_all('div.Nv2PK'))
                
                if current_count > last_count:
                    print(f"✅ Progress: {current_count} results (+{current_count - last_count})")
                    last_count = current_count
                    
                    if current_count >= max_results:
                        print(f"🎯 Reached target: {current_count} results")
                        break
                else:
                    print(f"⏳ No new results: {current_count} total")
                    
            except Exception as e:
                print(f"⚠️ Scroll error: {e}")
                break
        
        final_count = len(page.query_selector_all('div.Nv2PK'))
        print(f"📊 Final result count: {final_count}")
        return final_count
   
    def _scroll_with_mouse_wheel(self, page, max_results):
        main_area = page.query_selector('div[role="main"]')
        if not main_area:
            print("❌ Main area not found for scrolling")
            return 0

        main_area.click()
        last_count = 0

        for i in range(25):  # Adjust scroll attempts if needed
            page.mouse.wheel(0, 1000)
            time.sleep(random.uniform(2, 3))
            current_count = len(page.query_selector_all('div.Nv2PK'))

            if current_count > last_count:
                print(f"✅ Scroll progress: {current_count} results (+{current_count - last_count})")
                last_count = current_count
                if current_count >= max_results:
                    print("🎯 Reached target result count.")
                    break
            else:
                print("⏳ No new results loaded")

        return last_count
   
    def _is_business_card(self, element):
        """Check if element is actually a business card"""
        try:
            business_indicators = [
                'data-cid',
                'href*="/maps/place/"',
                'aria-label',
                'data-result-index'
            ]
            
            for indicator in business_indicators:
                if 'href' in indicator:
                    href = element.get_attribute('href')
                    if href and '/maps/place/' in href:
                        return True
                else:
                    if element.get_attribute(indicator.replace('*=', '').replace('"', '')):
                        return True
            
            try:
                text_content = element.inner_text().strip()
                if len(text_content) > 10 and not any(ui_word in text_content.lower() for ui_word in 
                                                    ['stars', 'collapse', 'arrow keys', 'search options']):
                    return True
            except:
                pass
                
            return False
            
        except:
            return False

    def _extract_all_businesses(self, page, max_results, category=None):
        """Extract business information from all visible cards"""
        results = []
        
        try:
            time.sleep(5)
            
            business_elements = []
            
            selectors_to_try = [
                'a[data-cid]',
                'div[role="article"]',
                'div[data-result-index]',
                'div.section-result',
                'div.Nv2PK',
                'a[aria-label][href*="/maps/place/"]',
                'div[jsaction*="pane.focusResult"]'
            ]
            
            for selector in selectors_to_try:
                elements = page.query_selector_all(selector)
                if elements:
                    print(f"✅ Found {len(elements)} elements with selector: {selector}")
                    business_elements = elements
                    break
            
            if not business_elements:
                print("⚠️ No business elements found")
                return []
            
            print(f"📊 Processing {min(len(business_elements), max_results)} businesses")
            business_elements = business_elements[:max_results]
            
            processed_places = set()
            
            for i, element in enumerate(business_elements, 1):
                try:
                    print(f"🏪 Processing business {i}/{len(business_elements)}")

                    if not self._is_business_card(element):
                        print(f"   Skipping non-business element {i}")
                        continue

                    # Extract name directly from the card for de-duplication
                    name_element = element.query_selector('[aria-label]')
                    if name_element:
                        name = name_element.get_attribute('aria-label').strip()
                        if name in processed_places:
                            print(f"⚠️ Skipping already processed place: {name}")
                            continue
                        processed_places.add(name)
                    else:
                        print(f"⚠️ Could not find name, skipping this element.")
                        continue

                    # Primary method - click and extract detailed data
                    business_data = self._extract_by_clicking(page, element, i, category)

                    # Fallback: Try direct extraction if clicking fails
                    if not business_data or not business_data.get('name'):
                        print(f"   Trying fallback extraction for business {i}")
                        business_data = self._extract_card_data(element, category)

                    if business_data and business_data.get('name'):
                        results.append(business_data)
                        print(f"✅ Extracted: {business_data['name']}")
                        if business_data.get('address'):
                            print(f"   📍 Address: {business_data['address']}")
                        if business_data.get('phone'):
                            print(f"   📞 Phone: {business_data['phone']}")
                        if business_data.get('latitude') and business_data.get('longitude'):
                            print(f"   🌍 Location: {business_data['latitude']}, {business_data['longitude']}")
                    else:
                        print(f"⚠️ No data found for business {i}")

                    time.sleep(random.uniform(1, 2))  # Increased delay
                    
                except Exception as e:
                    print(f"⚠️ Error processing business {i}: {str(e)}")
                    continue
            
        except Exception as e:
            print(f"❌ Error extracting businesses: {str(e)}")
        
        return results

    def _extract_by_clicking(self, page, element, index, category=None):
        db = DatabaseHandler()

        """IMPROVED: Extract data by clicking on the business card"""
        try:
            print(f"   🖱️ Clicking business {index} for detailed data...")
            
            # Scroll element into view
            element.scroll_into_view_if_needed()
            time.sleep(1)
            
            # Click the element
            element.click(timeout=5000)

            # Wait explicitly for the detailed view to load by waiting for the unique selector that appears only in the detailed view
            try:
                page.wait_for_selector('h1.DUwDvf.lfPIob', timeout=10000)
                print(f"   ✅ Details panel loaded for business {index}")
            except:
                print(f"   ⚠️ Details panel didn't load for business {index}")
                return None
            time.sleep(3)  # Increased wait time
            
            # Wait for business details to load
            try:
                page.wait_for_selector('h1, [data-attrid="title"], .DUwDvf', timeout=10000)
                print(f"   ✅ Details panel loaded for business {index}")

            except:
                print(f"   ⚠️ Details panel didn't load for business {index}")
                return None
            
            # Extract data from the details panel
            data = self._extract_detail_panel_data(page, category)
            if not data:
                print(f"   ⚠️ Failed to extract detail panel data for business {index}")
                return None

            place_id = self._store_single_place(data)  # You need this function to get the place_id immediately
            if not place_id:
                print(f"   ⚠️ Failed to store main place, skipping media and reviews")
                return data

            # Extract and store images
            images = self._extract_place_images(page)
            if images:
                db.insert_media(place_id, {'images': images, 'videos': [], 'scraped_at': datetime.now()})

            # Extract and store reviews
            reviews = self._extract_reviews(page, place_id)
            if reviews:
                db.insert_reviews(place_id, reviews)

            db.commit()
            db.close()


            
            # Go back to results
            try:
                # Try multiple methods to go back
                back_methods = [
                    lambda: page.keyboard.press("Escape"),
                    lambda: page.go_back(),
                    lambda: page.query_selector('button[aria-label*="Back"]').click() if page.query_selector('button[aria-label*="Back"]') else None
                ]
                
                for method in back_methods:
                    try:
                        method()
                        time.sleep(2)
                        break
                    except:
                        continue
                        
            except Exception as e:
                print(f"   ⚠️ Error going back: {e}")
            
            return data
            previous_url = page.url
            element.click(timeout=5000)

            # Wait for URL to change, indicating detail pane has updated
            try:
                page.wait_for_function(f"window.location.href !== '{previous_url}'", timeout=10000)
                print(f"   ✅ URL changed, detail panel loaded for business {index}")
            except:
                print(f"   ⚠️ URL did not change for business {index}")
                return None

            time.sleep(2)  # Allow animations to settle

            
        except Exception as e:
            print(f"   ⚠️ Error in click extraction: {e}")
            return None
    
    def _extract_place_images(self, page):
        """Extract place images using fallback selectors and scroll strategy"""
        images = []
        try:
            # Try to open the photo gallery
            photos_button_selectors = [
                'button[aria-label*="Photos"]',
                'button[aria-label*="View photos"]',
                'button[aria-label*="See photos"]',
                'button[aria-label*="Gallery"]',
                'button[jsaction*="pane.photoGallery"]',    # Sometimes photo gallery is triggered via jsaction
                'button[aria-label*="images"]',             # Sometimes labeled as "images"
                'div[jsaction*="pane.photoGallery"]',  # Newer Google Maps uses div with jsaction  
            ]

            photos_button = None
            for selector in photos_button_selectors:
                photos_button = page.query_selector(selector)
                if photos_button:
                    photos_button.click()
                    time.sleep(3)
                    break

            if not photos_button:
                print("⚠️ Photos button not found or no gallery allowed.")
                return []

            # Scroll through gallery to load more images
            for _ in range(10):
                page.mouse.wheel(0, 1000)
                time.sleep(2)

            # Try multiple image selectors (Google changes these often)
            image_selectors = [
                'img[src^="https://lh3.googleusercontent.com"]',  # Primary
                'img[src^="https://maps.gstatic.com"]',           # Google cached images
                'img[src^="https://encrypted-tbn0.gstatic.com"]', # Thumbnail backups
                'img[src^="https://"]'                            # Broad fallback
            ]

            found_images = []
            for selector in image_selectors:
                found_images = page.query_selector_all(selector)
                if found_images:
                    print(f"✅ Found {len(found_images)} images using selector: {selector}")
                    break

            if not found_images:
                print("⚠️ No images found with known selectors.")
                return []

            # Extract image URLs
            for img in found_images:
                src = img.get_attribute('src')
                if src and 'googleusercontent' in src:
                    images.append(src)

            print(f"✅ Total unique images found: {len(set(images))}")
            return list(set(images))  # Remove duplicates

        except Exception as e:
            print(f"⚠️ Error extracting images: {e}")
            return []


    def _extract_detail_panel_data(self, page, category=None):
        """IMPROVED: Extract comprehensive data from the opened business details panel"""
        try:
            data = {}
            data = {
                'name': None,
                'address': None,
                'phone': None,
                'rating': None,
                'review_count': None,
                'category': category or 'general',
                'scraped_at': datetime.now(),
                'latitude': None,
                'longitude': None
            }
            
            # Extract name - Multiple selectors
            name_selectors = [
                'h1.DUwDvf.lfPIob',
                'h1.fontHeadlineLarge',
                'h1[data-attrid="title"]',
                'h1',
                '.DUwDvf',
                '.lfPIob'
            ]
            
            for selector in name_selectors:
                try:
                    element = page.query_selector(selector)
                    if element:
                        name = element.inner_text().strip()
                        if name and len(name) > 0:
                            data['name'] = name
                            print(f"   ✅ Found name: {name}")
                            break
                except:
                    continue
            
            # Extract coordinates from URL
            try:
                current_url = page.url
                # Look for coordinates in various URL patterns
                coord_patterns = [
                    r'/@(-?\d+\.\d+),(-?\d+\.\d+)',
                    r'/place/[^/]+/@(-?\d+\.\d+),(-?\d+\.\d+)',
                    r'!3d(-?\d+\.\d+)!4d(-?\d+\.\d+)'
                ]
                
                for pattern in coord_patterns:
                    match = re.search(pattern, current_url)
                    if match:
                        data['latitude'] = float(match.group(1))
                        data['longitude'] = float(match.group(2))
                        print(f"   ✅ Found coordinates: {data['latitude']}, {data['longitude']}")
                        break
            except Exception as e:
                print(f"   ⚠️ Error extracting coordinates: {e}")

            # Extract address - Multiple approaches
            address_selectors = [
                'button[data-item-id="address"]',
                'div[data-item-id="address"]',
                '.rogA2c .Io6YTe',  # New Google Maps class
                '.rogA2c',
                'button[jsaction*="address"]',
                'div[aria-label*="Address"]',
                '.fontBodyMedium:has-text("Address")',
                '.CsEnBe[aria-label*="Address"]'
            ]
            
            for selector in address_selectors:
                try:
                    elements = page.query_selector_all(selector)
                    for element in elements:
                        address_text = element.inner_text().strip()
                        # Filter out obvious non-addresses
                        if (address_text and len(address_text) > 5 and 
                            not any(word in address_text.lower() for word in ['website', 'phone', 'directions', 'save'])):
                            data['address'] = address_text
                            print(f"   ✅ Found address: {address_text}")
                            break
                    if data['address']:
                        break
                except:
                    continue
            
            # Extract phone - Multiple approaches
            phone_selectors = [
                'button[data-item-id="phone"]',
                'div[data-item-id="phone"]',
                'button[jsaction*="phone"]',
                'a[href^="tel:"]',
                'div[aria-label*="Phone"]',
                '.fontBodyMedium:has-text("+")',
                '.CsEnBe[aria-label*="Phone"]'
            ]
            
            for selector in phone_selectors:
                try:
                    elements = page.query_selector_all(selector)
                    for element in elements:
                        phone_text = element.inner_text().strip()
                        phone_pattern = r'(\+?\d[\d\s\-\(\)]{8,})'  # Better phone pattern
                        phone_match = re.search(phone_pattern, phone_text)
                        if phone_match:
                            clean_phone = phone_match.group(1).strip()
                            data['phone'] = clean_phone
                            print(f"   ✅ Found phone: {clean_phone}")
                            break
                    if data['phone']:
                        break
                except:
                    continue

            
            # Extract rating and reviews
            try:
                # Rating
                rating_selectors = [
                    # '.MW4etd',
                    # '.ceNzKf',
                    # 'span[aria-hidden="true"]:has-text(".")',
                    'div.F7nice span span[aria-hidden="true"]'
                ]
                
                for selector in rating_selectors:
                    try:
                        element = page.query_selector(selector)
                        if element:
                            rating_text = element.inner_text().strip()
                            rating_match = re.search(r'(\d+\.?\d*)', rating_text)
                            if rating_match:
                                rating_value = float(rating_match.group(1))
                                rating_value = rating_value
                                if 0 <= rating_value <= 5:  # Valid rating range
                                    data['rating'] = rating_value
                                    print(f"   ✅ Found rating: {rating_value}")
                                break
                    except:
                        continue
                
                # Review count
                review_selectors = [
                    # '.UY7F9',
                    # '.ceNzKf',
                    # 'button:has-text("reviews")',
                    # 'span:has-text("reviews")'
                    'div.F7nice span span span[aria-label]'

                ]
                
                for selector in review_selectors:
                    try:
                        element = page.query_selector(selector)
                        if element:
                            review_text = element.inner_text().strip()
                            review_match = re.search(r'(\d{1,3}(?:,\d{3})*|\d+)', review_text)
                            if review_match:
                                review_count = int(review_match.group(1).replace(',', ''))
                                review_count = review_count
                                data['review_count'] = review_count
                                print(f"   ✅ Found review count: {review_count}")
                                break
                    except:
                        continue
                        
            except Exception as e:
                print(f"   ⚠️ Error extracting rating/reviews: {e}")
            
            return data if data['name'] else None
            
        except Exception as e:
            print(f"   ❌ Error extracting detail panel data: {e}")
            return None

    def _extract_card_data(self, element, category):
        """FALLBACK: Extract basic data from business card element"""
        try:
            data = {
                'name': None,
                'address': None,
                'phone': None,
                'rating': None,
                'review_count': None,
                'category': category or 'general',
                'scraped_at': datetime.now(),
                'latitude': None,
                'longitude': None
            }

            # Extract coordinates from href
            try:
                map_link = element.query_selector('a[href*="maps/place"], a[href*="/@"]')
                if map_link:
                    href = map_link.get_attribute('href')
                    match = re.search(r'/@(-?\d+\.\d+),(-?\d+\.\d+)', href)
                    if match:
                        data['latitude'] = float(match.group(1))
                        data['longitude'] = float(match.group(2))
                        print(f"   Found coordinates: {data['latitude']}, {data['longitude']}")
            except Exception as e:
                print(f"   Error extracting coordinates: {e}")

            # Extract name from aria-label
            try:
                aria_label = element.get_attribute('aria-label')
                if aria_label:
                    ui_elements = ['stars', 'Collapse side panel', 'Map ·', 'Available search options', 'Use arrow keys']
                    if not any(ui_text in aria_label for ui_text in ui_elements):
                        data['name'] = aria_label.strip()
                        print(f"   Found name via aria-label: {data['name']}")
            except:
                pass
            
            # Try other name extraction methods if aria-label didn't work
            if not data['name']:
                try:
                    heading_selectors = [
                        'div[class*="fontHeadline"]',
                        'span[class*="fontHeadline"]', 
                        'div[class*="fontDisplay"]',
                        'a[aria-label]'
                    ]
                    
                    for selector in heading_selectors:
                        name_element = element.query_selector(selector)
                        if name_element:
                            name_text = name_element.inner_text().strip()
                            if name_text and len(name_text) > 2:
                                data['name'] = name_text
                                print(f"   Found name via selector {selector}: {data['name']}")
                                break
                except:
                    pass
            
            return data if data['name'] else None
            
        except Exception as e:
            print(f"   Error extracting card data: {str(e)}")
            return None

    def _extract_reviews(self, page, place_id):
        """Robust review extractor using fallback selectors"""
        reviews = []
        try:
            # Click on reviews button if needed
            reviews_button = page.query_selector('button[aria-label*="reviews"]')
            if reviews_button:
                reviews_button.click()
                time.sleep(3)

            # Scroll to load more reviews
            for _ in range(10):
                page.mouse.wheel(0, 1000)
                time.sleep(2)

            # Try multiple possible review card selectors
            card_selectors = [
                'div.jftiEf',              # Common review container
                'div[data-review-id]',     # ID-based fallback
                'div.gws-localreviews__google-review',  # Legacy class
                'div[jscontroller="e6Mltc"]'  # Structured review container
            ]

            review_cards = []
            for selector in card_selectors:
                review_cards = page.query_selector_all(selector)
                if review_cards:
                    print(f"✅ Found {len(review_cards)} reviews using selector: {selector}")
                    break

            if not review_cards:
                print("⚠️ No review cards found with known selectors.")
                return []

            for card in review_cards:
                try:
                    # AUTHOR
                    author_selectors = [
                        'div.KFi5wf span',             # Common Google Maps structure
                        '.TSUbDb .d4r55',              # Older or legacy layout
                        'div[class*="d4r55"]',         # General fallback for class name
                        'div[class*="X5PpBb"] span',   # Newer design sometimes uses this
                    ]
                    author = 'Unknown'
                    for sel in author_selectors:
                        el = card.query_selector(sel)
                        if el:
                            author = el.inner_text().strip()
                            break


                    # RATING
                    rating = None
                    rating_selectors = ['span[role="img"]', 'div.gws-localreviews__rating']
                    for sel in rating_selectors:
                        el = card.query_selector(sel)
                        if el:
                            label = el.get_attribute('aria-label') or el.inner_text()
                            match = re.search(r'(\d+(\.\d+)?)', label)
                            if match:
                                rating = float(match.group(1))
                                break

                    # TEXT
                    text = ''
                    text_selectors = ['span.wiI7pd', '.review-full-text', '.Jtu6Td']
                    for sel in text_selectors:
                        el = card.query_selector(sel)
                        if el:
                            text = el.inner_text().strip()
                            break

                    # DATE
                    date = ''
                    date_selectors = ['span.rsqaWe', '.dehysf']
                    for sel in date_selectors:
                        el = card.query_selector(sel)
                        if el:
                            date = el.inner_text().strip()
                            break

                    # IMAGES
                    image_elements = card.query_selector_all('img[src^="https://"]')
                    images = [img.get_attribute('src') for img in image_elements if img.get_attribute('src')]

                    # Skip totally empty reviews
                    if not text and not rating:
                        print(f"⚠️ Skipping empty review (no text and no rating)")
                        continue

                    reviews.append({
                        'place_id': place_id,
                        'author': author,
                        'rating': rating,
                        'text': text,
                        'date': date,
                        'images': images,
                        'scraped_at': datetime.now()
                    })

                except Exception as e:
                    print(f"⚠️ Error extracting a review: {e}")
                    continue

        except Exception as e:
            print(f"❌ Error extracting reviews: {e}")
        return reviews


    def _store_results(self, results):
        """Store results in database"""
        try:
            db = DatabaseHandler()
            stored_count = 0
            
            for place_data in results:
                try:
                    if not db.place_exists(place_data['name'], place_data.get('address', '')):
                        place_id = db.insert_place(place_data)
                        if place_id:
                            stored_count += 1
                            print(f"✅ Stored: {place_data['name']}")
                        else:
                            print(f"❌ Failed to store: {place_data['name']}")
                    else:
                        print(f"⚠️ Already exists: {place_data['name']}")
                except Exception as e:
                    print(f"❌ Error storing {place_data['name']}: {e}")
            
            db.commit()
            db.close()
            print(f"🎉 Successfully stored {stored_count} new places!")
            
        except Exception as e:
            print(f"❌ Database error: {e}")

    def _store_single_place(self, place_data):
        """Store a single place and return its ID"""
        try:
            # Clean the address BEFORE checking for existence and inserting
            place_data['address'] = place_data['address'].replace('\ue0c8', '').replace('\n', '').strip()

            db = DatabaseHandler()
            if not db.place_exists(place_data['name'], place_data.get('address', '')):
                place_id = db.insert_place(place_data)
                db.commit()
                db.close()
                if place_id:
                    print(f"✅ Stored place: {place_data['name']}")
                    return place_id
                else:
                    print(f"❌ Failed to insert place: {place_data['name']}")
                    return None
            else:
                print(f"⚠️ Place already exists: {place_data['name']}")
                db.close()
                return None
        except Exception as e:
            print(f"❌ Error storing place: {e}")
            return None


    def close(self):
        """Clean up resources"""
        try:
            self.browser.close()
            self.playwright.stop()
        except:
            pass

# Test function
def test_scraper():
    """Test the scraper with a simple search"""
    scraper = GoogleMapsScraper(headless=False)  # Set to True for headless mode
    
    try:
        results = scraper.search_and_scrape("restaurants", "New York", max_results=5)
        
        print(f"\n🎉 Test Results: {len(results)} places found")
        print("-" * 50)
        
        for i, place in enumerate(results, 1):
            print(f"\n{i}. {place.get('name', 'Unknown')}")
            if place.get('rating'):
                print(f"   ⭐ Rating: {place['rating']} ({place.get('review_count', 0)} reviews)")
            if place.get('address'):
                print(f"   📍 Address: {place['address']}")
            if place.get('phone'):
                print(f"   📞 Phone: {place['phone']}")
            if place.get('latitude') and place.get('longitude'):
                print(f"   🌍 Coordinates: {place['latitude']}, {place['longitude']}")
            if place.get('category'):
                print(f"   🏷️ Category: {place['category']}")
            
    except Exception as e:
        print(f"Test error: {e}")
    finally:
        scraper.close()

if __name__ == "__main__":
    test_scraper()