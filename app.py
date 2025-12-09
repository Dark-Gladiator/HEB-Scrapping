import time
import json
import csv
import re
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import os

class HEBScraper:
    def __init__(self, headless=False):
        """
        Initialize the HEB scraper with Chrome WebDriverojjl;
        
        Args:
            headless (bool): Run browser in headless mode (no GUI)
        """
        self.base_url = "https://heb.com"
        self.products = []
        self.seen_urls = set()  # Track all product URLs to avoid duplicates
        self.setup_driver(headless)
    
    def setup_driver(self, headless=False):
        """Setup Chrome WebDriver with enhanced anti-detection options"""
        chrome_options = Options()
        
        # Don't use headless mode - it's easier to detect
        # if headless:
        #     chrome_options.add_argument("--headless")
        
        # Basic options
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--start-maximized")
        
        # Anti-detection options
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation", "enable-logging"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        chrome_options.add_experimental_option("detach", True)
        
        # Enhanced user agent
        chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")
        
        # Additional stealth options
        chrome_options.add_argument("--disable-web-security")
        chrome_options.add_argument("--allow-running-insecure-content")
        chrome_options.add_argument("--disable-features=IsolateOrigins,site-per-process")
        chrome_options.add_argument("--disable-site-isolation-trials")
        chrome_options.add_argument("--lang=en-US,en;q=0.9")
        chrome_options.add_argument("--accept-lang=en-US,en;q=0.9")
        
        # Disable automation flags
        prefs = {
            "credentials_enable_service": False,
            "profile.password_manager_enabled": False,
            "profile.default_content_setting_values.notifications": 2,
            "profile.managed_default_content_settings.images": 1
        }
        chrome_options.add_experimental_option("prefs", prefs)
        
        try:
            # Try to use webdriver-manager if available, otherwise use default
            try:
                from selenium.webdriver.chrome.service import Service
                from webdriver_manager.chrome import ChromeDriverManager
                service = Service(ChromeDriverManager().install())
                self.driver = webdriver.Chrome(service=service, options=chrome_options)
            except ImportError:
                # Fallback to system PATH ChromeDriver
                self.driver = webdriver.Chrome(options=chrome_options)
            
            # Execute stealth JavaScript to hide webdriver properties
            self.driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
                'source': '''
                    Object.defineProperty(navigator, 'webdriver', {
                        get: () => undefined
                    });
                    window.navigator.chrome = {
                        runtime: {}
                    };
                    Object.defineProperty(navigator, 'plugins', {
                        get: () => [1, 2, 3, 4, 5]
                    });
                    Object.defineProperty(navigator, 'languages', {
                        get: () => ['en-US', 'en']
                    });
                '''
            })
            
            self.driver.maximize_window()
            print("WebDriver initialized successfully with anti-detection measures")
        except Exception as e:
            print(f"Error setting up WebDriver: {e}")
            print("Please make sure ChromeDriver is installed and in your PATH")
            raise
    
    def wait_for_page_load(self, timeout=30):
        """Wait for page to fully load including JavaScript"""
        try:
            # Wait for document ready state
            WebDriverWait(self.driver, timeout).until(
                lambda d: d.execute_script('return document.readyState') == 'complete'
            )
            # Additional wait for any lazy-loaded content
            time.sleep(3)
        except TimeoutException:
            print("Page load timeout, continuing anyway...")
    
    def check_for_blocking(self):
        """Check if the page is blocking us"""
        try:
            page_source = self.driver.page_source.lower()
            blocking_indicators = [
                'ad blocker',
                'antivirus software',
                'vpn',
                'firewall',
                'could not load',
                'access denied',
                'blocked',
                'bot detected'
            ]
            for indicator in blocking_indicators:
                if indicator in page_source:
                    print(f"⚠ Warning: Possible blocking detected - '{indicator}' found in page")
                    return True
            return False
        except:
            return False
    
    def verify_product_page(self):
        """Verify we're on a page that contains products"""
        try:
            # Check URL
            current_url = self.driver.current_url.lower()
            if '/product' not in current_url and '/category' not in current_url and '/department' not in current_url and '/aisle' not in current_url and 'heb.com' not in current_url:
                print(f"⚠ Warning: Current URL doesn't look like a product page: {current_url}")
                return False
            
            # Check for product indicators in page
            page_source = self.driver.page_source.lower()
            product_indicators = ['product', 'price', '$', 'add to cart', 'buy now']
            found_indicators = sum(1 for indicator in product_indicators if indicator in page_source)
            
            if found_indicators < 2:
                print("⚠ Warning: Page doesn't seem to contain product listings")
                return False
            
            return True
        except:
            return True  # Assume OK if we can't check
    
    def scrape_category_page(self, page_url):
        """
        Scrape products from a page
        
        Args:
            page_url (str): URL to scrape products from
        
        Returns:
            list: List of product dictionaries
        """
        try:
            print(f"\nNavigating to: {page_url}")
            
            # Add random delay to mimic human behavior
            time.sleep(2 + (time.time() % 2))
            
            self.driver.get(page_url)
            
            # Wait for page to fully load
            self.wait_for_page_load(timeout=30)
            
            # Check for blocking
            if self.check_for_blocking():
                print("⚠ Page appears to be blocking the scraper. Trying to continue...")
                time.sleep(5)
            
            # Additional wait for dynamic content
            time.sleep(5)
            
            # Human-like mouse movement simulation
            try:
                self.driver.execute_script("window.scrollTo(0, 100);")
                time.sleep(1)
            except:
                pass
            
            # Scroll to load more products (lazy loading) - ENHANCED scrolling
            print("Scrolling to load ALL products (vertical + horizontal)...")
            self.scroll_page(scroll_pause_time=2.5, max_scrolls=150)
            
            # Additional wait after scrolling for any final lazy loads
            print("Waiting for final content to load...")
            time.sleep(5)
            
            # Scroll horizontal carousels once after all vertical scrolling is complete
            print("Scrolling horizontal carousels to reveal all products...")
            self.scroll_horizontal_carousels()
            
            # Try one more scroll pass to catch any missed items
            print("Performing additional scroll pass...")
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(3)
            self.driver.execute_script("window.scrollTo(0, 0);")
            time.sleep(2)
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(3)
            
            # Debug: Print page info
            print(f"Page title: {self.driver.title}")
            print(f"Current URL: {self.driver.current_url}")
            
            # Verify we're on a product listing page
            if not self.verify_product_page():
                print("⚠ Warning: This doesn't appear to be a product listing page!")
                print("   Trying to continue anyway...")
            
            # Check again for blocking after scrolling
            if self.check_for_blocking():
                print("⚠ Blocking detected after scrolling. Products may not be available.")
            
            # Find product elements - NO LIMIT on products
            # Extract products (this will add to self.products internally)
            products = self.extract_products(max_products=None)
            
            # Note: extract_products returns products but doesn't add to self.products
            # So we need to add them here
            self.products.extend(products)
            print(f"✓ Scraped {len(products)} products from this page (Total: {len(self.products)})")
            
            # Do a second pass after a short wait to catch any lazy-loaded products
            print("Performing second extraction pass to catch any missed products...")
            time.sleep(3)
            
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)
            self.driver.execute_script("window.scrollTo(0, 0);")
            time.sleep(2)
            
            # Second extraction pass
            products_pass2 = self.extract_products(max_products=None)
            # Filter out duplicates
            existing_urls = {p.get('product_hyperlink') for p in self.products if p.get('product_hyperlink')}
            existing_titles = {p.get('product_title') for p in self.products if p.get('product_title')}
            
            new_products = []
            for p in products_pass2:
                url = p.get('product_hyperlink')
                title = p.get('product_title')
                if (url and url not in existing_urls) or (title and title not in existing_titles):
                    new_products.append(p)
                    if url:
                        existing_urls.add(url)
                    if title:
                        existing_titles.add(title)
            
            if new_products:
                self.products.extend(new_products)
                print(f"✓ Second pass found {len(new_products)} additional products (Grand Total: {len(self.products)})")
            else:
                print(f"✓ Second pass found no additional products (Total: {len(self.products)})")
            
            return products
            
        except Exception as e:
            print(f"Error during scraping {page_url}: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def scrape_homepage(self):
        """Scrape products from the HEB.com homepage"""
        try:
            print(f"\n{'='*60}")
            print("Starting HOMEPAGE SCRAPE of heb.com")
            print("Scraping products from the homepage only")
            print(f"{'='*60}\n")
            
            # Scrape homepage
            homepage_url = "https://heb.com"
            print(f"Scraping homepage: {homepage_url}")
            
            products = self.scrape_category_page(homepage_url)
            
            print(f"\n{'='*60}")
            print(f"SCRAPING COMPLETE!")
            print(f"{'='*60}")
            print(f"Total unique products found: {len(self.products)}")
            print(f"{'='*60}\n")
            
            return self.products
            
        except Exception as e:
            print(f"Error in scrape_homepage: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def scroll_horizontal_carousels(self):
        """Scroll horizontal carousels to reveal all products in each carousel"""
        print("\nScrolling horizontal carousels to reveal all products...")
        
        try:
            # Find all horizontal scrollable containers (carousels)
            carousel_selectors = [
                "[class*='carousel' i]",
                "[class*='Carousel' i]",
                "[class*='slider' i]",
                "[class*='Slider' i]",
                "[class*='scroll' i][class*='horizontal' i]",
                "[class*='horizontal' i][class*='scroll' i]",
                "[style*='overflow-x']",
                "[style*='overflow: auto']",
                "[style*='overflow: scroll']",
                "[data-testid*='carousel' i]",
                "[data-testid*='slider' i]",
            ]
            
            carousels = []
            for selector in carousel_selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for elem in elements:
                        # Check if element is horizontally scrollable
                        try:
                            style = elem.get_attribute('style') or ''
                            computed_style = self.driver.execute_script(
                                "return window.getComputedStyle(arguments[0]).overflowX;", elem)
                            
                            if (computed_style in ['auto', 'scroll'] or 
                                'overflow-x' in style.lower() or
                                'overflow: auto' in style.lower() or
                                'overflow: scroll' in style.lower()):
                                # Check if it has scrollable content
                                scroll_width = self.driver.execute_script(
                                    "return arguments[0].scrollWidth;", elem)
                                client_width = self.driver.execute_script(
                                    "return arguments[0].clientWidth;", elem)
                                
                                if scroll_width > client_width:
                                    carousels.append(elem)
                        except:
                            continue
                except:
                    continue
            
            # Also look for arrow buttons that indicate carousels
            arrow_buttons = self.driver.find_elements(By.CSS_SELECTOR, 
                "button[aria-label*='next' i], button[aria-label*='right' i], " +
                "button[class*='arrow' i], button[class*='next' i], " +
                "[class*='arrow-right' i], [class*='carousel-next' i], " +
                "[class*='slider-next' i]")
            
            for btn in arrow_buttons:
                try:
                    # Find parent carousel container
                    parent = btn.find_element(By.XPATH, "./ancestor::*[contains(@class, 'carousel') or contains(@class, 'slider') or contains(@style, 'overflow')][1]")
                    if parent not in carousels:
                        carousels.append(parent)
                except:
                    pass
            
            print(f"  Found {len(carousels)} horizontal carousels")
            
            # Scroll each carousel horizontally
            for idx, carousel in enumerate(carousels, 1):
                try:
                    print(f"  Scrolling carousel {idx}/{len(carousels)}...")
                    
                    # Scroll carousel into view first
                    self.driver.execute_script("arguments[0].scrollIntoView({block: 'center', behavior: 'smooth'});", carousel)
                    time.sleep(1)
                    
                    # Get initial scroll position
                    scroll_left = self.driver.execute_script("return arguments[0].scrollLeft;", carousel)
                    scroll_width = self.driver.execute_script("return arguments[0].scrollWidth;", carousel)
                    client_width = self.driver.execute_script("return arguments[0].clientWidth;", carousel)
                    max_scroll = scroll_width - client_width
                    
                    if max_scroll <= 0:
                        continue  # Not scrollable
                    
                    # Try clicking arrow buttons first
                    try:
                        # Find arrow buttons within or near this carousel
                        carousel_arrows = carousel.find_elements(By.CSS_SELECTOR, 
                            "button[aria-label*='next' i], button[aria-label*='right' i], " +
                            "[class*='arrow-right' i], [class*='carousel-next' i]")
                        
                        # Also check siblings
                        try:
                            parent = carousel.find_element(By.XPATH, "./..")
                            sibling_arrows = parent.find_elements(By.CSS_SELECTOR,
                                "button[aria-label*='next' i], button[aria-label*='right' i]")
                            carousel_arrows.extend(sibling_arrows)
                        except:
                            pass
                        
                        # Click arrows until we can't scroll more (limited)
                        clicks = 0
                        max_clicks = 20  # Reduced from 50
                        last_scroll = scroll_left
                        
                        while clicks < max_clicks:
                            clicked = False
                            for arrow in carousel_arrows:
                                try:
                                    if arrow.is_displayed() and arrow.is_enabled():
                                        self.driver.execute_script("arguments[0].click();", arrow)
                                        time.sleep(0.3)  # Reduced wait time
                                        clicked = True
                                        break
                                except:
                                    continue
                            
                            if not clicked:
                                break
                            
                            # Check if we scrolled
                            new_scroll = self.driver.execute_script("return arguments[0].scrollLeft;", carousel)
                            if new_scroll == last_scroll:
                                break  # No more scrolling
                            
                            last_scroll = new_scroll
                            clicks += 1
                            
                            # Check if we've reached the end
                            if new_scroll >= max_scroll - 10:  # 10px tolerance
                                break
                        
                        if clicks > 0:
                            print(f"    Clicked arrow {clicks} times")
                    except Exception as e:
                        pass
                    
                    # Also do programmatic horizontal scrolling as backup (simplified)
                    scroll_amount = client_width * 0.9  # Scroll 90% of visible width
                    current_scroll = self.driver.execute_script("return arguments[0].scrollLeft;", carousel)
                    scrolls = 0
                    max_horizontal_scrolls = 10  # Reduced from 20
                    
                    while current_scroll < max_scroll and scrolls < max_horizontal_scrolls:
                        # Scroll right
                        new_scroll = min(current_scroll + scroll_amount, max_scroll)
                        self.driver.execute_script("arguments[0].scrollLeft = arguments[1];", carousel, new_scroll)
                        time.sleep(0.3)  # Reduced wait time
                        
                        # Check if we actually scrolled
                        actual_scroll = self.driver.execute_script("return arguments[0].scrollLeft;", carousel)
                        if actual_scroll == current_scroll:
                            break  # Can't scroll more
                        
                        current_scroll = actual_scroll
                        scrolls += 1
                    
                    # Scroll through once to ensure all products are visible
                    for i in range(0, int(max_scroll), int(client_width * 0.8)):
                        self.driver.execute_script("arguments[0].scrollLeft = arguments[1];", carousel, i)
                        time.sleep(0.2)  # Reduced wait time
                    
                    print(f"    Completed horizontal scrolling for carousel {idx}")
                    
                except Exception as e:
                    print(f"    Error scrolling carousel {idx}: {e}")
                    continue
            
            print(f"  Finished scrolling {len(carousels)} carousels")
            
        except Exception as e:
            print(f"  Error in horizontal carousel scrolling: {e}")
    
    def scroll_page(self, scroll_pause_time=2, max_scrolls=100):
        """Scroll the page to load lazy-loaded content - ENHANCED VERSION"""
        print("Starting enhanced scrolling to load all products...")
        
        last_height = self.driver.execute_script("return document.body.scrollHeight")
        last_product_count = 0
        scrolls = 0
        no_change_count = 0
        no_product_change_count = 0
        
        # First, try to scroll to load initial content
        self.driver.execute_script("window.scrollTo(0, 500);")
        time.sleep(3)
        
        # Count initial products
        try:
            initial_products = len(self.driver.find_elements(By.CSS_SELECTOR, "img"))
            print(f"Initial images found: {initial_products}")
        except:
            pass
        
        while scrolls < max_scrolls:
            # Scroll down incrementally (smaller increments for better loading)
            current_scroll = self.driver.execute_script("return window.pageYOffset;")
            scroll_amount = 800  # Smaller increments
            self.driver.execute_script(f"window.scrollTo(0, {current_scroll + scroll_amount});")
            
            # Wait for new content to load
            time.sleep(scroll_pause_time)
            
            # Try clicking "Load More" buttons if they exist
            try:
                load_more_selectors = [
                    "button[class*='load-more' i]",
                    "button[class*='LoadMore' i]",
                    "a[class*='load-more' i]",
                    "button:contains('Load More')",
                    "button:contains('Show More')",
                    "button:contains('See More')",
                    "*[aria-label*='load more' i]",
                    "*[aria-label*='show more' i]",
                ]
                
                for selector in load_more_selectors:
                    try:
                        load_btn = self.driver.find_element(By.CSS_SELECTOR, selector)
                        if load_btn.is_displayed():
                            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", load_btn)
                            time.sleep(1)
                            self.driver.execute_script("arguments[0].click();", load_btn)
                            print("  Clicked 'Load More' button")
                            time.sleep(3)
                            break
                    except:
                        continue
            except:
                pass
            
            # Calculate new scroll height
            new_height = self.driver.execute_script("return document.body.scrollHeight")
            
            # Count products/images to see if more loaded
            try:
                current_images = len(self.driver.find_elements(By.CSS_SELECTOR, "img"))
                if current_images > last_product_count:
                    last_product_count = current_images
                    no_product_change_count = 0
                    if scrolls % 10 == 0:
                        print(f"  Scrolled {scrolls} times, found {current_images} images so far...")
                else:
                    no_product_change_count += 1
            except:
                pass
            
            if new_height == last_height:
                no_change_count += 1
                # If no change for 5 consecutive scrolls, try different strategies
                if no_change_count >= 5:
                    # Strategy 1: Try scrolling to absolute bottom
                    self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                    time.sleep(scroll_pause_time * 2)
                    new_height = self.driver.execute_script("return document.body.scrollHeight")
                    
                    if new_height == last_height:
                        # Strategy 2: Try smooth scrolling
                        self.driver.execute_script("window.scrollTo({top: document.body.scrollHeight, behavior: 'smooth'});")
                        time.sleep(scroll_pause_time * 2)
                        new_height = self.driver.execute_script("return document.body.scrollHeight")
                        
                        if new_height == last_height and no_product_change_count >= 5:
                            # No more content loading
                            print(f"  No more content loading after {scrolls} scrolls")
                            break
                        else:
                            no_change_count = 0
                            no_product_change_count = 0
                    else:
                        no_change_count = 0
                        no_product_change_count = 0
            else:
                no_change_count = 0
                no_product_change_count = 0
            
            last_height = new_height
            scrolls += 1
        
        # Final scroll to bottom to ensure everything is loaded
        print("  Performing final scroll to bottom...")
        self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(scroll_pause_time * 2)
        
        # Scroll back to top slowly to trigger any remaining lazy loads
        print("  Scrolling back to top to trigger any remaining lazy loads...")
        for i in range(5):
            scroll_pos = self.driver.execute_script("return document.body.scrollHeight") - (i * 1000)
            if scroll_pos > 0:
                self.driver.execute_script(f"window.scrollTo(0, {scroll_pos});")
                time.sleep(1)
        
        # Final wait
        time.sleep(2)
        print(f"  Scrolling complete. Total scrolls: {scrolls}")
    
    def find_all_categories(self):
        """Find all category/department links from heb.com - Navigate to homepage and discover categories"""
        categories = []
        category_urls = set()
        
        try:
            print(f"\n{'='*60}")
            print("Discovering all categories from heb.com...")
            print(f"{'='*60}")
            
            # Navigate to homepage to discover categories
            homepage_url = "https://heb.com"
            print(f"Navigating to homepage: {homepage_url}")
            
            # Add random delay
            time.sleep(2)
            
            self.driver.get(homepage_url)
            self.wait_for_page_load(timeout=30)
            
            # Check for blocking
            if self.check_for_blocking():
                print("⚠ Homepage appears to be blocking. Continuing anyway...")
                time.sleep(5)
            
            # Wait for navigation menu to appear
            time.sleep(5)
            
            # Human-like behavior - small scroll first
            try:
                self.driver.execute_script("window.scrollTo(0, 200);")
                time.sleep(2)
            except:
                pass
            
            # Scroll to load navigation menu
            self.scroll_page(max_scrolls=5)
            
            # Try multiple selectors to find category/product links
            category_selectors = [
                # HEB specific patterns
                "a[href*='/product/']",
                "a[href*='/category/']",
                "a[href*='/department/']",
                "a[href*='/aisle/']",
                "a[href*='/brand/']",
                "a[href*='/p/']",
                # Navigation patterns
                "[data-testid*='category'] a",
                "[data-testid*='department'] a",
                "[class*='Category'] a",
                "[class*='Department'] a",
                "[class*='Navigation'] a",
                "[class*='Menu'] a",
                # Generic patterns
                "nav a",
                "[class*='category'] a",
                "[class*='department'] a",
                "[class*='nav'] a",
                "[class*='menu'] a",
                "a[href^='/product/']",
                "a[href^='/category/']",
                "a[href^='/department/']",
            ]
            
            for selector in category_selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for elem in elements:
                        try:
                            href = elem.get_attribute('href')
                            text = elem.text.strip()
                            
                            if href and (self.base_url in href or href.startswith('/')):
                                # Normalize URL
                                if not href.startswith('http'):
                                    href = self.base_url + href if href.startswith('/') else f"{self.base_url}/{href}"
                                
                                # Only include heb.com URLs
                                if 'heb.com' in href:
                                    # Filter for product/category URLs
                                    if any(pattern in href for pattern in ['/product/', '/category/', '/department/', '/aisle/', '/p/', '/brand/']):
                                        # Exclude unwanted URLs
                                        if not any(exclude in href for exclude in ['/search', '/account', '/cart', '/checkout', '/login', '/register', '/help', '/about']):
                                            if href not in category_urls:
                                                category_urls.add(href)
                                                categories.append({
                                                    'url': href,
                                                    'name': text or href.split('/')[-1].replace('-', ' ').title() or 'Category'
                                                })
                        except:
                            continue
                    
                    if categories:
                        print(f"Found {len(categories)} categories/links using selector: {selector}")
                        break
                except Exception as e:
                    continue
            
            # Also try searching for product/category links in page source
            if not categories:
                print("Trying alternative method to find categories...")
                try:
                    page_source = self.driver.page_source
                    # Look for product/category URLs in the HTML
                    product_urls = re.findall(r'href=["\']([^"\']*\/(?:product|category|department|aisle|brand|p)\/[^"\']*)["\']', page_source)
                    for url in product_urls[:50]:  # Limit to first 50
                        if not url.startswith('http'):
                            url = self.base_url + url if url.startswith('/') else f"{self.base_url}/{url}"
                        if 'heb.com' in url and url not in category_urls:
                            if '/search' not in url and '/account' not in url:
                                category_urls.add(url)
                                categories.append({
                                    'url': url,
                                    'name': url.split('/')[-1].replace('-', ' ').title() or 'Category'
                                })
                except Exception as e:
                    print(f"Error in alternative method: {e}")
            
            # If still no categories, use homepage as fallback
            if not categories:
                print("No categories found via discovery. Using homepage as fallback")
                categories.append({
                    'url': "https://heb.com",
                    'name': 'Homepage - All Products'
                })
            else:
                print(f"\n✓ Found {len(categories)} categories to scrape")
                for i, cat in enumerate(categories[:10], 1):
                    print(f"  {i}. {cat['name']}: {cat['url']}")
                if len(categories) > 10:
                    print(f"  ... and {len(categories) - 10} more categories")
            
            return categories
            
        except Exception as e:
            print(f"Error finding categories: {e}")
            # Return default homepage URL if category discovery fails
            return [{'url': self.base_url, 'name': 'All Products'}]
    
    def handle_pagination(self, category_url):
        """Handle pagination and return all page URLs for a category"""
        page_urls = [category_url]  # Start with the first page
        
        try:
            self.driver.get(category_url)
            time.sleep(3)
            
            # Scroll to see pagination
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)
            
            # Try to find pagination links
            pagination_selectors = [
                "a[aria-label*='next']",
                "a[aria-label*='Next']",
                "a[class*='next']",
                "a[class*='pagination']",
                "[class*='pagination'] a",
                "a[href*='page=']",
                "a[href*='?page=']",
                "a[href*='&page=']",
                "button[aria-label*='next']",
            ]
            
            # Find next page button/link
            next_page_url = None
            for selector in pagination_selectors:
                try:
                    next_btn = self.driver.find_element(By.CSS_SELECTOR, selector)
                    if next_btn:
                        href = next_btn.get_attribute('href')
                        if href:
                            if not href.startswith('http'):
                                href = self.base_url + href if href.startswith('/') else f"{self.base_url}/{href}"
                            if href not in page_urls and href != category_url:
                                next_page_url = href
                                break
                except:
                    continue
            
            # Alternative: Look for page numbers
            if not next_page_url:
                try:
                    page_links = self.driver.find_elements(By.CSS_SELECTOR, "a[href*='page'], button[data-page]")
                    for link in page_links:
                        href = link.get_attribute('href') or link.get_attribute('data-page')
                        if href:
                            if not href.startswith('http'):
                                href = self.base_url + href if href.startswith('/') else f"{self.base_url}/{href}"
                            if href not in page_urls:
                                page_urls.append(href)
                except:
                    pass
            
            # If we found a next page, try to discover more pages
            if next_page_url:
                page_urls.append(next_page_url)
            
        except Exception as e:
            print(f"Error handling pagination: {e}")
        
        return page_urls
    
    def extract_products(self, max_products=None):
        """
        Extract product information from the current page - IMPROVED with more selectors
        
        Args:
            max_products (int): Maximum products to extract (None = no limit)
        """
        products = []
        
        # Debug: Save page source for inspection (first time only)
        try:
            if not hasattr(self, '_debug_saved'):
                page_source = self.driver.page_source
                if len(page_source) < 500000:  # Only save if reasonable size
                    with open('debug_page_source.html', 'w', encoding='utf-8') as f:
                        f.write(page_source)
                    print("Debug: Saved page source to debug_page_source.html")
                    self._debug_saved = True
        except:
            pass
        
        # Comprehensive list of product selectors - ONLY ACTUAL PRODUCTS, NO CATEGORIES
        product_selectors = [
            # HEB specific patterns
            "[data-testid*='product']",
            "[data-testid*='Product']",
            "[data-product-id]",
            "[data-product-sku]",
            "[data-product-code]",
            # Common e-commerce patterns
            "div[class*='ProductCard']",
            "div[class*='product-card']",
            "div[class*='ProductTile']",
            "div[class*='product-tile']",
            "div[class*='ProductItem']",
            "div[class*='product-item']",
            "article[class*='product']",
            "article[class*='Product']",
            "li[class*='product']",
            "div[class*='grid-item']",
            "div[class*='GridItem']",
            # Link-based patterns - ONLY PRODUCT LINKS, NOT CATEGORIES
            "a[href*='/product/']",
            "a[href*='/p/']",
            # Generic patterns
            "[class*='card'][class*='product']",
            "[class*='tile'][class*='product']",
            "[itemtype*='Product']",
            # Try finding by structure
            "div.product-item",
            ".product-tile",
        ]
        
        product_elements = []
        seen_element_ids = set()  # Track elements we've already found
        
        print("Trying to find products with various selectors (collecting ALL matches)...")
        # Try ALL selectors and combine results instead of stopping at first match
        for selector in product_selectors:
            try:
                elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                if elements and len(elements) > 0:
                    # Filter out elements that are too small or don't have content
                    # ALSO FILTER OUT CATEGORY LINKS
                    filtered_elements = []
                    for elem in elements:
                        try:
                            # Get unique identifier for element
                            elem_id = id(elem)
                            if elem_id in seen_element_ids:
                                continue
                            
                            # EXCLUDE CATEGORY/DEPARTMENT LINKS
                            href = None
                            if elem.tag_name == 'a':
                                href = elem.get_attribute('href') or ''
                            else:
                                try:
                                    link_elem = elem.find_element(By.TAG_NAME, 'a')
                                    href = link_elem.get_attribute('href') or ''
                                except:
                                    pass
                            
                            # Skip if it's a category link
                            if href and ('/category/' in href or '/department/' in href or '/shop/' in href):
                                continue
                            
                            # Check if element has meaningful content
                            text = elem.text.strip()
                            has_img = len(elem.find_elements(By.TAG_NAME, 'img')) > 0
                            has_link = len(elem.find_elements(By.TAG_NAME, 'a')) > 0 or elem.tag_name == 'a'
                            has_price = bool(re.search(r'\$[\d,]+\.?\d*', elem.text))
                            
                            # Element should have image AND (text or price) - this is a real product
                            if has_img and (has_text or has_price or text):
                                filtered_elements.append(elem)
                                seen_element_ids.add(elem_id)
                        except:
                            continue
                    
                    if filtered_elements:
                        product_elements.extend(filtered_elements)
                        print(f"✓ Found {len(filtered_elements)} products using selector: {selector} (Total so far: {len(product_elements)})")
            except Exception as e:
                continue
        
        # Remove duplicates while preserving order
        if product_elements:
            unique_elements = []
            seen = set()
            for elem in product_elements:
                elem_id = id(elem)
                if elem_id not in seen:
                    seen.add(elem_id)
                    unique_elements.append(elem)
            product_elements = unique_elements
            print(f"✓ Total unique products found: {len(product_elements)}")
        
        # If still no products or want to find more, try finding by looking for price patterns
        if len(product_elements) < 10:  # If we found very few, try additional methods
            print("Trying to find products by price patterns...")
            try:
                # Look for elements containing price indicators
                price_containers = self.driver.find_elements(By.XPATH, 
                    "//*[contains(text(), '$') or contains(@class, 'price') or contains(@class, 'Price')]")
                # Get parent containers
                seen_containers = set()
                for price_elem in price_containers[:100]:  # Limit to avoid too many
                    try:
                        # Try to find a parent container that might be a product
                        parent = price_elem.find_element(By.XPATH, "./ancestor::*[contains(@class, 'card') or contains(@class, 'tile') or contains(@class, 'item')][1]")
                        parent_id = id(parent)
                        if parent_id not in seen_containers:
                            seen_containers.add(parent_id)
                            product_elements.append(parent)
                    except:
                        continue
                
                if product_elements:
                    # Add to existing list
                    for elem in product_elements:
                        elem_id = id(elem)
                        if elem_id not in seen_element_ids:
                            seen_element_ids.add(elem_id)
                            product_elements.append(elem)
                    print(f"✓ Found additional products by price patterns (Total: {len(product_elements)})")
            except Exception as e:
                print(f"Error in price pattern search: {e}")
        
        # Try finding all links that might be products (even if we found some already)
        if len(product_elements) < 50:  # If we found less than 50, try this method too
            print("Trying to find products by product links...")
            try:
                # Look for links containing product indicators - ONLY PRODUCT LINKS
                product_links = self.driver.find_elements(By.CSS_SELECTOR, 
                    "a[href*='/product/'], a[href*='/p/']")
                
                # Also try finding any links with images inside that look like products
                all_links = self.driver.find_elements(By.CSS_SELECTOR, "a")
                for link in all_links:
                    try:
                        href = link.get_attribute('href') or ''
                        
                        # EXCLUDE category/department/shop links
                        if '/category/' in href or '/department/' in href or '/shop/' in href:
                            continue
                        
                        # Check if link has an image inside AND price or meaningful text
                        has_img = len(link.find_elements(By.TAG_NAME, 'img')) > 0
                        has_text = link.text.strip() and len(link.text.strip()) > 5
                        has_price = bool(re.search(r'\$[\d,]+\.?\d*', link.text))
                        
                        # Must have image AND (text or price) to be a product
                        if has_img and (has_text or has_price) and 'heb.com' in href:
                            if link not in product_links:
                                product_links.append(link)
                    except:
                        continue
                
                if product_links:
                    # Add to existing list
                    for link in product_links:
                        link_id = id(link)
                        if link_id not in seen_element_ids:
                            seen_element_ids.add(link_id)
                            product_elements.append(link)
                    print(f"✓ Found additional product links (Total: {len(product_elements)})")
            except Exception as e:
                print(f"Error finding product links: {e}")
        
        # Last resort: Try finding elements with product-like structure (image + text)
        if len(product_elements) < 30:  # If we found less than 30, try this method
            print("Trying to find products by structure (image + text)...")
            try:
                # Find all elements that contain both an image and text
                all_elements = self.driver.find_elements(By.CSS_SELECTOR, "div, article, section, li")
                potential_products = []
                
                for elem in all_elements[:500]:  # Limit search
                    try:
                        # Check if element has product-like structure
                        has_img = len(elem.find_elements(By.TAG_NAME, 'img')) > 0
                        has_text = elem.text.strip() and len(elem.text.strip()) > 10
                        has_link = len(elem.find_elements(By.TAG_NAME, 'a')) > 0
                        has_price = bool(re.search(r'\$[\d,]+\.?\d*', elem.text))
                        
                        # Check for category links - EXCLUDE them
                        href = None
                        if has_link:
                            try:
                                link_elem = elem.find_element(By.TAG_NAME, 'a')
                                href = link_elem.get_attribute('href') or ''
                            except:
                                pass
                        
                        # Skip if it's a category link
                        if href and ('/category/' in href or '/department/' in href or '/shop/' in href):
                            continue
                        
                        # Element should have image + (text or price) + link
                        if has_img and (has_text or has_price) and has_link:
                            # Check element size (should be reasonable)
                            size = elem.size
                            if size['width'] > 100 and size['height'] > 100:
                                potential_products.append(elem)
                    except:
                        continue
                
                if potential_products:
                    # Add to existing list
                    for elem in potential_products[:100]:  # Limit to 100
                        elem_id = id(elem)
                        if elem_id not in seen_element_ids:
                            seen_element_ids.add(elem_id)
                            product_elements.append(elem)
                    print(f"✓ Found additional products by structure (Total: {len(product_elements)})")
            except Exception as e:
                print(f"Error in structure search: {e}")
        
        # Final cleanup: Remove duplicates one more time
        if product_elements:
            unique_elements = []
            seen = set()
            for elem in product_elements:
                elem_id = id(elem)
                if elem_id not in seen:
                    seen.add(elem_id)
                    unique_elements.append(elem)
            product_elements = unique_elements
        
        # Last resort: Try JavaScript to find products (only if we found very few)
        if len(product_elements) < 20:
            print("Trying JavaScript method to find products...")
            try:
                # Execute JavaScript to find product-like elements
                js_code = """
                var products = [];
                var allDivs = document.querySelectorAll('div, article, li, a');
                for (var i = 0; i < allDivs.length; i++) {
                    var elem = allDivs[i];
                    var hasImg = elem.querySelector('img') !== null;
                    var hasText = elem.innerText && elem.innerText.trim().length > 10;
                    var hasLink = elem.tagName === 'A' || elem.querySelector('a') !== null;
                    var hasPrice = elem.innerText && (elem.innerText.includes('$') || elem.innerText.match(/\\$[\\d,]+/));
                    
                    if ((hasImg && hasText && hasLink) || (hasPrice && hasText)) {
                        products.push(elem);
                        if (products.length >= 200) break;
                    }
                }
                return products.length;
                """
                product_count = self.driver.execute_script(js_code)
                if product_count > 0:
                    print(f"✓ Found {product_count} potential products using JavaScript")
                    # Get the actual elements and add to existing list
                    js_elements = self.driver.find_elements(By.CSS_SELECTOR, "div, article, li, a")
                    for elem in js_elements[:200]:  # Limit to 200
                        elem_id = id(elem)
                        if elem_id not in seen_element_ids:
                            # Quick validation
                            try:
                                has_img = len(elem.find_elements(By.TAG_NAME, 'img')) > 0
                                has_text = elem.text.strip() and len(elem.text.strip()) > 5
                                if has_img and has_text:
                                    seen_element_ids.add(elem_id)
                                    product_elements.append(elem)
                            except:
                                pass
                    print(f"✓ Added JavaScript-found products (Total: {len(product_elements)})")
            except Exception as e:
                print(f"Error in JavaScript search: {e}")
        
        if not product_elements:
            print("\n⚠ Warning: No products found on the page.")
            print("Page title:", self.driver.title)
            print("Current URL:", self.driver.current_url)
            print("\nDebugging info:")
            try:
                # Print some page stats
                body_text = self.driver.find_element(By.TAG_NAME, "body").text[:500]
                print(f"Body text preview: {body_text}...")
                print(f"Page source length: {len(self.driver.page_source)}")
                
                # Try to find any images
                images = self.driver.find_elements(By.TAG_NAME, "img")
                print(f"Found {len(images)} images on page")
                
                # Try to find any links
                links = self.driver.find_elements(By.TAG_NAME, "a")
                print(f"Found {len(links)} links on page")
                
                # Check for common product indicators in page source
                page_source = self.driver.page_source
                if 'product' in page_source.lower():
                    print("Page contains 'product' keyword")
                if '/product/' in page_source or '/p/' in page_source:
                    print("Page contains product URLs")
                    
            except:
                pass
            return products
        else:
            print(f"\n✓ Successfully found {len(product_elements)} product elements to extract data from")
        
        # Extract information from each product
        product_limit = product_elements if max_products is None else product_elements[:max_products]
        
        print(f"\nExtracting data from {len(product_limit)} products...")
        for idx, element in enumerate(product_limit):
            try:
                product_data = self.extract_product_data(element, idx)
                
                # Only add products that have at least title OR price OR image (not just link)
                # Also exclude category links
                product_url = product_data.get('product_hyperlink', '')
                is_category = product_url and ('/category/' in product_url or '/department/' in product_url or '/shop/' in product_url)
                
                has_essential_data = (product_data.get('product_title') or 
                                     product_data.get('product_price') or 
                                     product_data.get('product_image'))
                
                if product_data and has_essential_data and not is_category:
                    # Check for duplicates using hyperlink or product_title
                    product_title = product_data.get('product_title', '')
                    
                    # Use hyperlink as primary key, fallback to title
                    unique_key = product_url if product_url else product_title
                    
                    if unique_key and unique_key not in self.seen_urls:
                        self.seen_urls.add(unique_key)
                        products.append(product_data)
                        if (idx + 1) % 20 == 0:
                            print(f"  Processed {idx + 1}/{len(product_limit)} products...")
                elif idx < 5:
                    reason = "category link" if is_category else "no essential data"
                    print(f"  Product {idx + 1} skipped - {reason}")
                
            except Exception as e:
                if idx < 5:  # Only print first few errors
                    print(f"Error extracting product {idx + 1}: {e}")
                continue
        
        return products
    
    def extract_product_data(self, element, index):
        """Extract data from a single product element - ROBUST VERSION"""
        product = {
            'product_title': None,
            'product_price': None,
            'product_image': None,
            'product_hyperlink': None
        }
        
        try:
            # Get element's HTML and text for debugging
            element_html = element.get_attribute('outerHTML')[:200] if index < 3 else ""
            element_text = element.text.strip()[:100] if index < 3 else ""
            
            # ========== EXTRACT HYPERLINK ==========
            # Strategy 1: Element itself is a link
            if element.tag_name.lower() == 'a':
                href = element.get_attribute('href')
                if href and href.strip():
                    if not href.startswith('http'):
                        href = self.base_url + href if href.startswith('/') else f"{self.base_url}/{href}"
                    if 'heb.com' in href:
                        product['product_hyperlink'] = href
            
            # Strategy 2: Find link inside element (try multiple methods)
            if not product['product_hyperlink']:
                # Try direct child link
                try:
                    link_elem = element.find_element(By.TAG_NAME, 'a')
                    href = link_elem.get_attribute('href')
                    if href and href.strip():
                        if not href.startswith('http'):
                            href = self.base_url + href if href.startswith('/') else f"{self.base_url}/{href}"
                        if 'heb.com' in href:
                            product['product_hyperlink'] = href
                except:
                    pass
            
            # Strategy 3: Find any link in element (broader search)
            if not product['product_hyperlink']:
                try:
                    links = element.find_elements(By.TAG_NAME, 'a')
                    for link in links:
                        href = link.get_attribute('href')
                        if href and href.strip() and 'heb.com' in href:
                            if not href.startswith('http'):
                                href = self.base_url + href if href.startswith('/') else f"{self.base_url}/{href}"
                            product['product_hyperlink'] = href
                            break
                except:
                    pass
            
            # Strategy 4: Extract from onclick or data attributes
            if not product['product_hyperlink']:
                try:
                    onclick = element.get_attribute('onclick') or ''
                    href_match = re.search(r'["\']([^"\']*heb\.com[^"\']*)["\']', onclick)
                    if href_match:
                        product['product_hyperlink'] = href_match.group(1)
                except:
                    pass
            
            # ========== EXTRACT TITLE ==========
            # Strategy 1: Try specific title selectors (more comprehensive)
            title_selectors = [
                "h1", "h2", "h3", "h4", "h5", "h6",
                "[data-testid*='title' i]",
                "[data-testid*='name' i]",
                "[data-testid*='Title' i]",
                "[data-testid*='Name' i]",
                "[aria-label]",
                ".product-title",
                ".product-name",
                "[class*='title' i]",
                "[class*='name' i]",
                "[class*='Title' i]",
                "[class*='Name' i]",
                "span[class*='title' i]",
                "span[class*='name' i]",
                "div[class*='title' i]",
                "div[class*='name' i]",
                "a[class*='title' i]",
                "a[class*='name' i]",
                "p[class*='title' i]",
                "p[class*='name' i]",
                # Try finding text nodes that look like titles
                "*[class*='heading' i]",
                "*[class*='label' i]",
            ]
            
            for selector in title_selectors:
                try:
                    title_elems = element.find_elements(By.CSS_SELECTOR, selector)
                    for title_elem in title_elems:
                        title = title_elem.text.strip()
                        if title and 5 <= len(title) <= 200:  # Valid title length
                            # Skip if it's clearly not a title
                            if (not re.match(r'^\$[\d,]+\.?\d*$', title) and 
                                'price' not in title.lower() and 
                                'add to cart' not in title.lower() and
                                'buy now' not in title.lower() and
                                'view' not in title.lower() and
                                'shop' not in title.lower() and
                                'category' not in title.lower()):
                                product['product_title'] = title[:150]
                                break
                    if product['product_title']:
                        break
                except:
                    continue
            
            # Strategy 2: Extract from element's text (get first meaningful line)
            if not product['product_title']:
                try:
                    all_text = element.text.strip()
                    if all_text:
                        lines = [line.strip() for line in all_text.split('\n') if line.strip()]
                        for line in lines:
                            # Skip prices, buttons, metadata - but be more lenient
                            if (5 <= len(line) <= 200 and 
                                not re.match(r'^\$[\d,]+\.?\d*', line) and 
                                'price' not in line.lower() and
                                'add to cart' not in line.lower() and
                                'buy now' not in line.lower() and
                                'view details' not in line.lower() and
                                'shop now' not in line.lower() and
                                'learn more' not in line.lower() and
                                len(line.split()) >= 2):  # At least 2 words
                                product['product_title'] = line[:150]
                                break
                except:
                    pass
            
            # Strategy 2b: Try getting text from link if element is a link
            if not product['product_title'] and element.tag_name.lower() == 'a':
                try:
                    link_text = element.text.strip()
                    if link_text and 5 <= len(link_text) <= 200 and not re.match(r'^\$[\d,]+\.?\d*$', link_text):
                        product['product_title'] = link_text[:150]
                except:
                    pass
            
            # Strategy 3: Extract from aria-label
            if not product['product_title']:
                try:
                    aria_label = element.get_attribute('aria-label')
                    if aria_label and 5 <= len(aria_label) <= 200:
                        product['product_title'] = aria_label[:150]
                except:
                    pass
            
            # Strategy 4: Extract from title attribute
            if not product['product_title']:
                try:
                    title_attr = element.get_attribute('title')
                    if title_attr and 5 <= len(title_attr) <= 200:
                        product['product_title'] = title_attr[:150]
                except:
                    pass
            
            # ========== EXTRACT PRICE ==========
            # Strategy 1: Try specific price selectors (more comprehensive)
            price_selectors = [
                "[data-testid*='price' i]",
                "[data-testid*='Price' i]",
                ".price",
                "[class*='price' i]",
                "[class*='Price' i]",
                "span[class*='price' i]",
                "div[class*='price' i]",
                "p[class*='price' i]",
                "[aria-label*='price' i]",
                "[class*='cost' i]",
                "[class*='amount' i]",
                "[class*='value' i]",
            ]
            
            for selector in price_selectors:
                try:
                    price_elems = element.find_elements(By.CSS_SELECTOR, selector)
                    for price_elem in price_elems:
                        price_text = price_elem.text.strip()
                        if price_text:
                            # Look for price pattern - more flexible
                            price_match = re.search(r'\$[\d,]+\.?\d*', price_text)
                            if price_match:
                                product['product_price'] = price_match.group()
                                break
                    if product['product_price']:
                        break
                except:
                    continue
            
            # Strategy 2: Search in all text for price pattern (more aggressive)
            if not product['product_price']:
                try:
                    all_text = element.text
                    if all_text:
                        # Try multiple price patterns
                        price_patterns = [
                            r'\$[\d,]+\.?\d*',  # Standard: $12.99
                            r'\$\s*[\d,]+\.?\d*',  # With space: $ 12.99
                            r'[\d,]+\.?\d*\s*\$',  # Reversed: 12.99 $
                        ]
                        for pattern in price_patterns:
                            price_match = re.search(pattern, all_text)
                            if price_match:
                                product['product_price'] = price_match.group().strip()
                                break
                except:
                    pass
            
            # Strategy 3: Search in innerHTML
            if not product['product_price']:
                try:
                    inner_html = element.get_attribute('innerHTML')
                    if inner_html:
                        price_match = re.search(r'\$[\d,]+\.?\d*', inner_html)
                        if price_match:
                            product['product_price'] = price_match.group()
                except:
                    pass
            
            # Strategy 4: Look in child elements more thoroughly
            if not product['product_price']:
                try:
                    # Get all text from all child elements
                    all_children = element.find_elements(By.XPATH, ".//*")
                    for child in all_children:
                        child_text = child.text.strip()
                        if child_text:
                            price_match = re.search(r'\$[\d,]+\.?\d*', child_text)
                            if price_match:
                                product['product_price'] = price_match.group()
                                break
                except:
                    pass
            
            # ========== EXTRACT IMAGE ==========
            # Strategy 1: Find img tag directly (more comprehensive)
            try:
                img_elems = element.find_elements(By.TAG_NAME, 'img')
                for img_elem in img_elems:
                    # Try multiple attributes in order of preference
                    img_src = None
                    for attr in ['src', 'data-src', 'data-lazy-src', 'data-original', 'data-image', 'data-img', 'data-product-image']:
                        img_src = img_elem.get_attribute(attr)
                        if img_src and img_src.strip() and img_src != 'null' and img_src != 'undefined':
                            break
                    
                    if img_src and img_src.strip() and img_src != 'null' and img_src != 'undefined':
                        # Handle srcset
                        if ',' in str(img_src):
                            img_src = str(img_src).split(',')[0].strip().split(' ')[0]
                        
                        # Normalize URL
                        if not img_src.startswith('http'):
                            img_src = self.base_url + img_src if img_src.startswith('/') else f"{self.base_url}/{img_src}"
                        
                        # Skip placeholder images, logos, icons - but be less strict
                        skip_keywords = ['placeholder', 'logo', 'icon', 'sprite', '1x1', 'blank']
                        if not any(keyword in img_src.lower() for keyword in skip_keywords):
                            product['product_image'] = img_src
                            break
            except:
                pass
            
            # Strategy 2: Find picture > img or source > img
            if not product['product_image']:
                try:
                    # Try picture > img
                    picture_imgs = element.find_elements(By.CSS_SELECTOR, 'picture img, picture source')
                    for img_elem in picture_imgs:
                        img_src = (img_elem.get_attribute('src') or 
                                  img_elem.get_attribute('data-src') or
                                  img_elem.get_attribute('srcset'))
                        if img_src and img_src.strip():
                            # Handle srcset
                            if ',' in str(img_src):
                                img_src = str(img_src).split(',')[0].strip().split(' ')[0]
                            if not img_src.startswith('http'):
                                img_src = self.base_url + img_src if img_src.startswith('/') else f"{self.base_url}/{img_src}"
                            if 'placeholder' not in img_src.lower() and 'logo' not in img_src.lower():
                                product['product_image'] = img_src
                                break
                except:
                    pass
            
            # Strategy 2b: Find all images in element and pick the largest/most relevant
            if not product['product_image']:
                try:
                    all_imgs = element.find_elements(By.CSS_SELECTOR, 'img, [style*="background-image"]')
                    best_img = None
                    best_size = 0
                    
                    for img_elem in all_imgs:
                        try:
                            if img_elem.tag_name == 'img':
                                img_src = (img_elem.get_attribute('src') or 
                                          img_elem.get_attribute('data-src') or
                                          img_elem.get_attribute('data-lazy-src'))
                                if img_src and img_src.strip():
                                    # Check image size (larger images are more likely to be product images)
                                    try:
                                        size = img_elem.size
                                        img_size = size['width'] * size['height']
                                        if img_size > best_size and 'placeholder' not in img_src.lower():
                                            best_size = img_size
                                            best_img = img_src
                                    except:
                                        if not best_img:
                                            best_img = img_src
                        except:
                            continue
                    
                    if best_img:
                        if not best_img.startswith('http'):
                            best_img = self.base_url + best_img if best_img.startswith('/') else f"{self.base_url}/{best_img}"
                        product['product_image'] = best_img
                except:
                    pass
            
            # Strategy 3: Find background-image in style
            if not product['product_image']:
                try:
                    style = element.get_attribute('style') or ''
                    bg_match = re.search(r'url\(["\']?([^"\']+)["\']?\)', style)
                    if bg_match:
                        img_src = bg_match.group(1)
                        if not img_src.startswith('http'):
                            img_src = self.base_url + img_src if img_src.startswith('/') else f"{self.base_url}/{img_src}"
                        product['product_image'] = img_src
                except:
                    pass
            
            # Debug output for first few products
            if index < 3:
                print(f"\n  Product {index + 1} extraction:")
                print(f"    Title: {product['product_title'] or 'NOT FOUND'}")
                print(f"    Price: {product['product_price'] or 'NOT FOUND'}")
                print(f"    Image: {'FOUND' if product['product_image'] else 'NOT FOUND'}")
                print(f"    Link: {product['product_hyperlink'] or 'NOT FOUND'}")
        
        except Exception as e:
            if index < 3:  # Only print first few errors
                print(f"Error in extract_product_data for product {index + 1}: {e}")
                import traceback
                traceback.print_exc()
        
        return product
    
    def save_to_json(self, filename=None):
        """Save scraped products to JSON file"""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"heb_products_{timestamp}.json"
        
        filepath = os.path.join(os.path.dirname(__file__), filename)
        
        output_data = {
            'scrape_date': datetime.now().isoformat(),
            'total_products': len(self.products),
            'products': self.products
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)
        
        print(f"Data saved to {filepath}")
        return filepath
    
    def save_to_csv(self, filename=None):
        """Save scraped products to CSV file with tabular columns (Excel-friendly)."""
        if not self.products:
            print("No products to save")
            return None
        
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"heb_products_{timestamp}.csv"
        
        filepath = os.path.join(os.path.dirname(__file__), filename)
        
        fieldnames = ['product_title', 'product_price', 'product_image', 'product_hyperlink']
        
        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(self.products)
        
        print(f"Data saved to {filepath}")
        return filepath

    def save_to_excel(self, filename=None):
        """Save scraped products to an Excel file (tabular columns)."""
        if not self.products:
            print("No products to save")
            return None
        
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"heb_products_{timestamp}.xlsx"
        
        filepath = os.path.join(os.path.dirname(__file__), filename)
        
        try:
            import pandas as pd
        except ImportError:
            print("pandas is not installed; cannot create Excel file. Skipping Excel export.")
            return None
        
        try:
            df = pd.DataFrame(self.products)
            df.to_excel(filepath, index=False)
            print(f"Data saved to {filepath}")
            return filepath
        except Exception as e:
            print(f"Error saving Excel file: {e}")
            return None
    
    def close(self):
        """Close the WebDriver"""
        if hasattr(self, 'driver'):
            self.driver.quit()
            print("WebDriver closed")


def main():
    """Main function to run the scraper - Scrapes products from HEB.com homepage"""
    scraper = None
    
    try:
        print("=" * 60)
        print("HEB.com HOMEPAGE SCRAPER")
        print("Scraping products from the homepage only")
        print("=" * 60)
        
        # Initialize scraper
        scraper = HEBScraper(headless=False)  # Set to True for headless mode
        
        # Scrape products from homepage
        products = scraper.scrape_homepage()
        
        # Display summary
        print(f"\n{'=' * 60}")
        print(f"SCRAPING SUMMARY")
        print(f"{'=' * 60}")
        print(f"Total unique products scraped: {len(products)}")
        
        # Show extraction statistics
        if products:
            titles_count = sum(1 for p in products if p.get('product_title'))
            prices_count = sum(1 for p in products if p.get('product_price'))
            images_count = sum(1 for p in products if p.get('product_image'))
            links_count = sum(1 for p in products if p.get('product_hyperlink'))
            
            print(f"\nExtraction Statistics:")
            print(f"  Product Titles: {titles_count}/{len(products)} ({titles_count*100//len(products) if products else 0}%)")
            print(f"  Prices: {prices_count}/{len(products)} ({prices_count*100//len(products) if products else 0}%)")
            print(f"  Images: {images_count}/{len(products)} ({images_count*100//len(products) if products else 0}%)")
            print(f"  Hyperlinks: {links_count}/{len(products)} ({links_count*100//len(products) if products else 0}%)")
        
        print(f"{'=' * 60}\n")
        
        # Show first few products as preview
        if products:
            print("Sample products (first 5):")
            print("-" * 60)
            for i, product in enumerate(products[:5], 1):
                print(f"\nProduct {i}:")
                print(f"  Product Title: {product.get('product_title', 'N/A')}")
                print(f"  Price: {product.get('product_price', 'N/A')}")
                img = product.get('product_image', 'N/A')
                print(f"  Image: {img[:70] + '...' if len(str(img)) > 70 else img}")
                link = product.get('product_hyperlink', 'N/A')
                print(f"  Hyperlink: {link[:70] + '...' if len(str(link)) > 70 else link}")
            
            if len(products) > 5:
                print(f"\n... and {len(products) - 5} more products")
        
        # Save to files
        if products:
            print(f"\n{'=' * 60}")
            print("Saving data to files...")
            print(f"{'=' * 60}")
            csv_file = scraper.save_to_csv()
            excel_file = scraper.save_to_excel()
            print(f"\n✓ Data saved successfully!")
            print(f"  CSV: {csv_file}")
            if excel_file:
                print(f"  Excel: {excel_file}")
            print(f"\nTotal products in files: {len(products)}")
        else:
            print("\n⚠ No products found. The site structure may have changed or the page loaded differently.")
            print("Check debug_page_source.html for the actual page structure.")
            print("You may need to adjust the CSS selectors in the code.")
    
    except KeyboardInterrupt:
        print("\n\n⚠ Scraping interrupted by user")
        if scraper and scraper.products:
            print(f"\nSaving {len(scraper.products)} products scraped so far...")
            try:
                scraper.save_to_csv()
                scraper.save_to_excel()
                print("✓ Partial data saved successfully!")
            except:
                pass
    
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        if scraper and scraper.products:
            print(f"\nSaving {len(scraper.products)} products scraped so far...")
            try:
                scraper.save_to_csv()
                scraper.save_to_excel()
                print("✓ Partial data saved successfully!")
            except:
                pass
    
    finally:
        if scraper:
            scraper.close()


if __name__ == "__main__":
    main()