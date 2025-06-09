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
            print("🔄 Loading more results...")
            self._scroll_for_results(page)
            
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

    def _scroll_for_results(self, page, max_scrolls=10):
        """Scroll the results panel to load more places"""
        try:
            results_container = page.query_selector('div[role="main"] div[role="region"]')
            if not results_container:
                results_container = page.query_selector('div[role="main"]')
                
            for i in range(max_scrolls):
                try:
                    if results_container:
                        results_container.evaluate('el => el.scrollTop += 1000')
                    else:
                        page.evaluate('window.scrollBy(0, 1000)')
                    
                    print(f"Scroll {i+1}/{max_scrolls}")
                    time.sleep(random.uniform(2, 3))
                    
                except Exception as e:
                    print(f"⚠️ Scroll error: {e}")
                    break
                    
        except Exception as e:
            print(f"Error in scroll setup: {e}")
    
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
            
            for i, element in enumerate(business_elements, 1):
                try:
                    print(f"🏪 Processing business {i}/{len(business_elements)}")
                    
                    if not self._is_business_card(element):
                        print(f"   Skipping non-business element {i}")
                        continue

                    # FIXED: Primary method - click and extract detailed data
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
        """IMPROVED: Extract data by clicking on the business card"""
        try:
            print(f"   🖱️ Clicking business {index} for detailed data...")
            
            # Scroll element into view
            element.scroll_into_view_if_needed()
            time.sleep(1)
            
            # Click the element
            element.click(timeout=5000)
            time.sleep(4)  # Increased wait time
            
            # Wait for business details to load
            try:
                page.wait_for_selector('h1, [data-attrid="title"], .DUwDvf', timeout=10000)
                print(f"   ✅ Details panel loaded for business {index}")
            except:
                print(f"   ⚠️ Details panel didn't load for business {index}")
                return None
            
            # Extract data from the details panel
            data = self._extract_detail_panel_data(page, category)
            
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
            
        except Exception as e:
            print(f"   ⚠️ Error in click extraction: {e}")
            return None

    def _extract_detail_panel_data(self, page, category=None):
        """IMPROVED: Extract comprehensive data from the opened business details panel"""
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
                        # Look for phone number patterns
                        phone_pattern = r'[\+]?[\d\s\-\(\)]{10,}'
                        if re.search(phone_pattern, phone_text):
                            data['phone'] = phone_text
                            print(f"   ✅ Found phone: {phone_text}")
                            break
                    if data['phone']:
                        break
                except:
                    continue
            
            # Extract rating and reviews
            try:
                # Rating
                rating_selectors = [
                    '.MW4etd',
                    '.ceNzKf',
                    'span[aria-hidden="true"]:has-text(".")',
                    'div.F7nice span'
                ]
                
                for selector in rating_selectors:
                    try:
                        element = page.query_selector(selector)
                        if element:
                            rating_text = element.inner_text().strip()
                            rating_match = re.search(r'(\d+\.?\d*)', rating_text)
                            if rating_match:
                                rating_value = float(rating_match.group(1))
                                if 0 <= rating_value <= 5:  # Valid rating range
                                    data['rating'] = rating_value
                                    print(f"   ✅ Found rating: {rating_value}")
                                    break
                    except:
                        continue
                
                # Review count
                review_selectors = [
                    '.UY7F9',
                    '.ceNzKf',
                    'button:has-text("reviews")',
                    'span:has-text("reviews")'
                ]
                
                for selector in review_selectors:
                    try:
                        element = page.query_selector(selector)
                        if element:
                            review_text = element.inner_text().strip()
                            review_match = re.search(r'(\d{1,3}(?:,\d{3})*|\d+)', review_text)
                            if review_match:
                                review_count = int(review_match.group(1).replace(',', ''))
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