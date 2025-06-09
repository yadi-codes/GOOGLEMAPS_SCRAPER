"""
Business Models and Data Extraction Functions
Contains all business-related data processing and extraction logic
"""

from selenium.webdriver.common.by import By
from datetime import datetime
import re


class BusinessExtractor:
    """Handles extraction of business data from Google Maps"""
    
    def __init__(self):
        self.business_selectors = [
            "div[data-result-index]",
            "a[data-cid]",
            "div[role='article']",
            "div.hfpxzc",
            "div[jsaction*='pane.selectResult']",
        ]
        
        self.ui_patterns = [
            "Collapse side panel", "stars", "Map · Use arrow keys",
            "Available search options", "button", "search", "menu"
        ]

    def extract_businesses(self, driver):
        """Find actual business listings, filtering out UI elements"""
        for selector in self.business_selectors:
            elements = driver.find_elements(By.CSS_SELECTOR, selector)
            if elements:
                print(f"✅ Found {len(elements)} business elements using: {selector}")
                return elements
        
        print("🔄 No matches from primary selectors. Falling back to filtered elements...")
        return self._filter_generic_elements(driver)

    def _filter_generic_elements(self, driver):
        all_elements = driver.find_elements(By.CSS_SELECTOR, "div[jsaction*='mouseover']")
        return [el for el in all_elements if self._is_business_element(el)]

    def _is_business_element(self, element):
        aria_label = element.get_attribute("aria-label") or ""
        html_preview = element.get_attribute("outerHTML")[:200].lower()
        
        if any(pat in aria_label.lower() for pat in self.ui_patterns):
            return False
        if any(pat in html_preview for pat in self.ui_patterns):
            return False

        return (
            element.find_elements(By.CSS_SELECTOR, "div[class*='fontHeadline']") or
            element.find_elements(By.CSS_SELECTOR, "span[class*='fontHeadline']") or
            element.find_elements(By.CSS_SELECTOR, ".hfpxzc") or
            any(term in html_preview for term in [
                "salon", "restaurant", "hotel", "shop", "store", "clinic",
                "center", "service", "company", "office"
            ])
        )

    def extract_business_data(self, element, index):
        """Extract comprehensive business data from a given element"""
        data = BusinessData()
        bad_names = ["collapse side panel", "available search", "map · use arrow", "stars"]

        try:
            data.name = self._extract_name(element)
            if not data.name:
                return None

            # ✅ Skip fake UI elements based on name
            if any(bad in data.name.lower() for bad in bad_names):
                print(f"⚠️ Skipping UI element: {data.name}")
                return None

            data.address = self._extract_address(element)
            data.phone = self._extract_phone(element)
            data.rating = self._extract_rating(element)
            data.category = self._extract_category(element) or "Unknown"
            data.reviews_count = self._extract_reviews_count(element)

            print(f"✅ Extracted business: {data.name}")
            return data.to_dict()

        except Exception as e:
            print(f"❌ Error at index {index}: {e}")
            return None

    def _extract_name(self, element):
        name_selectors = [
            "div[class*='fontHeadline']",
            "span[class*='fontHeadline']",
            "h3", ".qBF1Pd", ".DUwDvf",
            "a[data-cid] div[class*='fontHeadline']"
        ]
        for selector in name_selectors:
            try:
                elem = element.find_element(By.CSS_SELECTOR, selector)
                if elem and elem.text.strip():
                    return elem.text.strip()
            except:
                continue
        return element.get_attribute("aria-label") or None

    def _extract_address(self, element):
        selectors = [
            ".W4Efsd:not(.W4Efsd .W4Efsd)",
            "span[jstcache*='3']",
            ".AeaXub",
            "div[class*='address']"
        ]
        return self._extract_by_selectors(element, selectors)

    def _extract_rating(self, element):
        selectors = [
            "span.MW4etd",
            "div[jsaction*='pane.rating']",
            ".U8T7xe"
        ]
        for selector in selectors:
            try:
                elem = element.find_element(By.CSS_SELECTOR, selector)
                text = elem.text.strip()
                if text and text.replace('.', '').isdigit():
                    return float(text)
            except:
                continue
        return None

    def _extract_category(self, element):
        selectors = [
            ".W4Efsd:last-child",
            "span[jstcache*='4']",
            ".DkEaL"
        ]
        for selector in selectors:
            try:
                elem = element.find_element(By.CSS_SELECTOR, selector)
                if elem:
                    text = elem.text.strip()
                    if not any(word in text.lower() for word in ['road', 'street', 'avenue', 'kerala', 'india']):
                        return text
            except:
                continue
        return "Business"

    def _extract_phone(self, element):
        try:
            elems = element.find_elements(
                By.XPATH,
                ".//*[contains(text(), '+91') or contains(text(), '0471') or contains(text(), '9')]"
            )
            for elem in elems:
                text = elem.text.strip()
                if len(text) >= 10 and any(char.isdigit() for char in text):
                    return text
        except:
            pass
        return None

    def _extract_reviews_count(self, element):
        try:
            elems = element.find_elements(By.XPATH, ".//*[contains(text(), 'review')]")
            for elem in elems:
                numbers = re.findall(r'\d+', elem.text.strip())
                if numbers:
                    return int(numbers[0])
        except:
            pass
        return None

    def _extract_by_selectors(self, element, selectors):
        for selector in selectors:
            try:
                elem = element.find_element(By.CSS_SELECTOR, selector)
                if elem and elem.text.strip():
                    return elem.text.strip()
            except:
                continue
        return None


class BusinessData:
    """Simple data class for business info"""

    def __init__(self):
        self.name = None
        self.address = None
        self.phone = None
        self.website = None
        self.rating = None
        self.category = None
        self.reviews_count = None
        self.created_at = datetime.now()

    def to_dict(self):
        return {
            'name': self.name,
            'address': self.address,
            'phone': self.phone,
            'website': self.website,
            'rating': self.rating,
            'category': self.category,
            'reviews_count': self.reviews_count
        }

    def is_valid(self):
        if not self.name or len(self.name) < 2:
            return False
        for ui_term in ['stars', 'collapse side panel', 'map', 'available search options', 'button']:
            if ui_term in self.name.lower():
                return False
        return True
