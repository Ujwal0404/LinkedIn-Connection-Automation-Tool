import os
import time
import random
import csv
import logging
import argparse
from datetime import datetime
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, ElementClickInterceptedException
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains


# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("linkedin_automation.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class LinkedInAutomation:
    def __init__(self, email, password, message_template, connection_delay=(20, 40), daily_limit=40, debug_mode=False):
        """
        Initialize the LinkedIn automation tool.
        
        Args:
            email (str): LinkedIn login email
            password (str): LinkedIn login password
            message_template (str): Template for connection messages
            connection_delay (tuple): Min and max delay between connection requests (in seconds)
            daily_limit (int): Maximum number of connection requests per day
            debug_mode (bool): Enable debug mode with more logging and screenshots
        """
        self.email = email
        self.password = password
        self.message_template = message_template
        self.connection_delay = connection_delay
        self.daily_limit = daily_limit
        self.debug_mode = debug_mode
        self.driver = None
        self.request_count = self._load_request_count()
        self._last_request_time = 0  # For throttling
        
        # Create screenshots directory if it doesn't exist
        if debug_mode:
            os.makedirs("debug_screenshots", exist_ok=True)
            
    def _take_screenshot(self, name):
        """Take a screenshot if debug mode is enabled."""
        if self.debug_mode and self.driver:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"debug_screenshots/{timestamp}_{name}.png"
            try:
                self.driver.save_screenshot(filename)
                logger.debug(f"Screenshot saved: {filename}")
            except Exception as e:
                logger.error(f"Failed to take screenshot: {str(e)}")
                
    def _take_detailed_screenshot(self, name):
        """Take a screenshot with detailed page analysis."""
        if self.debug_mode and self.driver:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"debug_screenshots/{timestamp}_{name}.png"
            try:
                self.driver.save_screenshot(filename)
                
                # Save additional page diagnostics
                with open(f"debug_screenshots/{timestamp}_{name}_diagnostics.txt", "w") as f:
                    f.write(f"URL: {self.driver.current_url}\n\n")
                    f.write(f"Page Title: {self.driver.title}\n\n")
                    
                    # Log visible buttons
                    buttons = self.driver.find_elements(By.TAG_NAME, "button")
                    f.write("Visible Buttons:\n")
                    for i, button in enumerate(buttons):
                        try:
                            if button.is_displayed():
                                text = button.text.strip() or button.get_attribute("aria-label") or "[No Text]"
                                class_name = button.get_attribute("class") or "[No Class]"
                                f.write(f"{i+1}. Text: {text}, Class: {class_name}\n")
                        except:
                            pass
                            
                    # Log connection related elements
                    f.write("\nConnection Related Elements:\n")
                    selectors = [
                        "//button[contains(text(), 'Connect')]",
                        "//button[contains(text(), 'Pending')]",
                        "//span[contains(text(), 'Pending')]",
                        "//span[contains(text(), '1st')]"
                    ]
                    
                    for selector in selectors:
                        elements = self.driver.find_elements(By.XPATH, selector)
                        if elements:
                            f.write(f"Found {len(elements)} elements for: {selector}\n")
                            for i, element in enumerate(elements):
                                try:
                                    visible = element.is_displayed()
                                    f.write(f"  - Element {i+1}: Visible: {visible}, Text: {element.text.strip()}\n")
                                except:
                                    f.write(f"  - Element {i+1}: [Error accessing properties]\n")
                
                logger.debug(f"Detailed screenshot saved: {filename}")
            except Exception as e:
                logger.error(f"Failed to take detailed screenshot: {str(e)}")
        
    def _load_request_count(self):
        """Load today's request count from file."""
        today = datetime.now().strftime("%Y-%m-%d")
        try:
            if os.path.exists("request_count.csv"):
                with open("request_count.csv", "r") as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        if row.get('date') == today:
                            return int(row.get('count', 0))
            return 0
        except Exception as e:
            logger.error(f"Error loading request count: {str(e)}")
            return 0
    
    def _save_request_count(self):
        """Save today's request count to file."""
        today = datetime.now().strftime("%Y-%m-%d")
        try:
            rows = []
            if os.path.exists("request_count.csv"):
                with open("request_count.csv", "r") as f:
                    reader = csv.DictReader(f)
                    rows = list(reader)
                    
                    # Update existing entry or add new one
                    found = False
                    for row in rows:
                        if row.get('date') == today:
                            row['count'] = str(self.request_count)
                            found = True
                            break
                    
                    if not found:
                        rows.append({'date': today, 'count': str(self.request_count)})
            else:
                rows = [{'date': today, 'count': str(self.request_count)}]
                
            with open("request_count.csv", "w", newline='') as f:
                writer = csv.DictWriter(f, fieldnames=['date', 'count'])
                writer.writeheader()
                writer.writerows(rows)
                
            logger.debug(f"Saved request count: {self.request_count} for {today}")
        except Exception as e:
            logger.error(f"Error saving request count: {str(e)}")

    def setup_driver(self, headless=False):
        """Set up the Chrome WebDriver with anti-detection measures."""
        chrome_options = Options()
        if headless:
            chrome_options.add_argument("--headless=new")  # Use newer headless mode
        
        # General configurations
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-notifications")
        chrome_options.add_argument("--start-maximized")
        
        # Anti-detection measures
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        # Reduce errors in logs
        chrome_options.add_argument("--log-level=3")
        chrome_options.add_experimental_option('excludeSwitches', ['enable-logging'])
        
        # Performance tweaks
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--disable-extensions")
        
        try:
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            
            # Mask WebDriver usage
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            logger.info("WebDriver setup complete")
        except Exception as e:
            logger.error(f"Error setting up WebDriver: {str(e)}")
            raise
        
    def login(self):
        """Login to LinkedIn with improved reliability."""
        self.driver.get("https://www.linkedin.com/login")
        self._take_screenshot("login_page")
        
        try:
            # Wait for the login page to load
            logger.info("Waiting for login page to load...")
            WebDriverWait(self.driver, 20).until(
                EC.visibility_of_element_located((By.ID, "username"))
            )
            
            # Enter username/email
            logger.info("Entering email...")
            username_field = self.driver.find_element(By.ID, "username")
            username_field.clear()
            # Type slowly to avoid triggering security measures
            for char in self.email:
                username_field.send_keys(char)
                time.sleep(random.uniform(0.1, 0.2))
            
            # Enter password
            logger.info("Entering password...")
            password_field = self.driver.find_element(By.ID, "password")
            password_field.clear()
            # Type slowly to avoid triggering security measures
            for char in self.password:
                password_field.send_keys(char)
                time.sleep(random.uniform(0.1, 0.2))
            
            self._take_screenshot("credentials_entered")
            
            # Click login button
            logger.info("Clicking login button...")
            login_button = self.driver.find_element(By.XPATH, "//button[@type='submit']")
            login_button.click()
            
            # Wait for login to complete with various success indicators
            logger.info("Waiting for successful login...")
            try:
                # Check for any sign of a successful login
                WebDriverWait(self.driver, 30).until(
                    EC.any_of(
                        EC.presence_of_element_located((By.XPATH, "//div[contains(@class, 'feed-identity-module')]")),
                        EC.presence_of_element_located((By.XPATH, "//div[contains(@class, 'global-nav')]")),
                        EC.presence_of_element_located((By.XPATH, "//div[@id='voyager-feed']")),
                        EC.presence_of_element_located((By.XPATH, "//div[contains(@class, 'authentication-outlet')]")),
                        EC.presence_of_element_located((By.XPATH, "//header[contains(@class, 'global-nav__header')]")),
                        EC.url_contains("feed"),
                        EC.url_contains("voyager")
                    )
                )
            except TimeoutException:
                logger.warning("Primary login check elements not found, checking URL...")
                # Check if URL changed to something other than login page
                if "login" not in self.driver.current_url and "checkpoint" not in self.driver.current_url:
                    logger.info("URL suggests successful login")
                else:
                    # Check for verification/security challenges
                    if "checkpoint" in self.driver.current_url:
                        self._take_screenshot("security_checkpoint")
                        logger.error("Security verification required. Please login manually and try again.")
                        return False
                    self._take_screenshot("login_timeout")
                    raise TimeoutException("Login page still showing after login attempt")
            
            # Take a screenshot after login
            self._take_screenshot("post_login")
            logger.info(f"Current URL after login: {self.driver.current_url}")
            
            # If we're still on the login page, login failed
            if "login" in self.driver.current_url:
                logger.error("Still on login page after login attempt")
                return False
                
            # An additional check to make sure we're actually logged in
            try:
                # Check for presence of user avatar or navigation
                WebDriverWait(self.driver, 10).until(
                    EC.any_of(
                        EC.presence_of_element_located((By.XPATH, "//img[contains(@class, 'global-nav__me-photo')]")),
                        EC.presence_of_element_located((By.XPATH, "//li[contains(@class, 'global-nav__primary-item')]"))
                    )
                )
                logger.info("Successfully logged in to LinkedIn")
                return True
            except:
                # If we can't find the nav elements but we're past login, still return success
                if "login" not in self.driver.current_url:
                    logger.info("Partially successful login - not on login page")
                    return True
                else:
                    logger.error("Failed to find navigation elements after login")
                    return False
            
        except TimeoutException as e:
            logger.error(f"Login failed: Timeout while waiting for elements: {str(e)}")
            self._take_screenshot("login_timeout")
            return False
        except Exception as e:
            logger.error(f"Login failed: {str(e)}")
            self._take_screenshot("login_error")
            return False
        
    def manual_login(self, timeout=300):
        """Allow manual login by user."""
        self.driver.get("https://www.linkedin.com/login")
        self._take_screenshot("manual_login_start")
        
        logger.info(f"Please login manually in the browser. You have {timeout} seconds.")
        
        # Wait for login to complete
        start_time = time.time()
        while "login" in self.driver.current_url and time.time() - start_time < timeout:
            time.sleep(5)
            remaining = int(timeout - (time.time() - start_time))
            logger.info(f"Waiting for manual login... {remaining} seconds remaining")
        
        if "login" not in self.driver.current_url:
            logger.info("Manual login successful!")
            self._take_screenshot("manual_login_success")
            return True
        else:
            logger.error("Manual login timeout")
            self._take_screenshot("manual_login_timeout")
            return False
        
    
    def _find_element(self, xpath_selector):
        """
        Find an element by XPath selector if it exists and is visible.
        
        Args:
            xpath_selector: XPath selector to find element
            
        Returns:
            WebElement or None: The element if found and visible, None otherwise
        """
        try:
            elements = self.driver.find_elements(By.XPATH, xpath_selector)
            for element in elements:
                try:
                    if element.is_displayed():
                        return element
                except:
                    continue
            return None
        except Exception as e:
            logger.debug(f"Error finding element with selector {xpath_selector}: {str(e)}")
            return None

    def _is_element_visible(self, xpath_selector):
        """
        Check if an element is visible on the page.
        
        Args:
            xpath_selector: XPath selector to check
            
        Returns:
            bool: True if element is visible, False otherwise
        """
        element = self._find_element(xpath_selector)
        return element is not None

    def _close_dialogs(self):
        """Close any open dialogs by clicking dismiss/close buttons."""
        try:
            # Find all dismiss/close buttons
            dismiss_selectors = [
                "//button[@aria-label='Dismiss']",
                "//button[contains(@class, 'artdeco-modal__dismiss')]",
                "//button[contains(@class, 'artdeco-toast-item__dismiss')]",
                "//button[contains(@aria-label, 'Close')]",
                "//button[contains(@aria-label, 'close')]"
            ]
            
            for selector in dismiss_selectors:
                dismiss_buttons = self.driver.find_elements(By.XPATH, selector)
                for button in dismiss_buttons:
                    try:
                        if button.is_displayed():
                            logger.info(f"Closing dialog with button: {selector}")
                            self.driver.execute_script("arguments[0].click();", button)
                            time.sleep(1)
                    except:
                        continue
        except Exception as e:
            logger.debug(f"Error closing dialogs: {str(e)}")
    
    def _try_all_click_methods(self, element, element_name="element"):
        """
        Try multiple methods to click an element to ensure maximum reliability.
        
        Args:
            element: WebElement to click
            element_name: Name of the element for logging
            
        Returns:
            bool: True if any click method succeeded, False if all failed
        """
        if not element:
            logger.warning(f"Cannot click {element_name}: element is None")
            return False
            
        # Ensure element is in view first
        try:
            self.driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", element)
            time.sleep(0.5)
        except Exception as e:
            logger.debug(f"Could not scroll to {element_name}: {str(e)}")
        
        # Method 1: JavaScript click - most reliable
        try:
            logger.info(f"Trying JavaScript click on {element_name}")
            self.driver.execute_script("arguments[0].click();", element)
            logger.info(f"JavaScript click succeeded on {element_name}")
            return True
        except Exception as e:
            logger.debug(f"JavaScript click failed on {element_name}: {str(e)}")
        
        # Method 2: JavaScript click with event simulation
        try:
            logger.info(f"Trying JavaScript event simulation on {element_name}")
            js_script = """
                let element = arguments[0];
                let event = new MouseEvent('click', {
                    'view': window,
                    'bubbles': true,
                    'cancelable': true
                });
                element.dispatchEvent(event);
            """
            self.driver.execute_script(js_script, element)
            logger.info(f"JavaScript event simulation succeeded on {element_name}")
            return True
        except Exception as e:
            logger.debug(f"JavaScript event simulation failed on {element_name}: {str(e)}")
        
        # Method 3: Standard Selenium click
        try:
            logger.info(f"Trying standard click on {element_name}")
            element.click()
            logger.info(f"Standard click succeeded on {element_name}")
            return True
        except Exception as e:
            logger.debug(f"Standard click failed on {element_name}: {str(e)}")
        
        # Method 4: ActionChains click - helps with overlays and hidden elements
        try:
            logger.info(f"Trying ActionChains click on {element_name}")
            action = ActionChains(self.driver)
            action.move_to_element(element).click().perform()
            logger.info(f"ActionChains click succeeded on {element_name}")
            return True
        except Exception as e:
            logger.debug(f"ActionChains click failed on {element_name}: {str(e)}")
        
        # Method 5: Click with coordinates
        try:
            logger.info(f"Trying click with coordinates on {element_name}")
            action = ActionChains(self.driver)
            action.move_to_element_with_offset(element, 5, 5).click().perform()
            logger.info(f"Coordinate click succeeded on {element_name}")
            return True
        except Exception as e:
            logger.debug(f"Coordinate click failed on {element_name}: {str(e)}")
            
        # Method 6: Try with a dynamic wait and retry
        try:
            logger.info(f"Trying click with dynamic wait on {element_name}")
            WebDriverWait(self.driver, 5).until(EC.element_to_be_clickable(
                (By.XPATH, f"//*[@id='{element.get_attribute('id')}']")
            )).click()
            logger.info(f"Dynamic wait click succeeded on {element_name}")
            return True
        except Exception as e:
            logger.debug(f"Dynamic wait click failed on {element_name}: {str(e)}")
        
        logger.warning(f"All click methods failed on {element_name}")
        return False

    def _go_to_next_page(self):
        """Go to the next page of search results."""
        try:
            next_button = self.driver.find_element(By.XPATH, "//button[contains(@aria-label, 'Next')]")
            if next_button.is_enabled():
                logger.info("Going to next page")
                self.driver.execute_script("arguments[0].click();", next_button)
                time.sleep(random.uniform(3, 5))  # Wait for the next page to load
                return True
            else:
                logger.info("Reached the last page of search results")
                return False
        except Exception as e:
            logger.info(f"No more pages available: {str(e)}")
            return False
        
    def check_connection_status(self, profile_url):
        """
        Check the connection status with a profile with highest accuracy.
        
        Returns:
            str: "not_connected", "pending", "connected", or "unknown"
        """
        try:
            # Navigate to profile
            self.driver.get(profile_url)
            time.sleep(random.uniform(3, 5))
            self._take_detailed_screenshot("connection_status_check")
            
            # First check if this is a profile page or a redirect
            if "/in/" not in self.driver.current_url:
                logger.warning(f"URL redirected from {profile_url} to {self.driver.current_url}")
                return "unknown"
            
            # HIGHEST PRIORITY: Check for visible Connect button
            # If there's a visible Connect button, we're definitely not connected
            connect_indicators = [
                "//button[contains(text(), 'Connect')]",
                "//button[contains(.//span, 'Connect')]",
                "//button[contains(@aria-label, 'Connect')]",
                "//button[contains(@aria-label, 'connect with')]",
                "//button[contains(@class, 'artdeco-button')][.//span[text()='Connect']]",
                "//div[contains(@class, 'pvs-profile-actions__action')]/button[contains(.//span, 'Connect')]"
            ]
            
            for indicator in connect_indicators:
                connect_buttons = self.driver.find_elements(By.XPATH, indicator)
                for button in connect_buttons:
                    try:
                        if button.is_displayed():
                            logger.info(f"Not connected with {profile_url} (visible Connect button)")
                            return "not_connected"
                    except:
                        continue
            
            # Check for pending status
            pending_indicators = [
                "//button[contains(text(), 'Pending')]",
                "//button[contains(.//span, 'Pending')]",
                "//button[contains(@aria-label, 'Withdraw invitation')]",
                "//span[contains(text(), 'Pending')]",
                "//div[contains(text(), 'Invitation sent')]"
            ]
            
            for indicator in pending_indicators:
                pending_elements = self.driver.find_elements(By.XPATH, indicator)
                for element in pending_elements:
                    try:
                        if element.is_displayed():
                            logger.info(f"Connection request is pending for {profile_url}")
                            return "pending"
                    except:
                        continue
            
            # Check for 1st degree connection indicators
            connection_indicator_selectors = [
                "//span[contains(text(), 'Connected')]", 
                "//span[contains(text(), '1st')]",
                "//span[text()='1st']",
                "//span[contains(@class, 'distance-badge') and contains(text(), '1st')]",
                "//span[contains(@class, 'connection-degree') and contains(text(), '1st')]"
            ]
            
            for selector in connection_indicator_selectors:
                elements = self.driver.find_elements(By.XPATH, selector)
                for element in elements:
                    try:
                        if element.is_displayed():
                            logger.info(f"Already connected with {profile_url} (1st degree connection)")
                            return "connected"
                    except:
                        continue
                        
            # Check the degree of connection in network badge
            degree_indicators = [
                "//span[contains(text(), '2nd')]",
                "//span[contains(text(), '3rd')]",
                "//span[contains(@class, 'distance-badge') and (contains(text(), '2nd') or contains(text(), '3rd'))]"
            ]
            
            for indicator in degree_indicators:
                elements = self.driver.find_elements(By.XPATH, indicator)
                for element in elements:
                    try:
                        if element.is_displayed():
                            logger.info(f"Not connected with {profile_url} (2nd or 3rd degree connection)")
                            return "not_connected"
                    except:
                        continue
            
            # Check for "More" button that might have Connect option
            more_buttons = self.driver.find_elements(By.XPATH, "//button[contains(text(), 'More') or contains(.//span, 'More')]")
            for more_button in more_buttons:
                try:
                    if more_button.is_displayed():
                        # Click More button to show dropdown
                        self.driver.execute_script("arguments[0].click();", more_button)
                        time.sleep(1)
                        
                        # Check dropdown for Connect button
                        connect_in_dropdown = self.driver.find_elements(By.XPATH, 
                            "//div[contains(@class, 'dropdown') or contains(@class, 'artdeco-dropdown__content')]//span[contains(text(), 'Connect')]")
                        
                        if any(elem.is_displayed() for elem in connect_in_dropdown if elem.is_displayed()):
                            logger.info(f"Not connected with {profile_url} (Connect option in More dropdown)")
                            # Click away to close dropdown
                            self.driver.find_element(By.TAG_NAME, "body").click()
                            return "not_connected"
                            
                        # Click away to close dropdown
                        self.driver.find_element(By.TAG_NAME, "body").click()
                except Exception as e:
                    logger.debug(f"Error checking More dropdown: {str(e)}")
                    # Try to click away to close dropdown if it opened
                    try:
                        self.driver.find_element(By.TAG_NAME, "body").click()
                    except:
                        pass
                        
            # Check for Follow button (suggests not connected)
            follow_button = self._is_element_visible("//button[contains(text(), 'Follow') and not(contains(text(), 'Following'))]")
            if follow_button:
                logger.info(f"Not connected with {profile_url} (Follow button present)")
                return "not_connected"
            
            # If we get here and found no indicators, warn and return unknown
            logger.warning(f"Could not definitively determine connection status for {profile_url}")
            return "unknown"
                
        except Exception as e:
            logger.error(f"Error checking connection status: {str(e)}")
            return "unknown"
        
    def _verify_connection_sent(self, profile_url):
        """
        Verify that a connection request was successfully sent with enhanced checks and UI verification.
        
        Args:
            profile_url (str): LinkedIn profile URL to verify
                
        Returns:
            bool: True if connection was sent, False otherwise
        """
        try:
            # Log the verification attempt
            logger.info("Verifying connection request was sent")
            self._take_detailed_screenshot("verification_attempt")
            
            # HIGHEST PRIORITY: Check for Pending button in profile actions area (where Connect was)
            profile_actions_pending_selectors = [
                "//div[contains(@class, 'pvs-profile-actions')]//button[contains(text(), 'Pending')]",
                "//div[contains(@class, 'pv-top-card')]//button[contains(text(), 'Pending')]",
                "//main//button[contains(text(), 'Pending')]",
                "//button[contains(@class, 'pvs-profile-actions__action')][.//span[contains(text(), 'Pending')]]",
                "//button[contains(@class, 'artdeco-button')][.//span[contains(text(), 'Pending')]]",
                "//span[text()='Pending']/ancestor::button"
            ]
            
            for selector in profile_actions_pending_selectors:
                if self._is_element_visible(selector):
                    logger.info(f"Found Pending button in profile actions area: {selector}")
                    self.request_count += 1
                    self._save_request_count()
                    return True
            
            # PRIORITY 1: Visual verification - look for Pending button in UI
            pending_button_selectors = [
                "//button[text()='Pending']",
                "//button[contains(text(), 'Pending')]",
                "//button[contains(@aria-label, 'Pending')]",
                "//span[contains(text(), 'Pending')]/ancestor::button",
                "//button[contains(@class, 'artdeco-button')][.//span[contains(text(), 'Pending')]]"
            ]
            
            for selector in pending_button_selectors:
                if self._is_element_visible(selector):
                    logger.info(f"Found visible Pending button: {selector}")
                    self.request_count += 1
                    self._save_request_count()
                    return True
            
            # PRIORITY 2: Check for toast notifications
            toast_selectors = [
                "//div[contains(@class, 'artdeco-toast-item')]//p[contains(text(), 'Invitation sent')]",
                "//div[contains(@class, 'artdeco-toast-item')]//p[contains(text(), 'Connection request sent')]",
                "//div[contains(@class, 'artdeco-toast')]//span[contains(text(), 'sent')]",
                "//div[contains(@class, 'artdeco-toast')]//p[contains(text(), 'sent')]"
            ]
            
            for selector in toast_selectors:
                if self._is_element_visible(selector):
                    logger.info(f"Found success toast notification: {selector}")
                    self.request_count += 1
                    self._save_request_count()
                    return True
            
            # PRIORITY 3: Check for any visual indication of success
            success_text_selectors = [
                "//span[contains(text(), 'Invitation sent')]",
                "//span[contains(text(), 'Request sent')]",
                "//div[contains(text(), 'Your invitation to connect has been sent')]",
                "//p[contains(text(), 'Invitation sent')]"
            ]
            
            for selector in success_text_selectors:
                if self._is_element_visible(selector):
                    logger.info(f"Found visible success text indicator: {selector}")
                    self.request_count += 1
                    self._save_request_count()
                    return True
            
            # PRIORITY 4: Check if the Connect button is no longer visible
            # This indicates the request was sent (if it was previously visible)
            connect_button_selectors = [
                "//button[text()='Connect']",
                "//button[contains(.//span, 'Connect')]",
                "//div[contains(@class, 'pvs-profile-actions')]//button[contains(.//span, 'Connect')]"
            ]
            
            # If none of the Connect buttons are visible anymore, it might be a success
            if not any(self._is_element_visible(selector) for selector in connect_button_selectors):
                # But only if we're on the profile page and not in some dialog
                if "/in/" in self.driver.current_url and not self._is_element_visible("//div[@role='dialog']"):
                    logger.info("Connect button is no longer visible, assuming request was sent")
                    self.request_count += 1
                    self._save_request_count()
                    return True
            
            # LOWER PRIORITY: Check page source but with caution
            # Only if we're on the profile page and not in a dialog
            if "/in/" in self.driver.current_url and not self._is_element_visible("//div[@role='dialog']"):
                page_source = self.driver.page_source.lower()
                
                # More specific keyword patterns with context
                invitation_patterns = [
                    '"invitationPending":true',
                    '"invitation-pending"',
                    '"connectionStatus":"PENDING"',
                    'class="connect-pending"',
                    '<button[^>]*pending[^>]*>'
                ]
                
                for pattern in invitation_patterns:
                    import re
                    if re.search(pattern, page_source):
                        logger.info(f"Found context-specific pattern '{pattern}' in page source")
                        self.request_count += 1
                        self._save_request_count()
                        return True
                    
                # Check general keywords as last resort, but only if no Connect button is visible
                if not any(self._is_element_visible(selector) for selector in connect_button_selectors):
                    general_keywords = ["invitation sent", "request sent", "invitation-pending"]
                    for keyword in general_keywords:
                        if keyword in page_source:
                            logger.info(f"Found '{keyword}' in page source as last resort check")
                            self.request_count += 1
                            self._save_request_count()
                            return True
            
            # If we get here, we couldn't verify the connection request
            logger.warning("Could not verify connection request was sent")
            return False
        except Exception as e:
            logger.warning(f"Error in verification: {str(e)}")
            return False

    def send_connection_request(self, profile_url, personalized_note=None, max_retries=2):
        """
        Send a connection request or follow the user if connect button is not available.
        
        Args:
            profile_url (str): LinkedIn profile URL to send connection request to
            personalized_note (str, optional): Personalized note to include with request
            max_retries (int): Maximum number of retry attempts
                
        Returns:
            bool: True if connection request was sent or user was followed successfully
        """
        # Apply throttling to avoid triggering LinkedIn's automated systems
        now = time.time()
        if hasattr(self, '_last_request_time'):
            time_since_last = now - self._last_request_time
            if time_since_last < 15:  # Minimum 15 seconds between requests
                wait_time = 15 - time_since_last
                logger.info(f"Throttling: waiting {wait_time:.2f} seconds")
                time.sleep(wait_time)
        
        self._last_request_time = time.time()
        
        # Check daily limit
        if self.request_count >= self.daily_limit:
            logger.warning(f"Daily connection limit reached ({self.daily_limit}). Skipping request.")
            return False
        
        # First check connection status
        conn_status = self.check_connection_status(profile_url)
        
        # If already pending or connected, return True (we count this as a success)
        if conn_status == "pending":
            logger.info(f"Connection request already pending for {profile_url}")
            return True
        elif conn_status == "connected":
            logger.info(f"Already connected with {profile_url}")
            # Double-check by looking for a visible Connect button before skipping
            # Only if we're specifically told to be paranoid about status checks
            if os.getenv('LINKEDIN_VERIFY_CONNECTED', 'false').lower() == 'true':
                self.driver.get(profile_url)
                time.sleep(2)
                connect_button = self._find_connect_button()
                if connect_button:
                    logger.warning(f"Connection status mismatch for {profile_url} - found Connect button for supposedly connected profile")
                    # Continue with connection attempt
                else:
                    return True
            else:
                return True
        
        # Track if we've hit premium limit
        premium_limit_hit = False
        
        
        
        # Implement retry logic
        for attempt in range(max_retries + 1):
            logger.info(f"Connection request attempt {attempt + 1}/{max_retries + 1}")
            
            try:
                # Navigate to profile
                logger.info(f"Navigating to {profile_url}")
                self.driver.get(profile_url)
                time.sleep(3)
                
                # Store the URL to detect refreshes
                initial_url = self.driver.current_url
                logger.info(f"Initial URL: {initial_url}")
                self._take_detailed_screenshot(f"profile_page_attempt_{attempt+1}")
                
                # Close any dialogs that might be open
                self._close_dialogs()
                
                # Try to find Connect button
                connect_button = self._find_connect_button()
                
                if connect_button:
                    # If Connect button found, proceed with normal connection flow
                    logger.info("Found Connect button, clicking it")
                    self._take_screenshot("before_connect_click")
                    
                    # Try all click methods to ensure it works
                    click_success = self._try_all_click_methods(connect_button, "Connect button")
                    
                    if not click_success:
                        logger.error("All methods to click Connect button failed")
                        if attempt < max_retries:
                            logger.info("Will retry in next attempt")
                            time.sleep(2)
                            continue
                        return False
                        
                    # Wait longer for any UI response
                    time.sleep(3)
                    self._take_screenshot("after_connect_click")
                    
                    # Check if URL changed (page refresh detection)
                    current_url = self.driver.current_url
                    logger.info(f"URL after clicking Connect: {current_url}")
                    
                    # If URL changed significantly, LinkedIn might have processed the request automatically
                    if current_url != initial_url and "/in/" in current_url:
                        logger.info("URL changed after clicking Connect button, possible auto-processing")
                        
                        # Wait a bit and check if connection was sent
                        time.sleep(2)
                        if self._verify_connection_sent(profile_url):
                            logger.info("Connection verified after URL change")
                            return True
                        
                        # If not verified, continue with normal flow by reloading profile
                        logger.info("Reloading profile to continue normal flow")
                        self.driver.get(profile_url)
                        time.sleep(3)
                        
                        # Try finding Connect button again
                        connect_button = self._find_connect_button()
                        if not connect_button:
                            logger.warning("Could not find Connect button after reload")
                            continue
                        
                        logger.info("Clicking Connect button after reload")
                        self._try_all_click_methods(connect_button, "Connect button after reload")
                        time.sleep(3)
                    
                    # Look for "Add a note" dialog
                    add_note_dialog_selectors = [
                        "//h2[contains(text(), 'Add a note to your invitation?')]",
                        "//h2[contains(text(), 'Add a note')]",
                        "//div[@role='dialog'][contains(., 'Add a note to your invitation')]"
                    ]
                    
                    add_note_dialog_visible = False
                    for selector in add_note_dialog_selectors:
                        if self._is_element_visible(selector):
                            add_note_dialog_visible = True
                            logger.info(f"'Add a note' dialog detected with selector: {selector}")
                            break
                    
                    if add_note_dialog_visible:
                        logger.info("'Add a note' dialog is visible")
                        
                        # If premium limit was previously hit or this is a retry attempt, go straight to "Send without note"
                        if premium_limit_hit or attempt > 0:
                            logger.info("Premium limit was hit or this is a retry - sending without note")
                            
                            # Find and click "Send without a note" button using enhanced approach
                            no_note_button_selectors = [
                                "//button[normalize-space(text())='Send without a note']",
                                "//span[normalize-space(text())='Send without a note']/parent::button",
                                "//div[@role='dialog']//button[contains(., 'Send without a note')]",
                                "//button[contains(@class, 'artdeco-button')][contains(., 'Send without a note')]",
                                "//footer//button[contains(., 'Send without a note')]",  # Try footer specific selector
                                "//div[@role='dialog']//button[2]",  # Try second button in dialog as fallback
                                "//div[contains(@class, 'send-invite')]//button[2]"  # Another fallback
                            ]
                            
                            # Try each selector
                            no_note_button = None
                            for selector in no_note_button_selectors:
                                try:
                                    elements = self.driver.find_elements(By.XPATH, selector)
                                    for element in elements:
                                        if element.is_displayed():
                                            no_note_button = element
                                            logger.info(f"Found 'Send without a note' button with selector: {selector}")
                                            break
                                    if no_note_button:
                                        break
                                except:
                                    continue
                            
                            if no_note_button:
                                logger.info("Clicking 'Send without a note' button with multiple methods")
                                
                                # Take screenshot before clicking
                                self._take_detailed_screenshot("before_send_without_note")
                                
                                # Try multiple click methods in sequence
                                try:
                                    # Method 1: JavaScript click (most reliable)
                                    logger.info("Trying JavaScript click on Send without note button")
                                    self.driver.execute_script("arguments[0].click();", no_note_button)
                                    time.sleep(3)
                                    if self._verify_connection_sent(profile_url):
                                        logger.info("JavaScript click succeeded")
                                        return True
                                except Exception as e:
                                    logger.debug(f"JavaScript click failed: {str(e)}")
                                
                                try:
                                    # Method 2: ActionChains click
                                    logger.info("Trying ActionChains click on Send without note button")
                                    from selenium.webdriver.common.action_chains import ActionChains
                                    ActionChains(self.driver).move_to_element(no_note_button).click().perform()
                                    time.sleep(3)
                                    if self._verify_connection_sent(profile_url):
                                        logger.info("ActionChains click succeeded")
                                        return True
                                except Exception as e:
                                    logger.debug(f"ActionChains click failed: {str(e)}")
                                
                                try:
                                    # Method 3: Direct click
                                    logger.info("Trying direct click on Send without note button")
                                    no_note_button.click()
                                    time.sleep(3)
                                    if self._verify_connection_sent(profile_url):
                                        logger.info("Direct click succeeded")
                                        return True
                                except Exception as e:
                                    logger.debug(f"Direct click failed: {str(e)}")
                                
                                try:
                                    # Method 4: Send Enter key
                                    logger.info("Trying Enter key on Send without note button")
                                    from selenium.webdriver.common.keys import Keys
                                    no_note_button.send_keys(Keys.ENTER)
                                    time.sleep(3)
                                    if self._verify_connection_sent(profile_url):
                                        logger.info("Enter key succeeded")
                                        return True
                                except Exception as e:
                                    logger.debug(f"Enter key failed: {str(e)}")
                                
                                try:
                                    # Method 5: Click with JavaScript event dispatch
                                    logger.info("Trying JavaScript event dispatch on Send without note button")
                                    self.driver.execute_script("""
                                        var event = new MouseEvent('click', {
                                            'view': window,
                                            'bubbles': true,
                                            'cancelable': true
                                        });
                                        arguments[0].dispatchEvent(event);
                                    """, no_note_button)
                                    time.sleep(3)
                                    if self._verify_connection_sent(profile_url):
                                        logger.info("JavaScript event dispatch succeeded")
                                        return True
                                except Exception as e:
                                    logger.debug(f"JavaScript event dispatch failed: {str(e)}")
                                
                                # Take screenshot after all click attempts
                                self._take_detailed_screenshot("after_send_without_note_attempts")
                                
                                logger.warning("All click methods failed for 'Send without a note' button")
                            else:
                                logger.error("Could not find 'Send without a note' button with any selector")
                        else:
                            # First time - try "Add a note" option
                            if personalized_note:
                                # Find and click "Add a note" button
                                add_note_button_selectors = [
                                    "//button[text()='Add a note']",
                                    "//button[contains(text(), 'Add a note')]",
                                    "//div[@role='dialog']//button[contains(., 'Add a note')]"
                                ]
                                
                                add_note_button = None
                                for selector in add_note_button_selectors:
                                    add_note_button = self._find_element(selector)
                                    if add_note_button:
                                        logger.info(f"Found 'Add a note' button with selector: {selector}")
                                        break
                                
                                if add_note_button:
                                    logger.info("Clicking 'Add a note' button")
                                    note_click_success = self._try_all_click_methods(add_note_button, "Add a note button")
                                    time.sleep(2)
                                    
                                    # Check for premium limit dialog
                                    premium_limit = self._is_element_visible("//h2[contains(text(), 'No free personalized invitations left')]")
                                    
                                    if premium_limit:
                                        logger.info("Premium limit reached, will try without note")
                                        premium_limit_hit = True
                                        
                                        # Dismiss premium limit dialog
                                        dismiss_button = self._find_element("//button[@aria-label='Dismiss']")
                                        if dismiss_button:
                                            self._try_all_click_methods(dismiss_button, "Dismiss premium dialog")
                                            time.sleep(1)
                                        
                                        # Go back to profile and try again
                                        logger.info("Reloading profile to try connecting without a note")
                                        self.driver.get(profile_url)
                                        time.sleep(3)
                                        
                                        # Find and click Connect button again
                                        connect_button = self._find_connect_button()
                                        if connect_button:
                                            logger.info("Clicking Connect button again (after premium limit)")
                                            self._try_all_click_methods(connect_button, "Connect button (retry)")
                                            time.sleep(3)
                                            
                                            # Now look for "Add a note" dialog again
                                            add_note_dialog_visible = False
                                            for selector in add_note_dialog_selectors:
                                                if self._is_element_visible(selector):
                                                    add_note_dialog_visible = True
                                                    break
                                            
                                            if add_note_dialog_visible:
                                                # Find and click "Send without a note" button using enhanced approach
                                                no_note_button_selectors = [
                                                    "//button[normalize-space(text())='Send without a note']",
                                                    "//span[normalize-space(text())='Send without a note']/parent::button",
                                                    "//div[@role='dialog']//button[contains(., 'Send without a note')]",
                                                    "//button[contains(@class, 'artdeco-button')][contains(., 'Send without a note')]",
                                                    "//footer//button[contains(., 'Send without a note')]",
                                                    "//div[@role='dialog']//button[2]",
                                                    "//div[contains(@class, 'send-invite')]//button[2]"
                                                ]
                                                
                                                # Try each selector
                                                no_note_button = None
                                                for selector in no_note_button_selectors:
                                                    try:
                                                        elements = self.driver.find_elements(By.XPATH, selector)
                                                        for element in elements:
                                                            if element.is_displayed():
                                                                no_note_button = element
                                                                logger.info(f"Found 'Send without a note' button with selector: {selector}")
                                                                break
                                                        if no_note_button:
                                                            break
                                                    except:
                                                        continue
                                                
                                                if no_note_button:
                                                    logger.info("Clicking 'Send without a note' button after premium limit")
                                                    # Try multiple click methods
                                                    try:
                                                        # JavaScript click
                                                        self.driver.execute_script("arguments[0].click();", no_note_button)
                                                        time.sleep(3)
                                                        if self._verify_connection_sent(profile_url):
                                                            return True
                                                    except Exception as e:
                                                        logger.debug(f"JavaScript click failed: {str(e)}")
                                                        
                                                        # Direct click as fallback
                                                        try:
                                                            no_note_button.click()
                                                            time.sleep(3)
                                                            if self._verify_connection_sent(profile_url):
                                                                return True
                                                        except Exception as e:
                                                            logger.debug(f"Direct click failed too: {str(e)}")
                                            else:
                                                logger.warning("'Add a note' dialog not found after retry")
                                    else:
                                        # No premium limit, enter personalized note
                                        note_field_selectors = [
                                            "//textarea[contains(@id, 'custom-message')]",
                                            "//textarea[contains(@name, 'message')]",
                                            "//div[@role='dialog']//textarea"
                                        ]
                                        
                                        note_field = None
                                        for selector in note_field_selectors:
                                            note_field = self._find_element(selector)
                                            if note_field:
                                                logger.info(f"Found note textarea with selector: {selector}")
                                                break
                                        
                                        if note_field:
                                            logger.info(f"Entering personalized note: {personalized_note}")
                                            note_field.clear()
                                            for char in personalized_note:
                                                note_field.send_keys(char)
                                                time.sleep(random.uniform(0.01, 0.05))  # Type naturally
                                            time.sleep(1)
                                            self._take_screenshot("note_entered")
                                            
                                            # Click Send button
                                            send_button_selectors = [
                                                "//button[text()='Send']",
                                                "//button[contains(text(), 'Send')]",
                                                "//div[@role='dialog']//button[contains(., 'Send')]"
                                            ]
                                            
                                            send_button = None
                                            for selector in send_button_selectors:
                                                send_button = self._find_element(selector)
                                                if send_button:
                                                    logger.info(f"Found Send button with selector: {selector}")
                                                    break
                                            
                                            if send_button:
                                                logger.info("Clicking Send button after entering note")
                                                self._try_all_click_methods(send_button, "Send button")
                                                time.sleep(3)
                                                
                                                # Verify connection request was sent
                                                if self._verify_connection_sent(profile_url):
                                                    return True
                                        else:
                                            logger.warning("Could not find textarea for note")
                                else:
                                    logger.warning("Could not find 'Add a note' button")
                                    
                                    # Fall back to "Send without a note"
                                    no_note_button = self._find_element("//button[contains(text(), 'Send without a note')]")
                                    if no_note_button:
                                        logger.info("Falling back to 'Send without a note'")
                                        self._try_all_click_methods(no_note_button, "Send without note button")
                                        time.sleep(3)
                                        
                                        # Verify connection request was sent
                                        if self._verify_connection_sent(profile_url):
                                            return True
                            else:
                                # No personalized note provided, click "Send without a note"
                                no_note_button_selectors = [
                                    "//button[normalize-space(text())='Send without a note']",
                                    "//span[normalize-space(text())='Send without a note']/parent::button",
                                    "//div[@role='dialog']//button[contains(., 'Send without a note')]",
                                    "//button[contains(@class, 'artdeco-button')][contains(., 'Send without a note')]",
                                    "//footer//button[contains(., 'Send without a note')]",
                                    "//div[@role='dialog']//button[2]", 
                                    "//div[contains(@class, 'send-invite')]//button[2]"
                                ]
                                
                                no_note_button = None
                                for selector in no_note_button_selectors:
                                    try:
                                        elements = self.driver.find_elements(By.XPATH, selector)
                                        for element in elements:
                                            if element.is_displayed():
                                                no_note_button = element
                                                logger.info(f"Found 'Send without a note' button with selector: {selector}")
                                                break
                                        if no_note_button:
                                            break
                                    except:
                                        continue
                                
                                if no_note_button:
                                    logger.info("Clicking 'Send without a note' button (no note provided)")
                                    # Try multiple click methods
                                    try:
                                        # JavaScript click
                                        self.driver.execute_script("arguments[0].click();", no_note_button)
                                        time.sleep(3)
                                        if self._verify_connection_sent(profile_url):
                                            return True
                                    except:
                                        # Direct click as fallback
                                        try:
                                            no_note_button.click()
                                            time.sleep(3)
                                            if self._verify_connection_sent(profile_url):
                                                return True
                                        except:
                                            logger.warning("Failed to click 'Send without a note'")
                    else:
                        logger.info("'Add a note' dialog not detected")
                        
                        # Check if connection was sent automatically
                        if self._verify_connection_sent(profile_url):
                            logger.info("Connection appears to have been sent automatically")
                            return True
                else:
                    # No Connect button found, look for Follow button instead
                    logger.info("No Connect button found, looking for Follow button instead")
                    
                    follow_button_selectors = [
                        "//button[text()='Follow']",
                        "//button[contains(text(), 'Follow')]",
                        "//div[contains(@class, 'pvs-profile-actions')]//button[contains(., 'Follow')]",
                        "//span[text()='Follow']/parent::button",
                        "//div[contains(@class, 'pv-top-card')]//button[text()='Follow']"
                    ]
                    
                    follow_button = None
                    for selector in follow_button_selectors:
                        follow_button = self._find_element(selector)
                        if follow_button:
                            logger.info(f"Found Follow button with selector: {selector}")
                            break
                    
                    if follow_button:
                        logger.info("Clicking Follow button")
                        self._take_screenshot("before_follow_click")
                        
                        # Try to click Follow button
                        follow_clicked = self._try_all_click_methods(follow_button, "Follow button")
                        
                        if follow_clicked:
                            logger.info("Successfully clicked Follow button")
                            time.sleep(2)
                            self._take_screenshot("after_follow_click")
                            
                            # Check if Follow button text changed to "Following"
                            following_button = self._find_element("//button[contains(text(), 'Following')]")
                            if following_button:
                                logger.info("Follow successful - button text changed to 'Following'")
                                self.request_count += 1
                                self._save_request_count()
                                return True
                            
                            # Check if we have an "Unfollow" button
                            unfollow_visible = self._is_element_visible("//button[contains(text(), 'Unfollow') or contains(@aria-label, 'Unfollow')]")
                            if unfollow_visible:
                                logger.info("Follow successful - Unfollow button is now visible")
                                self.request_count += 1
                                self._save_request_count()
                                return True
                            
                            # Look for any confirmation tooltips or toasts
                            confirmation_selectors = [
                                "//div[contains(@class, 'artdeco-toast')]",
                                "//span[contains(text(), 'Following')]",
                                "//button[contains(text(), 'Following')]"
                            ]
                            
                            for selector in confirmation_selectors:
                                if self._is_element_visible(selector):
                                    logger.info(f"Follow confirmation found with selector: {selector}")
                                    self.request_count += 1
                                    self._save_request_count()
                                    return True
                            
                            # If we can't verify follow status, assume success
                            logger.info("Cannot confirm follow status but assuming success")
                            self.request_count += 1
                            self._save_request_count()
                            return True
                        else:
                            logger.warning("Failed to click Follow button")
                    else:
                        logger.warning(f"Could not find any Connect or Follow button for {profile_url}")
                
                # Final verification - reload profile and check connection status
                logger.info("Performing final verification by reloading profile")
                self.driver.get(profile_url)
                time.sleep(3)
                self._take_screenshot("reload_verification")
                
                # Check status after reload
                conn_status = self.check_connection_status(profile_url)
                if conn_status == "pending":
                    logger.info("Connection status is now pending after reloading profile")
                    self.request_count += 1
                    self._save_request_count()
                    return True
                
                logger.warning("Could not confirm connection request was sent")
                # If this is not the last attempt, try again
                if attempt < max_retries:
                    logger.info(f"Retry attempt {attempt + 1} failed, trying again...")
                    time.sleep(2)
                    continue
                return False
                    
            except Exception as e:
                logger.error(f"Error in connection attempt {attempt + 1}: {str(e)}")
                import traceback
                logger.error(traceback.format_exc())
                
                if attempt < max_retries:
                    logger.info(f"Retry attempt {attempt + 1} failed, trying again...")
                    time.sleep(2)
                    continue
        
        return False

        
    def _find_connect_button(self):
        """
        Find the Connect button on a profile page using multiple selector strategies.
        Handles both direct Connect buttons and those in the More dropdown.
        
        Returns:
            WebElement or None: The connect button if found, None otherwise
        """
        # First try all the direct connect button patterns
        connect_selectors = [
            "//button[text()='Connect']",
            "//button[contains(.//span, 'Connect')]",
            "//div[contains(@class, 'pvs-profile-actions')]//button[contains(.//span, 'Connect')]",
            "//div[contains(@class, 'pv-top-card')]//button[contains(.//span, 'Connect')]",
            "//main//button[contains(.//span, 'Connect')]",
            "//button[contains(@aria-label, 'Invite') and contains(@aria-label, 'to connect')]",
            "//button[contains(@aria-label, 'Connect with')]",
            "//button[contains(@class, 'artdeco-button')][.//span[contains(text(), 'Connect')]]",
            "//button[starts-with(@id, 'ember') and contains(.//span, 'Connect')]",
            "//button[contains(@class, 'artdeco-button')][.//span[text()='Connect']]",
            "//div[contains(@class, 'pvs-profile-actions__action')]/button[contains(.//span, 'Connect')]",
            "//div[contains(@class, 'pv-top-card-v2-ctas')]//button[contains(.//span, 'Connect')]",
            "//span[text()='Connect']/parent::button",
            "//button[contains(@id, 'ember')][.//span[text()='Connect']]"
        ]
        
        for selector in connect_selectors:
            connect_button = self._find_element(selector)
            if connect_button:
                logger.info(f"Found direct Connect button with selector: {selector}")
                return connect_button
        
        # If no direct connect button found, try the More button
        logger.info("No direct Connect button found, trying More dropdown")
        
        more_selectors = [
            "//button[text()='More']",
            "//button[contains(.//span, 'More')]",
            "//button[contains(@aria-label, 'More actions')]",
            "//button[contains(@class, 'artdeco-dropdown__trigger')]",
            "//div[contains(@class, 'pvs-profile-actions')]//button[contains(.//span, 'More')]"
        ]
        
        for selector in more_selectors:
            more_button = self._find_element(selector)
            if more_button:
                logger.info(f"Found More button with selector: {selector}")
                self._take_screenshot("before_more_click")
                
                # Click the More button
                if self._try_all_click_methods(more_button, "More button"):
                    time.sleep(2)
                    self._take_screenshot("after_more_click")
                    
                    # Now look for Connect in the dropdown
                    dropdown_selectors = [
                        "//div[contains(@class, 'artdeco-dropdown__content')]//span[text()='Connect']/parent::*",
                        "//div[contains(@role, 'menu')]//span[text()='Connect']/parent::*",
                        "//div[contains(@class, 'dropdown-options')]//span[contains(text(), 'Connect')]/parent::*",
                        "//ul[contains(@class, 'dropdown-menu')]//li//*[contains(text(), 'Connect')]",
                        "//div[contains(@class, 'artdeco-dropdown__content')]//div[contains(@role, 'menuitem')][.//span[text()='Connect']]"
                    ]
                    
                    for selector in dropdown_selectors:
                        connect_in_dropdown = self._find_element(selector)
                        if connect_in_dropdown:
                            logger.info(f"Found Connect in dropdown with selector: {selector}")
                            return connect_in_dropdown
                    
                    # If we get here, we couldn't find Connect in the dropdown
                    # Close the dropdown by clicking elsewhere
                    try:
                        self.driver.find_element(By.TAG_NAME, "body").click()
                        time.sleep(1)
                    except:
                        pass
                
                break  # Break after trying the first More button
        
        return None
    
    

    def apply_location_filter(self, location):
        """
        Apply location filter in search with improved reliability.
        """
        logger.info(f"Applying location filter for: {location}")
        self._take_screenshot("before_location_filter")
        
        try:
            # Look for the Locations filter dropdown
            locations_filter_selectors = [
                "//button[contains(@aria-label, 'Locations filter')]",
                "//button[contains(text(), 'Locations')]",
                "//button[.//span[contains(text(), 'Locations')]]",
                "//span[contains(text(), 'Locations')]/ancestor::button",
                "//div[contains(@class, 'search-reusables__filter-dropdown-button')][.//span[contains(text(), 'Locations')]]"
            ]
            
            locations_dropdown = None
            for selector in locations_filter_selectors:
                try:
                    elements = self.driver.find_elements(By.XPATH, selector)
                    for element in elements:
                        if element.is_displayed():
                            locations_dropdown = element
                            logger.info(f"Found locations dropdown with selector: {selector}")
                            break
                    if locations_dropdown:
                        break
                except Exception as e:
                    logger.debug(f"Selector {selector} error: {str(e)}")
            
            if not locations_dropdown:
                # Check if a location pill is already selected
                location_pills = self.driver.find_elements(By.XPATH, 
                    "//div[@role='listitem'][contains(@class, 'search-reusables__primary-filter')]//button[contains(text(), 'Location:')]")
                
                if location_pills:
                    # Remove existing location filters first
                    for pill in location_pills:
                        try:
                            close_btn = pill.find_element(By.XPATH, ".//span[contains(@class, 'close')]")
                            self.driver.execute_script("arguments[0].click();", close_btn)
                            time.sleep(1)
                        except:
                            continue
                
                # Try looking for "All Filters" button
                all_filters_button = None
                all_filters_selectors = [
                    "//button[text()='All filters']",
                    "//button[contains(text(), 'All filters')]",
                    "//button[.//span[contains(text(), 'All filters')]]"
                ]
                
                for selector in all_filters_selectors:
                    try:
                        elements = self.driver.find_elements(By.XPATH, selector)
                        for element in elements:
                            if element.is_displayed():
                                all_filters_button = element
                                logger.info(f"Found All filters button with selector: {selector}")
                                break
                        if all_filters_button:
                            break
                    except:
                        continue
                
                if all_filters_button:
                    # Click All Filters to open modal
                    logger.info("Clicking All Filters button")
                    self.driver.execute_script("arguments[0].click();", all_filters_button)
                    time.sleep(2)
                    self._take_screenshot("all_filters_modal")
                    
                    # Find location section in All Filters modal
                    location_section_selectors = [
                        "//h3[contains(text(), 'Location')]/ancestor::div[contains(@class, 'search-reusables__filter-trigger-dropdown')]",
                        "//h3[contains(text(), 'Location')]/ancestor::div[contains(@class, 'search-filter')]",
                        "//div[contains(@class, 'search-filter')][contains(., 'Location')]",
                        "//fieldset[contains(.//legend, 'Location')]"
                    ]
                    
                    location_section = None
                    for selector in location_section_selectors:
                        try:
                            elements = self.driver.find_elements(By.XPATH, selector)
                            for element in elements:
                                if element.is_displayed():
                                    location_section = element
                                    logger.info(f"Found location section with selector: {selector}")
                                    break
                            if location_section:
                                break
                        except:
                            continue
                    
                    if location_section:
                        # Click to expand location section if needed
                        try:
                            # Check if input field is already visible
                            input_fields = location_section.find_elements(By.XPATH, ".//input[@type='text']")
                            if not any(field.is_displayed() for field in input_fields if field.is_displayed()):
                                logger.info("Expanding location section")
                                self.driver.execute_script("arguments[0].click();", location_section)
                                time.sleep(1)
                        except Exception as e:
                            logger.debug(f"Error checking/expanding location section: {str(e)}")
                        
                        # Look for the location input field
                        location_input = None
                        location_input_selectors = [
                            ".//input[@placeholder='Add a location']",
                            ".//input[contains(@placeholder, 'location')]",
                            ".//input[@type='text']"
                        ]
                        
                        for selector in location_input_selectors:
                            try:
                                elements = location_section.find_elements(By.XPATH, selector)
                                for element in elements:
                                    if element.is_displayed():
                                        location_input = element
                                        logger.info(f"Found location input with selector: {selector}")
                                        break
                                if location_input:
                                    break
                            except:
                                continue
                        
                        if location_input:
                            # Enter location in the input field
                            logger.info(f"Entering location: {location}")
                            location_input.clear()
                            # Type slowly to avoid issues
                            for char in location:
                                location_input.send_keys(char)
                                time.sleep(random.uniform(0.05, 0.1))
                            time.sleep(1)
                            self._take_screenshot("location_entered")
                            
                            # Press Enter to select the first suggestion
                            location_input.send_keys(Keys.ENTER)
                            time.sleep(2)
                            self._take_screenshot("location_selected")
                            
                            # Look for Apply/Show Results button
                            show_results_buttons = self.driver.find_elements(By.XPATH, 
                                "//button[contains(text(), 'Show results') or contains(text(), 'Apply') or contains(@aria-label, 'Apply')]")
                            
                            for button in show_results_buttons:
                                if button.is_displayed():
                                    logger.info("Clicking Show Results button")
                                    self.driver.execute_script("arguments[0].click();", button)
                                    time.sleep(3)  # Wait for search results to update
                                    self._take_screenshot("after_location_applied")
                                    return True
                        else:
                            # If no input field, try checkbox approach
                            logger.info("Looking for location checkboxes")
                            checkbox_found = False
                            
                            # Look for checkbox with the location
                            checkbox_labels = self.driver.find_elements(By.XPATH, f"//label[contains(text(), '{location}')]")
                            for label in checkbox_labels:
                                if label.is_displayed():
                                    logger.info(f"Found checkbox for location: {location}")
                                    self.driver.execute_script("arguments[0].click();", label)
                                    checkbox_found = True
                                    time.sleep(1)
                                    break
                            
                            if not checkbox_found:
                                # Try clicking on elements containing the location text
                                location_elements = self.driver.find_elements(By.XPATH, f"//*[contains(text(), '{location}')]")
                                for element in location_elements:
                                    try:
                                        if element.is_displayed() and element.tag_name in ["span", "div", "label"]:
                                            logger.info(f"Clicking element with text: {location}")
                                            self.driver.execute_script("arguments[0].click();", element)
                                            checkbox_found = True
                                            time.sleep(1)
                                            break
                                    except:
                                        continue
                            
                            if checkbox_found:
                                # Click Apply/Show Results button
                                show_results_buttons = self.driver.find_elements(By.XPATH, 
                                    "//button[contains(text(), 'Show results') or contains(text(), 'Apply') or contains(@aria-label, 'Apply')]")
                                
                                for button in show_results_buttons:
                                    if button.is_displayed():
                                        logger.info("Clicking Show Results button")
                                        self.driver.execute_script("arguments[0].click();", button)
                                        time.sleep(3)  # Wait for search results to update
                                        self._take_screenshot("after_location_applied")
                                        return True
                    
                    # If we get here, try closing the modal and using alternative method
                    close_buttons = self.driver.find_elements(By.XPATH, "//button[contains(@aria-label, 'Dismiss')]")
                    for button in close_buttons:
                        if button.is_displayed():
                            logger.info("Closing All Filters modal")
                            self.driver.execute_script("arguments[0].click();", button)
                            time.sleep(1)
                            break
            
            # If we get here, try using the search-box method directly
            try:
                # Look for the search box
                search_box = self.driver.find_element(By.XPATH, "//input[contains(@class, 'search-global-typeahead__input')]")
                current_search = search_box.get_attribute("value")
                
                # Append location if not already in the search
                if f"location:{location}" not in current_search.lower():
                    new_search = current_search + f" location:{location}"
                    logger.info(f"Adding location directly to search: {new_search}")
                    
                    # Clear and type new search
                    search_box.clear()
                    for char in new_search:
                        search_box.send_keys(char)
                        time.sleep(random.uniform(0.05, 0.1))
                    
                    time.sleep(1)
                    search_box.send_keys(Keys.ENTER)
                    time.sleep(3)  # Wait for search results to update
                    self._take_screenshot("after_location_search")
                    return True
            except Exception as e:
                logger.warning(f"Error adding location to search box: {str(e)}")
            
            logger.warning(f"Could not apply location filter for: {location}")
            return False
            
        except Exception as e:
            logger.error(f"Error applying location filter: {str(e)}")
            self._take_screenshot("location_filter_error")
            return False

    def _apply_industry_filter(self, industry):
        """Apply industry filter in search results."""
        logger.info(f"Applying industry filter: {industry}")
        
        try:
            # Look for All Filters button
            all_filters_button = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'All filters')]"))
            )
            self.driver.execute_script("arguments[0].click();", all_filters_button)
            time.sleep(2)
            self._take_screenshot("all_filters_modal")
            
            # Find and click on Industry section
            industry_section = None
            industry_selectors = [
                "//h3[contains(text(), 'Industry')]/ancestor::div[contains(@class, 'search-filter')]",
                "//div[contains(@class, 'search-filter')][contains(., 'Industry')]",
                "//fieldset[contains(.//legend, 'Industry')]"
            ]
            
            for selector in industry_selectors:
                try:
                    elements = self.driver.find_elements(By.XPATH, selector)
                    for element in elements:
                        if element.is_displayed():
                            industry_section = element
                            logger.info(f"Found industry section with selector: {selector}")
                            break
                    if industry_section:
                        break
                except:
                    continue
            
            if industry_section:
                # Click to expand if needed
                try:
                    # Check if checkbox list is already visible
                    checkboxes = industry_section.find_elements(By.XPATH, ".//input[@type='checkbox']")
                    if not any(checkbox.is_displayed() for checkbox in checkboxes if checkbox.is_displayed()):
                        logger.info("Expanding industry section")
                        self.driver.execute_script("arguments[0].click();", industry_section)
                        time.sleep(1)
                except Exception as e:
                    logger.debug(f"Error checking/expanding industry section: {str(e)}")
                
                # Find industry checkbox
                industry_checkbox = None
                checkbox_selectors = [
                    f".//label[contains(text(), '{industry}')]//input[@type='checkbox']",
                    f".//label[contains(text(), '{industry}')]",
                    f"//label[contains(text(), '{industry}')]"
                ]
                
                for selector in checkbox_selectors:
                    try:
                        elements = self.driver.find_elements(By.XPATH, selector)
                        for element in elements:
                            if element.is_displayed():
                                industry_checkbox = element
                                logger.info(f"Found industry checkbox with selector: {selector}")
                                break
                        if industry_checkbox:
                            break
                    except:
                        continue
                
                if industry_checkbox:
                    # Click the checkbox
                    logger.info(f"Selecting industry: {industry}")
                    self.driver.execute_script("arguments[0].click();", industry_checkbox)
                    time.sleep(1)
                    self._take_screenshot("industry_selected")
                    
                    # Click Apply/Show Results button
                    show_results_buttons = self.driver.find_elements(By.XPATH, 
                        "//button[contains(text(), 'Show results') or contains(text(), 'Apply')]")
                    
                    for button in show_results_buttons:
                        if button.is_displayed():
                            logger.info("Clicking Show Results button")
                            self.driver.execute_script("arguments[0].click();", button)
                            time.sleep(3)  # Wait for search results to update
                            self._take_screenshot("after_industry_filter")
                            return True
                else:
                    logger.warning(f"Could not find checkbox for industry: {industry}")
            
            # If we get here, try closing the modal
            close_buttons = self.driver.find_elements(By.XPATH, "//button[contains(@aria-label, 'Dismiss')]")
            for button in close_buttons:
                if button.is_displayed():
                    logger.info("Closing All Filters modal")
                    self.driver.execute_script("arguments[0].click();", button)
                    time.sleep(1)
                    break
                    
            return False
            
        except Exception as e:
            logger.error(f"Error applying industry filter: {str(e)}")
            self._take_screenshot("industry_filter_error")
            return False
        

    def _find_profile_elements(self):
        """Find all profile elements in search results using CSS selectors."""
        try:
            # Try multiple CSS selectors for profile cards
            css_selectors = [
                "li.reusable-search__result-container",
                "li.entity-result",
                "li.search-result",
                "div.entity-result__item",
                ".search-entity",
                ".entity-result",
                ".artdeco-list__item"  # More generic selector that might catch profile cards
            ]
            
            for selector in css_selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    if elements:
                        logger.info(f"Found {len(elements)} profiles with CSS selector: {selector}")
                        return elements
                except Exception as e:
                    logger.debug(f"CSS selector '{selector}' error: {str(e)}")
            
            # Fallback to looking for profile links
            logger.info("Trying fallback approach with profile links")
            try:
                # Look for profile links directly
                profile_links = self.driver.find_elements(By.CSS_SELECTOR, "a[href*='/in/']")
                
                # For each link find the closest parent that resembles a profile card
                profile_elements = []
                for link in profile_links:
                    try:
                        # Try to find parent elements that could be profile cards
                        parent = None
                        
                        # Try several parent levels to find a good profile card container
                        for level in range(1, 6):  # Try up to 5 levels up
                            try:
                                # Use JavaScript to get the ancestor
                                ancestor_script = f"return arguments[0].parentElement{'.parentElement' * (level-1)};"
                                potential_parent = self.driver.execute_script(ancestor_script, link)
                                
                                # Check if this parent seems to be a profile card
                                if potential_parent:
                                    class_name = potential_parent.get_attribute("class") or ""
                                    if any(keyword in class_name.lower() for keyword in ["result", "entity", "item", "card"]):
                                        parent = potential_parent
                                        break
                            except:
                                continue
                        
                        # If we found a valid parent, add it to our list
                        if parent and parent not in profile_elements:
                            profile_elements.append(parent)
                        # If we can't find a valid parent, use the closest div as fallback
                        elif link not in profile_elements:
                            # Add the link itself as a last resort
                            profile_elements.append(link)
                    except:
                        continue
                        
                if profile_elements:
                    logger.info(f"Found {len(profile_elements)} profiles using link fallback approach")
                    return profile_elements
            except Exception as e:
                logger.debug(f"Error in fallback approach: {str(e)}")
                
            logger.warning("Could not find any profile elements using any method")
            return []
        
        except Exception as e:
            logger.error(f"Error finding profile elements: {str(e)}")
            return []

    def _extract_profile_data(self, profile_element, industry=None):
        """Extract profile data with improved CSS selector approach."""
        try:
            profile_data = {
                'profile': "",
                'full_name': "",
                'job_title': "",
                'company': "",
                'location': "",
                'industry': industry or ""
            }
            
            # Extract profile URL - try both CSS and XPath for maximum reliability
            try:
                # First try CSS selector
                profile_links = profile_element.find_elements(By.CSS_SELECTOR, "a[href*='/in/']")
                
                # For each link, get the href and stop at the first valid one
                for link in profile_links:
                    href = link.get_attribute("href")
                    if href and '/in/' in href:
                        # Clean the URL by removing tracking parameters
                        profile_data['profile'] = href.split("?")[0]
                        break
                        
                # If we didn't find a profile, try alternate methods
                if not profile_data['profile']:
                    # Look for any link with "/in/" in the URL using XPath as fallback
                    links = profile_element.find_elements(By.TAG_NAME, "a")
                    for link in links:
                        href = link.get_attribute("href")
                        if href and '/in/' in href:
                            profile_data['profile'] = href.split("?")[0]
                            break
            except Exception as e:
                logger.debug(f"Error extracting profile URL: {str(e)}")
            
            # Extract name with multiple approaches
            try:
                # Multiple CSS selectors to try for names
                name_selectors = [
                    ".entity-result__title-text span[dir='ltr']",
                    ".entity-result__title-text",
                    ".actor-name",
                    "a[href*='/in/'] span",
                    ".name",
                    ".artdeco-entity-lockup__title",
                    ".app-aware-link span"  # Another common pattern
                ]
                
                # Try each selector until we find a name
                for selector in name_selectors:
                    try:
                        name_elements = profile_element.find_elements(By.CSS_SELECTOR, selector)
                        for element in name_elements:
                            if element.is_displayed():
                                name_text = element.text.strip()
                                if name_text:
                                    profile_data['full_name'] = name_text
                                    break
                        if profile_data['full_name']:
                            break
                    except:
                        continue
                        
                # Fallback to profile link text if name not found
                if not profile_data['full_name']:
                    profile_links = profile_element.find_elements(By.CSS_SELECTOR, "a[href*='/in/']")
                    for link in profile_links:
                        if link.is_displayed():
                            link_text = link.text.strip()
                            if link_text:
                                profile_data['full_name'] = link_text
                                break
                                
                # Last resort - try to get name from URL
                if not profile_data['full_name'] and profile_data['profile']:
                    try:
                        # Extract from /in/firstname-lastname pattern
                        profile_path = profile_data['profile'].split('/in/')[-1].split('/')[0].split('?')[0]
                        extracted_name = profile_path.replace('-', ' ').replace('.', ' ').title()
                        if len(extracted_name) > 3:  # Ensure it's a reasonable name length
                            profile_data['full_name'] = extracted_name
                    except:
                        pass
            except Exception as e:
                logger.debug(f"Error extracting name: {str(e)}")
                    
            # Extract job title
            try:
                # Multiple CSS selectors for job titles
                job_selectors = [
                    ".entity-result__primary-subtitle",
                    ".subline-level-1",
                    ".artdeco-entity-lockup__subtitle",
                    ".entity-result__summary span",
                    ".job-title",
                    ".headline"
                ]
                
                for selector in job_selectors:
                    try:
                        elements = profile_element.find_elements(By.CSS_SELECTOR, selector)
                        for element in elements:
                            if element.is_displayed():
                                text = element.text.strip()
                                if text:
                                    profile_data['job_title'] = text
                                    break
                        if profile_data['job_title']:
                            break
                    except:
                        continue
            except Exception as e:
                logger.debug(f"Error extracting job title: {str(e)}")
                
            # Extract company
            try:
                # Multiple CSS selectors for company names
                company_selectors = [
                    ".entity-result__secondary-subtitle",
                    ".subline-level-2",
                    ".artdeco-entity-lockup__subtitle:nth-child(2)",
                    ".company-name",
                    ".org-name"
                ]
                
                for selector in company_selectors:
                    try:
                        elements = profile_element.find_elements(By.CSS_SELECTOR, selector)
                        for element in elements:
                            if element.is_displayed():
                                text = element.text.strip()
                                if text:
                                    profile_data['company'] = text
                                    break
                        if profile_data['company']:
                            break
                    except:
                        continue
            except Exception as e:
                logger.debug(f"Error extracting company: {str(e)}")
                
            # Extract location
            try:
                # Multiple CSS selectors for location
                location_selectors = [
                    ".entity-result__tertiary-subtitle",
                    ".subline-level-3",
                    ".artdeco-entity-lockup__caption",
                    ".location"
                ]
                
                for selector in location_selectors:
                    try:
                        elements = profile_element.find_elements(By.CSS_SELECTOR, selector)
                        for element in elements:
                            if element.is_displayed():
                                text = element.text.strip()
                                if text:
                                    profile_data['location'] = text
                                    break
                        if profile_data['location']:
                            break
                    except:
                        continue
            except Exception as e:
                logger.debug(f"Error extracting location: {str(e)}")
                
            # Log the extracted data for debugging
            logger.debug(f"Extracted profile data: URL={profile_data['profile']}, Name={profile_data['full_name']}, " +
                         f"Title={profile_data['job_title']}, Company={profile_data['company']}, Location={profile_data['location']}")
                        
            return profile_data
        except Exception as e:
            logger.warning(f"Error extracting profile data: {str(e)}")
            return None

    def _save_profiles_to_csv(self, profiles_data, filename):
        """Save profile data to CSV with improved error handling."""
        try:
            if not profiles_data:
                logger.warning("No profile data to save")
                return False
                
            # Ensure directory exists
            os.makedirs(os.path.dirname(os.path.abspath(filename)) if os.path.dirname(filename) else '.', exist_ok=True)
            
            # Define the fieldnames
            fieldnames = ['profile', 'full_name', 'job_title', 'company', 'location', 'industry']
            
            # Ensure all profiles have all required fields
            for profile in profiles_data:
                for field in fieldnames:
                    if field not in profile:
                        profile[field] = ""
                        
            # Write to CSV with explicit encoding
            with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                for profile in profiles_data:
                    # Ensure all values are strings to prevent type errors
                    profile_row = {key: str(value) if value is not None else "" for key, value in profile.items() if key in fieldnames}
                    writer.writerow(profile_row)
                    
            logger.info(f"Successfully saved {len(profiles_data)} profiles to {filename}")
            return True
        except Exception as e:
            logger.error(f"Error saving profiles to CSV: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return False
        

    def search_and_save_profiles(self, job_title, industry=None, location=None, limit=100, filename="profiles.csv"):
        """
        Search LinkedIn for profiles matching the job title and industry/location and save to CSV.
        
        Args:
            job_title (str): Job title to search for
            industry (str, optional): Industry to filter by
            location (str, optional): Location to filter by
            limit (int): Maximum number of profiles to collect
            filename (str): CSV filename to save the results
            
        Returns:
            int: Number of profiles found and saved
        """
        logger.info(f"Searching for profiles with job title: '{job_title}'")
        if industry:
            logger.info(f"Industry filter: '{industry}'")
        if location:
            logger.info(f"Location filter: '{location}'")
        
        # Navigate to LinkedIn search page and perform search
        try:
            # Start directly with the people search page
            self.driver.get("https://www.linkedin.com/search/results/people/")
            time.sleep(random.uniform(2, 4))
            self._take_screenshot("search_page_initial")
            
            # Find and use the search box
            try:
                # Wait for search box to be available
                search_box = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "input.search-global-typeahead__input"))
                )
                
                # Create search query with all parameters
                search_query = job_title
                if location:
                    search_query += f" location:{location}"
                    
                # Clear and enter search terms
                logger.info(f"Entering search query: {search_query}")
                search_box.clear()
                for char in search_query:
                    search_box.send_keys(char)
                    time.sleep(random.uniform(0.05, 0.1))
                    
                self._take_screenshot("search_terms_entered")
                
                # Submit search query
                search_box.send_keys(Keys.RETURN)
                time.sleep(random.uniform(3, 5))
                self._take_screenshot("search_results_initial")
                
                # Apply industry filter if provided
                if industry:
                    self._apply_industry_filter(industry)
                    time.sleep(random.uniform(2, 3))
                    self._take_screenshot("after_industry_filter")
                    
                # Wait for search results to fully load
                time.sleep(3)
                
                # Initialize data collection
                profiles_data = []
                profiles_processed = 0
                page_num = 1
                pages_without_new_profiles = 0
                max_empty_pages = 3  # Maximum number of pages to check with no new profiles before giving up
                
                # Now process search results
                while profiles_processed < limit and pages_without_new_profiles < max_empty_pages:
                    logger.info(f"Scanning search results page {page_num}")
                    self._take_screenshot(f"search_page_{page_num}")
                    
                    # Find all profile cards on the current page
                    profile_elements = self._find_profile_elements()
                    
                    if not profile_elements:
                        logger.info("No profiles found on this page")
                        pages_without_new_profiles += 1
                        
                        if pages_without_new_profiles >= max_empty_pages:
                            logger.info(f"No new profiles found for {max_empty_pages} consecutive pages, stopping search")
                            break
                        
                        # Try going to the next page
                        if self._go_to_next_page():
                            page_num += 1
                            continue
                        else:
                            break
                    
                    logger.info(f"Found {len(profile_elements)} profile elements on page {page_num}")
                    
                    # Track if we found any new profiles on this page
                    new_profiles_on_page = 0
                    
                    # Process each profile on the page
                    for profile_element in profile_elements:
                        if profiles_processed >= limit:
                            break
                        
                        try:
                            # Extract profile data
                            profile_data = self._extract_profile_data(profile_element, industry)
                            
                            # Only add profiles that have at least a URL and name
                            if profile_data and profile_data.get('profile'):
                                # Check if profile URL looks valid
                                if '/in/' in profile_data['profile']:
                                    # Check if we already have this profile
                                    if not any(p.get('profile') == profile_data['profile'] for p in profiles_data):
                                        profiles_data.append(profile_data)
                                        profiles_processed += 1
                                        new_profiles_on_page += 1
                                        logger.info(f"Added profile {profiles_processed}/{limit}: " +
                                                f"{profile_data.get('full_name', 'Unknown')} - {profile_data.get('profile')}")
                                else:
                                    logger.warning(f"Skipping invalid profile URL: {profile_data.get('profile')}")
                        except Exception as e:
                            logger.warning(f"Error extracting profile data: {str(e)}")
                    
                    # Update consecutive empty pages counter
                    if new_profiles_on_page == 0:
                        pages_without_new_profiles += 1
                        logger.info(f"No new profiles found on page {page_num}")
                    else:
                        pages_without_new_profiles = 0  # Reset counter if we found profiles
                    
                    # Save intermediate results every page
                    if profiles_data:
                        self._save_profiles_to_csv(profiles_data, filename)
                        logger.info(f"Saved {len(profiles_data)} profiles so far")
                    
                    # Go to next page if needed
                    if profiles_processed < limit:
                        if self._go_to_next_page():
                            page_num += 1
                        else:
                            logger.info("No more pages available")
                            break
                
                # Final save to CSV
                if profiles_data:
                    success = self._save_profiles_to_csv(profiles_data, filename)
                    if success:
                        logger.info(f"Successfully saved {len(profiles_data)} profiles to {filename}")
                        return len(profiles_data)
                    else:
                        logger.error("Failed to save profiles to CSV")
                        return 0
                else:
                    logger.warning("No profiles found matching the criteria")
                    return 0
                    
            except Exception as e:
                logger.error(f"Error during search: {str(e)}")
                import traceback
                logger.error(traceback.format_exc())
                self._take_screenshot("search_error")
                return 0
                
        except Exception as e:
            logger.error(f"Error navigating to search page: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            self._take_screenshot("navigation_error")
            return 0
        

    def process_profiles_from_csv(self, csv_file, profile_url_column, name_column=None, action='connect', csv_output=None):
        """
        Process LinkedIn profiles from a CSV file with improved error handling and reporting.
        
        Args:
            csv_file (str): Path to CSV file containing profile URLs
            profile_url_column (str): Column name containing LinkedIn profile URLs
            name_column (str, optional): Column name containing names for personalization
            action (str): Action to take ('connect', 'message', or 'both')
            csv_output (str, optional): Path to save results CSV
            
        Returns:
            list: Results of operations with connection statuses
        """
        try:
            # Read CSV file
            with open(csv_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                profiles = list(reader)
            
            logger.info(f"Loaded {len(profiles)} profiles from {csv_file}")
            
            # Check if profile URL column exists
            if not profiles or profile_url_column not in profiles[0]:
                available_columns = list(profiles[0].keys()) if profiles else []
                logger.error(f"Column '{profile_url_column}' not found in CSV file. Available columns: {', '.join(available_columns)}")
                
                # Try to find a suitable column
                url_column_candidates = [col for col in available_columns if any(keyword in col.lower() for keyword in ['url', 'link', 'profile', 'linkedin'])]
                if url_column_candidates:
                    profile_url_column = url_column_candidates[0]
                    logger.info(f"Using '{profile_url_column}' as the profile URL column instead")
                else:
                    return []
            
            # Create results list
            results = []
            successful_count = 0
            failed_count = 0
            already_connected_count = 0
            already_pending_count = 0
            
            for idx, row in enumerate(profiles):
                # Skip empty URLs
                if not row.get(profile_url_column):
                    logger.warning(f"Skipping row {idx+1} - empty URL")
                    continue
                
                profile_url = row[profile_url_column].strip()
                
                # Ensure URL is valid LinkedIn profile URL
                if not profile_url.startswith(('https://www.linkedin.com/in/', 'https://linkedin.com/in/')):
                    if 'linkedin.com' in profile_url and '/in/' in profile_url:
                        # Try to extract the profile URL
                        parts = profile_url.split('/in/')
                        if len(parts) > 1:
                            profile_url = f"https://www.linkedin.com/in/{parts[1].split('?')[0].split('#')[0]}"
                            logger.info(f"Fixed profile URL: {profile_url}")
                        else:
                            logger.warning(f"Skipping invalid LinkedIn URL: {profile_url}")
                            continue
                    else:
                        logger.warning(f"Skipping invalid LinkedIn URL: {profile_url}")
                        continue
                
                logger.info(f"Processing profile {idx+1}/{len(profiles)}: {profile_url}")
                
                result = {
                    'profile_url': profile_url,
                    'connect_status': False,
                    'message_status': False,
                    'connection_state': 'unknown',
                    'note': '',
                    'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
                
                # Get name for personalization
                profile_name = None
                if name_column and name_column in row and row[name_column]:
                    profile_name = row[name_column].strip()
                else:
                    # Extract name from URL if name column not provided
                    try:
                        # Extract from /in/firstname-lastname pattern
                        profile_path = profile_url.split('/in/')[-1].split('/')[0].split('?')[0]
                        profile_name = profile_path.replace('-', ' ').replace('.', ' ').title()
                    except:
                        profile_name = "there"  # Fallback
                
                logger.info(f"Using name: {profile_name}")
                
                # Personalize message
                personalized_note = self.message_template
                if '{name}' in personalized_note and profile_name:
                    personalized_note = personalized_note.replace('{name}', profile_name)
                
                # Check if daily limit reached
                if self.request_count >= self.daily_limit and action in ['connect', 'both']:
                    logger.warning(f"Daily connection limit reached ({self.daily_limit}). Stopping automation.")
                    result['note'] = 'Skipped due to daily limit'
                    results.append(result)
                    break
                
                # Check connection status first
                connection_state = self.check_connection_status(profile_url)
                result['connection_state'] = connection_state
                
                # Update counts based on connection state
                if connection_state == 'connected':
                    already_connected_count += 1
                    result['note'] = 'Already connected'
                elif connection_state == 'pending':
                    already_pending_count += 1
                    result['note'] = 'Request already pending'
                
                # Send connection request if not already connected or pending
                if action in ['connect', 'both']:
                    if connection_state in ['pending', 'connected']:
                        logger.info(f"Skipping connection request as status is: {connection_state}")
                        result['connect_status'] = True
                    else:
                        start_time = time.time()
                        result['connect_status'] = self.send_connection_request(profile_url, personalized_note)
                        end_time = time.time()
                        
                        # Update result note and counts
                        if result['connect_status']:
                            successful_count += 1
                            result['note'] = f'Connection request sent (took {end_time - start_time:.1f}s)'
                        else:
                            failed_count += 1
                            result['note'] = f'Failed to send connection request (after {end_time - start_time:.1f}s)'
                    
                # Add result to list
                results.append(result)
                
                # Save intermediate results every 5 profiles or after failures
                if csv_output and (idx % 5 == 0 or not result['connect_status']):
                    self._save_results_to_csv(results, csv_output)
                
                # Add random delay between requests to avoid being flagged
                if idx < len(profiles) - 1:
                    delay = random.uniform(self.connection_delay[0], self.connection_delay[1])
                    logger.info(f"Waiting for {delay:.2f} seconds before next profile...")
                    time.sleep(delay)
            
            # Final save to CSV
            if csv_output:
                self._save_results_to_csv(results, csv_output)
                logger.info(f"Results saved to {csv_output}")
            
            # Print statistics
            logger.info("\nConnection Request Statistics:")
            logger.info(f"Total profiles processed: {len(results)}")
            logger.info(f"Successful new requests: {successful_count}")
            logger.info(f"Failed requests: {failed_count}")
            logger.info(f"Already connected: {already_connected_count}")
            logger.info(f"Already pending: {already_pending_count}")
            
            return results
        
        except Exception as e:
            logger.error(f"Error processing profiles from CSV: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return []

    def _save_results_to_csv(self, results, csv_file):
        """Save results to CSV file with improved error handling and column formatting."""
        try:
            # Ensure directory exists
            directory = os.path.dirname(csv_file)
            if directory and not os.path.exists(directory):
                os.makedirs(directory)
                
            # Define columns with explicit order
            fieldnames = [
                'profile_url', 
                'connect_status', 
                'message_status', 
                'connection_state', 
                'note', 
                'timestamp'
            ]
            
            # Ensure all results have all required fields
            for result in results:
                for field in fieldnames:
                    if field not in result:
                        result[field] = ""
            
            # Write to CSV
            with open(csv_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                for result in results:
                    # Create a new dict with only the fields we want, in the right order
                    row = {field: result.get(field, "") for field in fieldnames}
                    writer.writerow(row)
                    
            logger.debug(f"Saved {len(results)} results to {csv_file}")
        except Exception as e:
            logger.error(f"Error saving results to CSV: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())

    
    def close(self):
        """Close the browser."""
        if self.driver:
            self.driver.quit()


def main():
    """Main function to run the automation with improved connection status handling."""
    # Load environment variables from .env file
    load_dotenv()
    
    parser = argparse.ArgumentParser(description='LinkedIn Automation Tool')
    parser.add_argument('--csv', help='Path to CSV file with LinkedIn profile URLs')
    parser.add_argument('--url-column', help='Column name in CSV that contains profile URLs')
    parser.add_argument('--name-column', help='Column name in CSV that contains names (optional)')
    parser.add_argument('--action', choices=['connect', 'message', 'both'], help='Action to perform')
    parser.add_argument('--headless', action='store_true', help='Run browser in headless mode')
    parser.add_argument('--output', help='Path to save results CSV')
    parser.add_argument('--manual-login', action='store_true', help='Wait for manual login')
    parser.add_argument('--debug', action='store_true', help='Enable debug mode (extra logging and screenshots)')
    parser.add_argument('--email', help='LinkedIn login email (overrides .env)')
    parser.add_argument('--password', help='LinkedIn login password (overrides .env)')
    parser.add_argument('--message', help='Custom connection message (overrides .env)')
    parser.add_argument('--delay-min', type=int, help='Minimum delay between requests (seconds)')
    parser.add_argument('--delay-max', type=int, help='Maximum delay between requests (seconds)')
    parser.add_argument('--limit', type=int, help='Daily connection request limit')
    # Add search-related arguments
    parser.add_argument('--job-title', help='Job title to search for')
    parser.add_argument('--industry', help='Industry to filter by')
    parser.add_argument('--location', help='Location to filter by')
    parser.add_argument('--search-limit', type=int, default=100, help='Maximum number of profiles to collect')
    parser.add_argument('--search-output', default='profiles.csv', help='File to save search results')
    
    args = parser.parse_args()
    
    # Set debug level if requested
    if args.debug or os.getenv('LINKEDIN_DEBUG', 'false').lower() == 'true':
        logging.getLogger().setLevel(logging.DEBUG)
        logger.debug("Debug mode enabled")
    
    # Print current working directory for debugging
    logger.debug(f"Current working directory: {os.getcwd()}")
    
    # Check .env file existence
    env_file = os.path.join(os.getcwd(), '.env')
    if os.path.exists(env_file):
        logger.debug(f".env file found at {env_file}")
    else:
        logger.warning(f".env file not found at {env_file}")
    
    # Get settings from environment variables with fallbacks to defaults
    email = args.email if hasattr(args, 'email') and args.email else os.getenv('LINKEDIN_EMAIL')
    password = args.password if hasattr(args, 'password') and args.password else os.getenv('LINKEDIN_PASSWORD')
    message_template = args.message if hasattr(args, 'message') and args.message else os.getenv('LINKEDIN_MESSAGE', 'Hello {name}, I would like to connect with you.')
    
    # Get search parameters
    job_title = args.job_title or os.getenv('LINKEDIN_JOB_TITLE')
    industry = args.industry or os.getenv('LINKEDIN_INDUSTRY')
    location = args.location or os.getenv('LINKEDIN_LOCATION')
    search_limit = args.search_limit or int(os.getenv('LINKEDIN_SEARCH_LIMIT', '50'))
    search_output = args.search_output or os.getenv('LINKEDIN_SEARCH_OUTPUT', 'profiles.csv')
    process_after_search = os.getenv('LINKEDIN_PROCESS_AFTER_SEARCH', 'true').lower() == 'true'

    # Check if we're in search mode
    search_mode = job_title is not None

    # Log env vars (without password)
    logger.debug(f"Email set: {'Yes' if email else 'No'}")
    logger.debug(f"Message template from env: {'Yes' if os.getenv('LINKEDIN_MESSAGE') else 'No'}")
    
    # Message template from file if specified
    message_template_file = os.getenv('LINKEDIN_MESSAGE_FILE')
    if message_template_file:
        logger.debug(f"Looking for message template file: {message_template_file}")
        if os.path.exists(message_template_file):
            try:
                with open(message_template_file, 'r', encoding='utf-8') as f:
                    message_template = f.read().strip()
                logger.debug(f"Loaded message template from file ({len(message_template)} chars)")
            except Exception as e:
                logger.error(f"Error reading message template file: {str(e)}")
        else:
            logger.warning(f"Message template file not found: {message_template_file}")
    
    # Connection limits and delays
    try:
        delay_min = args.delay_min if hasattr(args, 'delay_min') and args.delay_min is not None else int(os.getenv('LINKEDIN_DELAY_MIN', 20))
        delay_max = args.delay_max if hasattr(args, 'delay_max') and args.delay_max is not None else int(os.getenv('LINKEDIN_DELAY_MAX', 40))
        daily_limit = args.limit if hasattr(args, 'limit') and args.limit is not None else int(os.getenv('LINKEDIN_DAILY_LIMIT', 40))
        logger.debug(f"Delay range: {delay_min}-{delay_max}s, Daily limit: {daily_limit}")
    except ValueError as e:
        logger.error(f"Error parsing numeric settings: {str(e)}")
        logger.warning("Using default values instead")
        delay_min, delay_max, daily_limit = 20, 40, 40

    # CSV file and columns from env or args
    csv_file = args.csv or os.getenv('LINKEDIN_CSV_FILE')
    url_column = args.url_column or os.getenv('LINKEDIN_URL_COLUMN', 'profile')
    name_column = args.name_column or os.getenv('LINKEDIN_NAME_COLUMN', 'full_name')
    
    # Check if CSV file exists
    if csv_file:
        logger.debug(f"CSV file path: {csv_file}")
        if os.path.exists(csv_file):
            logger.debug(f"CSV file found: {csv_file}")
            # Preview CSV headers if possible
            try:
                with open(csv_file, 'r', encoding='utf-8') as f:
                    reader = csv.reader(f)
                    headers = next(reader, [])
                    logger.debug(f"CSV columns: {', '.join(headers)}")
                    if url_column not in headers:
                        logger.warning(f"URL column '{url_column}' not found in CSV. Available columns: {', '.join(headers)}")
                        # Try to find a suitable column
                        url_candidates = [col for col in headers if any(keyword in col.lower() for keyword in ['url', 'link', 'profile', 'linkedin'])]
                        if url_candidates:
                            url_column = url_candidates[0]
                            logger.info(f"Using '{url_column}' as the URL column instead")
            except Exception as e:
                logger.warning(f"Could not preview CSV headers: {str(e)}")
        else:
            logger.error(f"CSV file not found: {csv_file}")
            if not search_mode:
                csv_file = None
    
    # Action from env or args
    action = args.action or os.getenv('LINKEDIN_ACTION', 'connect')
    logger.debug(f"Action: {action}")
    
    # Output file
    output_file = args.output or os.getenv('LINKEDIN_OUTPUT_FILE', 'linkedin_results.csv')
    logger.debug(f"Output file: {output_file}")
    
    # Headless mode
    headless = args.headless or os.getenv('LINKEDIN_HEADLESS', 'false').lower() == 'true'
    logger.debug(f"Headless mode: {headless}")
    
    # Manual login mode
    manual_login = args.manual_login or os.getenv('LINKEDIN_MANUAL_LOGIN', 'false').lower() == 'true'
    logger.debug(f"Manual login mode: {manual_login}")
    
    # Debug mode for screenshots
    debug_mode = args.debug or os.getenv('LINKEDIN_DEBUG', 'false').lower() == 'true'
    
    # Validate required parameters
    if not manual_login and (not email or not password):
        logger.error("LinkedIn email and password are required for automated login. Set these in .env file or use --manual-login.")
        return

    # Only check for CSV file if we're not in search mode
    if not search_mode and not csv_file:
        logger.error("CSV file not provided and search mode not enabled. Set LINKEDIN_CSV_FILE in .env file, provide with --csv argument, or use search parameters.")
        return
    
    # Initialize automation
    automation = LinkedInAutomation(
        email=email,
        password=password,
        message_template=message_template,
        connection_delay=(delay_min, delay_max),
        daily_limit=daily_limit,
        debug_mode=debug_mode
    )
    
    try:
        # Setup driver
        automation.setup_driver(headless=headless)
        
        # Login to LinkedIn
        login_success = False
        
        if manual_login:
            logger.info("Manual login mode enabled. Please log in manually in the browser window...")
            login_success = automation.manual_login()
            if not login_success:
                logger.error("Manual login failed or timed out. Exiting.")
                return
        else:
            # Try automated login up to 3 times
            for attempt in range(3):
                logger.info(f"Login attempt {attempt + 1}/3")
                if automation.login():
                    login_success = True
                    break
                time.sleep(5)
        
        if not login_success:
            logger.error("Failed to log in after multiple attempts. Try using manual login mode with --manual-login")
            return
        
        # If we're in search mode, perform the search first
        if search_mode:
            logger.info(f"Starting LinkedIn search for {job_title}")
            if industry:
                logger.info(f"With industry filter: {industry}")
            if location:
                logger.info(f"With location filter: {location}")
                
            num_profiles = automation.search_and_save_profiles(
                job_title=job_title,
                industry=industry,
                location=location,
                limit=search_limit,
                filename=search_output
            )
            
            if num_profiles == 0:
                logger.error("No profiles found matching the search criteria. Exiting.")
                return
            
            logger.info(f"Search complete. Found {num_profiles} profiles and saved to {search_output}")
            
            # If we shouldn't process after search, exit here
            if not process_after_search and not args.action:
                logger.info("Search completed. Skipping connection requests as per configuration.")
                return
            
            # Set CSV file to the search output file
            csv_file = search_output
        
        # Process profiles from CSV
        results = automation.process_profiles_from_csv(
            csv_file=csv_file,
            profile_url_column=url_column,
            name_column=name_column,
            action=action,
            csv_output=output_file
        )
        
        # Print summary
        logger.info("\nSummary:")
        if results:
            logger.info(f"Total profiles processed: {len(results)}")
            if action in ['connect', 'both']:
                success_connects = sum(1 for r in results if r.get('connect_status', False))
                success_rate = (success_connects/len(results)*100) if len(results) > 0 else 0
                logger.info(f"Successful connection requests: {success_connects}/{len(results)} ({success_rate:.1f}%)")
                
                # Add detailed connection status breakdown
                already_connected = sum(1 for r in results if r.get('connection_state') == 'connected')
                pending = sum(1 for r in results if r.get('connection_state') == 'pending')
                new_requests = success_connects - already_connected - pending
                
                logger.info(f"Connection breakdown:")
                logger.info(f"  - Already connected: {already_connected}")
                logger.info(f"  - Already pending: {pending}")
                logger.info(f"  - New requests sent: {new_requests}")
        else:
            logger.warning("No profiles were processed")
    
    except Exception as e:
        logger.error(f"An error occurred: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
    
    finally:
        # Clean up
        automation.close()


if __name__ == "__main__":
    main()
    
