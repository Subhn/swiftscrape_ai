# scrape_advanced.py (OPTIMIZED VERSION)
"""
Advanced scraping utilities - optimized for speed
"""

import time
import re
from urllib.parse import urljoin, urlparse
from collections import deque
from bs4 import BeautifulSoup

try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    
    try:
        from webdriver_manager.chrome import ChromeDriverManager
        WM_AVAILABLE = True
    except ImportError:
        ChromeDriverManager = None
        WM_AVAILABLE = False
except ImportError:
    webdriver = None
    Options = None
    Service = None
    WM_AVAILABLE = False

DEFAULT_PAGE_LOAD_TIMEOUT = 20
DEFAULT_SLEEP_BETWEEN_REQUESTS = 0.5  # Reduced for speed


def get_driver(headless=True, disable_images=True):
    """Return a Selenium Chrome driver."""
    if webdriver is None:
        # FIX: Added missing dependency beautifulsoup4 to error message
        raise RuntimeError("Selenium not installed. Run: pip install selenium webdriver-manager beautifulsoup4")
        
    chrome_options = Options()
    if headless:
        chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
    
    if disable_images:
        prefs = {
            "profile.managed_default_content_settings.images": 2,
            "profile.default_content_setting_values.notifications": 2
        }
        chrome_options.add_experimental_option("prefs", prefs)

    chrome_options.add_experimental_option('excludeSwitches', ['enable-logging'])

    try:
        if WM_AVAILABLE and ChromeDriverManager is not None:
            service = Service(ChromeDriverManager().install())
            return webdriver.Chrome(service=service, options=chrome_options)
        else:
            return webdriver.Chrome(options=chrome_options)
    except Exception as e:
        raise RuntimeError(f"Failed to create Chrome driver: {e}")


def extract_body_content(html_content):
    """Extract body content from HTML."""
    soup = BeautifulSoup(html_content, "html.parser")
    body = soup.body or soup
    return str(body)


def clean_body_content(body_content):
    """Clean and extract text from HTML body."""
    soup = BeautifulSoup(body_content, "html.parser")
    
    for tag in soup(["script", "style", "noscript", "iframe", "header", "footer", "nav", "aside"]):
        tag.decompose()
    
    text = soup.get_text(separator="\n")
    lines = [line.strip() for line in text.splitlines()]
    lines = [l for l in lines if l and len(l) > 3]
    
    cleaned = "\n".join(lines)
    cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)
    
    return cleaned


def is_valid_url(url):
    """Check if URL is valid for scraping."""
    if not url:
        return False
    if not url.startswith("http"):
        return False
    
    skip_extensions = r"\.(pdf|jpg|jpeg|png|gif|svg|ico|webp|mp4|mp3|zip|exe|dmg|docx?|xls|pptx?|css|js)($|\?)"
    if re.search(skip_extensions, url, re.IGNORECASE):
        return False
    
    skip_paths = ['login', 'signup', 'register', 'cart', 'checkout', 'admin']
    parsed = urlparse(url)
    if any(path in parsed.path.lower() for path in skip_paths):
        return False
    
    return True


def scrape_page(url, driver=None, timeout=DEFAULT_PAGE_LOAD_TIMEOUT):
    """Return page HTML for a single URL."""
    local_driver = driver
    created = False
    
    try:
        if local_driver is None:
            local_driver = get_driver(headless=True)
            created = True
        
        local_driver.set_page_load_timeout(timeout)
        local_driver.get(url)
        
        try:
            WebDriverWait(local_driver, 3).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
        except:
            pass
        
        time.sleep(0.8)  # Reduced wait time
        html = local_driver.page_source
        return html
        
    except Exception as e:
        print(f"❌ Error scraping {url}: {e}")
        return ""
        
    finally:
        if created and local_driver:
            try:
                local_driver.quit()
            except:
                pass


def scrape_website_recursive(
    start_url, 
    max_pages=2,  # Reduced default for speed
    same_domain=True, 
    polite_delay=DEFAULT_SLEEP_BETWEEN_REQUESTS
):
    """
    Crawl start_url up to max_pages (BFS). Returns dict: {url: cleaned_text}
    """
    start_url = start_url.rstrip("/")
    domain = urlparse(start_url).netloc
    visited = set()
    results = {}
    queue = deque([start_url])
    driver = None

    try:
        driver = get_driver(headless=True)
        print(f"✅ Chrome driver initialized")
    except Exception as e:
        print(f"⚠️ Could not create driver: {e}")
        return {}

    try:
        while queue and len(visited) < max_pages:
            current = queue.popleft()
            
            if current in visited:
                continue
            
            if same_domain and urlparse(current).netloc != domain:
                continue

            print(f"🔍 Scraping: {current} ({len(visited)+1}/{max_pages})")
            
            html = scrape_page(current, driver=driver)
            if not html or len(html) < 500:
                visited.add(current)
                continue

            body = extract_body_content(html)
            cleaned = clean_body_content(body)
            
            if cleaned and len(cleaned) > 200:
                results[current] = cleaned
                print(f"  ✅ Extracted {len(cleaned)} characters")
            else:
                print(f"  ⚠️ Minimal content, skipping")
            
            visited.add(current)

            soup = BeautifulSoup(html, "html.parser")
            for a in soup.find_all("a", href=True):
                full = urljoin(current, a["href"])
                full = full.split("#")[0].rstrip("/")
                
                if full not in visited and is_valid_url(full):
                    if same_domain and urlparse(full).netloc == domain:
                        queue.append(full)

            time.sleep(polite_delay)
            
    except KeyboardInterrupt:
        print("\n⚠️ Scraping interrupted")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        
    finally:
        if driver:
            try:
                driver.quit()
                print("✅ Driver closed")
            except:
                pass

    print(f"\n📊 Scraping complete: {len(results)} pages scraped")
    return results


def split_dom_content(dom_content, max_length=3000, overlap=500):
    """
    Split large text into chunks - OPTIMIZED for faster processing.
    Smaller chunks = faster API calls.
    """
    if not dom_content:
        return []
    
    dom_content = dom_content.strip()
    
    if len(dom_content) <= max_length:
        return [dom_content]
    
    chunks = []
    start = 0
    n = len(dom_content)
    
    while start < n:
        end = min(start + max_length, n)
        
        if end < n:
            newline_pos = dom_content.rfind('\n', start, end)
            if newline_pos > start + (max_length // 2):
                end = newline_pos
        
        chunks.append(dom_content[start:end])
        
        if end < n:
            start = max(end - overlap, start + max_length // 2)
        else:
            break
    
    print(f"📄 Split into {len(chunks)} chunks")
    return chunks