# LinkedIn Connection Automation Tool

[![Python Version](https://img.shields.io/badge/python-3.8%2B-blue)](https://www.python.org/downloads/)
[![Selenium](https://img.shields.io/badge/selenium-4.0%2B-green)](https://www.selenium.dev/)
[![License](https://img.shields.io/badge/license-MIT-yellow)](LICENSE)

A robust, feature-rich automation tool for LinkedIn connection requests. This script helps you automatically send personalized connection requests to LinkedIn profiles while avoiding detection and rate limiting.

```
         _    _       _          _ _       
        | |  (_)     | |        | | |      
        | |   _ _ __ | | _____  | | | _ __ 
        | |  | | '_ \| |/ / _ \ | | || '_ \ 
        | |__| | | | |   <  __/_| | || | | |
        \____/|_| |_|_|\_\___(_)_|_||_| |_|
                 
       Connection Automation Tool v1.0.0
```

## 🚀 Features

- **Multi-strategy connection detection**: Intelligent algorithms to find and click Connect buttons across various LinkedIn UI layouts
- **Smart personalization**: Customizable connection messages with name detection
- **Anti-detection measures**: Randomized typing, delays, and browser fingerprint protection
- **Comprehensive logging**: Detailed activity logs for monitoring and troubleshooting
- **Debug mode with screenshots**: Visual tracking of automation steps for easy debugging
- **Bulk processing**: Process lists of profiles from CSV files
- **Connection tracking**: Daily limits and request counting to prevent account restrictions
- **Customizable delays**: Control timing between requests to appear more human-like
- **Manual login support**: Option for manual authentication to avoid security checks

## 📋 Prerequisites

- Python 3.8 or higher
- Chrome browser installed
- Basic understanding of browser automation
- A LinkedIn account in good standing

## 🔧 Installation

1. **Clone this repository**
   ```bash
   git clone https://github.com/yourusername/linkedin-automation.git
   cd linkedin-automation
   ```

2. **Create a virtual environment** (recommended)
   ```bash
   python -m venv venv
   
   # Activate on Windows
   venv\Scripts\activate
   
   # Activate on macOS/Linux
   source venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Create a `.env` file** with your LinkedIn credentials and settings (see Configuration section)

## ⚙️ Configuration

Create a `.env` file in the root directory with the following parameters:

```ini
# LinkedIn Credentials
LINKEDIN_EMAIL=your_email@example.com
LINKEDIN_PASSWORD=your_password

# Message Template (use either direct template or file)
LINKEDIN_MESSAGE=Hello {name}, I'd like to connect with you on LinkedIn. I was impressed by your profile and would love to add you to my professional network.
# LINKEDIN_MESSAGE_FILE=message_template.txt

# CSV Configuration
LINKEDIN_CSV_FILE=profiles.csv
LINKEDIN_URL_COLUMN=profile
LINKEDIN_NAME_COLUMN=full_name

# Automation Settings
LINKEDIN_ACTION=connect  # connect, message, or both
LINKEDIN_DELAY_MIN=20
LINKEDIN_DELAY_MAX=40
LINKEDIN_DAILY_LIMIT=40
LINKEDIN_HEADLESS=false
LINKEDIN_OUTPUT_FILE=results.csv

# Advanced Settings
LINKEDIN_MANUAL_LOGIN=false  # Set to true if you want to log in manually
LINKEDIN_DEBUG=true  # Set to true for verbose logging and screenshots
```

## 📊 CSV Format

Prepare a CSV file with LinkedIn profile URLs and optional names for personalization:

```csv
profile,full_name,job_title,company
https://www.linkedin.com/in/johndoe/,John Doe,Software Engineer,ABC Tech
https://www.linkedin.com/in/janedoe/,Jane Doe,Marketing Manager,XYZ Corp
```

At minimum, the CSV needs a column with LinkedIn profile URLs, but additional columns can be used for personalization.

## 🖥️ Usage

### Basic Usage

```bash
python linkedin_automation.py
```

This will read settings from your `.env` file and begin the automation process.

### Command-Line Options

The script supports numerous command-line arguments that override `.env` settings:

```bash
python linkedin_automation.py --csv my_leads.csv --manual-login --debug
```

#### Available Arguments:

| Argument | Description |
|----------|-------------|
| `--csv` | Path to CSV file with LinkedIn profile URLs |
| `--url-column` | Column name in CSV that contains profile URLs |
| `--name-column` | Column name in CSV that contains names |
| `--action` | Action to perform: 'connect', 'message', or 'both' |
| `--headless` | Run browser in headless mode |
| `--output` | Path to save results CSV |
| `--manual-login` | Wait for manual login instead of automated login |
| `--debug` | Enable debug mode with screenshots |
| `--email` | LinkedIn login email (overrides .env) |
| `--password` | LinkedIn login password (overrides .env) |
| `--message` | Custom connection message (overrides .env) |
| `--delay-min` | Minimum delay between requests in seconds |
| `--delay-max` | Maximum delay between requests in seconds |
| `--limit` | Daily connection request limit |

## 💡 Best Practices

### Staying Under LinkedIn's Radar

1. **Start small**: Begin with 5-10 connection requests per day
2. **Use realistic delays**: Set longer delays (30-60 seconds) between requests
3. **Enable manual login**: Reduces chance of triggering security checks
4. **Personalize messages**: Custom messages appear more genuine
5. **Be patient**: Gradually increase daily limits over time
6. **Use debug mode**: Monitor activity with screenshots to ensure proper operation
7. **Respect LinkedIn's community guidelines**: Don't use this tool for spamming

```
┌─────────────────────────────────────────────────┐
│                                                 │
│    CONNECTION STRATEGY                          │
│    ───────────────────                          │
│                                                 │
│    ✓ Be selective with connection requests      │
│    ✓ Personalize messages when possible         │
│    ✓ Start with small batches (5-10 per day)    │
│    ✓ Use manual login for better security       │
│    ✓ Gradually increase volume over time        │
│                                                 │
└─────────────────────────────────────────────────┘
```

### Troubleshooting Connection Issues

If the script can't find the Connect button:

1. Enable debug mode to see screenshots of what the script is seeing
2. Check if the profiles are already connected or have a pending invitation
3. Try manual login mode as LinkedIn might be showing security challenges
4. Look for patterns in the profiles that fail - they might have special privacy settings
5. Check the logs for specific error messages

## 🚫 Rate Limiting and Security

LinkedIn has algorithms to detect automation and may:
- Temporarily restrict your account
- Present CAPTCHA or other security challenges
- Permanently limit your account in severe cases

This script implements several measures to reduce detection risk, but use it responsibly and at your own risk.

## 📷 Debug Screenshots

When debug mode is enabled, the script captures screenshots at each step of the process, stored in the `debug_screenshots` directory. The screenshots are named with timestamps and action descriptions.

```
DEBUG SCREENSHOTS EXAMPLE
─────────────────────────

┌─────────────────────────────────────────────────────────┐
│                                                         │
│  20250323_191143_login_page.png                         │
│  LinkedIn login screen capture                          │
│                                                         │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  20250323_191155_profile_page.png                       │
│  Target profile before connection attempt               │
│                                                         │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  20250323_191158_before_connect_click.png               │
│  Connect button located and ready to click              │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

Example screenshots:
- `20250323_191143_login_page.png`
- `20250323_191145_credentials_entered.png`
- `20250323_191150_post_login.png`
- `20250323_191155_profile_page.png`
- `20250323_191158_before_connect_click.png`
- `20250323_191159_after_connect_click.png`

## 📋 Logging

The script creates a detailed log file `linkedin_automation.log` that captures all actions, decisions, and errors. This is invaluable for troubleshooting.

Example log entry:
```
2025-03-23 19:11:43,075 - INFO - Waiting for login page to load...
2025-03-23 19:11:43,180 - INFO - Entering email...
2025-03-23 19:11:45,135 - INFO - Entering password...
2025-03-23 19:11:47,180 - INFO - Clicking login button...
2025-03-23 19:11:47,631 - INFO - Waiting for successful login...
2025-03-23 19:11:52,016 - INFO - Successfully logged in to LinkedIn
```

## 🛠️ Advanced Customization

### Custom Connection Messages

You can either set your message directly in the `.env` file or create a text file with your message template:

```
Hello {name},

I came across your profile and was impressed by your work at {company}. I'd like to connect to share insights in the {industry} industry.

Best regards,
Your Name
```

Use variables like `{name}` that match columns in your CSV file.

### Connection Request Tracking

The script tracks daily connection requests in a `request_count.csv` file to ensure you don't exceed LinkedIn's limits.

```
DATE,COUNT
2025-03-23,23
2025-03-24,17
2025-03-25,30
```

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## ⚠️ Disclaimer

This tool is for educational purposes only. Automated interactions with LinkedIn may violate their Terms of Service. Use responsibly and at your own risk. The authors are not responsible for any account restrictions or other consequences resulting from the use of this tool.

LinkedIn's User Agreement explicitly prohibits:
- Scraping or data extraction
- Using bots or other automated methods
- Creating fake profiles or misrepresenting yourself

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the project
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📧 Contact

If you have questions or need assistance, please open an issue on this repository.

---

```
  _    _                           _   _      _                      _    _             _ 
 | |  | |                         | \ | |    | |                    | |  (_)           | |
 | |__| | __ _ _ __  _ __  _   _  |  \| | ___| |___      _____  _ __| | ___ _ __   __ _| |
 |  __  |/ _` | '_ \| '_ \| | | | | . ` |/ _ \ __\ \ /\ / / _ \| '__| |/ / | '_ \ / _` | |
 | |  | | (_| | |_) | |_) | |_| | | |\  |  __/ |_ \ V  V / (_) | |  |   <| | | | | (_| |_|
 |_|  |_|\__,_| .__/| .__/ \__, | |_| \_|\___|\__| \_/\_/ \___/|_|  |_|\_\_|_| |_|\__, (_)
              | |   | |     __/ |                                                   __/ |  
              |_|   |_|    |___/                                                   |___/   
```