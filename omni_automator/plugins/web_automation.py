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
try:
    # webdriver-manager for automatic driver resolution
    from webdriver_manager.chrome import ChromeDriverManager
    from webdriver_manager.firefox import GeckoDriverManager
    from selenium.webdriver.chrome.service import Service as ChromeService
    from selenium.webdriver.firefox.service import Service as FirefoxService
    HAS_WDM = True
except Exception:
    HAS_WDM = False
try:
    from playwright.sync_api import sync_playwright
    HAS_PLAYWRIGHT = True
except Exception:
    HAS_PLAYWRIGHT = False


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
        # Include canonical capability names plus common parser-emitted aliases
        return [
            'open_browser', 'launch_headless_browser', 'open_headless', 'open_browser',
            'navigate_to', 'navigate_to_url', 'goto', 'navigate',
            'click_element', 'click', 'click_selector',
            'type_text', 'type', 'enter_text',
            'get_text', 'read_text',
            'take_screenshot', 'screenshot', 'save_screenshot',
            'close_browser', 'close', 'quit_browser',
            'find_element', 'find',
            'wait_for_element', 'wait'
        ]
    
    def initialize(self) -> bool:
        """Initialize the web automation plugin"""
        if not HAS_SELENIUM:
            print("Selenium not available. Install with: pip install selenium")
            return False
        return True
    
    def execute(self, action: str, params: Dict[str, Any]) -> Any:
        """Execute web automation action"""
        # Support canonical actions and parser-emitted alias names so the parser
        # can emit GUI-like verbs that map to plugin capabilities.
        # Aliases commonly emitted by the parser: launch_headless_browser, navigate_to_url,
        # take_screenshot, close_browser, click, type, etc.
        try:
            if action in ('open_browser', 'launch_headless_browser', 'open_headless'):
                # If alias indicates headless, prefer headless True
                headless = params.get('headless', False) or (action == 'launch_headless_browser' or action == 'open_headless')
                return self._open_browser(params.get('browser', 'chrome'), headless)
            elif action in ('navigate_to', 'navigate_to_url', 'goto', 'navigate'):
                url = params.get('url') or params.get('target') or params.get('location')
                return self._navigate_to(url)
            elif action in ('click_element', 'click', 'click_selector'):
                return self._click_element(params.get('selector'), params.get('by', 'css'))
            elif action in ('type_text', 'type', 'enter_text'):
                return self._type_text(params.get('selector'), params.get('text') or params.get('value', ''), params.get('by', 'css'))
            elif action in ('get_text', 'read_text'):
                return self._get_text(params.get('selector'), params.get('by', 'css'))
            elif action in ('take_screenshot', 'screenshot', 'save_screenshot'):
                # pass full params to allow fallbacks that use workflow_context or url
                return self._take_screenshot(params)
            elif action in ('close_browser', 'close', 'quit_browser'):
                return self._close_browser()
            elif action in ('find_element', 'find'):
                return self._find_element(params.get('selector'), params.get('by', 'css'))
            elif action in ('wait_for_element', 'wait'):
                return self._wait_for_element(params.get('selector'), params.get('by', 'css'), params.get('timeout', 10))
            else:
                raise ValueError(f"Unknown web automation action: {action}")
        except Exception:
            # Re-raise to keep original behavior but allow caller to handle mapping errors
            raise
    
    def _open_browser(self, browser: str = 'chrome', headless: bool = False) -> bool:
        """Open a web browser"""
        import platform
        try:
            plat = platform.system().lower()
            # Enforce environment policy: only allow headless on Linux
            if headless and plat.startswith('win'):
                # Convert to non-headless on Windows to maintain behavior
                headless = False

            if browser.lower() == 'chrome':
                options = Options()
                if headless:
                    options.add_argument('--headless')
                options.add_argument('--no-sandbox')
                options.add_argument('--disable-dev-shm-usage')
                try:
                    if HAS_WDM:
                        service = ChromeService(ChromeDriverManager().install())
                        self.driver = webdriver.Chrome(service=service, options=options)
                    else:
                        self.driver = webdriver.Chrome(options=options)
                except Exception as e:
                    return {'success': False, 'error': f'Failed to start Chrome WebDriver: {e}'}
            elif browser.lower() == 'firefox':
                from selenium.webdriver.firefox.options import Options as FirefoxOptions
                options = FirefoxOptions()
                if headless:
                    options.add_argument('--headless')
                try:
                    if HAS_WDM:
                        service = FirefoxService(GeckoDriverManager().install())
                        self.driver = webdriver.Firefox(service=service, options=options)
                    else:
                        self.driver = webdriver.Firefox(options=options)
                except Exception as e:
                    return {'success': False, 'error': f'Failed to start Firefox WebDriver: {e}'}
            else:
                return {'success': False, 'error': f'Unsupported browser: {browser}'}

            self.wait = WebDriverWait(self.driver, 10)
            return {'success': True, 'message': 'Browser opened', 'headless': headless}

        except Exception as e:
            return {'success': False, 'error': f'Failed to open browser: {e}'}
    
    def _navigate_to(self, url: str) -> bool:
        """Navigate to a URL"""
        if not self.driver:
            return {'success': False, 'error': 'Browser not open'}

        try:
            self.driver.get(url)
            # remember last navigated URL for potential screenshot fallbacks
            try:
                self.last_url = url
            except Exception:
                pass
            return {'success': True, 'url': url}
        except Exception as e:
            return {'success': False, 'error': f'Failed to navigate to {url}: {e}'}
    
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
    
    def _take_screenshot(self, params: Dict[str, Any]) -> Any:
        """Take a screenshot"""
        import time
        try:
            # Extract filename and context from many possible param keys
            workflow_ctx = params.get('workflow_context', {}) if isinstance(params, dict) else {}
            candidate_keys = ['filename', 'path', 'dest', 'destination', 'file', 'save_to', 'output', 'save_path', 'target']
            filename = None
            for k in candidate_keys:
                if isinstance(params, dict) and k in params and params.get(k):
                    filename = params.get(k)
                    break

            # Also accept nested targets in workflow_ctx
            if not filename and isinstance(workflow_ctx, dict):
                for k in candidate_keys:
                    if k in workflow_ctx and workflow_ctx.get(k):
                        filename = workflow_ctx.get(k)
                        break

            if filename:
                fn = str(filename)
                # Expand user (~) first
                fn = os.path.expanduser(fn)

                # Normalize separators
                norm = fn.replace('\\', '/').lstrip('/')

                # If Desktop appears anywhere in the path (case-insensitive), resolve to user's Desktop
                parts = norm.split('/')
                lower_parts = [p.lower() for p in parts]
                if 'desktop' in lower_parts:
                    idx = lower_parts.index('desktop')
                    # everything after 'Desktop' becomes subpath under the real Desktop
                    tail = parts[idx+1:]
                    home = os.path.expanduser('~')
                    if tail:
                        fn = os.path.join(home, 'Desktop', *tail)
                    else:
                        fn = os.path.join(home, 'Desktop')
                else:
                    # If relative, make absolute relative to cwd
                    if not os.path.isabs(fn):
                        fn = os.path.abspath(fn)

                filename = os.path.abspath(fn)
                parent = os.path.dirname(filename)
                if parent and not os.path.exists(parent):
                    os.makedirs(parent, exist_ok=True)
            else:
                filename = os.path.abspath(f"web_screenshot_{int(time.time())}.png")

            # Debug: expose resolved filename to logs
            try:
                import logging
                logging.getLogger(__name__).info(f"WebAutomation: resolved screenshot path: {filename}")
            except Exception:
                pass

            # If driver is available, use it
            if self.driver:
                try:
                    # If caller provided a URL, navigate there first to ensure content is loaded
                    url = params.get('url') or workflow_ctx.get('last_url') or getattr(self, 'last_url', None)
                    if url:
                        try:
                            # set a reasonable window size for screenshots
                            try:
                                self.driver.set_window_size(1366, 768)
                            except Exception:
                                pass
                            self.driver.get(url)
                            # wait until document.readyState == 'complete' or body present
                            try:
                                WebDriverWait(self.driver, 10).until(
                                    lambda d: d.execute_script('return document.readyState') == 'complete'
                                )
                            except Exception:
                                # fallback to waiting for body element
                                try:
                                    WebDriverWait(self.driver, 10).until(
                                        EC.presence_of_element_located((By.TAG_NAME, 'body'))
                                    )
                                except Exception:
                                    pass
                            # give rendering a moment
                            import time as _time
                            _time.sleep(0.5)
                        except Exception:
                            # continue to try saving even if navigation failed
                            pass

                    saved = False
                    try:
                        saved = self.driver.save_screenshot(filename)
                    except Exception:
                        saved = False

                    if saved:
                        return {'success': True, 'filename': filename}
                except Exception as e:
                    # continue to fallback
                    pass

            # Fallback: if no driver or screenshot failed, try saving page HTML
            url = params.get('url') or workflow_ctx.get('last_url') or getattr(self, 'last_url', None)
            if url:
                try:
                    import requests
                    resp = requests.get(url, timeout=10)
                    # If requested filename ends with .png, change to .html for fallback
                    out_path = filename
                    if out_path.lower().endswith('.png'):
                        out_path = out_path[:-4] + '.html'
                    parent2 = os.path.dirname(out_path)
                    if parent2 and not os.path.exists(parent2):
                        os.makedirs(parent2, exist_ok=True)
                    with open(out_path, 'w', encoding='utf-8') as f:
                        f.write(resp.text)
                    # Try to render HTML -> PNG using Playwright if available and PNG was requested
                    if HAS_PLAYWRIGHT:
                        try:
                            # determine desired png output
                            png_out = filename if filename.lower().endswith('.png') else (filename + '.png')
                            parent3 = os.path.dirname(png_out)
                            if parent3 and not os.path.exists(parent3):
                                os.makedirs(parent3, exist_ok=True)
                            with sync_playwright() as pw:
                                browser = pw.chromium.launch(headless=True)
                                page = browser.new_page(viewport={"width":1366,"height":768})
                                # open the saved HTML file directly
                                page.goto('file://' + os.path.abspath(out_path), wait_until='networkidle')
                                page.screenshot(path=png_out)
                                browser.close()
                            return {'success': True, 'filename': png_out, 'fallback': 'playwright_png'}
                        except Exception:
                            # If Playwright rendering fails, return saved HTML result
                            return {'success': True, 'filename': out_path, 'fallback': 'saved_html'}
                    return {'success': True, 'filename': out_path, 'fallback': 'saved_html'}
                except Exception as e:
                    return {'success': False, 'error': f'Fallback to HTML failed: {e}'}

            return {'success': False, 'error': 'No browser available and no URL to fallback to'}
        except Exception as e:
            return {'success': False, 'error': f'Failed to take screenshot: {e}'}
    
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
                return {'success': True, 'message': 'Browser closed'}
            except Exception as e:
                return {'success': False, 'error': f'Failed to close browser: {e}'}
        return {'success': True, 'message': 'No browser open'}
    
    def cleanup(self):
        """Cleanup plugin resources"""
        self._close_browser()
