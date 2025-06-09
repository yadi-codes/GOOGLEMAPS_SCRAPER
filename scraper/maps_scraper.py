import time
import random
from datetime import datetime
from playwright.sync_api import sync_playwright
import re
import time
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Add to your scraping function
def wait_for_results(driver, timeout=10):
    try:
        # Wait for search results to load
        WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "[data-result-index]"))
        )
        
        # Scroll to load more results
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(3)
        
    except Exception as e:
        print(f"Timeout waiting for results: {e}")

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
            # Wait for and click the "Accept all" button
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
                # Look for the results panel
                page.wait_for_selector('div[role="main"]', timeout=15000)
                print("✅ Results panel loaded")
            except:
                print("⚠️ Results panel timeout, continuing...")
            
            # Scroll to load more results
            print("🔄 Loading more results...")
            self._scroll_for_results(page)
            
            # Get all business cards from the sidebar
            results = self._extract_all_businesses(page, max_results)
            
            print(f"🎉 Successfully scraped {len(results)} places")
            return results
            
        except Exception as e:
            print(f"❌ Error in search_and_scrape: {str(e)}")
            page.screenshot(path=f'error_{datetime.now().strftime("%Y%m%d_%H%M%S")}.png')
            return []
        finally:
            context.close()

    def _scroll_for_results(self, page, max_scrolls=10):
        """Scroll the results panel to load more places"""
        for i in range(max_scrolls):
            try:
                # Scroll down in the results panel
                page.evaluate("""
                    const resultsPanel = document.querySelector('div[role="main"]');
                    if (resultsPanel) {
                        resultsPanel.scrollBy(0, 1000);
                    } else {
                        window.scrollBy(0, 1000);
                    }
                """)
                
                print(f"Scroll {i+1}/{max_scrolls}")
                time.sleep(random.uniform(1.5, 2.5))
                
            except Exception as e:
                print(f"⚠️ Scroll error: {e}")
                break

    def _extract_all_businesses(self, page, max_results):
        """Extract business information from all visible cards"""
        results = []
        
        try:
            # Wait a bit for all content to load
            time.sleep(5)
            
            # Try multiple approaches to find business elements
            business_elements = []
            
            # Method 1: Look for clickable business cards
            selectors_to_try = [
                'a[data-cid]',  # Business cards with place IDs
                'div[role="article"]',  # Article containers
                'div[jsaction*="mouseover"]',  # Interactive elements
                'div.Nv2PK',  # Common business card class
                'div[data-result-index]',  # Indexed results
                'div.section-result',  # Section results
                '[aria-label][tabindex="-1"]'  # Focusable elements with labels
            ]
            
            for selector in selectors_to_try:
                elements = page.query_selector_all(selector)
                if elements:
                    print(f"✅ Found {len(elements)} elements with selector: {selector}")
                    business_elements = elements
                    break
            
            if not business_elements:
                print("⚠️ No business elements found, trying alternative extraction...")
                return self._extract_from_page_content(page, max_results)
            
            print(f"📊 Processing {min(len(business_elements), max_results)} businesses")
            
            # Limit results
            business_elements = business_elements[:max_results]
            
            for i, element in enumerate(business_elements, 1):
                try:
                    print(f"🏪 Processing business {i}/{len(business_elements)}")
                    
                    # Try direct extraction first
                    business_data = self._extract_card_data(element)
                    
                    # If that fails, try clicking approach
                    if not business_data or not business_data.get('name'):
                        business_data = self._extract_by_clicking(page, element, i)
                    
                    if business_data and business_data.get('name'):
                        results.append(business_data)
                        print(f"✅ Extracted: {business_data['name']}")
                    else:
                        print(f"⚠️ No data found for business {i}")
                        # Debug: save element HTML for inspection
                        try:
                            element_html = element.inner_html()[:200]
                            print(f"   Debug: Element HTML preview: {element_html}")
                        except:
                            pass
                        
                    time.sleep(random.uniform(0.5, 1))
                    
                except Exception as e:
                    print(f"⚠️ Error processing business {i}: {str(e)}")
                    continue
            
        except Exception as e:
            print(f"❌ Error extracting businesses: {str(e)}")
        
        return results

    def _extract_card_data(self, element):
        """Extract data from a business card element - improved version"""
        try:
            data = {
                'name': None,
                'address': None,
                'phone': None,
                'rating': None,
                'review_count': None,
                'category': None,
                'scraped_at': datetime.now().isoformat()
            }
            
            # Method 1: Try to get aria-label (most reliable)
            try:
                aria_label = element.get_attribute('aria-label')
                if aria_label:
                    data['name'] = aria_label.strip()
                    print(f"   Found name via aria-label: {data['name']}")
            except:
                pass
            
            # Method 2: Try to get text content directly
            if not data['name']:
                try:
                    # Look for heading elements
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
            
            # Method 3: Parse HTML content
            if not data['name']:
                try:
                    card_html = element.inner_html()
                    
                    # Look for common name patterns in HTML
                    name_patterns = [
                        r'aria-label="([^"]+)"',
                        r'<div[^>]*fontHeadlineSmall[^>]*>([^<]+)</div>',
                        r'<span[^>]*fontHeadlineSmall[^>]*>([^<]+)</span>',
                        r'<div[^>]*fontDisplaySmall[^>]*>([^<]+)</div>',
                        r'data-value="([^"]+)"[^>]*role="button"'
                    ]
                    
                    for pattern in name_patterns:
                        match = re.search(pattern, card_html, re.IGNORECASE)
                        if match:
                            potential_name = match.group(1).strip()
                            # Filter out common non-name text
                            if (len(potential_name) > 3 and 
                                not any(word in potential_name.lower() for word in 
                                       ['directions', 'website', 'save', 'share', 'more info', 'menu'])):
                                data['name'] = potential_name
                                print(f"   Found name via HTML pattern: {data['name']}")
                                break
                except Exception as e:
                    print(f"   Error parsing HTML: {e}")
            
            # Extract rating if name was found
            if data['name']:
                try:
                    card_html = element.inner_html()
                    
                    # Look for rating
                    rating_patterns = [
                        r'(\d+[.,]\d+)\s*stars?',
                        r'aria-label="(\d+[.,]\d+) stars"',
                        r'>(\d+[.,]\d+)<.*?star',
                        r'(\d+[.,]\d+).*?★'
                    ]
                    
                    for pattern in rating_patterns:
                        match = re.search(pattern, card_html, re.IGNORECASE)
                        if match:
                            try:
                                rating_str = match.group(1).replace(',', '.')
                                data['rating'] = float(rating_str)
                                break
                            except:
                                continue
                    
                    # Look for review count
                    review_patterns = [
                        r'(\d{1,3}(?:,\d{3})*)\s*reviews?',
                        r'\((\d{1,3}(?:,\d{3})*)\)',
                        r'(\d+)\s*reviews?'
                    ]
                    
                    for pattern in review_patterns:
                        match = re.search(pattern, card_html, re.IGNORECASE)
                        if match:
                            try:
                                review_str = match.group(1).replace(',', '')
                                data['review_count'] = int(review_str)
                                break
                            except:
                                continue
                
                except:
                    pass
            
            return data if data['name'] else None
            
        except Exception as e:
            print(f"   Error extracting card data: {str(e)}")
            return None

    def close(self):
        """Clean up resources"""
        try:
            self.browser.close()
            self.playwright.stop()
        except:
            pass

    def _extract_by_clicking(self, page, element, index):
        """Extract data by clicking on the business card"""
        try:
            # Scroll element into view
            element.scroll_into_view_if_needed()
            time.sleep(1)
            
            # Click the element
            element.click(timeout=5000)
            time.sleep(3)
            
            # Wait for business details to load
            try:
                page.wait_for_selector('h1, [data-attrid="title"]', timeout=10000)
            except:
                print(f"   ⚠️ Details panel didn't load for business {index}")
                return None
            
            # Extract data from the details panel
            data = self._extract_detail_panel_data(page)
            
            # Close the details panel
            try:
                # Try multiple ways to go back
                back_selectors = [
                    'button[aria-label*="Back"]',
                    'button[data-value="Back"]',
                    'button[jsaction*="back"]'
                ]
                
                back_clicked = False
                for selector in back_selectors:
                    back_button = page.query_selector(selector)
                    if back_button:
                        back_button.click()
                        back_clicked = True
                        break
                
                if not back_clicked:
                    page.keyboard.press("Escape")
                
                time.sleep(2)
                
            except Exception as e:
                print(f"   ⚠️ Error closing details panel: {e}")
                page.keyboard.press("Escape")
            
            return data
            
        except Exception as e:
            print(f"   ⚠️ Error in click extraction: {e}")
            return None

    def _extract_detail_panel_data(self, page):
        """Extract data from the opened business details panel"""
        try:
            data = {
                'name': None,
                'address': None,
                'phone': None,
                'rating': None,
                'review_count': None,
                'category': None,
                'scraped_at': datetime.now().isoformat()
            }
            
            # Extract name
            name_selectors = [
                'h1.fontHeadlineLarge',
                'h1.DUwDvf',
                'h1[data-attrid="title"]',
                'h1',
                '[data-attrid="title"] span'
            ]
            
            for selector in name_selectors:
                try:
                    element = page.query_selector(selector)
                    if element:
                        name = element.inner_text().strip()
                        if name and len(name) > 0:
                            data['name'] = name
                            break
                except:
                    continue
            
            # Extract other details using similar approach
            # Rating
            try:
                rating_element = page.query_selector('div.F7nice span[aria-hidden="true"]')
                if rating_element:
                    rating_text = rating_element.inner_text().strip()
                    rating_match = re.search(r'(\d+\.?\d*)', rating_text)
                    if rating_match:
                        data['rating'] = float(rating_match.group(1))
            except:
                pass
            
            # Address
            address_selectors = [
                'button[data-item-id="address"] div.fontBodyMedium',
                '[data-item-id="address"] div'
            ]
            
            for selector in address_selectors:
                try:
                    element = page.query_selector(selector)
                    if element:
                        address = element.inner_text().strip()
                        if address:
                            data['address'] = address
                            break
                except:
                    continue
            
            # Phone
            try:
                phone_element = page.query_selector('button[data-item-id="phone"] div.fontBodyMedium')
                if phone_element:
                    data['phone'] = phone_element.inner_text().strip()
            except:
                pass
            
            return data
            
        except Exception as e:
            print(f"   Error extracting detail panel data: {e}")
            return None

    def _extract_from_page_content(self, page, max_results):
        """Alternative extraction method using page content"""
        try:
            print("🔄 Trying alternative extraction method...")
            
            # Get all text content and look for patterns
            page_content = page.content()
            
            # Look for business names and data in the HTML
            results = []
            
            # Use regex to find business information patterns
            business_patterns = [
                r'"([^"]{10,100})"[^>]*aria-label[^>]*tabindex',
                r'data-cid="(\d+)"[^>]*aria-label="([^"]+)"',
                r'<div[^>]*fontHeadlineSmall[^>]*>([^<]+)</div>'
            ]
            
            for pattern in business_patterns:
                matches = re.finditer(pattern, page_content, re.IGNORECASE)
                for match in matches:
                    name = match.group(1) if len(match.groups()) == 1 else match.group(2)
                    if name and len(name.strip()) > 5:
                        results.append({
                            'name': name.strip(),
                            'address': None,
                            'phone': None,
                            'rating': None,
                            'review_count': None,
                            'category': None,
                            'scraped_at': datetime.now().isoformat()
                        })
                        
                        if len(results) >= max_results:
                            break
                
                if len(results) >= max_results:
                    break
            
            # Remove duplicates
            seen_names = set()
            unique_results = []
            for result in results:
                if result['name'] not in seen_names:
                    seen_names.add(result['name'])
                    unique_results.append(result)
            
            return unique_results[:max_results]
            
        except Exception as e:
            print(f"Error in alternative extraction: {e}")
            return []

# Test function
def test_scraper():
    """Test the scraper with a simple search"""
    scraper = GoogleMapsScraper(headless=False)  # Set to True for headless mode
    
    try:
        results = scraper.search_and_scrape("restaurants", "New York", max_results=10)
        
        print(f"\n🎉 Test Results: {len(results)} places found")
        print("-" * 50)
        
        for i, place in enumerate(results, 1):
            print(f"\n{i}. {place.get('name', 'Unknown')}")
            if place.get('rating'):
                print(f"   Rating: {place['rating']} ({place.get('review_count', 0)} reviews)")
            if place.get('address'):
                print(f"   Address: {place['address']}")
            if place.get('category'):
                print(f"   Category: {place['category']}")
            if place.get('phone'):
                print(f"   Phone: {place['phone']}")
            
    except Exception as e:
        print(f"Test error: {e}")
    finally:
        scraper.close()
    
#     # Add this to the end of maps_scraper.py for debugging
# def debug_extraction():
#     """Debug function to see what elements are being found"""
#     scraper = GoogleMapsScraper(headless=False)
    
#     context = scraper.browser.new_context()
#     page = context.new_page()
    
#     try:
#         page.goto("https://www.google.com/maps")
#         time.sleep(3)
        
#         # Search
#         search_box = page.wait_for_selector('input#searchboxinput', timeout=15000)
#         search_box.fill("schools in trivandrum")
#         search_box.press("Enter")
#         time.sleep(8)
        
#         # Find elements and print their HTML
#         selectors = [
#         "[data-result-index]",
#         ".hfpxzc",
#         "[data-cid]",
#         ".VkpGBb",
#         ".bfdHYd",
#         "[jsaction*='pane.selectResult']"
#     ]
        
#         for selector in selectors:
#             elements = driver.find_elements(By.CSS_SELECTOR, selector)
#             print(f"=== {selector} found {len(elements)} elements ===")
#             if elements:
#                 break
            
#             for i, elem in enumerate(elements[:3]):  # Check first 3
#                 try:
#                     html_preview = elem.inner_html()[:300]
#                     aria_label = elem.get_attribute('aria-label')
#                     print(f"\nElement {i+1}:")
#                     print(f"Aria-label: {aria_label}")
#                     print(f"HTML preview: {html_preview}")
#                 except Exception as e:
#                     print(f"Error getting element {i}: {e}")
    
#     finally:
#         context.close()
#         scraper.close()

# # Uncomment to run debug
# debug_extraction()
if __name__ == "__main__":
    test_scraper()