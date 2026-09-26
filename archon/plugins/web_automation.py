"""
Web automation plugin using Selenium
"""

import contextlib
import os
import re
import sys
import time as time_module
from typing import Any

from loguru import logger

from archon.core.plugin_manager import AutomationPlugin

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from bs4 import BeautifulSoup

    HAS_BS4 = True
except ImportError:
    HAS_BS4 = False

try:
    import requests

    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.support.ui import WebDriverWait

    HAS_SELENIUM = True
except ImportError:
    HAS_SELENIUM = False
try:
    # webdriver-manager for automatic driver resolution
    from selenium.webdriver.chrome.service import Service as ChromeService
    from selenium.webdriver.firefox.service import Service as FirefoxService
    from webdriver_manager.chrome import ChromeDriverManager
    from webdriver_manager.firefox import GeckoDriverManager

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
        self._playwright_active = False
        self._pw = None
        self._pw_browser = None
        self._pw_context = None
        self._pw_page = None

    @property
    def name(self) -> str:
        return "web_automation"

    @property
    def description(self) -> str:
        return "Web browser automation using Selenium"

    @property
    def version(self) -> str:
        return "1.0.0"

    def get_capabilities(self) -> list[str]:
        if not HAS_SELENIUM:
            return []
        # Include canonical capability names plus common parser-emitted aliases
        return [
            "open_browser",
            "launch_headless_browser",
            "open_headless",
            "open_browser",
            "navigate_to",
            "navigate_to_url",
            "goto",
            "navigate",
            "click_element",
            "click",
            "click_selector",
            "type_text",
            "type",
            "enter_text",
            "press",
            "press_key",
            "press_enter",
            "press_keys",
            "get_text",
            "read_text",
            "take_screenshot",
            "screenshot",
            "save_screenshot",
            "close_browser",
            "close",
            "quit_browser",
            "find_element",
            "find",
            "wait_for_element",
            "wait",
            "wait_for_page_load",
            "perform_search",
            "search_web",
            "web_search",
            "scrape_website",
            "extract_data",
            "scrape_page",
            "get_page_content",
            "extract_text",
            "extract_links",
            "extract_images",
            "scrape_table",
            "extract_table_data",
            "get_article_content",
            "extract_article",
            "search_and_extract",
            "browse_and_scrape",
        ]

    def initialize(self) -> bool:
        """Initialize the web automation plugin"""
        if not HAS_SELENIUM:
            logger.warning("Selenium not available. Install with: pip install selenium")
            return False
        return True

    def execute(self, action: str, params: dict[str, Any]) -> Any:
        """Execute web automation action"""
        # Normalize plugin outputs: always return a dict with 'success' key.
        import logging

        logger = logging.getLogger(__name__)
        logger.info(f"web_automation.execute called: action={action}, params={params}")

        try:
            if action in ("open_browser", "launch_headless_browser", "open_headless"):
                headless = params.get("headless", False) or (
                    action == "launch_headless_browser" or action == "open_headless"
                )
                res = self._open_browser(params.get("browser", "chrome"), headless)
            # Accept any action that starts with 'navigate_to' as a navigation request
            elif action in (
                "navigate_to",
                "navigate_to_url",
                "goto",
                "navigate",
            ) or action.startswith("navigate_to"):
                # If parser requested 'navigate_to_search_engine' without a URL, open Google
                if action == "navigate_to_search_engine" and not (
                    params.get("url") or params.get("target") or params.get("location")
                ):
                    url = "https://www.google.com"
                else:
                    url = params.get("url") or params.get("target") or params.get("location")
                res = self._navigate_to(url)
            elif action in ("click_element", "click", "click_selector"):
                res = self._click_element(params.get("selector"), params.get("by", "css"))
            elif action in ("type_text", "type", "enter_text"):
                res = self._type_text(
                    params.get("selector"),
                    params.get("text") or params.get("value", ""),
                    params.get("by", "css"),
                )
            elif action in ("press", "press_key", "press_enter", "press_keys"):
                key = (
                    params.get("key")
                    or params.get("keys")
                    or ("ENTER" if action == "press_enter" else None)
                )
                res = self._press_key(params.get("selector"), key)
            elif action in ("get_text", "read_text"):
                res = self._get_text(params.get("selector"), params.get("by", "css"))
            elif action == "perform_search":
                # Perform a search: open browser if needed, navigate to search engine, type query, press enter
                query = (
                    params.get("query")
                    or params.get("q")
                    or params.get("text")
                    or params.get("value")
                )
                browser = params.get("browser") or params.get("which") or "default"
                # If caller requests the system (interactive) browser, open the search URL with the user's default browser
                use_system = (
                    params.get("use_system_browser")
                    if "use_system_browser" in params
                    else params.get("interactive", True)
                )
                try:
                    import webbrowser
                    from urllib.parse import quote_plus
                except Exception:
                    quote_plus = None
                    webbrowser = None

                search_engine = params.get("search_engine") or "https://www.google.com"
                # build search URL
                try:
                    if query:
                        # prefer search path if given
                        if search_engine.endswith("/"):
                            search_base = search_engine.rstrip("/")
                        else:
                            search_base = search_engine
                        # common search engines accept '/search?q='
                        search_url = (
                            f"{search_base}/search?q={quote_plus(query)}"
                            if quote_plus
                            else f"{search_base}/search?q={query}"
                        )
                    else:
                        search_url = search_engine
                except Exception:
                    search_url = search_engine

                if use_system and webbrowser:
                    try:
                        import logging
                        import platform

                        logging.getLogger(__name__).info(
                            f"perform_search: opening system browser url={search_url}"
                        )
                        # prefer opening a new tab/window
                        try:
                            opened = webbrowser.open_new_tab(search_url)
                        except Exception:
                            opened = webbrowser.open(search_url)

                        if not opened:
                            # On Windows, try os.startfile as a last resort
                            if platform.system().lower().startswith("win"):
                                try:
                                    os.startfile(search_url)
                                    return {
                                        "success": True,
                                        "message": "Opened system browser via startfile",
                                        "url": search_url,
                                    }
                                except Exception:
                                    pass

                        return {
                            "success": True,
                            "message": "Opened system browser",
                            "url": search_url,
                        }
                    except Exception:
                        # fall through to webdriver-based approach
                        pass
                # Open browser if not already open
                if not self.driver and not getattr(self, "_playwright_active", False):
                    import logging

                    logging.getLogger(__name__).info(
                        f"perform_search: attempting to open browser (requested={browser})"
                    )
                    ob = self._ensure_browser_open(
                        browser if browser and browser != "default" else "chrome",
                        params.get("headless", False),
                    )
                    if isinstance(ob, dict) and ob.get("success") is False:
                        return ob

                # Navigate to the search engine (or provided search_engine)
                nav = self._navigate_to(
                    search_url
                    if "search_url" in locals()
                    else (params.get("search_engine") or "https://www.google.com")
                )
                if isinstance(nav, dict) and nav.get("success") is False:
                    return nav

                # Type query into common search input and press enter
                try:
                    typed = self._type_text(
                        params.get("selector") or "input[name='q']",
                        query or "",
                        params.get("by", "css"),
                    )
                    if not typed:
                        return {"success": False, "error": "Failed to type search query"}
                except Exception as e:
                    return {"success": False, "error": f"Failed to type query: {e}"}

                try:
                    pressed = self._press_key(
                        params.get("selector") or "input[name='q']", params.get("key") or "Enter"
                    )
                    if not pressed:
                        return {"success": False, "error": "Failed to submit search"}
                except Exception as e:
                    return {"success": False, "error": f"Failed to submit search: {e}"}

                # Wait briefly for results
                with contextlib.suppress(Exception):
                    self._wait_for_element("h3", "css", timeout=10)

                return {"success": True, "message": "Search performed", "query": query}
            elif action in ("take_screenshot", "screenshot", "save_screenshot"):
                res = self._take_screenshot(params)
            elif action in ("close_browser", "close", "quit_browser"):
                res = self._close_browser()
            elif action in ("find_element", "find"):
                res = self._find_element(params.get("selector"), params.get("by", "css"))
            elif action in ("wait_for_element", "wait"):
                res = self._wait_for_element(
                    params.get("selector"), params.get("by", "css"), params.get("timeout", 10)
                )
            elif action == "wait_for_page_load":
                # Best-effort wait for document ready or body element
                try:
                    if getattr(self, "_playwright_active", False):
                        self._pw_page.wait_for_load_state(
                            "load", timeout=(params.get("timeout", 10) * 1000)
                        )
                        return {"success": True}
                    else:
                        # Selenium: wait for readyState == 'complete'
                        try:
                            WebDriverWait(self.driver, params.get("timeout", 10)).until(
                                lambda d: (
                                    d.execute_script("return document.readyState") == "complete"
                                )
                            )
                            return {"success": True}
                        except Exception:
                            # fallback: wait for body element presence
                            WebDriverWait(self.driver, params.get("timeout", 10)).until(
                                EC.presence_of_element_located((By.TAG_NAME, "body"))
                            )
                            return {"success": True}
                except Exception as e:
                    return {"success": False, "error": f"wait_for_page_load failed: {e}"}

            # Advanced web scraping and data extraction
            elif action in ("scrape_website", "extract_data", "scrape_page", "get_page_content"):
                res = self._scrape_website(params)
            elif action in ("extract_text", "get_text_content"):
                res = self._extract_text(params)
            elif action in ("extract_links",):
                res = self._extract_links(params)
            elif action in ("extract_images",):
                res = self._extract_images(params)
            elif action in ("scrape_table", "extract_table_data"):
                res = self._scrape_table(params)
            elif action in ("get_article_content", "extract_article"):
                res = self._extract_article(params)
            elif action in ("search_and_extract", "browse_and_scrape"):
                res = self._search_and_extract(params)
            else:
                return {"success": False, "error": f"Unknown web automation action: {action}"}

            # Normalize return types: many internal helpers return booleans or other values
            if isinstance(res, dict):
                return res
            if isinstance(res, bool):
                return {"success": res}

            # If res is something else (e.g., WebElement), return success and include it
            return {"success": True, "result": res}

        except Exception as e:
            logger.exception(f"web_automation action failed: {action}")
            return {"success": False, "error": str(e)}

    def _open_browser(self, browser: str = "chrome", headless: bool = False) -> bool:
        """Open a web browser"""
        import platform

        try:
            plat = platform.system().lower()
            # Enforce environment policy: only allow headless on Linux
            if headless and plat.startswith("win"):
                # Convert to non-headless on Windows to maintain behavior
                headless = False

            # Normalize browser selection: treat 'default'/'auto' as a heuristic choice
            br = str(browser).lower() if browser is not None else ""
            if br in ("default", "auto", "any", "system", "none", ""):
                # Prefer Selenium + Chrome when available, else Playwright
                if HAS_SELENIUM:
                    browser = "chrome"
                elif HAS_PLAYWRIGHT:
                    browser = "playwright"
                else:
                    browser = "chrome"
            else:
                browser = br

            # If caller explicitly asked for Playwright, prefer it
            if browser.lower() == "playwright" and HAS_PLAYWRIGHT:
                try:
                    pw = sync_playwright().start()
                    browser_obj = pw.chromium.launch(headless=headless)
                    self._pw = pw
                    self._pw_browser = browser_obj
                    self._pw_context = browser_obj.new_context()
                    self._pw_page = self._pw_context.new_page()
                    self._playwright_active = True
                    return {
                        "success": True,
                        "message": "Browser opened (Playwright)",
                        "headless": headless,
                    }
                except Exception as e:
                    try:
                        import logging

                        logging.getLogger(__name__).exception("Playwright launch failed (explicit)")
                    except Exception:
                        pass
                    return {
                        "success": False,
                        "error": f"Failed to open browser via Playwright explicitly: {e}",
                    }

            # Try Selenium first
            if HAS_SELENIUM:
                try:
                    import logging

                    logging.getLogger(__name__).info(
                        f"Attempting to open browser with Selenium: {browser}, headless={headless}"
                    )
                    if browser.lower() == "chrome":
                        options = Options()
                        # Keep Chrome window open after WebDriver session ends when not headless
                        try:
                            if not headless:
                                options.add_experimental_option("detach", True)
                        except Exception:
                            pass
                        if headless:
                            options.add_argument("--headless")
                        options.add_argument("--no-sandbox")
                        options.add_argument("--disable-dev-shm-usage")
                        try:
                            if HAS_WDM:
                                service = ChromeService(ChromeDriverManager().install())
                                self.driver = webdriver.Chrome(service=service, options=options)
                            else:
                                self.driver = webdriver.Chrome(options=options)
                        except Exception as e:
                            return {
                                "success": False,
                                "error": f"Failed to start Chrome WebDriver: {e}",
                            }
                    elif browser.lower() == "firefox":
                        from selenium.webdriver.firefox.options import Options as FirefoxOptions

                        options = FirefoxOptions()
                        if headless:
                            options.add_argument("--headless")
                        try:
                            if HAS_WDM:
                                service = FirefoxService(GeckoDriverManager().install())
                                self.driver = webdriver.Firefox(service=service, options=options)
                            else:
                                self.driver = webdriver.Firefox(options=options)
                        except Exception as e:
                            return {
                                "success": False,
                                "error": f"Failed to start Firefox WebDriver: {e}",
                            }
                    else:
                        return {"success": False, "error": f"Unsupported browser: {browser}"}

                    self.wait = WebDriverWait(self.driver, 10)
                    # mark playwright inactive when selenium driver is used
                    self._playwright_active = False
                    return {
                        "success": True,
                        "message": "Browser opened (Selenium)",
                        "headless": headless,
                    }
                except Exception as e:
                    return {"success": False, "error": f"Failed to open browser via Selenium: {e}"}

            # Selenium not available; try Playwright if present
            if HAS_PLAYWRIGHT:
                try:
                    # Properly start Playwright for persistent use
                    pw = sync_playwright().start()
                    browser_obj = pw.chromium.launch(headless=headless)
                    self._pw = pw
                    self._pw_browser = browser_obj
                    self._pw_context = browser_obj.new_context()
                    self._pw_page = self._pw_context.new_page()
                    # Provide minimal markers so other methods can detect Playwright usage
                    self.driver = None
                    self.wait = None
                    self._playwright_active = True
                    try:
                        import logging

                        logging.getLogger(__name__).info("Playwright browser started successfully")
                    except Exception:
                        pass
                    # mark playwright active
                    self._playwright_active = True
                    return {
                        "success": True,
                        "message": "Browser opened (Playwright)",
                        "headless": headless,
                    }
                except Exception as e:
                    try:
                        import logging

                        logging.getLogger(__name__).exception("Playwright launch failed")
                    except Exception:
                        pass
                    return {
                        "success": False,
                        "error": f"Failed to open browser via Playwright: {e}",
                    }

            return {
                "success": False,
                "error": "No browser automation backend available (install selenium or playwright)",
            }

        except Exception as e:
            return {"success": False, "error": f"Failed to open browser: {e}"}

    def _ensure_browser_open(self, preferred: str = "chrome", headless: bool = False):
        """Ensure a browser is open; try Selenium then Playwright if needed."""
        import logging

        logger = logging.getLogger(__name__)
        if self.driver or getattr(self, "_playwright_active", False):
            return {"success": True}

        logger.info(f"Ensuring browser open (preferred={preferred}, headless={headless})")
        res = self._open_browser(preferred, headless)
        # If _open_browser returned dict and was successful, ensure state
        if isinstance(res, dict) and res.get("success"):
            return {"success": True}

        # Try Playwright as fallback if available
        if HAS_PLAYWRIGHT:
            try:
                logger.info("Attempting Playwright fallback")
                res2 = self._open_browser("playwright", headless)
                if isinstance(res2, dict) and res2.get("success"):
                    return {"success": True}
            except Exception:
                logger.exception("Playwright fallback failed")

        # propagate original error dict or create one
        if isinstance(res, dict):
            return res
        return {"success": False, "error": "Failed to open any browser backend"}

    def _navigate_to(self, url: str) -> bool:
        """Navigate to a URL"""
        # Support both Selenium driver and Playwright
        import logging

        logging.getLogger(__name__).info(f"_navigate_to called with url={url}")

        # Ensure browser is open (attempt auto-start if necessary)
        ensure = self._ensure_browser_open()
        if isinstance(ensure, dict) and ensure.get("success") is False:
            return ensure

        if not url or not str(url).strip():
            return {"success": False, "error": "No URL provided to navigate_to"}

        try:
            if getattr(self, "_playwright_active", False):
                try:
                    self._pw_page.goto(url)
                    self.last_url = url
                    return {"success": True, "url": url}
                except Exception as e:
                    logging.getLogger(__name__).exception("Playwright navigate failed")
                    return {"success": False, "error": f"Playwright navigate failed: {e}"}

            try:
                self.driver.get(url)
            except Exception as e:
                logging.getLogger(__name__).exception("Selenium navigate failed")
                return {"success": False, "error": f"Failed to navigate to {url}: {e}"}
            # remember last navigated URL for potential screenshot fallbacks
            with contextlib.suppress(Exception):
                self.last_url = url
            return {"success": True, "url": url}
        except Exception as e:
            return {"success": False, "error": f"Failed to navigate to {url}: {e}"}

    def _click_element(self, selector: str, by: str = "css") -> bool:
        """Click an element"""
        ensure = self._ensure_browser_open()
        if isinstance(ensure, dict) and ensure.get("success") is False:
            raise Exception(ensure.get("error") or "Browser not open")

        try:
            if getattr(self, "_playwright_active", False):
                el = self._pw_page.query_selector(selector)
                if not el:
                    raise Exception(f"Element not found: {selector}")
                el.click()
                return True

            element = self._find_element(selector, by)
            element.click()
            return True
        except Exception as e:
            raise Exception(f"Failed to click element: {e}") from None

    def _type_text(self, selector: str, text: str, by: str = "css") -> bool:
        """Type text into an element"""
        ensure = self._ensure_browser_open()
        if isinstance(ensure, dict) and ensure.get("success") is False:
            raise Exception(ensure.get("error") or "Browser not open")

        try:
            # Playwright path
            if getattr(self, "_playwright_active", False):
                if selector:
                    try:
                        el = self._pw_page.query_selector(selector)
                        if el:
                            el.fill(text)
                            return True
                    except Exception:
                        pass

                # Try common selectors
                common_selectors = [
                    "input[name='q']",
                    "input[name=q]",
                    "input[type=search]",
                    "input[type=text]",
                ]
                for sel in common_selectors:
                    try:
                        el = self._pw_page.query_selector(sel)
                        if el:
                            el.fill(text)
                            return True
                    except Exception:
                        pass

                # Fallback to keyboard typing into active element
                try:
                    self._pw_page.keyboard.type(text)
                    return True
                except Exception as e:
                    raise Exception(f"Playwright type failed: {e}") from None

            # Selenium path
            element = None
            if selector:
                try:
                    element = self._find_element(selector, by)
                except Exception:
                    element = None

            # If no selector found, try common search input heuristics
            if element is None:
                common_selectors = [
                    "input[name='q']",
                    "input[name=q]",
                    "input[type=search]",
                    "input[type=text]",
                    "input[aria-label=Search]",
                    "input[title=Search]",
                    "input[role=searchbox]",
                ]
                for sel in common_selectors:
                    try:
                        element = self._find_element(sel, "css")
                        if element:
                            break
                    except Exception:
                        element = None

            # If still no element, try active element
            if element is None:
                try:
                    element = self.driver.switch_to.active_element
                except Exception:
                    element = None

            if element is None:
                raise Exception("No target element to type into")

            with contextlib.suppress(Exception):
                element.clear()
            element.send_keys(text)
            return True
        except Exception as e:
            raise Exception(f"Failed to type text: {e}") from None

    def _press_key(self, selector: str, key: str = None):
        """Press a key (like ENTER) on an element or active element"""
        ensure = self._ensure_browser_open()
        if isinstance(ensure, dict) and ensure.get("success") is False:
            raise Exception(ensure.get("error") or "Browser not open")

        try:
            if getattr(self, "_playwright_active", False):
                k = key or "Enter"
                try:
                    self._pw_page.keyboard.press(k if isinstance(k, str) else str(k))
                    return True
                except Exception as e:
                    raise Exception(f"Playwright press failed: {e}") from None

            element = None
            if selector:
                try:
                    element = self._find_element(selector)
                except Exception:
                    element = None

            if element is None:
                try:
                    element = self.driver.switch_to.active_element
                except Exception:
                    element = None

            if element is None:
                raise Exception("No target element to press key on")

            from selenium.webdriver.common.keys import Keys

            k = Keys.ENTER if not key else getattr(Keys, str(key).upper(), None) or str(key)

            element.send_keys(k)
            return True
        except Exception as e:
            raise Exception(f"Failed to press key: {e}") from None

    def _get_text(self, selector: str, by: str = "css") -> str:
        """Get text from an element"""
        ensure = self._ensure_browser_open()
        if isinstance(ensure, dict) and ensure.get("success") is False:
            raise Exception(ensure.get("error") or "Browser not open")

        try:
            element = self._find_element(selector, by)
            return element.text
        except Exception as e:
            raise Exception(f"Failed to get text: {e}") from None

    def _take_screenshot(self, params: dict[str, Any]) -> Any:
        """Take a screenshot"""
        import time

        try:
            # Extract filename and context from many possible param keys
            workflow_ctx = params.get("workflow_context", {}) if isinstance(params, dict) else {}
            candidate_keys = [
                "filename",
                "path",
                "dest",
                "destination",
                "file",
                "save_to",
                "output",
                "save_path",
                "target",
            ]
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
                norm = fn.replace("\\", "/").lstrip("/")

                # If Desktop appears anywhere in the path (case-insensitive), resolve to user's Desktop
                parts = norm.split("/")
                lower_parts = [p.lower() for p in parts]
                if "desktop" in lower_parts:
                    idx = lower_parts.index("desktop")
                    # everything after 'Desktop' becomes subpath under the real Desktop
                    tail = parts[idx + 1 :]
                    home = os.path.expanduser("~")
                    if tail:
                        fn = os.path.join(home, "Desktop", *tail)
                    else:
                        fn = os.path.join(home, "Desktop")
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

                logging.getLogger(__name__).info(
                    f"WebAutomation: resolved screenshot path: {filename}"
                )
            except Exception:
                pass

            # If driver is available, use it
            if self.driver:
                try:
                    # If caller provided a URL, navigate there first to ensure content is loaded
                    url = (
                        params.get("url")
                        or workflow_ctx.get("last_url")
                        or getattr(self, "last_url", None)
                    )
                    if url:
                        try:
                            # set a reasonable window size for screenshots
                            with contextlib.suppress(Exception):
                                self.driver.set_window_size(1366, 768)
                            self.driver.get(url)
                            # wait until document.readyState == 'complete' or body present
                            try:
                                WebDriverWait(self.driver, 10).until(
                                    lambda d: (
                                        d.execute_script("return document.readyState") == "complete"
                                    )
                                )
                            except Exception:
                                # fallback to waiting for body element
                                with contextlib.suppress(Exception):
                                    WebDriverWait(self.driver, 10).until(
                                        EC.presence_of_element_located((By.TAG_NAME, "body"))
                                    )
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
                        return {"success": True, "filename": filename}
                except Exception:
                    # continue to fallback
                    pass

            # Fallback: if no driver or screenshot failed, try saving page HTML
            url = (
                params.get("url") or workflow_ctx.get("last_url") or getattr(self, "last_url", None)
            )
            if url:
                try:
                    import requests

                    resp = requests.get(url, timeout=10)
                    # If requested filename ends with .png, change to .html for fallback
                    out_path = filename
                    if out_path.lower().endswith(".png"):
                        out_path = out_path[:-4] + ".html"
                    parent2 = os.path.dirname(out_path)
                    if parent2 and not os.path.exists(parent2):
                        os.makedirs(parent2, exist_ok=True)
                    with open(out_path, "w", encoding="utf-8") as f:
                        f.write(resp.text)
                    # Try to render HTML -> PNG using Playwright if available and PNG was requested
                    if HAS_PLAYWRIGHT:
                        try:
                            # determine desired png output
                            png_out = (
                                filename
                                if filename.lower().endswith(".png")
                                else (filename + ".png")
                            )
                            parent3 = os.path.dirname(png_out)
                            if parent3 and not os.path.exists(parent3):
                                os.makedirs(parent3, exist_ok=True)
                            with sync_playwright() as pw:
                                browser = pw.chromium.launch(headless=True)
                                page = browser.new_page(viewport={"width": 1366, "height": 768})
                                # open the saved HTML file directly
                                page.goto(
                                    "file://" + os.path.abspath(out_path), wait_until="networkidle"
                                )
                                page.screenshot(path=png_out)
                                browser.close()
                            return {
                                "success": True,
                                "filename": png_out,
                                "fallback": "playwright_png",
                            }
                        except Exception:
                            # If Playwright rendering fails, return saved HTML result
                            return {"success": True, "filename": out_path, "fallback": "saved_html"}
                    return {"success": True, "filename": out_path, "fallback": "saved_html"}
                except Exception as e:
                    return {"success": False, "error": f"Fallback to HTML failed: {e}"}

            return {"success": False, "error": "No browser available and no URL to fallback to"}
        except Exception as e:
            return {"success": False, "error": f"Failed to take screenshot: {e}"}

    def _find_element(self, selector: str, by: str = "css"):
        """Find an element"""
        ensure = self._ensure_browser_open()
        if isinstance(ensure, dict) and ensure.get("success") is False:
            raise Exception(ensure.get("error") or "Browser not open")

        if getattr(self, "_playwright_active", False):
            try:
                el = self._pw_page.query_selector(selector)
                if not el:
                    raise Exception(f"Element not found: {selector}")
                return el
            except Exception:
                raise Exception(f"Element not found: {selector}") from None

        by_mapping = {
            "css": By.CSS_SELECTOR,
            "xpath": By.XPATH,
            "id": By.ID,
            "name": By.NAME,
            "class": By.CLASS_NAME,
            "tag": By.TAG_NAME,
        }

        by_method = by_mapping.get(by.lower(), By.CSS_SELECTOR)

        try:
            return self.driver.find_element(by_method, selector)
        except Exception:
            raise Exception(f"Element not found: {selector}") from None

    def _wait_for_element(self, selector: str, by: str = "css", timeout: int = 10) -> bool:
        """Wait for an element to be present"""
        ensure = self._ensure_browser_open()
        if isinstance(ensure, dict) and ensure.get("success") is False:
            raise Exception(ensure.get("error") or "Browser not open")

        if getattr(self, "_playwright_active", False):
            try:
                self._pw_page.wait_for_selector(selector, timeout=timeout * 1000)
                return True
            except Exception:
                raise Exception(f"Element not found within {timeout} seconds: {selector}") from None

        by_mapping = {
            "css": By.CSS_SELECTOR,
            "xpath": By.XPATH,
            "id": By.ID,
            "name": By.NAME,
            "class": By.CLASS_NAME,
            "tag": By.TAG_NAME,
        }

        by_method = by_mapping.get(by.lower(), By.CSS_SELECTOR)

        try:
            wait = WebDriverWait(self.driver, timeout)
            wait.until(EC.presence_of_element_located((by_method, selector)))
            return True
        except Exception:
            raise Exception(f"Element not found within {timeout} seconds: {selector}") from None

    def _close_browser(self) -> bool:
        """Close the browser"""
        if self.driver:
            try:
                self.driver.quit()
                self.driver = None
                self.wait = None
                return {"success": True, "message": "Browser closed"}
            except Exception as e:
                return {"success": False, "error": f"Failed to close browser: {e}"}
        return {"success": True, "message": "No browser open"}

    def cleanup(self):
        """Cleanup plugin resources"""
        self._close_browser()

    def _scrape_website(self, params: dict[str, Any]) -> dict[str, Any]:
        """Scrape website content with intelligent extraction"""
        url = params.get("url") or params.get("website")
        if not url:
            return {"success": False, "error": "No URL provided"}

        try:
            # Try to get page content
            html_content = None

            # Try using active browser first
            if self.driver or getattr(self, "_playwright_active", False):
                try:
                    nav_result = self._navigate_to(url)
                    if isinstance(nav_result, dict) and nav_result.get("success"):
                        time_module.sleep(2)  # Wait for dynamic content

                        if getattr(self, "_playwright_active", False):
                            html_content = self._pw_page.content()
                        else:
                            html_content = self.driver.page_source
                except Exception:
                    pass

            # Fallback to requests if no browser or browser failed
            if not html_content and HAS_REQUESTS:
                try:
                    response = requests.get(
                        url,
                        timeout=15,
                        headers={
                            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                        },
                    )
                    response.raise_for_status()
                    html_content = response.text
                except Exception as e:
                    return {"success": False, "error": f"Failed to fetch content: {e}"}

            if not html_content:
                return {"success": False, "error": "Could not retrieve page content"}

            # Parse with BeautifulSoup
            if not HAS_BS4:
                return {
                    "success": True,
                    "raw_html": html_content,
                    "note": "BeautifulSoup not available, returning raw HTML",
                }

            soup = BeautifulSoup(html_content, "html.parser")

            # Extract structured data
            data = {
                "url": url,
                "title": soup.title.string if soup.title else "",
                "headings": {
                    "h1": [h.get_text(strip=True) for h in soup.find_all("h1")],
                    "h2": [h.get_text(strip=True) for h in soup.find_all("h2")],
                    "h3": [h.get_text(strip=True) for h in soup.find_all("h3")],
                },
                "paragraphs": [
                    p.get_text(strip=True) for p in soup.find_all("p") if p.get_text(strip=True)
                ],
                "links": [
                    {"text": a.get_text(strip=True), "href": a.get("href")}
                    for a in soup.find_all("a", href=True)
                ],
                "images": [
                    {"alt": img.get("alt", ""), "src": img.get("src")}
                    for img in soup.find_all("img")
                ],
                "meta": {
                    meta.get("name", meta.get("property", "")): meta.get("content", "")
                    for meta in soup.find_all("meta")
                    if meta.get("content")
                },
            }

            return {"success": True, "data": data, "raw_html": html_content}

        except Exception as e:
            import logging

            logging.getLogger(__name__).exception("Scraping failed")
            return {"success": False, "error": str(e)}

    def _extract_text(self, params: dict[str, Any]) -> dict[str, Any]:
        """Extract clean text content from a webpage"""
        url = params.get("url")
        selector = params.get("selector")

        try:
            # Navigate to page if URL provided
            if url:
                nav_result = self._navigate_to(url)
                if isinstance(nav_result, dict) and not nav_result.get("success"):
                    # Try requests fallback
                    if HAS_REQUESTS:
                        response = requests.get(
                            url,
                            timeout=15,
                            headers={
                                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                            },
                        )
                        html_content = response.text
                        if HAS_BS4:
                            soup = BeautifulSoup(html_content, "html.parser")
                            if selector:
                                elements = soup.select(selector)
                                text = "\n".join([el.get_text(strip=True) for el in elements])
                            else:
                                # Remove script and style elements
                                for script in soup(["script", "style", "nav", "footer", "header"]):
                                    script.decompose()
                                text = soup.get_text(separator="\n", strip=True)
                            return {"success": True, "text": text, "length": len(text)}

            # Get text from browser
            if selector:
                text = self._get_text(selector)
            else:
                # Get all visible text
                if getattr(self, "_playwright_active", False):
                    text = self._pw_page.inner_text("body")
                else:
                    text = self.driver.find_element(By.TAG_NAME, "body").text

            return {"success": True, "text": text, "length": len(text)}

        except Exception as e:
            return {"success": False, "error": str(e)}

    def _extract_links(self, params: dict[str, Any]) -> dict[str, Any]:
        """Extract all links from a webpage"""
        url = params.get("url")
        filter_pattern = params.get("filter")

        try:
            if url:
                self._navigate_to(url)

            links = []

            if getattr(self, "_playwright_active", False):
                elements = self._pw_page.query_selector_all("a[href]")
                links = [
                    {"text": el.inner_text(), "href": el.get_attribute("href")} for el in elements
                ]
            else:
                elements = self.driver.find_elements(By.TAG_NAME, "a")
                links = [
                    {"text": el.text, "href": el.get_attribute("href")}
                    for el in elements
                    if el.get_attribute("href")
                ]

            # Apply filter if provided
            if filter_pattern:
                links = [link for link in links if re.search(filter_pattern, link["href"] or "")]

            return {"success": True, "links": links, "count": len(links)}

        except Exception as e:
            return {"success": False, "error": str(e)}

    def _extract_images(self, params: dict[str, Any]) -> dict[str, Any]:
        """Extract all images from a webpage"""
        url = params.get("url")

        try:
            if url:
                self._navigate_to(url)

            images = []

            if getattr(self, "_playwright_active", False):
                elements = self._pw_page.query_selector_all("img")
                images = [
                    {"src": el.get_attribute("src"), "alt": el.get_attribute("alt")}
                    for el in elements
                ]
            else:
                elements = self.driver.find_elements(By.TAG_NAME, "img")
                images = [
                    {"src": el.get_attribute("src"), "alt": el.get_attribute("alt")}
                    for el in elements
                ]

            return {"success": True, "images": images, "count": len(images)}

        except Exception as e:
            return {"success": False, "error": str(e)}

    def _scrape_table(self, params: dict[str, Any]) -> dict[str, Any]:
        """Extract table data from webpage"""
        url = params.get("url")
        table_index = params.get("table_index", 0)

        try:
            if url:
                self._navigate_to(url)

            # Get page source
            if getattr(self, "_playwright_active", False):
                html_content = self._pw_page.content()
            else:
                html_content = self.driver.page_source

            if not HAS_BS4:
                return {"success": False, "error": "BeautifulSoup required for table extraction"}

            soup = BeautifulSoup(html_content, "html.parser")
            tables = soup.find_all("table")

            if not tables:
                return {"success": False, "error": "No tables found on page"}

            if table_index >= len(tables):
                return {
                    "success": False,
                    "error": f"Table index {table_index} out of range (found {len(tables)} tables)",
                }

            table = tables[table_index]

            # Extract headers
            headers = []
            header_row = table.find("thead")
            if header_row:
                headers = [th.get_text(strip=True) for th in header_row.find_all(["th", "td"])]
            else:
                # Try first row
                first_row = table.find("tr")
                if first_row:
                    headers = [th.get_text(strip=True) for th in first_row.find_all(["th", "td"])]

            # Extract rows
            rows = []
            tbody = table.find("tbody") or table
            for tr in tbody.find_all("tr")[1 if not table.find("thead") else 0 :]:
                cells = [td.get_text(strip=True) for td in tr.find_all(["td", "th"])]
                if cells:
                    rows.append(cells)

            return {
                "success": True,
                "headers": headers,
                "rows": rows,
                "row_count": len(rows),
                "column_count": len(headers),
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def _extract_article(self, params: dict[str, Any]) -> dict[str, Any]:
        """Extract main article content from webpage (intelligent extraction)"""
        url = params.get("url")

        try:
            if url:
                self._navigate_to(url)
                time_module.sleep(1)  # Wait for content to load

            # Get page source
            if getattr(self, "_playwright_active", False):
                html_content = self._pw_page.content()
            elif self.driver:
                html_content = self.driver.page_source
            elif HAS_REQUESTS and url:
                response = requests.get(
                    url,
                    timeout=15,
                    headers={
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                    },
                )
                html_content = response.text
            else:
                return {"success": False, "error": "No content source available"}

            if not HAS_BS4:
                return {"success": False, "error": "BeautifulSoup required for article extraction"}

            soup = BeautifulSoup(html_content, "html.parser")

            # Remove unwanted elements
            for element in soup(
                ["script", "style", "nav", "footer", "header", "aside", "iframe", "noscript"]
            ):
                element.decompose()

            # Try to find main content area
            article = None
            for selector in [
                "article",
                '[role="main"]',
                "main",
                ".content",
                "#content",
                ".post-content",
                ".article-content",
            ]:
                article = soup.select_one(selector)
                if article:
                    break

            if not article:
                article = soup.find("body")

            # Extract title
            title = ""
            title_elem = soup.find("h1") or soup.find("title")
            if title_elem:
                title = title_elem.get_text(strip=True)

            # Extract text content
            paragraphs = article.find_all("p") if article else []
            content = "\n\n".join(
                [p.get_text(strip=True) for p in paragraphs if len(p.get_text(strip=True)) > 20]
            )

            # Extract headings
            headings = []
            if article:
                for h in article.find_all(["h1", "h2", "h3", "h4"]):
                    headings.append({"level": h.name, "text": h.get_text(strip=True)})

            # Extract images in article
            images = []
            if article:
                for img in article.find_all("img"):
                    images.append(
                        {
                            "src": img.get("src"),
                            "alt": img.get("alt", ""),
                            "title": img.get("title", ""),
                        }
                    )

            return {
                "success": True,
                "title": title,
                "content": content,
                "headings": headings,
                "images": images,
                "word_count": len(content.split()),
                "url": url,
            }

        except Exception as e:
            import logging

            logging.getLogger(__name__).exception("Article extraction failed")
            return {"success": False, "error": str(e)}

    def _search_and_extract(self, params: dict[str, Any]) -> dict[str, Any]:
        """Perform web search and extract data from results"""
        query = params.get("query") or params.get("search_term")
        num_results = params.get("num_results", 5)
        extract_from_first = params.get("extract_from_first", True)

        try:
            # Perform search
            search_result = self.execute(
                "perform_search",
                {
                    "query": query,
                    "use_system_browser": False,
                    "headless": params.get("headless", False),
                },
            )

            if not search_result.get("success"):
                return search_result

            time_module.sleep(2)  # Wait for results

            # Extract search result links
            results = []

            if getattr(self, "_playwright_active", False):
                # Get search result links
                links = self._pw_page.query_selector_all("a[href]")
                for link in links[:num_results]:
                    href = link.get_attribute("href")
                    text = link.inner_text()
                    if href and text and "http" in href:
                        results.append({"title": text, "url": href})
            else:
                # Selenium
                links = self.driver.find_elements(By.CSS_SELECTOR, "a[href]")
                for link in links[: num_results * 2]:  # Get more to filter
                    try:
                        href = link.get_attribute("href")
                        text = link.text
                        if href and text and "http" in href and len(text) > 10:
                            results.append({"title": text, "url": href})
                            if len(results) >= num_results:
                                break
                    except Exception:
                        continue

            # Extract content from first result if requested
            extracted_content = None
            if extract_from_first and results:
                first_url = results[0]["url"]
                article_result = self._extract_article({"url": first_url})
                if article_result.get("success"):
                    extracted_content = article_result

            return {
                "success": True,
                "query": query,
                "results": results,
                "extracted_content": extracted_content,
            }

        except Exception as e:
            import logging

            logging.getLogger(__name__).exception("Search and extract failed")
            return {"success": False, "error": str(e)}
