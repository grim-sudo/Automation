"""
Web automation plugin using Selenium
"""

from typing import Dict, Any, List
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from omni_automator.core.plugin_manager import AutomationPlugin

try:
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.chrome.options import Options
    HAS_SELENIUM = True
except ImportError:
    HAS_SELENIUM = False


class WebAutomationPlugin(AutomationPlugin):
    """Plugin for web browser automation"""
    
    def __init__(self):
        self.driver = None
        self.wait = None
    
    @property
    def name(self) -> str:
        return "web_automation"
    
    @property
    def description(self) -> str:
        return "Web browser automation using Selenium"
    
    @property
    def version(self) -> str:
        return "1.0.0"
    
    def get_capabilities(self) -> List[str]:
        if not HAS_SELENIUM:
            return []
        
        return [
            'open_browser',
            'navigate_to',
            'click_element',
            'type_text',
            'get_text',
            'take_screenshot',
            'close_browser',
            'find_element',
            'wait_for_element'
        ]
    
    def initialize(self) -> bool:
        """Initialize the web automation plugin"""
        if not HAS_SELENIUM:
            print("Selenium not available. Install with: pip install selenium")
            return False
        return True
    
    def execute(self, action: str, params: Dict[str, Any]) -> Any:
        """Execute web automation action"""
        if action == 'open_browser':
            return self._open_browser(params.get('browser', 'chrome'), params.get('headless', False))
        elif action == 'navigate_to':
            return self._navigate_to(params.get('url'))
        elif action == 'click_element':
            return self._click_element(params.get('selector'), params.get('by', 'css'))
        elif action == 'type_text':
            return self._type_text(params.get('selector'), params.get('text'), params.get('by', 'css'))
        elif action == 'get_text':
            return self._get_text(params.get('selector'), params.get('by', 'css'))
        elif action == 'take_screenshot':
            return self._take_screenshot(params.get('filename'))
        elif action == 'close_browser':
            return self._close_browser()
        elif action == 'find_element':
            return self._find_element(params.get('selector'), params.get('by', 'css'))
        elif action == 'wait_for_element':
            return self._wait_for_element(params.get('selector'), params.get('by', 'css'), params.get('timeout', 10))
        else:
            raise ValueError(f"Unknown web automation action: {action}")
    
    def _open_browser(self, browser: str = 'chrome', headless: bool = False) -> bool:
        """Open a web browser"""
        try:
            if browser.lower() == 'chrome':
                options = Options()
                if headless:
                    options.add_argument('--headless')
                options.add_argument('--no-sandbox')
                options.add_argument('--disable-dev-shm-usage')
                self.driver = webdriver.Chrome(options=options)
            elif browser.lower() == 'firefox':
                from selenium.webdriver.firefox.options import Options as FirefoxOptions
                options = FirefoxOptions()
                if headless:
                    options.add_argument('--headless')
                self.driver = webdriver.Firefox(options=options)
            else:
                raise ValueError(f"Unsupported browser: {browser}")
            
            self.wait = WebDriverWait(self.driver, 10)
            return True
            
        except Exception as e:
            raise Exception(f"Failed to open browser: {e}")
    
    def _navigate_to(self, url: str) -> bool:
        """Navigate to a URL"""
        if not self.driver:
            raise Exception("Browser not open")
        
        try:
            self.driver.get(url)
            return True
        except Exception as e:
            raise Exception(f"Failed to navigate to {url}: {e}")
    
    def _click_element(self, selector: str, by: str = 'css') -> bool:
        """Click an element"""
        if not self.driver:
            raise Exception("Browser not open")
        
        try:
            element = self._find_element(selector, by)
            element.click()
            return True
        except Exception as e:
            raise Exception(f"Failed to click element: {e}")
    
    def _type_text(self, selector: str, text: str, by: str = 'css') -> bool:
        """Type text into an element"""
        if not self.driver:
            raise Exception("Browser not open")
        
        try:
            element = self._find_element(selector, by)
            element.clear()
            element.send_keys(text)
            return True
        except Exception as e:
            raise Exception(f"Failed to type text: {e}")
    
    def _get_text(self, selector: str, by: str = 'css') -> str:
        """Get text from an element"""
        if not self.driver:
            raise Exception("Browser not open")
        
        try:
            element = self._find_element(selector, by)
            return element.text
        except Exception as e:
            raise Exception(f"Failed to get text: {e}")
    
    def _take_screenshot(self, filename: str = None) -> str:
        """Take a screenshot"""
        if not self.driver:
            raise Exception("Browser not open")
        
        try:
            if not filename:
                import time
                filename = f"web_screenshot_{int(time.time())}.png"
            
            self.driver.save_screenshot(filename)
            return filename
        except Exception as e:
            raise Exception(f"Failed to take screenshot: {e}")
    
    def _find_element(self, selector: str, by: str = 'css'):
        """Find an element"""
        if not self.driver:
            raise Exception("Browser not open")
        
        by_mapping = {
            'css': By.CSS_SELECTOR,
            'xpath': By.XPATH,
            'id': By.ID,
            'name': By.NAME,
            'class': By.CLASS_NAME,
            'tag': By.TAG_NAME
        }
        
        by_method = by_mapping.get(by.lower(), By.CSS_SELECTOR)
        
        try:
            return self.driver.find_element(by_method, selector)
        except Exception as e:
            raise Exception(f"Element not found: {selector}")
    
    def _wait_for_element(self, selector: str, by: str = 'css', timeout: int = 10) -> bool:
        """Wait for an element to be present"""
        if not self.driver:
            raise Exception("Browser not open")
        
        by_mapping = {
            'css': By.CSS_SELECTOR,
            'xpath': By.XPATH,
            'id': By.ID,
            'name': By.NAME,
            'class': By.CLASS_NAME,
            'tag': By.TAG_NAME
        }
        
        by_method = by_mapping.get(by.lower(), By.CSS_SELECTOR)
        
        try:
            wait = WebDriverWait(self.driver, timeout)
            wait.until(EC.presence_of_element_located((by_method, selector)))
            return True
        except Exception as e:
            raise Exception(f"Element not found within {timeout} seconds: {selector}")
    
    def _close_browser(self) -> bool:
        """Close the browser"""
        if self.driver:
            try:
                self.driver.quit()
                self.driver = None
                self.wait = None
                return True
            except Exception as e:
                raise Exception(f"Failed to close browser: {e}")
        return True
    
    def cleanup(self):
        """Cleanup plugin resources"""
        self._close_browser()
