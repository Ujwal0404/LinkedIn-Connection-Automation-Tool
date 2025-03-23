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
    
    def send_connection_request(self, profile_url, personalized_note=None):
        """
        Send a connection request to a LinkedIn profile with improved selector strategies.
        
        Args:
            profile_url (str): URL of the LinkedIn profile
            personalized_note (str, optional): Personalized note to send with request
        
        Returns:
            bool: True if request sent successfully, False otherwise
        """
        # Check daily limit
        if self.request_count >= self.daily_limit:
            logger.warning(f"Daily connection limit reached ({self.daily_limit}). Skipping request.")
            return False
            
        try:
            # Navigate to profile
            logger.info(f"Navigating to {profile_url}")
            self.driver.get(profile_url)
            time.sleep(random.uniform(5, 7))  # Longer initial wait
            self._take_screenshot("profile_page")
            
            # Force a page refresh to ensure elements are loaded
            self.driver.refresh()
            time.sleep(random.uniform(4, 6))
            self._take_screenshot("after_refresh")
            
            # Multiple strategies to find the connect button
            connect_button = None
            
            # New Strategy: Look for direct "Connect" button visible in page (common UI pattern)
            try:
                logger.info("Trying visible Connect button")
                # Look for all visible connect buttons
                buttons = self.driver.find_elements(By.XPATH, "//button[contains(.//span, 'Connect') or contains(text(), 'Connect')]")
                
                # Filter for visible buttons
                visible_buttons = []
                for button in buttons:
                    try:
                        if button.is_displayed():
                            visible_buttons.append(button)
                    except:
                        continue
                
                if visible_buttons:
                    connect_button = visible_buttons[0]
                    logger.info(f"Found visible Connect button ({len(visible_buttons)} buttons found)")
            except Exception as e:
                logger.warning(f"Error finding visible buttons: {str(e)}")
            
            # Strategy 1: Click a Connect button that's already on the page
            if not connect_button:
                try:
                    logger.info("Trying to find direct Connect button by text")
                    selectors = [
                        "//button[contains(text(), 'Connect')]",
                        "//button[.//span[contains(text(), 'Connect')]]",
                        "//button[contains(@aria-label, 'Connect')]",
                    ]
                    
                    for selector in selectors:
                        elements = self.driver.find_elements(By.XPATH, selector)
                        for element in elements:
                            try:
                                if element.is_displayed():
                                    connect_button = element
                                    logger.info(f"Found direct Connect button with selector: {selector}")
                                    break
                            except:
                                continue
                        if connect_button:
                            break
                except Exception as e:
                    logger.warning(f"Error with direct button strategy: {str(e)}")
            
            # Strategy 2: "Connect" button in primary actions section
            if not connect_button:
                try:
                    logger.info("Looking for Connect in primary actions")
                    # Primary buttons section - might contain Connect as a primary action
                    primary_buttons = self.driver.find_elements(By.XPATH, 
                        "//div[contains(@class, 'pvs-profile-actions')]//button | //div[contains(@class, 'pv-top-card')]//button")
                    
                    for button in primary_buttons:
                        try:
                            button_text = button.text.lower()
                            if 'connect' in button_text and button.is_displayed():
                                connect_button = button
                                logger.info("Found Connect in primary actions")
                                break
                        except:
                            continue
                except Exception as e:
                    logger.warning(f"Error with primary actions strategy: {str(e)}")
            
            # Strategy 3: More button that might contain Connect
            if not connect_button:
                try:
                    logger.info("Looking for More button")
                    # Try different patterns for the More button
                    more_selectors = [
                        "//button[contains(.//span, 'More')]",
                        "//button[text()='More']",
                        "//button[contains(@aria-label, 'More actions')]",
                        "//div[contains(@class, 'pvs-profile-actions')]//button[last()]",
                        "//div[contains(@class, 'pv-top-card')]//button[last()]"
                    ]
                    
                    more_button = None
                    for selector in more_selectors:
                        elements = self.driver.find_elements(By.XPATH, selector)
                        for element in elements:
                            try:
                                if element.is_displayed():
                                    more_button = element
                                    logger.info(f"Found More button with selector: {selector}")
                                    break
                            except:
                                continue
                        if more_button:
                            break
                    
                    if more_button:
                        self._take_screenshot("before_more_click")
                        
                        # Use JavaScript click which is more reliable
                        self.driver.execute_script("arguments[0].click();", more_button)
                        logger.info("Clicked More button with JavaScript")
                        time.sleep(3)  # Longer wait for dropdown
                        self._take_screenshot("after_more_click")
                        
                        # Now look for Connect in the dropdown - try multiple approaches
                        try:
                            # Wait for dropdown to appear
                            WebDriverWait(self.driver, 5).until(
                                EC.visibility_of_element_located((By.XPATH, "//div[contains(@class, 'artdeco-dropdown__content')]"))
                            )
                            
                            # Look for Connect in dropdown with multiple patterns
                            dropdown_selectors = [
                                "//div[contains(@class, 'artdeco-dropdown__content')]//span[text()='Connect']/..",
                                "//div[contains(@class, 'artdeco-dropdown__content')]//span[contains(text(), 'Connect')]/..",
                                "//div[contains(@class, 'artdeco-dropdown__content')]//li[@role='menuitem'][contains(., 'Connect')]",
                                "//div[contains(@class, 'artdeco-dropdown__content')]//li[contains(@class, 'artdeco-dropdown__item')][1]",
                                "//div[contains(@role, 'menu')]//span[text()='Connect']/..",
                                "//div[contains(@role, 'menu')]//span[contains(text(), 'Connect')]/.."
                            ]
                            
                            for selector in dropdown_selectors:
                                elements = self.driver.find_elements(By.XPATH, selector)
                                for element in elements:
                                    try:
                                        if element.is_displayed():
                                            connect_button = element
                                            logger.info(f"Found connect in dropdown with selector: {selector}")
                                            break
                                    except:
                                        continue
                                if connect_button:
                                    break
                        except Exception as e:
                            logger.warning(f"Error finding Connect in dropdown: {str(e)}")
                            self._take_screenshot("dropdown_error")
                except Exception as e:
                    logger.warning(f"Error with More button strategy: {str(e)}")
                    self._take_screenshot("more_button_failure")
            
            # Strategy 4: Try clicking the Connect button on specific page sections
            if not connect_button:
                try:
                    logger.info("Trying profile page specific Connect buttons")
                    # Specific profile page sections that might contain connect buttons
                    page_specific_selectors = [
                        "//main//button[contains(text(), 'Connect')]",
                        "//main//button[contains(.//span, 'Connect')]",
                        "//button[@data-control-name='connect']",
                        "//button[contains(@class, 'connect')]",
                        "//button[contains(@class, 'artdeco-button')][contains(.//span, 'Connect')]",
                        "//div[contains(@class, 'pvs-profile-actions')]//button[2]",  # Sometimes the second button
                        "//button[contains(@aria-label, 'Invite')]",
                        "//span[text()='Connect']/ancestor::button"
                    ]
                    
                    for selector in page_specific_selectors:
                        elements = self.driver.find_elements(By.XPATH, selector)
                        for element in elements:
                            try:
                                if element.is_displayed():
                                    connect_button = element
                                    logger.info(f"Found connect button with selector: {selector}")
                                    break
                            except:
                                continue
                        if connect_button:
                            break
                except Exception as e:
                    logger.warning(f"Error with page specific selectors: {str(e)}")
            
            # Last resort: Get all buttons and look for connect
            if not connect_button:
                try:
                    logger.info("Last resort: Checking all buttons")
                    all_buttons = self.driver.find_elements(By.TAG_NAME, "button")
                    for button in all_buttons:
                        try:
                            button_text = button.text.lower()
                            if 'connect' in button_text and button.is_displayed():
                                connect_button = button
                                logger.info("Found Connect button through all buttons search")
                                break
                        except:
                            continue
                except Exception as e:
                    logger.warning(f"Error searching all buttons: {str(e)}")
            
            # Take screenshot of what we see before clicking
            self._take_screenshot("before_any_click")
            
            # If we found a connect button, click it
            if connect_button:
                self._take_screenshot("before_connect_click")
                logger.info("Clicking Connect button")
                try:
                    # First try normal click
                    connect_button.click()
                except Exception as e:
                    logger.warning(f"Normal click failed: {str(e)}, trying JavaScript click")
                    # Then try JavaScript click which can bypass some overlays
                    try:
                        self.driver.execute_script("arguments[0].click();", connect_button)
                        logger.info("Used JavaScript click for Connect button")
                    except Exception as js_e:
                        logger.error(f"JavaScript click also failed: {str(js_e)}")
                        self._take_screenshot("connect_click_failed")
                        return False
                
                time.sleep(3)  # Longer wait after click
                self._take_screenshot("after_connect_click")
                
                # Check if the "Add a note" button exists
                if personalized_note:
                    try:
                        logger.info("Looking for Add a note button")
                        # Try multiple selectors for the Add note button
                        add_note_selectors = [
                            "//button[contains(.//span, 'Add a note')]",
                            "//button[text()='Add a note']",
                            "//button[contains(@aria-label, 'Add a note')]",
                            "//div[contains(@role, 'dialog')]//button[contains(text(), 'Add a note')]",
                            "//div[contains(@role, 'dialog')]//button[2]"  # Often the second button in modal
                        ]
                        
                        add_note_button = None
                        for selector in add_note_selectors:
                            elements = self.driver.find_elements(By.XPATH, selector)
                            for element in elements:
                                try:
                                    if element.is_displayed():
                                        add_note_button = element
                                        logger.info(f"Found Add a note button with selector: {selector}")
                                        break
                                except:
                                    continue
                            if add_note_button:
                                break
                        
                        if add_note_button:
                            try:
                                # First try normal click
                                add_note_button.click()
                            except:
                                # Then try JavaScript click
                                self.driver.execute_script("arguments[0].click();", add_note_button)
                                
                            logger.info("Clicked Add a note")
                            time.sleep(2)
                            self._take_screenshot("note_dialog")
                            
                            # Enter personalized note - try different selectors
                            note_field = None
                            note_selectors = [
                                "//textarea[@name='message']",
                                "//div[contains(@role, 'dialog')]//textarea",
                                "//div[contains(@role, 'textbox')]",
                                "//div[contains(@contenteditable, 'true')]"
                            ]
                            
                            for selector in note_selectors:
                                try:
                                    elements = self.driver.find_elements(By.XPATH, selector)
                                    for element in elements:
                                        if element.is_displayed():
                                            note_field = element
                                            break
                                    if note_field:
                                        break
                                except:
                                    continue
                            
                            if note_field:
                                # Clear field and type slowly
                                try:
                                    note_field.clear()
                                except:
                                    pass  # Some fields can't be cleared
                                    
                                for char in personalized_note:
                                    note_field.send_keys(char)
                                    time.sleep(random.uniform(0.01, 0.05))  # Type like a human
                                
                                logger.info("Entered personalized note")
                                time.sleep(1)
                                self._take_screenshot("note_entered")
                            else:
                                logger.warning("Could not find note field")
                        else:
                            logger.warning("Could not find Add a note button")
                    except Exception as e:
                        logger.warning(f"Could not add personalized note: {str(e)}")
                        self._take_screenshot("note_error")
                
                # Find and click the Send/Done button
                try:
                    logger.info("Looking for Send/Done button")
                    send_selectors = [
                        "//button[contains(.//span, 'Send')]",
                        "//button[contains(.//span, 'Done')]",
                        "//button[@aria-label='Send now']",
                        "//button[text()='Send']",
                        "//button[text()='Done']",
                        "//div[contains(@role, 'dialog')]//button[2]",  # Often the second button in modal
                        "//div[contains(@class, 'artdeco-modal__actionbar')]//button[2]",  # Often the second button in modal
                        "//footer//button[2]"  # Second button in footer
                    ]
                    
                    send_button = None
                    for selector in send_selectors:
                        elements = self.driver.find_elements(By.XPATH, selector)
                        for element in elements:
                            try:
                                if element.is_displayed():
                                    send_button = element
                                    logger.info(f"Found send button with selector: {selector}")
                                    break
                            except:
                                continue
                        if send_button:
                            break
                    
                    if send_button:
                        self._take_screenshot("before_send_click")
                        try:
                            # First try normal click
                            send_button.click()
                        except:
                            # Then try JavaScript click
                            self.driver.execute_script("arguments[0].click();", send_button)
                            
                        time.sleep(3)  # Longer wait after send
                        self._take_screenshot("after_send_click")
                        
                        # Take one more screenshot to verify the state after sending
                        time.sleep(1)
                        self._take_screenshot("final_state")
                        
                        # Update request count
                        self.request_count += 1
                        self._save_request_count()
                        logger.info(f"Successfully sent connection request to {profile_url}")
                        return True
                    else:
                        logger.warning("Could not find Send/Done button")
                        self._take_screenshot("no_send_button")
                        return False
                except Exception as e:
                    logger.warning(f"Failed to click Send button: {str(e)}")
                    self._take_screenshot("send_button_failure")
                    return False
            else:
                # Get all visible buttons for debugging
                try:
                    logger.warning(f"Unable to find connect button for {profile_url}")
                    all_buttons = self.driver.find_elements(By.TAG_NAME, "button")
                    visible_buttons = []
                    for button in all_buttons:
                        try:
                            if button.is_displayed():
                                visible_buttons.append(button.text)
                        except:
                            continue
                    logger.info(f"Visible buttons on page: {visible_buttons}")
                    
                    # Final check for possible connection status
                    page_source = self.driver.page_source.lower()
                    if 'pending' in page_source:
                        logger.info("Connection might be pending already")
                    elif 'message' in page_source and ('connect' not in page_source):
                        logger.info("Already connected (only message option available)")
                    
                    self._take_screenshot("no_connect_button")
                    return False
                except Exception as e:
                    logger.error(f"Error during connection button search debug: {str(e)}")
                    return False
                    
        except Exception as e:
            logger.error(f"Error sending connection request to {profile_url}: {str(e)}")
            self._take_screenshot("connection_error")
            return False
    
    def process_profiles_from_csv(self, csv_file, profile_url_column, name_column=None, action='connect', csv_output=None):
        """
        Process LinkedIn profiles from a CSV file.
        
        Args:
            csv_file (str): Path to CSV file containing profile URLs
            profile_url_column (str): Column name containing LinkedIn profile URLs
            name_column (str, optional): Column name containing names for personalization
            action (str): Action to take ('connect', 'message', or 'both')
            csv_output (str, optional): Path to save results CSV
            
        Returns:
            list: Results of operations
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
                    'message_status': False
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
                    break
                
                # Send connection request
                if action in ['connect', 'both']:
                    result['connect_status'] = self.send_connection_request(profile_url, personalized_note)
                    
                # Add result to list
                results.append(result)
                
                # Save intermediate results
                if csv_output:
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
            
            return results
        
        except Exception as e:
            logger.error(f"Error processing profiles from CSV: {str(e)}")
            return []
    
    def _save_results_to_csv(self, results, csv_file):
        """Save results to CSV file."""
        try:
            with open(csv_file, 'w', newline='', encoding='utf-8') as f:
                fieldnames = ['profile_url', 'connect_status', 'message_status']
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(results)
        except Exception as e:
            logger.error(f"Error saving results to CSV: {str(e)}")
    
    def close(self):
        """Close the browser."""
        if self.driver:
            self.driver.quit()


def main():
    """Main function to run the automation."""
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
        delay_min = args.delay_min if hasattr(args, 'delay_min') and args.delay_min else int(os.getenv('LINKEDIN_DELAY_MIN', 20))
        delay_max = args.delay_max if hasattr(args, 'delay_max') and args.delay_max else int(os.getenv('LINKEDIN_DELAY_MAX', 40))
        daily_limit = args.limit if hasattr(args, 'limit') and args.limit else int(os.getenv('LINKEDIN_DAILY_LIMIT', 40))
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
    
    if not csv_file:
        logger.error("CSV file not provided. Set LINKEDIN_CSV_FILE in .env file or provide with --csv argument.")
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
                logger.info(f"Successful connection requests: {success_connects}/{len(results)} ({success_connects/len(results)*100:.1f}%)")
            if action in ['message', 'both']:
                success_messages = sum(1 for r in results if r.get('message_status', False))
                logger.info(f"Successful messages sent: {success_messages}/{len(results)} ({success_messages/len(results)*100:.1f}%)")
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