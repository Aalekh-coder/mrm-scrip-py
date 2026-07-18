# import os
# import re
# import io
# import json
# import time
# import requests
# from urllib.parse import urlparse
# from dotenv import load_dotenv

# load_dotenv()

# SCRAPERAPI_KEY = os.getenv("SCRAPER_API_KEY")
# SCRAPERAPI_SEARCH_URL = "https://api.scraperapi.com/structured/google/search"

# HEADERS = {
#     "User-Agent": (
#         "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
#         "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
#     )
# }

# def sanitize_domain(domain):
#     """Clean and sanitize domain input."""
#     # Remove trailing slashes and whitespace
#     domain = domain.strip().rstrip('/')
#     # Remove http:// or https:// if present
#     domain = re.sub(r'^https?://', '', domain)
#     # Remove any path components
#     domain = domain.split('/')[0]
#     return domain

# def get_root_domain(domain):
#     """Extract the root domain (handles subdomains)."""
#     domain = sanitize_domain(domain)
#     domain_clean = domain.lower().strip()
#     domain_parts = domain_clean.split('.')
    
#     if len(domain_parts) > 2:
#         # Handle multi-part TLDs like co.uk, com.au
#         if domain_parts[-2] in ['co', 'com', 'org', 'net', 'gov', 'edu'] and len(domain_parts[-1]) <= 3:
#             root_domain = '.'.join(domain_parts[-3:])
#         else:
#             root_domain = '.'.join(domain_parts[-2:])
#     else:
#         root_domain = domain_clean
    
#     return root_domain

# # --- Search (ScraperAPI structured Google search) ------------------------

# def google_search(query, num_results=None):
#     """Perform a Google search using ScraperAPI."""
#     params = {
#         "api_key": SCRAPERAPI_KEY,
#         "query": query,
#     }
#     if num_results is not None:
#         params["num"] = num_results

#     response = requests.get(
#         SCRAPERAPI_SEARCH_URL,
#         params=params,
#         headers=HEADERS,
#         timeout=60,
#     )
#     response.raise_for_status()
#     data = response.json()

#     results = []
#     items = data.get("organic_results", [])
#     if num_results is not None:
#         items = items[:num_results]

#     for item in items:
#         link = item.get("link") or item.get("url")
#         if link:
#             results.append({
#                 "title": item.get("title"),
#                 "url": link,
#                 "snippet": item.get("snippet"),
#             })
#     return results

# def search_github_repos(domain, num_results=None):
#     """Search for GitHub repositories related to the domain."""
#     all_results = []
#     seen_urls = set()
    
#     # Sanitize domain
#     domain_clean = sanitize_domain(domain)
#     root_domain = get_root_domain(domain_clean)
    
#     # Search patterns for GitHub with various combinations
#     github_patterns = [
#         f'"{domain_clean}" site:github.com',
#         f'"{root_domain}" site:github.com',
#         f'{domain_clean} site:github.com',
#         f'{root_domain} site:github.com',
#         f'intitle:"{domain_clean}" site:github.com',
#         f'"{domain_clean}" inurl:github.com',
#     ]
    
#     # Remove duplicate patterns
#     github_patterns = list(dict.fromkeys(github_patterns))
    
#     print(f"Searching for GitHub repositories related to: {domain_clean}")
#     print(f"Root domain: {root_domain}")
#     print("-" * 60)
    
#     for pattern in github_patterns:
#         print(f"Searching: {pattern}")
#         try:
#             results = google_search(pattern, num_results=num_results)
#             count = 0
#             for r in results:
#                 # Filter to only GitHub URLs
#                 if ('github.com' in r['url'] or 'github.io' in r['url']):
#                     # Exclude common non-repo GitHub pages
#                     if not any(x in r['url'].lower() for x in ['/issues', '/pulls', '/wiki', '/actions', '/security']):
#                         if r['url'] not in seen_urls:
#                             seen_urls.add(r['url'])
#                             r['source'] = 'github'
#                             r['filetype'] = 'github_repo'
#                             all_results.append(r)
#                             count += 1
#             print(f"  Found {count} new GitHub repository links")
#         except Exception as e:
#             print(f"  [!] GitHub search failed for {pattern}: {e}")
        
#         time.sleep(1.5)  # Delay between searches
    
#     return all_results

# def get_repo_details(url):
#     """Extract repository details from GitHub URL."""
#     try:
#         parsed = urlparse(url)
#         path_parts = parsed.path.strip('/').split('/')
        
#         if len(path_parts) >= 2:
#             # Check if it's a gist
#             if 'gist' in parsed.netloc.lower():
#                 return {
#                     'type': 'gist',
#                     'gist_id': path_parts[0] if path_parts else 'unknown'
#                 }
            
#             owner = path_parts[0]
#             repo = path_parts[1]
#             return {
#                 'type': 'repository',
#                 'owner': owner,
#                 'repo': repo,
#                 'full_name': f"{owner}/{repo}"
#             }
#     except:
#         pass
#     return {'type': 'unknown'}

# def fetch_github_readme(owner, repo):
#     """Fetch README content from GitHub API."""
#     api_url = f"https://api.github.com/repos/{owner}/{repo}/readme"
#     headers = {
#         'Accept': 'application/vnd.github.v3+json',
#         'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
#     }
    
#     try:
#         response = requests.get(api_url, headers=headers, timeout=10)
#         if response.status_code == 200:
#             data = response.json()
#             if 'content' in data:
#                 import base64
#                 content = base64.b64decode(data['content']).decode('utf-8', errors='ignore')
#                 return content[:500] + "..." if len(content) > 500 else content
#     except:
#         pass
#     return None

# def get_github_repo_info(url):
#     """Get detailed information about a GitHub repository."""
#     details = get_repo_details(url)
    
#     if details.get('type') == 'repository':
#         owner = details['owner']
#         repo = details['repo']
        
#         # Try to fetch additional info from GitHub API
#         api_url = f"https://api.github.com/repos/{owner}/{repo}"
#         headers = {
#             'Accept': 'application/vnd.github.v3+json',
#             'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
#         }
        
#         try:
#             response = requests.get(api_url, headers=headers, timeout=10)
#             if response.status_code == 200:
#                 data = response.json()
#                 details.update({
#                     'description': data.get('description', ''),
#                     'stars': data.get('stargazers_count', 0),
#                     'forks': data.get('forks_count', 0),
#                     'language': data.get('language', ''),
#                     'created_at': data.get('created_at', ''),
#                     'updated_at': data.get('updated_at', ''),
#                     'has_wiki': data.get('has_wiki', False),
#                     'has_pages': data.get('has_pages', False),
#                     'open_issues': data.get('open_issues_count', 0),
#                     'license': data.get('license', {}).get('name', '') if data.get('license') else '',
#                 })
                
#                 # Try to fetch README preview
#                 readme = fetch_github_readme(owner, repo)
#                 if readme:
#                     details['readme_preview'] = readme
#             else:
#                 details['api_error'] = f"HTTP {response.status_code}"
#         except Exception as e:
#             details['api_error'] = str(e)
#     elif details.get('type') == 'gist':
#         details['note'] = 'GitHub Gist (not a repository)'
    
#     return details

# def scrape_all_github_repos(domain, num_results=None, delay=1.5):
#     """Search and scrape GitHub repositories related to the domain."""
    
#     # Sanitize domain for display and search
#     domain_clean = sanitize_domain(domain)
    
#     # Search for GitHub repositories
#     found = search_github_repos(domain_clean, num_results=num_results)
    
#     print(f"\nFound {len(found)} unique GitHub repository(ies). Fetching details...\n")
#     print("-" * 60)
    
#     results = []
#     for idx, item in enumerate(found, 1):
#         print(f"[{idx}/{len(found)}] Processing: {item['url']}")
        
#         # Get repository details
#         repo_details = get_github_repo_info(item['url'])
        
#         results.append({
#             "title": item.get('title'),
#             "url": item['url'],
#             "snippet": item.get('snippet'),
#             "source": "github_search",
#             "filetype": "github_repo",
#             "repository_details": repo_details,
#         })
        
#         time.sleep(delay)
    
#     return results

# if __name__ == "__main__":
#     if not SCRAPERAPI_KEY:
#         raise SystemExit("ERROR: Set SCRAPER_API_KEY in your .env file or environment.")

#     domain = input("Domain (e.g. example.com): ").strip()
#     n = input("Results per search query (leave blank for all): ").strip()
#     num_results = int(n) if n else None

#     print("\n" + "="*60)
#     print("SCRAPING GITHUB REPOSITORIES")
#     print("="*60 + "\n")
    
#     data = scrape_all_github_repos(domain, num_results=num_results)
    
#     # Sanitize domain for filename
#     clean_domain = sanitize_domain(domain)
    
#     # Save with timestamp
#     timestamp = time.strftime("%Y%m%d_%H%M%S")
#     filename = f"github_repos_{clean_domain}_{timestamp}.json"
    
#     # Ensure the filename doesn't contain invalid characters
#     filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
    
#     with open(filename, "w", encoding="utf-8") as f:
#         json.dump(data, f, indent=2, ensure_ascii=False)
    
#     print("\n" + "="*60)
#     print(f"✅ Saved {len(data)} GitHub repository result(s) to {filename}")
#     print("="*60)
    
#     # Summary
#     print(f"\n📊 SUMMARY:")
#     print(f"  Total repositories found: {len(data)}")
    
#     # Filter out gists and non-repositories
#     repos = [item for item in data if item.get('repository_details', {}).get('type') == 'repository']
#     gists = [item for item in data if item.get('repository_details', {}).get('type') == 'gist']
    
#     if gists:
#         print(f"  Gists found: {len(gists)}")
#     if repos:
#         print(f"  Repositories found: {len(repos)}")
    
#     if repos:
#         # Show top repositories by stars if available
#         repos_with_stars = []
#         for item in repos:
#             details = item.get('repository_details', {})
#             if details and details.get('stars', 0) > 0:
#                 repos_with_stars.append((details.get('full_name', 'unknown'), details.get('stars', 0)))
        
#         if repos_with_stars:
#             print(f"\n  ⭐ Top repositories by stars:")
#             repos_with_stars.sort(key=lambda x: x[1], reverse=True)
#             for name, stars in repos_with_stars[:5]:
#                 print(f"    {name}: {stars} ⭐")
        
#         # Language distribution
#         languages = {}
#         for item in repos:
#             details = item.get('repository_details', {})
#             lang = details.get('language', 'Unknown')
#             languages[lang] = languages.get(lang, 0) + 1
        
#         if languages:
#             print(f"\n  📁 Languages used:")
#             for lang, count in sorted(languages.items(), key=lambda x: x[1], reverse=True)[:10]:
#                 print(f"    {lang}: {count} repo(s)")
    
#     # Display results in console
#     print("\n" + "="*60)
#     print("DETAILED RESULTS:")
#     print("="*60)
#     print(json.dumps(data, indent=2, ensure_ascii=False))




# deep research 

# import os
# import re
# import io
# import json
# import time
# import requests
# import base64
# from urllib.parse import urlparse
# from datetime import datetime
# from dotenv import load_dotenv

# load_dotenv()

# SCRAPERAPI_KEY = os.getenv("SCRAPER_API_KEY")
# SCRAPERAPI_SEARCH_URL = "https://api.scraperapi.com/structured/google/search"

# HEADERS = {
#     "User-Agent": (
#         "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
#         "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
#     )
# }

# # Sensitive file patterns to search for
# SENSITIVE_FILE_PATTERNS = [
#     # Environment files
#     (".env", "Environment file"),
#     (".env.local", "Local environment file"),
#     (".env.production", "Production environment file"),
#     (".env.development", "Development environment file"),
#     (".env.staging", "Staging environment file"),
#     (".env.example", "Environment example file"),
#     (".env.test", "Test environment file"),
#     (".env.ci", "CI environment file"),
#     (".env.docker", "Docker environment file"),
#     (".env.sample", "Environment sample file"),
    
#     # Configuration files
#     ("config.php", "PHP configuration"),
#     ("settings.py", "Python settings"),
#     ("application.properties", "Java properties"),
#     ("application.yml", "YAML configuration"),
#     ("application.yaml", "YAML configuration"),
#     ("docker-compose.yml", "Docker compose"),
#     ("docker-compose.yaml", "Docker compose"),
#     (".travis.yml", "Travis CI config"),
#     (".gitlab-ci.yml", "GitLab CI config"),
#     (".github/workflows/*.yml", "GitHub Actions"),
#     ("config.json", "JSON configuration"),
#     ("config.ini", "INI configuration"),
#     ("config.yaml", "YAML config"),
#     ("config.yml", "YAML config"),
#     ("web.config", "IIS configuration"),
#     ("appsettings.json", ".NET configuration"),
#     ("database.yml", "Database configuration"),
#     ("secrets.yml", "Secrets configuration"),
#     ("settings.ini", "Settings file"),
#     (".htaccess", "Apache configuration"),
#     (".htpasswd", "Apache password file"),
# ]

# # Sensitive content patterns to search for
# SENSITIVE_CONTENT_PATTERNS = [
#     # Password patterns
#     (r'(?i)password\s*[=:]\s*[\'"]?([^\'"\s]+)', "Password found"),
#     (r'(?i)passwd\s*[=:]\s*[\'"]?([^\'"\s]+)', "Passwd found"),
#     (r'(?i)pwd\s*[=:]\s*[\'"]?([^\'"\s]+)', "PWD found"),
    
#     # API Keys
#     (r'(?i)api[_-]?key\s*[=:]\s*[\'"]?([^\'"\s]+)', "API Key found"),
#     (r'(?i)apikey\s*[=:]\s*[\'"]?([^\'"\s]+)', "API Key found"),
#     (r'(?i)api_token\s*[=:]\s*[\'"]?([^\'"\s]+)', "API Token found"),
#     (r'(?i)access_token\s*[=:]\s*[\'"]?([^\'"\s]+)', "Access Token found"),
#     (r'(?i)auth_token\s*[=:]\s*[\'"]?([^\'"\s]+)', "Auth Token found"),
    
#     # Database credentials
#     (r'(?i)db[_-]?password\s*[=:]\s*[\'"]?([^\'"\s]+)', "Database password found"),
#     (r'(?i)db[_-]?user\s*[=:]\s*[\'"]?([^\'"\s]+)', "Database user found"),
#     (r'(?i)database[_-]?url\s*[=:]\s*[\'"]?([^\'"\s]+)', "Database URL found"),
#     (r'(?i)db_[a-z_]*password\s*[=:]\s*[\'"]?([^\'"\s]+)', "Database password found"),
#     (r'(?i)mongodb\s*[=:]\s*[\'"]?([^\'"\s]+)', "MongoDB connection string"),
#     (r'(?i)mysql\s*[=:]\s*[\'"]?([^\'"\s]+)', "MySQL connection string"),
#     (r'(?i)postgresql\s*[=:]\s*[\'"]?([^\'"\s]+)', "PostgreSQL connection string"),
    
#     # Secret keys
#     (r'(?i)secret[_-]?key\s*[=:]\s*[\'"]?([^\'"\s]+)', "Secret key found"),
#     (r'(?i)SECRET_KEY\s*[=:]\s*[\'"]?([^\'"\s]+)', "Secret key found"),
#     (r'(?i)APP_KEY\s*[=:]\s*[\'"]?([^\'"\s]+)', "Application key found"),
#     (r'(?i)JWT_SECRET\s*[=:]\s*[\'"]?([^\'"\s]+)', "JWT Secret found"),
#     (r'(?i)JWT_KEY\s*[=:]\s*[\'"]?([^\'"\s]+)', "JWT Key found"),
    
#     # Cloud credentials
#     (r'(?i)AWS_ACCESS_KEY_ID\s*[=:]\s*[\'"]?([^\'"\s]+)', "AWS Access Key found"),
#     (r'(?i)AWS_SECRET_ACCESS_KEY\s*[=:]\s*[\'"]?([^\'"\s]+)', "AWS Secret Key found"),
#     (r'(?i)aws_access_key_id\s*[=:]\s*[\'"]?([^\'"\s]+)', "AWS Access Key found"),
#     (r'(?i)aws_secret_access_key\s*[=:]\s*[\'"]?([^\'"\s]+)', "AWS Secret Key found"),
#     (r'(?i)GCP_*KEY\s*[=:]\s*[\'"]?([^\'"\s]+)', "GCP Key found"),
#     (r'(?i)GOOGLE_APPLICATION_CREDENTIALS\s*[=:]\s*[\'"]?([^\'"\s]+)', "Google credentials found"),
#     (r'(?i)AZURE_*KEY\s*[=:]\s*[\'"]?([^\'"\s]+)', "Azure Key found"),
    
#     # Payment credentials
#     (r'(?i)STRIPE_[A-Z_]*KEY\s*[=:]\s*[\'"]?([^\'"\s]+)', "Stripe key found"),
#     (r'(?i)STRIPE_SECRET\s*[=:]\s*[\'"]?([^\'"\s]+)', "Stripe secret found"),
#     (r'(?i)STRIPE_PUBLISHABLE\s*[=:]\s*[\'"]?([^\'"\s]+)', "Stripe publishable key found"),
#     (r'(?i)PAYPAL_*KEY\s*[=:]\s*[\'"]?([^\'"\s]+)', "PayPal key found"),
#     (r'(?i)PAYPAL_SECRET\s*[=:]\s*[\'"]?([^\'"\s]+)', "PayPal secret found"),
    
#     # Email/SMTP
#     (r'(?i)SMTP_PASSWORD\s*[=:]\s*[\'"]?([^\'"\s]+)', "SMTP password found"),
#     (r'(?i)MAIL_PASSWORD\s*[=:]\s*[\'"]?([^\'"\s]+)', "Mail password found"),
#     (r'(?i)EMAIL_PASSWORD\s*[=:]\s*[\'"]?([^\'"\s]+)', "Email password found"),
#     (r'(?i)SENDGRID_API_KEY\s*[=:]\s*[\'"]?([^\'"\s]+)', "SendGrid API key found"),
#     (r'(?i)MAILGUN_API_KEY\s*[=:]\s*[\'"]?([^\'"\s]+)', "Mailgun API key found"),
    
#     # Tokens
#     (r'(?i)token\s*[=:]\s*[\'"]?([^\'"\s]+)', "Token found"),
#     (r'(?i)bearer\s+([^\s\'"]+)', "Bearer token found"),
#     (r'(?i)authorization\s*[=:]\s*[\'"]?([^\'"\s]+)', "Authorization token found"),
#     (r'(?i)auth[_-]?token\s*[=:]\s*[\'"]?([^\'"\s]+)', "Auth token found"),
    
#     # SSH Keys
#     (r'-----BEGIN (RSA|DSA|EC|OPENSSH) PRIVATE KEY-----', "SSH Private Key found"),
#     (r'-----BEGIN RSA PRIVATE KEY-----', "RSA Private Key found"),
#     (r'-----BEGIN DSA PRIVATE KEY-----', "DSA Private Key found"),
#     (r'-----BEGIN EC PRIVATE KEY-----', "EC Private Key found"),
#     (r'-----BEGIN OPENSSH PRIVATE KEY-----', "OpenSSH Private Key found"),
    
#     # Other sensitive
#     (r'(?i)encryption_key\s*[=:]\s*[\'"]?([^\'"\s]+)', "Encryption key found"),
#     (r'(?i)salt\s*[=:]\s*[\'"]?([^\'"\s]+)', "Salt found"),
#     (r'(?i)hash\s*[=:]\s*[\'"]?([^\'"\s]+)', "Hash found"),
#     (r'(?i)private_key\s*[=:]\s*[\'"]?([^\'"\s]+)', "Private key found"),
#     (r'(?i)public_key\s*[=:]\s*[\'"]?([^\'"\s]+)', "Public key found"),
# ]

# # Search patterns for sensitive files on GitHub
# GITHUB_SENSITIVE_PATTERNS = [
#     # .env files
#     ('.env', 'Environment file'),
#     ('.env.local', 'Local environment file'),
#     ('.env.production', 'Production environment file'),
#     ('.env.development', 'Development environment file'),
#     ('.env.staging', 'Staging environment file'),
#     ('.env.example', 'Environment example file'),
#     ('.env.test', 'Test environment file'),
    
#     # Sensitive files
#     ('config.php', 'PHP configuration'),
#     ('settings.py', 'Python settings'),
#     ('application.properties', 'Java properties'),
#     ('docker-compose.yml', 'Docker compose'),
#     ('.travis.yml', 'Travis CI config'),
#     ('.gitlab-ci.yml', 'GitLab CI config'),
#     ('web.config', 'IIS configuration'),
#     ('appsettings.json', '.NET configuration'),
#     ('database.yml', 'Database configuration'),
#     ('secrets.yml', 'Secrets configuration'),
#     ('.htaccess', 'Apache configuration'),
#     ('.htpasswd', 'Apache password file'),
    
#     # Token/secret files
#     ('secrets.json', 'Secrets JSON file'),
#     ('secrets.yaml', 'Secrets YAML file'),
#     ('credentials.json', 'Credentials file'),
#     ('credentials.txt', 'Credentials text file'),
#     ('tokens.txt', 'Tokens file'),
#     ('keys.txt', 'Keys file'),
#     ('private.pem', 'Private key file'),
#     ('id_rsa', 'SSH private key'),
#     ('id_dsa', 'SSH private key'),
#     ('id_ecdsa', 'SSH private key'),
#     ('id_ed25519', 'SSH private key'),
# ]

# def sanitize_domain(domain):
#     """Clean and sanitize domain input."""
#     domain = domain.strip().rstrip('/')
#     domain = re.sub(r'^https?://', '', domain)
#     domain = domain.split('/')[0]
#     return domain

# def get_root_domain(domain):
#     """Extract the root domain."""
#     domain = sanitize_domain(domain)
#     domain_clean = domain.lower().strip()
#     domain_parts = domain_clean.split('.')
    
#     if len(domain_parts) > 2:
#         if domain_parts[-2] in ['co', 'com', 'org', 'net', 'gov', 'edu'] and len(domain_parts[-1]) <= 3:
#             root_domain = '.'.join(domain_parts[-3:])
#         else:
#             root_domain = '.'.join(domain_parts[-2:])
#     else:
#         root_domain = domain_clean
    
#     return root_domain

# def google_search(query, num_results=None):
#     """Perform a Google search using ScraperAPI."""
#     params = {
#         "api_key": SCRAPERAPI_KEY,
#         "query": query,
#     }
#     if num_results is not None:
#         params["num"] = num_results

#     try:
#         response = requests.get(
#             SCRAPERAPI_SEARCH_URL,
#             params=params,
#             headers=HEADERS,
#             timeout=60,
#         )
#         response.raise_for_status()
#         data = response.json()

#         results = []
#         items = data.get("organic_results", [])
#         if num_results is not None:
#             items = items[:num_results]

#         for item in items:
#             link = item.get("link") or item.get("url")
#             if link:
#                 results.append({
#                     "title": item.get("title"),
#                     "url": link,
#                     "snippet": item.get("snippet"),
#                 })
#         return results
#     except Exception as e:
#         print(f"  [!] Search failed: {e}")
#         return []

# def search_sensitive_files_google(domain, num_results=None):
#     """Search for sensitive files using Google search."""
#     all_results = []
#     seen_urls = set()
#     domain_clean = sanitize_domain(domain)
    
#     print(f"\n🔍 Searching for sensitive files via Google...")
#     print("-" * 60)
    
#     # Search for each sensitive file pattern
#     for pattern, description in SENSITIVE_FILE_PATTERNS:
#         # Skip if pattern contains wildcards
#         if '*' in pattern:
#             continue
            
#         query = f'site:{domain_clean} "{pattern}"'
#         print(f"  Searching: {query}")
        
#         try:
#             results = google_search(query, num_results=num_results)
#             count = 0
#             for r in results:
#                 if r['url'] not in seen_urls:
#                     seen_urls.add(r['url'])
#                     r['file_type'] = pattern
#                     r['description'] = description
#                     r['search_type'] = 'google_sensitive_file'
#                     all_results.append(r)
#                     count += 1
#             print(f"    Found {count} new results")
#         except Exception as e:
#             print(f"    [!] Error: {e}")
        
#         time.sleep(1)
    
#     return all_results

# def search_sensitive_content_google(domain, num_results=None):
#     """Search for sensitive content patterns using Google search."""
#     all_results = []
#     seen_urls = set()
#     domain_clean = sanitize_domain(domain)
    
#     print(f"\n🔍 Searching for sensitive content patterns...")
#     print("-" * 60)
    
#     # Search for key sensitive patterns
#     key_patterns = [
#         ('password', 'Password in code'),
#         ('api_key', 'API Key'),
#         ('secret', 'Secret'),
#         ('token', 'Token'),
#         ('db_password', 'Database password'),
#         ('aws_key', 'AWS Key'),
#         ('private_key', 'Private key'),
#         ('auth', 'Authentication'),
#         ('credentials', 'Credentials'),
#         ('jwt', 'JWT Token'),
#     ]
    
#     for keyword, description in key_patterns:
#         query = f'site:{domain_clean} {keyword}'
#         print(f"  Searching: {query}")
        
#         try:
#             results = google_search(query, num_results=num_results)
#             count = 0
#             for r in results:
#                 # Check if snippet contains sensitive pattern
#                 snippet = r.get('snippet', '').lower()
#                 if any(pat in snippet for pat in ['password', 'secret', 'key', 'token', 'auth']):
#                     if r['url'] not in seen_urls:
#                         seen_urls.add(r['url'])
#                         r['file_type'] = keyword
#                         r['description'] = f"Sensitive content: {description}"
#                         r['search_type'] = 'google_sensitive_content'
#                         all_results.append(r)
#                         count += 1
#             print(f"    Found {count} new results")
#         except Exception as e:
#             print(f"    [!] Error: {e}")
        
#         time.sleep(1)
    
#     return all_results

# def search_github_sensitive(domain, num_results=None):
#     """Search GitHub for sensitive files and content."""
#     all_results = []
#     seen_urls = set()
#     domain_clean = sanitize_domain(domain)
    
#     print(f"\n🔍 Searching GitHub for sensitive files...")
#     print("-" * 60)
    
#     # Search for sensitive files on GitHub
#     for pattern, description in GITHUB_SENSITIVE_PATTERNS:
#         # GitHub search queries
#         queries = [
#             f'"{domain_clean}" "{pattern}" site:github.com',
#             f'{domain_clean} "{pattern}" site:github.com',
#         ]
        
#         for query in queries:
#             print(f"  Searching: {query}")
            
#             try:
#                 results = google_search(query, num_results=num_results)
#                 count = 0
#                 for r in results:
#                     if 'github.com' in r['url'] or 'github.io' in r['url']:
#                         if r['url'] not in seen_urls:
#                             seen_urls.add(r['url'])
#                             r['file_type'] = pattern
#                             r['description'] = f"GitHub: {description}"
#                             r['search_type'] = 'github_sensitive_file'
#                             all_results.append(r)
#                             count += 1
#                 print(f"    Found {count} new results")
#             except Exception as e:
#                 print(f"    [!] Error: {e}")
            
#             time.sleep(1.5)
    
#     # Search for .env files with specific patterns
#     env_patterns = [
#         '.env',
#         '.env.local',
#         '.env.production',
#         '.env.development',
#         '.env.staging',
#         '.env.example',
#     ]
    
#     for env in env_patterns:
#         query = f'"{domain_clean}" {env} site:github.com'
#         print(f"  Searching: {query}")
        
#         try:
#             results = google_search(query, num_results=num_results)
#             count = 0
#             for r in results:
#                 if 'github.com' in r['url']:
#                     if r['url'] not in seen_urls:
#                         seen_urls.add(r['url'])
#                         r['file_type'] = env
#                         r['description'] = f"GitHub Environment file: {env}"
#                         r['search_type'] = 'github_env_file'
#                         all_results.append(r)
#                         count += 1
#             print(f"    Found {count} new results")
#         except Exception as e:
#             print(f"    [!] Error: {e}")
        
#         time.sleep(1.5)
    
#     return all_results

# def search_github_secrets(domain, num_results=None):
#     """Search GitHub for exposed secrets and credentials."""
#     all_results = []
#     seen_urls = set()
#     domain_clean = sanitize_domain(domain)
    
#     print(f"\n🔍 Searching GitHub for exposed secrets...")
#     print("-" * 60)
    
#     # Secret patterns to search for
#     secret_patterns = [
#         ('DB_PASSWORD', 'Database password'),
#         ('API_KEY', 'API Key'),
#         ('SECRET_KEY', 'Secret key'),
#         ('JWT_SECRET', 'JWT Secret'),
#         ('AWS_ACCESS_KEY', 'AWS Access Key'),
#         ('AWS_SECRET_KEY', 'AWS Secret Key'),
#         ('STRIPE_SECRET', 'Stripe Secret'),
#         ('PAYPAL_SECRET', 'PayPal Secret'),
#         ('SENDGRID_API_KEY', 'SendGrid API Key'),
#         ('MAILGUN_API_KEY', 'Mailgun API Key'),
#         ('SMTP_PASSWORD', 'SMTP Password'),
#         ('APP_KEY', 'Application Key'),
#         ('TOKEN', 'Token'),
#         ('PASSWORD', 'Password'),
#         ('CREDENTIALS', 'Credentials'),
#     ]
    
#     for pattern, description in secret_patterns:
#         # Search in files on GitHub
#         queries = [
#             f'"{domain_clean}" "{pattern}" site:github.com',
#             f'{domain_clean} "{pattern}" site:github.com',
#             f'"{pattern}" site:github.com {domain_clean}',
#         ]
        
#         for query in queries:
#             print(f"  Searching: {query}")
            
#             try:
#                 results = google_search(query, num_results=num_results)
#                 count = 0
#                 for r in results:
#                     if 'github.com' in r['url']:
#                         # Exclude common false positives
#                         exclude_patterns = ['example', 'sample', 'demo', 'test']
#                         snippet = r.get('snippet', '').lower()
#                         if not any(ex in snippet for ex in exclude_patterns):
#                             if r['url'] not in seen_urls:
#                                 seen_urls.add(r['url'])
#                                 r['file_type'] = pattern
#                                 r['description'] = f"GitHub Secret: {description}"
#                                 r['search_type'] = 'github_secret'
#                                 all_results.append(r)
#                                 count += 1
#                 print(f"    Found {count} new results")
#             except Exception as e:
#                 print(f"    [!] Error: {e}")
            
#             time.sleep(1.5)
    
#     return all_results

# def extract_sensitive_from_content(content, url):
#     """Extract sensitive patterns from content."""
#     findings = []
    
#     if not content:
#         return findings
    
#     for pattern, description in SENSITIVE_CONTENT_PATTERNS:
#         matches = re.findall(pattern, content, re.IGNORECASE)
#         if matches:
#             for match in matches:
#                 # Clean up the match (remove quotes, etc.)
#                 clean_match = match.strip('"\'')
#                 if len(clean_match) > 3:  # Avoid false positives with very short matches
#                     findings.append({
#                         'pattern': pattern,
#                         'description': description,
#                         'match': clean_match,
#                         'url': url
#                     })
    
#     return findings

# def search_all_sensitive(domain, num_results=None):
#     """Comprehensive search for all sensitive information."""
#     domain_clean = sanitize_domain(domain)
#     all_results = []
    
#     print("\n" + "="*60)
#     print("🔐 COMPREHENSIVE SENSITIVE DATA SEARCH")
#     print("="*60)
#     print(f"Target Domain: {domain_clean}")
#     print(f"Start Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
#     print("="*60)
    
#     # 1. Google search for sensitive files
#     google_file_results = search_sensitive_files_google(domain_clean, num_results)
#     all_results.extend(google_file_results)
    
#     # 2. Google search for sensitive content
#     google_content_results = search_sensitive_content_google(domain_clean, num_results)
#     all_results.extend(google_content_results)
    
#     # 3. GitHub sensitive files
#     github_file_results = search_github_sensitive(domain_clean, num_results)
#     all_results.extend(github_file_results)
    
#     # 4. GitHub secrets
#     github_secret_results = search_github_secrets(domain_clean, num_results)
#     all_results.extend(github_secret_results)
    
#     # Remove duplicates based on URL
#     seen_urls = set()
#     unique_results = []
#     for item in all_results:
#         if item['url'] not in seen_urls:
#             seen_urls.add(item['url'])
#             unique_results.append(item)
    
#     print("\n" + "="*60)
#     print(f"✅ Search completed! Found {len(unique_results)} unique sensitive findings.")
#     print("="*60)
    
#     return unique_results

# def save_results(data, domain):
#     """Save results to JSON file with timestamp."""
#     clean_domain = sanitize_domain(domain)
#     timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
#     filename = f"sensitive_findings_{clean_domain}_{timestamp}.json"
#     filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
    
#     # Create summary
#     summary = {
#         'domain': clean_domain,
#         'search_time': datetime.now().isoformat(),
#         'total_findings': len(data),
#         'findings_by_type': {},
#         'findings': data
#     }
    
#     # Group by search type
#     for item in data:
#         search_type = item.get('search_type', 'unknown')
#         if search_type not in summary['findings_by_type']:
#             summary['findings_by_type'][search_type] = 0
#         summary['findings_by_type'][search_type] += 1
    
#     with open(filename, 'w', encoding='utf-8') as f:
#         json.dump(summary, f, indent=2, ensure_ascii=False)
    
#     return filename

# if __name__ == "__main__":
#     if not SCRAPERAPI_KEY:
#         raise SystemExit("ERROR: Set SCRAPER_API_KEY in your .env file or environment.")
    
#     print("="*60)
#     print("🔐 SENSITIVE DATA DISCOVERY TOOL")
#     print("="*60)
    
#     domain = input("\nDomain (e.g. example.com): ").strip()
#     n = input("Results per search (leave blank for all): ").strip()
#     num_results = int(n) if n else None
    
#     # Run comprehensive search
#     results = search_all_sensitive(domain, num_results)
    
#     # Save results
#     filename = save_results(results, domain)
#     print(f"\n📁 Results saved to: {filename}")
    
#     # Print summary
#     print("\n📊 SUMMARY:")
#     print("-" * 40)
#     print(f"Total sensitive findings: {len(results)}")
    
#     # Group by type
#     type_counts = {}
#     for item in results:
#         file_type = item.get('file_type', 'unknown')
#         if file_type not in type_counts:
#             type_counts[file_type] = 0
#         type_counts[file_type] += 1
    
#     print("\nFindings by file type:")
#     for file_type, count in sorted(type_counts.items(), key=lambda x: x[1], reverse=True)[:10]:
#         print(f"  {file_type}: {count}")
    
#     # Show sensitive findings summary
#     sensitive_count = sum(1 for item in results if item.get('search_type') in 
#                          ['github_secret', 'google_sensitive_content'])
#     print(f"\nHigh-priority sensitive findings: {sensitive_count}")
    
#     # Print a few sample findings
#     print("\n🔍 Sample Findings:")
#     for i, item in enumerate(results[:5]):
#         print(f"  {i+1}. {item.get('description', 'Unknown')}")
#         print(f"     URL: {item.get('url', 'N/A')}")
#         print(f"     Type: {item.get('file_type', 'Unknown')}")
#         print()
    
#     print("="*60)
#     print("✅ Search complete! Check the JSON file for full results.")
#     print("="*60)


# deep research - 2

# import os
# import re
# import io
# import json
# import time
# import requests
# import base64
# import socket
# import dns.resolver
# from urllib.parse import urlparse
# from datetime import datetime
# from dotenv import load_dotenv

# load_dotenv()

# SCRAPERAPI_KEY = os.getenv("SCRAPER_API_KEY")
# SCRAPERAPI_SEARCH_URL = "https://api.scraperapi.com/structured/google/search"
# VIRUSTOTAL_API_KEY = os.getenv("VIRUSTOTAL_API_KEY")  # Optional for subdomain discovery
# SECURITYTRAILS_API_KEY = os.getenv("SECURITYTRAILS_API_KEY")  # Optional

# HEADERS = {
#     "User-Agent": (
#         "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
#         "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
#     )
# }

# # Sensitive file patterns to search for
# SENSITIVE_FILE_PATTERNS = [
#     # Environment files
#     (".env", "Environment file"),
#     (".env.local", "Local environment file"),
#     (".env.production", "Production environment file"),
#     (".env.development", "Development environment file"),
#     (".env.staging", "Staging environment file"),
#     (".env.example", "Environment example file"),
#     (".env.test", "Test environment file"),
#     (".env.ci", "CI environment file"),
#     (".env.docker", "Docker environment file"),
#     (".env.sample", "Environment sample file"),
    
#     # Configuration files
#     ("config.php", "PHP configuration"),
#     ("settings.py", "Python settings"),
#     ("application.properties", "Java properties"),
#     ("application.yml", "YAML configuration"),
#     ("application.yaml", "YAML configuration"),
#     ("docker-compose.yml", "Docker compose"),
#     ("docker-compose.yaml", "Docker compose"),
#     (".travis.yml", "Travis CI config"),
#     (".gitlab-ci.yml", "GitLab CI config"),
#     (".github/workflows/*.yml", "GitHub Actions"),
#     ("config.json", "JSON configuration"),
#     ("config.ini", "INI configuration"),
#     ("config.yaml", "YAML config"),
#     ("config.yml", "YAML config"),
#     ("web.config", "IIS configuration"),
#     ("appsettings.json", ".NET configuration"),
#     ("database.yml", "Database configuration"),
#     ("secrets.yml", "Secrets configuration"),
#     ("settings.ini", "Settings file"),
#     (".htaccess", "Apache configuration"),
#     (".htpasswd", "Apache password file"),
# ]

# # Sensitive content patterns to search for
# SENSITIVE_CONTENT_PATTERNS = [
#     # Password patterns
#     (r'(?i)password\s*[=:]\s*[\'"]?([^\'"\s]+)', "Password found"),
#     (r'(?i)passwd\s*[=:]\s*[\'"]?([^\'"\s]+)', "Passwd found"),
#     (r'(?i)pwd\s*[=:]\s*[\'"]?([^\'"\s]+)', "PWD found"),
    
#     # API Keys
#     (r'(?i)api[_-]?key\s*[=:]\s*[\'"]?([^\'"\s]+)', "API Key found"),
#     (r'(?i)apikey\s*[=:]\s*[\'"]?([^\'"\s]+)', "API Key found"),
#     (r'(?i)api_token\s*[=:]\s*[\'"]?([^\'"\s]+)', "API Token found"),
#     (r'(?i)access_token\s*[=:]\s*[\'"]?([^\'"\s]+)', "Access Token found"),
#     (r'(?i)auth_token\s*[=:]\s*[\'"]?([^\'"\s]+)', "Auth Token found"),
    
#     # Database credentials
#     (r'(?i)db[_-]?password\s*[=:]\s*[\'"]?([^\'"\s]+)', "Database password found"),
#     (r'(?i)db[_-]?user\s*[=:]\s*[\'"]?([^\'"\s]+)', "Database user found"),
#     (r'(?i)database[_-]?url\s*[=:]\s*[\'"]?([^\'"\s]+)', "Database URL found"),
#     (r'(?i)db_[a-z_]*password\s*[=:]\s*[\'"]?([^\'"\s]+)', "Database password found"),
#     (r'(?i)mongodb\s*[=:]\s*[\'"]?([^\'"\s]+)', "MongoDB connection string"),
#     (r'(?i)mysql\s*[=:]\s*[\'"]?([^\'"\s]+)', "MySQL connection string"),
#     (r'(?i)postgresql\s*[=:]\s*[\'"]?([^\'"\s]+)', "PostgreSQL connection string"),
    
#     # Secret keys
#     (r'(?i)secret[_-]?key\s*[=:]\s*[\'"]?([^\'"\s]+)', "Secret key found"),
#     (r'(?i)SECRET_KEY\s*[=:]\s*[\'"]?([^\'"\s]+)', "Secret key found"),
#     (r'(?i)APP_KEY\s*[=:]\s*[\'"]?([^\'"\s]+)', "Application key found"),
#     (r'(?i)JWT_SECRET\s*[=:]\s*[\'"]?([^\'"\s]+)', "JWT Secret found"),
#     (r'(?i)JWT_KEY\s*[=:]\s*[\'"]?([^\'"\s]+)', "JWT Key found"),
    
#     # Cloud credentials
#     (r'(?i)AWS_ACCESS_KEY_ID\s*[=:]\s*[\'"]?([^\'"\s]+)', "AWS Access Key found"),
#     (r'(?i)AWS_SECRET_ACCESS_KEY\s*[=:]\s*[\'"]?([^\'"\s]+)', "AWS Secret Key found"),
#     (r'(?i)aws_access_key_id\s*[=:]\s*[\'"]?([^\'"\s]+)', "AWS Access Key found"),
#     (r'(?i)aws_secret_access_key\s*[=:]\s*[\'"]?([^\'"\s]+)', "AWS Secret Key found"),
#     (r'(?i)GCP_*KEY\s*[=:]\s*[\'"]?([^\'"\s]+)', "GCP Key found"),
#     (r'(?i)GOOGLE_APPLICATION_CREDENTIALS\s*[=:]\s*[\'"]?([^\'"\s]+)', "Google credentials found"),
#     (r'(?i)AZURE_*KEY\s*[=:]\s*[\'"]?([^\'"\s]+)', "Azure Key found"),
    
#     # Payment credentials
#     (r'(?i)STRIPE_[A-Z_]*KEY\s*[=:]\s*[\'"]?([^\'"\s]+)', "Stripe key found"),
#     (r'(?i)STRIPE_SECRET\s*[=:]\s*[\'"]?([^\'"\s]+)', "Stripe secret found"),
#     (r'(?i)STRIPE_PUBLISHABLE\s*[=:]\s*[\'"]?([^\'"\s]+)', "Stripe publishable key found"),
#     (r'(?i)PAYPAL_*KEY\s*[=:]\s*[\'"]?([^\'"\s]+)', "PayPal key found"),
#     (r'(?i)PAYPAL_SECRET\s*[=:]\s*[\'"]?([^\'"\s]+)', "PayPal secret found"),
    
#     # Email/SMTP
#     (r'(?i)SMTP_PASSWORD\s*[=:]\s*[\'"]?([^\'"\s]+)', "SMTP password found"),
#     (r'(?i)MAIL_PASSWORD\s*[=:]\s*[\'"]?([^\'"\s]+)', "Mail password found"),
#     (r'(?i)EMAIL_PASSWORD\s*[=:]\s*[\'"]?([^\'"\s]+)', "Email password found"),
#     (r'(?i)SENDGRID_API_KEY\s*[=:]\s*[\'"]?([^\'"\s]+)', "SendGrid API key found"),
#     (r'(?i)MAILGUN_API_KEY\s*[=:]\s*[\'"]?([^\'"\s]+)', "Mailgun API key found"),
    
#     # Tokens
#     (r'(?i)token\s*[=:]\s*[\'"]?([^\'"\s]+)', "Token found"),
#     (r'(?i)bearer\s+([^\s\'"]+)', "Bearer token found"),
#     (r'(?i)authorization\s*[=:]\s*[\'"]?([^\'"\s]+)', "Authorization token found"),
#     (r'(?i)auth[_-]?token\s*[=:]\s*[\'"]?([^\'"\s]+)', "Auth token found"),
    
#     # SSH Keys
#     (r'-----BEGIN (RSA|DSA|EC|OPENSSH) PRIVATE KEY-----', "SSH Private Key found"),
#     (r'-----BEGIN RSA PRIVATE KEY-----', "RSA Private Key found"),
#     (r'-----BEGIN DSA PRIVATE KEY-----', "DSA Private Key found"),
#     (r'-----BEGIN EC PRIVATE KEY-----', "EC Private Key found"),
#     (r'-----BEGIN OPENSSH PRIVATE KEY-----', "OpenSSH Private Key found"),
    
#     # Other sensitive
#     (r'(?i)encryption_key\s*[=:]\s*[\'"]?([^\'"\s]+)', "Encryption key found"),
#     (r'(?i)salt\s*[=:]\s*[\'"]?([^\'"\s]+)', "Salt found"),
#     (r'(?i)hash\s*[=:]\s*[\'"]?([^\'"\s]+)', "Hash found"),
#     (r'(?i)private_key\s*[=:]\s*[\'"]?([^\'"\s]+)', "Private key found"),
#     (r'(?i)public_key\s*[=:]\s*[\'"]?([^\'"\s]+)', "Public key found"),
# ]

# # GitHub sensitive patterns
# GITHUB_SENSITIVE_PATTERNS = [
#     ('.env', 'Environment file'),
#     ('.env.local', 'Local environment file'),
#     ('.env.production', 'Production environment file'),
#     ('.env.development', 'Development environment file'),
#     ('.env.staging', 'Staging environment file'),
#     ('.env.example', 'Environment example file'),
#     ('.env.test', 'Test environment file'),
#     ('config.php', 'PHP configuration'),
#     ('settings.py', 'Python settings'),
#     ('application.properties', 'Java properties'),
#     ('docker-compose.yml', 'Docker compose'),
#     ('.travis.yml', 'Travis CI config'),
#     ('.gitlab-ci.yml', 'GitLab CI config'),
#     ('web.config', 'IIS configuration'),
#     ('appsettings.json', '.NET configuration'),
#     ('database.yml', 'Database configuration'),
#     ('secrets.yml', 'Secrets configuration'),
#     ('.htaccess', 'Apache configuration'),
#     ('.htpasswd', 'Apache password file'),
#     ('secrets.json', 'Secrets JSON file'),
#     ('secrets.yaml', 'Secrets YAML file'),
#     ('credentials.json', 'Credentials file'),
#     ('credentials.txt', 'Credentials text file'),
#     ('tokens.txt', 'Tokens file'),
#     ('keys.txt', 'Keys file'),
#     ('private.pem', 'Private key file'),
#     ('id_rsa', 'SSH private key'),
#     ('id_dsa', 'SSH private key'),
#     ('id_ecdsa', 'SSH private key'),
#     ('id_ed25519', 'SSH private key'),
# ]

# def sanitize_domain(domain):
#     """Clean and sanitize domain input."""
#     domain = domain.strip().rstrip('/')
#     domain = re.sub(r'^https?://', '', domain)
#     domain = domain.split('/')[0]
#     return domain

# def get_root_domain(domain):
#     """Extract the root domain."""
#     domain = sanitize_domain(domain)
#     domain_clean = domain.lower().strip()
#     domain_parts = domain_clean.split('.')
    
#     if len(domain_parts) > 2:
#         if domain_parts[-2] in ['co', 'com', 'org', 'net', 'gov', 'edu'] and len(domain_parts[-1]) <= 3:
#             root_domain = '.'.join(domain_parts[-3:])
#         else:
#             root_domain = '.'.join(domain_parts[-2:])
#     else:
#         root_domain = domain_clean
    
#     return root_domain

# def google_search(query, num_results=None):
#     """Perform a Google search using ScraperAPI."""
#     params = {
#         "api_key": SCRAPERAPI_KEY,
#         "query": query,
#     }
#     if num_results is not None:
#         params["num"] = num_results

#     try:
#         response = requests.get(
#             SCRAPERAPI_SEARCH_URL,
#             params=params,
#             headers=HEADERS,
#             timeout=60,
#         )
#         response.raise_for_status()
#         data = response.json()

#         results = []
#         items = data.get("organic_results", [])
#         if num_results is not None:
#             items = items[:num_results]

#         for item in items:
#             link = item.get("link") or item.get("url")
#             if link:
#                 results.append({
#                     "title": item.get("title"),
#                     "url": link,
#                     "snippet": item.get("snippet"),
#                 })
#         return results
#     except Exception as e:
#         print(f"  [!] Search failed: {e}")
#         return []

# # --- Subdomain Discovery Functions ---

# def discover_subdomains_crt_sh(domain):
#     """Discover subdomains using crt.sh certificate transparency logs."""
#     subdomains = set()
#     domain_clean = sanitize_domain(domain)
    
#     try:
#         url = f"https://crt.sh/?q=%25.{domain_clean}&output=json"
#         response = requests.get(url, headers=HEADERS, timeout=30)
        
#         if response.status_code == 200:
#             data = response.json()
#             for entry in data:
#                 name = entry.get('name_value', '')
#                 if name:
#                     # Split multiple names
#                     for sub in name.split('\n'):
#                         sub = sub.strip()
#                         if sub and sub.endswith(domain_clean) and sub != domain_clean:
#                             # Remove wildcard
#                             if sub.startswith('*.'):
#                                 sub = sub[2:]
#                             subdomains.add(sub.lower())
        
#         print(f"    Found {len(subdomains)} subdomains from crt.sh")
#         return list(subdomains)
#     except Exception as e:
#         print(f"    [!] crt.sh error: {e}")
#         return []

# def discover_subdomains_dns(domain):
#     """Discover subdomains using DNS enumeration."""
#     subdomains = set()
#     domain_clean = sanitize_domain(domain)
    
#     # Common subdomain prefixes
#     common_prefixes = [
#         'www', 'mail', 'ftp', 'localhost', 'webmail', 'smtp', 'pop', 'ns1', 'webdisk',
#         'ns2', 'cpanel', 'whm', 'autodiscover', 'autoconfig', 'm', 'imap', 'test',
#         'ns3', 'ns4', 'admin', 'staging', 'dev', 'api', 'blog', 'docs', 'app',
#         'dev', 'test', 'stage', 'prod', 'production', 'uat', 'sit', 'demo',
#         'portal', 'secure', 'vpn', 'remote', 'exchange', 'lync', 'office',
#         'owa', 'msoffice', 'sharepoint', 'sp', 'intranet', 'extranet',
#         'backup', 'db', 'mysql', 'postgres', 'redis', 'elastic', 'kibana',
#         'grafana', 'prometheus', 'jenkins', 'sonar', 'gitlab', 'github',
#         'jira', 'confluence', 'bitbucket', 'artifactory', 'nexus',
#         'monitor', 'stats', 'analytics', 'metrics', 'logs', 'trace',
#         'auth', 'login', 'signup', 'register', 'account', 'profile',
#         'support', 'help', 'status', 'uptime', 'health', 'ping',
#         'cdn', 'static', 'assets', 'images', 'media', 'files',
#         'download', 'upload', 'stream', 'video', 'audio',
#         'news', 'events', 'calendar', 'forum', 'community',
#         'shop', 'store', 'cart', 'checkout', 'payment',
#         'learn', 'training', 'university', 'academy', 'courses'
#     ]
    
#     # Try to resolve each subdomain
#     print(f"    Performing DNS enumeration (this may take a moment)...")
#     for prefix in common_prefixes:
#         subdomain = f"{prefix}.{domain_clean}"
#         try:
#             # Try to resolve A record
#             answers = dns.resolver.resolve(subdomain, 'A')
#             if answers:
#                 subdomains.add(subdomain)
#                 print(f"      Found: {subdomain}")
#         except:
#             pass
        
#         # Add delay to avoid rate limiting
#         time.sleep(0.1)
    
#     return list(subdomains)

# def discover_subdomains_securitytrails(domain):
#     """Discover subdomains using SecurityTrails API."""
#     subdomains = set()
#     domain_clean = sanitize_domain(domain)
    
#     if not SECURITYTRAILS_API_KEY:
#         return []
    
#     try:
#         url = f"https://api.securitytrails.com/v1/domain/{domain_clean}/subdomains"
#         headers = {
#             'APIKEY': SECURITYTRAILS_API_KEY,
#             'User-Agent': 'Mozilla/5.0'
#         }
#         response = requests.get(url, headers=headers, timeout=30)
        
#         if response.status_code == 200:
#             data = response.json()
#             for sub in data.get('subdomains', []):
#                 subdomain = f"{sub}.{domain_clean}"
#                 subdomains.add(subdomain.lower())
        
#         print(f"    Found {len(subdomains)} subdomains from SecurityTrails")
#         return list(subdomains)
#     except Exception as e:
#         print(f"    [!] SecurityTrails error: {e}")
#         return []

# def discover_subdomains_virustotal(domain):
#     """Discover subdomains using VirusTotal API."""
#     subdomains = set()
#     domain_clean = sanitize_domain(domain)
    
#     if not VIRUSTOTAL_API_KEY:
#         return []
    
#     try:
#         url = f"https://www.virustotal.com/api/v3/domains/{domain_clean}/subdomains"
#         headers = {
#             'x-apikey': VIRUSTOTAL_API_KEY,
#             'User-Agent': 'Mozilla/5.0'
#         }
#         response = requests.get(url, headers=headers, timeout=30)
        
#         if response.status_code == 200:
#             data = response.json()
#             for item in data.get('data', []):
#                 sub = item.get('id', '')
#                 if sub:
#                     subdomains.add(sub.lower())
        
#         print(f"    Found {len(subdomains)} subdomains from VirusTotal")
#         return list(subdomains)
#     except Exception as e:
#         print(f"    [!] VirusTotal error: {e}")
#         return []

# def discover_subdomains_google(domain, num_results=None):
#     """Discover subdomains using Google search."""
#     subdomains = set()
#     domain_clean = sanitize_domain(domain)
    
#     print(f"    Searching Google for subdomains...")
    
#     # Google dorks to find subdomains
#     queries = [
#         f'site:{domain_clean} -www.{domain_clean} -mail.{domain_clean}',
#         f'site:*.{domain_clean}',
#         f'intitle:"index of" {domain_clean}',
#         f'inurl:{domain_clean} -www -mail',
#     ]
    
#     for query in queries:
#         try:
#             results = google_search(query, num_results=num_results or 20)
#             for item in results:
#                 url = item.get('url', '')
#                 if url:
#                     # Extract subdomain from URL
#                     parsed = urlparse(url)
#                     hostname = parsed.netloc.lower()
#                     if hostname and hostname.endswith(domain_clean) and hostname != domain_clean:
#                         subdomains.add(hostname)
#         except Exception as e:
#             print(f"      [!] Google search error: {e}")
        
#         time.sleep(1)
    
#     return list(subdomains)

# def discover_all_subdomains(domain, num_results=None):
#     """Discover subdomains using multiple sources."""
#     domain_clean = sanitize_domain(domain)
#     all_subdomains = set()
    
#     print(f"\n🌐 Discovering subdomains for: {domain_clean}")
#     print("-" * 60)
    
#     # Method 1: crt.sh Certificate Transparency
#     print("  [1/5] Checking crt.sh...")
#     crt_subdomains = discover_subdomains_crt_sh(domain_clean)
#     all_subdomains.update(crt_subdomains)
    
#     # Method 2: DNS Enumeration
#     print("\n  [2/5] Performing DNS enumeration...")
#     dns_subdomains = discover_subdomains_dns(domain_clean)
#     all_subdomains.update(dns_subdomains)
    
#     # Method 3: SecurityTrails API
#     if SECURITYTRAILS_API_KEY:
#         print("\n  [3/5] Checking SecurityTrails...")
#         st_subdomains = discover_subdomains_securitytrails(domain_clean)
#         all_subdomains.update(st_subdomains)
#     else:
#         print("\n  [3/5] SecurityTrails API key not set (skipping)")
    
#     # Method 4: VirusTotal API
#     if VIRUSTOTAL_API_KEY:
#         print("\n  [4/5] Checking VirusTotal...")
#         vt_subdomains = discover_subdomains_virustotal(domain_clean)
#         all_subdomains.update(vt_subdomains)
#     else:
#         print("\n  [4/5] VirusTotal API key not set (skipping)")
    
#     # Method 5: Google Search
#     print("\n  [5/5] Searching Google for subdomains...")
#     google_subdomains = discover_subdomains_google(domain_clean, num_results)
#     all_subdomains.update(google_subdomains)
    
#     # Filter out the main domain
#     all_subdomains = {s for s in all_subdomains if s != domain_clean}
    
#     # Sort and return
#     return sorted(list(all_subdomains))

# # --- Sensitive Data Search Functions ---

# def search_sensitive_files_google(domain, num_results=None):
#     """Search for sensitive files using Google search."""
#     all_results = []
#     seen_urls = set()
#     domain_clean = sanitize_domain(domain)
    
#     print(f"\n🔍 Searching for sensitive files via Google...")
#     print("-" * 60)
    
#     for pattern, description in SENSITIVE_FILE_PATTERNS:
#         if '*' in pattern:
#             continue
            
#         query = f'site:{domain_clean} "{pattern}"'
#         print(f"  Searching: {query}")
        
#         try:
#             results = google_search(query, num_results=num_results)
#             count = 0
#             for r in results:
#                 if r['url'] not in seen_urls:
#                     seen_urls.add(r['url'])
#                     r['file_type'] = pattern
#                     r['description'] = description
#                     r['search_type'] = 'google_sensitive_file'
#                     all_results.append(r)
#                     count += 1
#             print(f"    Found {count} new results")
#         except Exception as e:
#             print(f"    [!] Error: {e}")
        
#         time.sleep(1)
    
#     return all_results

# def search_sensitive_content_google(domain, num_results=None):
#     """Search for sensitive content patterns using Google search."""
#     all_results = []
#     seen_urls = set()
#     domain_clean = sanitize_domain(domain)
    
#     print(f"\n🔍 Searching for sensitive content patterns...")
#     print("-" * 60)
    
#     key_patterns = [
#         ('password', 'Password in code'),
#         ('api_key', 'API Key'),
#         ('secret', 'Secret'),
#         ('token', 'Token'),
#         ('db_password', 'Database password'),
#         ('aws_key', 'AWS Key'),
#         ('private_key', 'Private key'),
#         ('auth', 'Authentication'),
#         ('credentials', 'Credentials'),
#         ('jwt', 'JWT Token'),
#     ]
    
#     for keyword, description in key_patterns:
#         query = f'site:{domain_clean} {keyword}'
#         print(f"  Searching: {query}")
        
#         try:
#             results = google_search(query, num_results=num_results)
#             count = 0
#             for r in results:
#                 snippet = r.get('snippet', '').lower()
#                 if any(pat in snippet for pat in ['password', 'secret', 'key', 'token', 'auth']):
#                     if r['url'] not in seen_urls:
#                         seen_urls.add(r['url'])
#                         r['file_type'] = keyword
#                         r['description'] = f"Sensitive content: {description}"
#                         r['search_type'] = 'google_sensitive_content'
#                         all_results.append(r)
#                         count += 1
#             print(f"    Found {count} new results")
#         except Exception as e:
#             print(f"    [!] Error: {e}")
        
#         time.sleep(1)
    
#     return all_results

# def search_github_sensitive(domain, num_results=None):
#     """Search GitHub for sensitive files and content."""
#     all_results = []
#     seen_urls = set()
#     domain_clean = sanitize_domain(domain)
    
#     print(f"\n🔍 Searching GitHub for sensitive files...")
#     print("-" * 60)
    
#     for pattern, description in GITHUB_SENSITIVE_PATTERNS:
#         queries = [
#             f'"{domain_clean}" "{pattern}" site:github.com',
#             f'{domain_clean} "{pattern}" site:github.com',
#         ]
        
#         for query in queries:
#             print(f"  Searching: {query}")
            
#             try:
#                 results = google_search(query, num_results=num_results)
#                 count = 0
#                 for r in results:
#                     if 'github.com' in r['url'] or 'github.io' in r['url']:
#                         if r['url'] not in seen_urls:
#                             seen_urls.add(r['url'])
#                             r['file_type'] = pattern
#                             r['description'] = f"GitHub: {description}"
#                             r['search_type'] = 'github_sensitive_file'
#                             all_results.append(r)
#                             count += 1
#                 print(f"    Found {count} new results")
#             except Exception as e:
#                 print(f"    [!] Error: {e}")
            
#             time.sleep(1.5)
    
#     # Search for .env files with specific patterns
#     env_patterns = [
#         '.env',
#         '.env.local',
#         '.env.production',
#         '.env.development',
#         '.env.staging',
#         '.env.example',
#     ]
    
#     for env in env_patterns:
#         query = f'"{domain_clean}" {env} site:github.com'
#         print(f"  Searching: {query}")
        
#         try:
#             results = google_search(query, num_results=num_results)
#             count = 0
#             for r in results:
#                 if 'github.com' in r['url']:
#                     if r['url'] not in seen_urls:
#                         seen_urls.add(r['url'])
#                         r['file_type'] = env
#                         r['description'] = f"GitHub Environment file: {env}"
#                         r['search_type'] = 'github_env_file'
#                         all_results.append(r)
#                         count += 1
#             print(f"    Found {count} new results")
#         except Exception as e:
#             print(f"    [!] Error: {e}")
        
#         time.sleep(1.5)
    
#     return all_results

# def search_github_secrets(domain, num_results=None):
#     """Search GitHub for exposed secrets and credentials."""
#     all_results = []
#     seen_urls = set()
#     domain_clean = sanitize_domain(domain)
    
#     print(f"\n🔍 Searching GitHub for exposed secrets...")
#     print("-" * 60)
    
#     secret_patterns = [
#         ('DB_PASSWORD', 'Database password'),
#         ('API_KEY', 'API Key'),
#         ('SECRET_KEY', 'Secret key'),
#         ('JWT_SECRET', 'JWT Secret'),
#         ('AWS_ACCESS_KEY', 'AWS Access Key'),
#         ('AWS_SECRET_KEY', 'AWS Secret Key'),
#         ('STRIPE_SECRET', 'Stripe Secret'),
#         ('PAYPAL_SECRET', 'PayPal Secret'),
#         ('SENDGRID_API_KEY', 'SendGrid API Key'),
#         ('MAILGUN_API_KEY', 'Mailgun API Key'),
#         ('SMTP_PASSWORD', 'SMTP Password'),
#         ('APP_KEY', 'Application Key'),
#         ('TOKEN', 'Token'),
#         ('PASSWORD', 'Password'),
#         ('CREDENTIALS', 'Credentials'),
#     ]
    
#     for pattern, description in secret_patterns:
#         queries = [
#             f'"{domain_clean}" "{pattern}" site:github.com',
#             f'{domain_clean} "{pattern}" site:github.com',
#             f'"{pattern}" site:github.com {domain_clean}',
#         ]
        
#         for query in queries:
#             print(f"  Searching: {query}")
            
#             try:
#                 results = google_search(query, num_results=num_results)
#                 count = 0
#                 for r in results:
#                     if 'github.com' in r['url']:
#                         snippet = r.get('snippet', '').lower()
#                         exclude_patterns = ['example', 'sample', 'demo', 'test']
#                         if not any(ex in snippet for ex in exclude_patterns):
#                             if r['url'] not in seen_urls:
#                                 seen_urls.add(r['url'])
#                                 r['file_type'] = pattern
#                                 r['description'] = f"GitHub Secret: {description}"
#                                 r['search_type'] = 'github_secret'
#                                 all_results.append(r)
#                                 count += 1
#                 print(f"    Found {count} new results")
#             except Exception as e:
#                 print(f"    [!] Error: {e}")
            
#             time.sleep(1.5)
    
#     return all_results

# def extract_sensitive_from_content(content, url):
#     """Extract sensitive patterns from content."""
#     findings = []
    
#     if not content:
#         return findings
    
#     for pattern, description in SENSITIVE_CONTENT_PATTERNS:
#         matches = re.findall(pattern, content, re.IGNORECASE)
#         if matches:
#             for match in matches:
#                 clean_match = match.strip('"\'')
#                 if len(clean_match) > 3:
#                     findings.append({
#                         'pattern': pattern,
#                         'description': description,
#                         'match': clean_match,
#                         'url': url
#                     })
    
#     return findings

# def search_sensitive_for_subdomain(domain, subdomain, num_results=None):
#     """Search for sensitive information on a specific subdomain."""
#     print(f"\n{'='*60}")
#     print(f"🔍 Searching subdomain: {subdomain}")
#     print(f"{'='*60}")
    
#     results = []
    
#     # Search for sensitive files
#     file_results = search_sensitive_files_google(subdomain, num_results)
#     results.extend(file_results)
    
#     # Search for sensitive content
#     content_results = search_sensitive_content_google(subdomain, num_results)
#     results.extend(content_results)
    
#     # Search GitHub for this subdomain
#     github_results = search_github_sensitive(subdomain, num_results)
#     results.extend(github_results)
    
#     # Search GitHub secrets
#     secret_results = search_github_secrets(subdomain, num_results)
#     results.extend(secret_results)
    
#     return results

# def search_all_sensitive_with_subdomains(domain, num_results=None, search_subdomains=True):
#     """Comprehensive search for all sensitive information including subdomains."""
#     domain_clean = sanitize_domain(domain)
#     all_results = []
#     all_subdomains = []
    
#     print("\n" + "="*60)
#     print("🔐 COMPREHENSIVE SENSITIVE DATA SEARCH")
#     print("="*60)
#     print(f"Target Domain: {domain_clean}")
#     print(f"Start Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
#     print("="*60)
    
#     # Search main domain
#     print(f"\n📌 Searching main domain: {domain_clean}")
#     main_results = search_all_sensitive_for_domain(domain_clean, num_results)
#     all_results.extend(main_results)
    
#     # Discover and search subdomains
#     if search_subdomains:
#         subdomains = discover_all_subdomains(domain_clean, num_results)
#         all_subdomains = subdomains
        
#         if subdomains:
#             print(f"\n✅ Found {len(subdomains)} subdomains")
#             print("Subdomains found:")
#             for i, sub in enumerate(subdomains, 1):
#                 print(f"  {i}. {sub}")
            
#             # Ask user if they want to search all subdomains
#             search_all = input(f"\nSearch all {len(subdomains)} subdomains? (y/n, default: y): ").strip().lower()
#             if search_all != 'n':
#                 for subdomain in subdomains:
#                     sub_results = search_sensitive_for_subdomain(domain_clean, subdomain, num_results)
#                     all_results.extend(sub_results)
                    
#                     # Save after each subdomain to avoid losing progress
#                     temp_filename = f"temp_results_{domain_clean}.json"
#                     with open(temp_filename, 'w', encoding='utf-8') as f:
#                         json.dump(all_results, f, indent=2, ensure_ascii=False)
                    
#                     print(f"  ✅ Completed {subdomain} - Found {len(sub_results)} items")
#                     print(f"  💾 Progress saved to {temp_filename}")
#             else:
#                 print("\n⏭️  Skipping subdomain searches")
#         else:
#             print("\n❌ No subdomains found")
    
#     # Remove duplicates based on URL
#     seen_urls = set()
#     unique_results = []
#     for item in all_results:
#         if item['url'] not in seen_urls:
#             seen_urls.add(item['url'])
#             unique_results.append(item)
    
#     print("\n" + "="*60)
#     print(f"✅ Search completed! Found {len(unique_results)} unique sensitive findings.")
#     print(f"   Main domain: {len([r for r in unique_results if domain_clean in r['url']])}")
#     print(f"   Subdomains: {len([r for r in unique_results if domain_clean not in r['url']])}")
#     print("="*60)
    
#     return unique_results, all_subdomains

# def search_all_sensitive_for_domain(domain, num_results=None):
#     """Search for sensitive information on a single domain."""
#     domain_clean = sanitize_domain(domain)
#     results = []
    
#     # 1. Google search for sensitive files
#     google_file_results = search_sensitive_files_google(domain_clean, num_results)
#     results.extend(google_file_results)
    
#     # 2. Google search for sensitive content
#     google_content_results = search_sensitive_content_google(domain_clean, num_results)
#     results.extend(google_content_results)
    
#     # 3. GitHub sensitive files
#     github_file_results = search_github_sensitive(domain_clean, num_results)
#     results.extend(github_file_results)
    
#     # 4. GitHub secrets
#     github_secret_results = search_github_secrets(domain_clean, num_results)
#     results.extend(github_secret_results)
    
#     return results

# def save_results(data, domain, subdomains=None):
#     """Save results to JSON file with timestamp."""
#     clean_domain = sanitize_domain(domain)
#     timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
#     filename = f"sensitive_findings_{clean_domain}_{timestamp}.json"
#     filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
    
#     # Create summary
#     summary = {
#         'domain': clean_domain,
#         'search_time': datetime.now().isoformat(),
#         'total_findings': len(data),
#         'subdomains_found': subdomains if subdomains else [],
#         'total_subdomains': len(subdomains) if subdomains else 0,
#         'findings_by_type': {},
#         'findings_by_domain': {},
#         'high_priority_findings': [],
#         'findings': data
#     }
    
#     # Group by search type
#     for item in data:
#         search_type = item.get('search_type', 'unknown')
#         if search_type not in summary['findings_by_type']:
#             summary['findings_by_type'][search_type] = 0
#         summary['findings_by_type'][search_type] += 1
        
#         # Group by domain
#         url = item.get('url', '')
#         domain_match = re.search(r'(?:https?://)?([^/]+)', url)
#         if domain_match:
#             domain_key = domain_match.group(1)
#             if domain_key not in summary['findings_by_domain']:
#                 summary['findings_by_domain'][domain_key] = 0
#             summary['findings_by_domain'][domain_key] += 1
    
#     # Identify high priority findings (secrets, passwords, keys)
#     high_priority_keywords = ['password', 'secret', 'key', 'token', 'auth', 'credential']
#     for item in data:
#         desc = item.get('description', '').lower()
#         if any(keyword in desc for keyword in high_priority_keywords):
#             summary['high_priority_findings'].append({
#                 'url': item.get('url'),
#                 'description': item.get('description'),
#                 'file_type': item.get('file_type')
#             })
    
#     with open(filename, 'w', encoding='utf-8') as f:
#         json.dump(summary, f, indent=2, ensure_ascii=False)
    
#     return filename

# if __name__ == "__main__":
#     if not SCRAPERAPI_KEY:
#         raise SystemExit("ERROR: Set SCRAPER_API_KEY in your .env file or environment.")
    
#     print("="*60)
#     print("🔐 SENSITIVE DATA DISCOVERY TOOL (WITH SUBDOMAIN SUPPORT)")
#     print("="*60)
    
#     domain = input("\nDomain (e.g. example.com): ").strip()
#     n = input("Results per search (leave blank for all): ").strip()
#     num_results = int(n) if n else None
    
#     search_subdomains_input = input("Search for subdomains? (y/n, default: y): ").strip().lower()
#     search_subdomains = search_subdomains_input != 'n'
    
#     # Run comprehensive search
#     results, subdomains = search_all_sensitive_with_subdomains(domain, num_results, search_subdomains)
    
#     # Save results
#     filename = save_results(results, domain, subdomains)
#     print(f"\n📁 Results saved to: {filename}")
    
#     # Print summary
#     print("\n📊 SUMMARY:")
#     print("-" * 40)
#     print(f"Total sensitive findings: {len(results)}")
#     print(f"Subdomains discovered: {len(subdomains) if subdomains else 0}")
    
#     # Group by type
#     type_counts = {}
#     for item in results:
#         file_type = item.get('file_type', 'unknown')
#         if file_type not in type_counts:
#             type_counts[file_type] = 0
#         type_counts[file_type] += 1
    
#     print("\nFindings by file type (top 10):")
#     for file_type, count in sorted(type_counts.items(), key=lambda x: x[1], reverse=True)[:10]:
#         print(f"  {file_type}: {count}")
    
#     # Show high priority findings
#     high_priority = [item for item in results if any(k in item.get('description', '').lower() 
#                     for k in ['password', 'secret', 'key', 'token', 'auth', 'credential'])]
#     print(f"\n🔥 High-priority sensitive findings: {len(high_priority)}")
    
#     if high_priority:
#         print("\nTop 5 High-Priority Findings:")
#         for i, item in enumerate(high_priority[:5], 1):
#             print(f"  {i}. {item.get('description', 'Unknown')}")
#             print(f"     URL: {item.get('url', 'N/A')}")
#             print(f"     Type: {item.get('file_type', 'Unknown')}")
#             print()
    
#     print("="*60)
#     print("✅ Search complete! Check the JSON file for full results.")
#     print("="*60)


# deep research testing 2 

import os
import re
import io
import json
import time
import requests
import base64
import dns.resolver
from urllib.parse import urlparse
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

SCRAPERAPI_KEY = os.getenv("SCRAPER_API_KEY")
SCRAPERAPI_SEARCH_URL = "https://api.scraperapi.com/structured/google/search"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    )
}

# Sensitive patterns to search for in code
SENSITIVE_PATTERNS = [
    # Environment files
    (r'\.env', 'Environment file'),
    (r'\.env\.local', 'Local environment file'),
    (r'\.env\.production', 'Production environment'),
    (r'\.env\.development', 'Development environment'),
    (r'\.env\.staging', 'Staging environment'),
    (r'\.env\.example', 'Environment example'),
    (r'\.env\.test', 'Test environment'),
    
    # Database credentials
    (r'DB_PASSWORD\s*=\s*[\'"]?([^\'"\s]+)', 'Database password'),
    (r'DB_USERNAME\s*=\s*[\'"]?([^\'"\s]+)', 'Database username'),
    (r'DB_HOST\s*=\s*[\'"]?([^\'"\s]+)', 'Database host'),
    (r'DB_DATABASE\s*=\s*[\'"]?([^\'"\s]+)', 'Database name'),
    (r'DATABASE_URL\s*=\s*[\'"]?([^\'"\s]+)', 'Database URL'),
    
    # API Keys & Secrets
    (r'API_KEY\s*=\s*[\'"]?([^\'"\s]+)', 'API Key'),
    (r'API_SECRET\s*=\s*[\'"]?([^\'"\s]+)', 'API Secret'),
    (r'SECRET_KEY\s*=\s*[\'"]?([^\'"\s]+)', 'Secret key'),
    (r'APP_KEY\s*=\s*[\'"]?([^\'"\s]+)', 'App key'),
    (r'JWT_SECRET\s*=\s*[\'"]?([^\'"\s]+)', 'JWT Secret'),
    (r'JWT_KEY\s*=\s*[\'"]?([^\'"\s]+)', 'JWT Key'),
    
    # Cloud credentials
    (r'AWS_ACCESS_KEY_ID\s*=\s*[\'"]?([^\'"\s]+)', 'AWS Access Key'),
    (r'AWS_SECRET_ACCESS_KEY\s*=\s*[\'"]?([^\'"\s]+)', 'AWS Secret Key'),
    (r'AWS_S3_BUCKET\s*=\s*[\'"]?([^\'"\s]+)', 'AWS S3 Bucket'),
    (r'GOOGLE_APPLICATION_CREDENTIALS\s*=\s*[\'"]?([^\'"\s]+)', 'Google Credentials'),
    
    # Payment credentials
    (r'STRIPE_SECRET\s*=\s*[\'"]?([^\'"\s]+)', 'Stripe Secret'),
    (r'STRIPE_PUBLISHABLE\s*=\s*[\'"]?([^\'"\s]+)', 'Stripe Publishable Key'),
    (r'PAYPAL_SECRET\s*=\s*[\'"]?([^\'"\s]+)', 'PayPal Secret'),
    (r'PAYPAL_CLIENT_ID\s*=\s*[\'"]?([^\'"\s]+)', 'PayPal Client ID'),
    
    # Email/SMTP
    (r'SMTP_PASSWORD\s*=\s*[\'"]?([^\'"\s]+)', 'SMTP Password'),
    (r'MAIL_PASSWORD\s*=\s*[\'"]?([^\'"\s]+)', 'Mail Password'),
    (r'SENDGRID_API_KEY\s*=\s*[\'"]?([^\'"\s]+)', 'SendGrid API Key'),
    (r'MAILGUN_API_KEY\s*=\s*[\'"]?([^\'"\s]+)', 'Mailgun API Key'),
    
    # Tokens
    (r'token\s*=\s*[\'"]?([^\'"\s]+)', 'Token found'),
    (r'Bearer\s+([^\s\'"]+)', 'Bearer token'),
    (r'authorization\s*=\s*[\'"]?([^\'"\s]+)', 'Authorization token'),
    
    # SSH Keys
    (r'-----BEGIN (RSA|DSA|EC|OPENSSH) PRIVATE KEY-----', 'SSH Private Key'),
    
    # Passwords
    (r'password\s*=\s*[\'"]?([^\'"\s]+)', 'Password found'),
    (r'passwd\s*=\s*[\'"]?([^\'"\s]+)', 'Passwd found'),
    (r'pwd\s*=\s*[\'"]?([^\'"\s]+)', 'PWD found'),
]

def sanitize_domain(domain):
    """Clean and sanitize domain input."""
    domain = domain.strip().rstrip('/')
    domain = re.sub(r'^https?://', '', domain)
    domain = domain.split('/')[0]
    return domain

def get_root_domain(domain):
    """Extract the root domain (handles subdomains)."""
    domain = sanitize_domain(domain)
    domain_clean = domain.lower().strip()
    domain_parts = domain_clean.split('.')
    
    if len(domain_parts) > 2:
        if domain_parts[-2] in ['co', 'com', 'org', 'net', 'gov', 'edu'] and len(domain_parts[-1]) <= 3:
            root_domain = '.'.join(domain_parts[-3:])
        else:
            root_domain = '.'.join(domain_parts[-2:])
    else:
        root_domain = domain_clean
    
    return root_domain

def google_search(query, num_results=None):
    """Perform a Google search using ScraperAPI."""
    params = {
        "api_key": SCRAPERAPI_KEY,
        "query": query,
    }
    if num_results is not None:
        params["num"] = num_results

    try:
        response = requests.get(
            SCRAPERAPI_SEARCH_URL,
            params=params,
            headers=HEADERS,
            timeout=60,
        )
        response.raise_for_status()
        data = response.json()

        results = []
        items = data.get("organic_results", [])
        if num_results is not None:
            items = items[:num_results]

        for item in items:
            link = item.get("link") or item.get("url")
            if link:
                results.append({
                    "title": item.get("title"),
                    "url": link,
                    "snippet": item.get("snippet"),
                })
        return results
    except Exception as e:
        print(f"  [!] Search failed: {e}")
        return []

# --- Subdomain Discovery Functions ---

def discover_subdomains_crt_sh(domain):
    """Discover subdomains using crt.sh certificate transparency logs."""
    subdomains = set()
    domain_clean = sanitize_domain(domain)
    
    try:
        url = f"https://crt.sh/?q=%25.{domain_clean}&output=json"
        response = requests.get(url, headers=HEADERS, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            for entry in data:
                name = entry.get('name_value', '')
                if name:
                    for sub in name.split('\n'):
                        sub = sub.strip()
                        if sub and sub.endswith(domain_clean) and sub != domain_clean:
                            if sub.startswith('*.'):
                                sub = sub[2:]
                            subdomains.add(sub.lower())
        
        return list(subdomains)
    except Exception as e:
        print(f"    [!] crt.sh error: {e}")
        return []

def discover_subdomains_dns(domain):
    """Discover subdomains using DNS enumeration."""
    subdomains = set()
    domain_clean = sanitize_domain(domain)
    
    # Common subdomain prefixes
    common_prefixes = [
        'www', 'mail', 'ftp', 'webmail', 'smtp', 'pop', 'ns1', 'ns2',
        'cpanel', 'whm', 'autodiscover', 'autoconfig', 'm', 'imap',
        'admin', 'staging', 'dev', 'api', 'blog', 'docs', 'app',
        'test', 'stage', 'prod', 'production', 'uat', 'demo',
        'portal', 'secure', 'vpn', 'remote', 'exchange',
        'backup', 'db', 'mysql', 'postgres', 'redis', 'elastic',
        'monitor', 'stats', 'analytics', 'metrics', 'logs',
        'auth', 'login', 'signup', 'register', 'account',
        'support', 'help', 'status', 'health',
        'cdn', 'static', 'assets', 'images', 'media', 'files',
        'download', 'upload', 'shop', 'store', 'cart',
        'learn', 'training', 'university', 'academy'
    ]
    
    print(f"    Performing DNS enumeration...")
    for prefix in common_prefixes:
        subdomain = f"{prefix}.{domain_clean}"
        try:
            answers = dns.resolver.resolve(subdomain, 'A')
            if answers:
                subdomains.add(subdomain)
                print(f"      Found: {subdomain}")
        except:
            pass
        
        time.sleep(0.05)
    
    return list(subdomains)

def discover_subdomains_google(domain, num_results=None):
    """Discover subdomains using Google search."""
    subdomains = set()
    domain_clean = sanitize_domain(domain)
    
    print(f"    Searching Google for subdomains...")
    
    queries = [
        f'site:*.{domain_clean} -www -mail -dev',
        f'site:*.*.{domain_clean}',
        f'intitle:"index of" {domain_clean}',
    ]
    
    for query in queries:
        try:
            results = google_search(query, num_results=num_results or 20)
            for item in results:
                url = item.get('url', '')
                if url:
                    parsed = urlparse(url)
                    hostname = parsed.netloc.lower()
                    if hostname and hostname.endswith(domain_clean) and hostname != domain_clean:
                        subdomains.add(hostname)
        except Exception as e:
            print(f"      [!] Google search error: {e}")
        
        time.sleep(1)
    
    return list(subdomains)

def discover_all_subdomains(domain, num_results=None):
    """Discover subdomains using multiple sources."""
    domain_clean = sanitize_domain(domain)
    all_subdomains = set()
    
    print(f"\n🌐 Discovering subdomains for: {domain_clean}")
    print("-" * 60)
    
    # Method 1: crt.sh
    print("  [1/3] Checking crt.sh...")
    crt_subdomains = discover_subdomains_crt_sh(domain_clean)
    all_subdomains.update(crt_subdomains)
    print(f"    Found {len(crt_subdomains)} subdomains from crt.sh")
    
    # Method 2: DNS Enumeration
    print("\n  [2/3] Performing DNS enumeration...")
    dns_subdomains = discover_subdomains_dns(domain_clean)
    all_subdomains.update(dns_subdomains)
    
    # Method 3: Google Search
    print("\n  [3/3] Searching Google for subdomains...")
    google_subdomains = discover_subdomains_google(domain_clean, num_results)
    all_subdomains.update(google_subdomains)
    
    # Filter out the main domain
    all_subdomains = {s for s in all_subdomains if s != domain_clean}
    
    return sorted(list(all_subdomains))

# --- GitHub Repository Search ---

def search_github_repos(domain, num_results=None):
    """Search for GitHub repositories related to the domain."""
    all_results = []
    seen_urls = set()
    domain_clean = sanitize_domain(domain)
    root_domain = get_root_domain(domain_clean)
    
    github_patterns = [
        f'"{domain_clean}" site:github.com',
        f'"{root_domain}" site:github.com',
        f'{domain_clean} site:github.com',
        f'{root_domain} site:github.com',
        f'intitle:"{domain_clean}" site:github.com',
        f'"{domain_clean}" inurl:github.com',
    ]
    
    github_patterns = list(dict.fromkeys(github_patterns))
    
    for pattern in github_patterns:
        try:
            results = google_search(pattern, num_results=num_results)
            for r in results:
                if ('github.com' in r['url'] or 'github.io' in r['url']):
                    if not any(x in r['url'].lower() for x in ['/issues', '/pulls', '/wiki', '/actions', '/security']):
                        if r['url'] not in seen_urls:
                            seen_urls.add(r['url'])
                            r['source'] = 'github'
                            r['filetype'] = 'github_repo'
                            all_results.append(r)
        except Exception as e:
            print(f"  [!] GitHub search failed for {pattern}: {e}")
        
        time.sleep(1)
    
    return all_results

def get_repo_details(url):
    """Extract repository details from GitHub URL."""
    try:
        parsed = urlparse(url)
        path_parts = parsed.path.strip('/').split('/')
        
        if len(path_parts) >= 2:
            if 'gist' in parsed.netloc.lower():
                return {
                    'type': 'gist',
                    'gist_id': path_parts[0] if path_parts else 'unknown'
                }
            
            owner = path_parts[0]
            repo = path_parts[1]
            return {
                'type': 'repository',
                'owner': owner,
                'repo': repo,
                'full_name': f"{owner}/{repo}"
            }
    except:
        pass
    return {'type': 'unknown'}

def fetch_file_content(owner, repo, filepath):
    """Fetch content of a specific file from GitHub."""
    api_url = f"https://api.github.com/repos/{owner}/{repo}/contents/{filepath}"
    headers = {
        'Accept': 'application/vnd.github.v3+json',
        'User-Agent': 'Mozilla/5.0'
    }
    
    try:
        response = requests.get(api_url, headers=headers, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if 'content' in data:
                content = base64.b64decode(data['content']).decode('utf-8', errors='ignore')
                return content
    except:
        pass
    return None

def search_sensitive_in_repo(owner, repo):
    """Search for sensitive patterns in repository files."""
    sensitive_findings = []
    
    # Common sensitive files to check
    sensitive_files = [
        '.env', '.env.local', '.env.production', '.env.development',
        '.env.staging', '.env.example', '.env.test',
        'config.php', 'settings.py', 'application.properties',
        'docker-compose.yml', '.travis.yml', '.gitlab-ci.yml',
        'secrets.yml', 'credentials.json', 'tokens.txt',
        'config.json', 'config.ini', 'secrets.json'
    ]
    
    for file in sensitive_files:
        content = fetch_file_content(owner, repo, file)
        if content:
            # Check for sensitive patterns
            for pattern, description in SENSITIVE_PATTERNS:
                matches = re.findall(pattern, content, re.IGNORECASE)
                if matches:
                    for match in matches:
                        if len(str(match)) > 3:  # Avoid false positives
                            sensitive_findings.append({
                                'file': file,
                                'pattern': description,
                                'match': str(match)[:100],  # Truncate long matches
                                'type': 'sensitive_data'
                            })
    
    return sensitive_findings

def get_github_repo_info_with_sensitive(url):
    """Get detailed information about a GitHub repository including sensitive data."""
    details = get_repo_details(url)
    
    if details.get('type') == 'repository':
        owner = details['owner']
        repo = details['repo']
        
        # Fetch basic repo info
        api_url = f"https://api.github.com/repos/{owner}/{repo}"
        headers = {
            'Accept': 'application/vnd.github.v3+json',
            'User-Agent': 'Mozilla/5.0'
        }
        
        try:
            response = requests.get(api_url, headers=headers, timeout=10)
            if response.status_code == 200:
                data = response.json()
                details.update({
                    'description': data.get('description', ''),
                    'stars': data.get('stargazers_count', 0),
                    'forks': data.get('forks_count', 0),
                    'language': data.get('language', ''),
                    'created_at': data.get('created_at', ''),
                    'updated_at': data.get('updated_at', ''),
                    'license': data.get('license', {}).get('name', '') if data.get('license') else '',
                    'default_branch': data.get('default_branch', 'main'),
                })
                
                # Search for sensitive files
                print(f"      Scanning for sensitive data...")
                sensitive_findings = search_sensitive_in_repo(owner, repo)
                if sensitive_findings:
                    details['sensitive_findings'] = sensitive_findings
                    details['has_sensitive_data'] = True
                else:
                    details['has_sensitive_data'] = False
                    
        except Exception as e:
            details['api_error'] = str(e)
    
    return details

# --- Main Function ---

def search_all_with_subdomains(domain, num_results=None):
    """Main function to search subdomains and GitHub repos with sensitive data."""
    domain_clean = sanitize_domain(domain)
    
    print("\n" + "="*60)
    print(" COMPREHENSIVE SUBDOMAIN & SENSITIVE DATA SEARCH")
    print("="*60)
    print(f"Target Domain: {domain_clean}")
    print(f"Start Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)
    
    # Discover subdomains
    subdomains = discover_all_subdomains(domain_clean, num_results)
    
    if not subdomains:
        print("\n❌ No subdomains found. Searching main domain only.")
        subdomains = [domain_clean]
    
    # Results container
    all_results = {
        'domain': domain_clean,
        'search_time': datetime.now().isoformat(),
        'total_subdomains': len(subdomains),
        'subdomains': [],
        'total_repositories': 0,
        'total_sensitive_findings': 0,
        'repositories_with_sensitive': 0
    }
    
    # Search each subdomain
    for idx, subdomain in enumerate(subdomains, 1):
        print(f"\n{'='*60}")
        print(f"📌 [{idx}/{len(subdomains)}] Searching: {subdomain}")
        print(f"{'='*60}")
        
        subdomain_data = {
            'subdomain': subdomain,
            'repositories': [],
            'sensitive_repositories': 0,
            'total_sensitive_findings': 0
        }
        
        # Search for GitHub repositories
        print(f"\n  Searching GitHub repositories...")
        repos = search_github_repos(subdomain, num_results)
        
        if repos:
            print(f"  Found {len(repos)} repositories")
            
            for repo_item in repos:
                print(f"\n    Processing: {repo_item['url']}")
                repo_details = get_github_repo_info_with_sensitive(repo_item['url'])
                
                repo_data = {
                    'url': repo_item['url'],
                    'title': repo_item.get('title'),
                    'snippet': repo_item.get('snippet'),
                    'details': repo_details
                }
                
                subdomain_data['repositories'].append(repo_data)
                
                # Count sensitive findings
                if repo_details.get('has_sensitive_data'):
                    subdomain_data['sensitive_repositories'] += 1
                    sensitive_count = len(repo_details.get('sensitive_findings', []))
                    subdomain_data['total_sensitive_findings'] += sensitive_count
                    all_results['total_sensitive_findings'] += sensitive_count
                    
                    print(f"       Found {sensitive_count} sensitive data items!")
                else:
                    print(f"       No sensitive data found")
                
                time.sleep(0.5)
        else:
            print(f"   No repositories found")
        
        all_results['subdomains'].append(subdomain_data)
        all_results['total_repositories'] += len(repos)
        all_results['repositories_with_sensitive'] += subdomain_data['sensitive_repositories']
        
        time.sleep(1)
    
    # Final summary
    print("\n" + "="*60)
    print("📊 FINAL SUMMARY")
    print("="*60)
    print(f"Total Subdomains: {all_results['total_subdomains']}")
    print(f"Total Repositories: {all_results['total_repositories']}")
    print(f"Repositories with Sensitive Data: {all_results['repositories_with_sensitive']}")
    print(f"Total Sensitive Findings: {all_results['total_sensitive_findings']}")
    print("="*60)
    
    return all_results

if __name__ == "__main__":
    if not SCRAPERAPI_KEY:
        raise SystemExit("ERROR: Set SCRAPER_API_KEY in your .env file or environment.")
    
    print("="*60)
    print("🔐 GITHUB SENSITIVE DATA DISCOVERY WITH SUBDOMAINS")
    print("="*60)
    
    domain = input("\nDomain (e.g. example.com): ").strip()
    n = input("Results per search (leave blank for all): ").strip()
    num_results = int(n) if n else None
    
    # Run comprehensive search
    results = search_all_with_subdomains(domain, num_results)
    
    # Print JSON output (not saved)
    print("\n" + "="*60)
    print("📄 JSON OUTPUT:")
    print("="*60)
    print(json.dumps(results, indent=2, ensure_ascii=False))
    
    # Optional: Ask if user wants to save
    save = input("\n💾 Save results to file? (y/n): ").strip().lower()
    if save == 'y':
        clean_domain = sanitize_domain(domain)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"subdomain_sensitive_{clean_domain}_{timestamp}.json"
        filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        print(f"✅ Saved to: {filename}")