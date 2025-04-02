import requests
import google.generativeai as genai
import os

# Configure Google Gemini API
api_key = os.environ.get("GEMINI_API_KEY")
if not api_key:
    raise ValueError("GEMINI_API_KEY environment variable not set")
    
genai.configure(api_key=api_key)

def fetch_repo_details(repo_url):
    """Fetches repository details using GitHub API and analyzes the tech stack."""
    try:
        parts = repo_url.rstrip('/').split('/')
        owner, repo = parts[-2], parts[-1]
    except IndexError:
        return None

    # GitHub API URLs
    repo_api_url = f"https://api.github.com/repos/{owner}/{repo}"
    contents_api_url = f"https://api.github.com/repos/{owner}/{repo}/contents"
    languages_api_url = f"https://api.github.com/repos/{owner}/{repo}/languages"

    # Fetch repo metadata
    repo_data = requests.get(repo_api_url).json()
    contents_data = requests.get(contents_api_url).json()
    languages_data = requests.get(languages_api_url).json()

    if "message" in repo_data:  # Check if API limit exceeded or repo doesn't exist
        return None

    # Extract repository details
    repo_info = {
        "name": repo_data.get("name", "Unknown"),
        "description": repo_data.get("description", "No description provided."),
        "owner": repo_data["owner"]["login"],
        "stars": repo_data["stargazers_count"],
        "forks": repo_data["forks_count"],
        "issues": repo_data["open_issues_count"],
        "language": repo_data["language"],
        "license": repo_data["license"]["name"] if repo_data["license"] else "Not specified",
        "languages": languages_data,
        # Get file names
        "files": [file["name"] for file in contents_data if "name" in file]
    }

    # Fetch code samples from key files
    code_samples = fetch_code_samples(owner, repo, contents_data)
    
    # Detect Technologies
    tech_stack = detect_technologies(repo_info["files"], languages_data)

    # Generate AI-enhanced README using Google Gemini
    readme_content = generate_readme(repo_info, tech_stack, code_samples)

    return readme_content


def fetch_code_samples(owner, repo, contents_data, max_files=5):
    """Fetches code samples from key files in the repository."""
    code_samples = []

    # Priority file extensions to look for
    priority_extensions = ['.js', '.py', '.html',
                           '.css', '.tsx', '.jsx', '.java', '.go', '.php']

    # First pass: look for priority files
    for file_data in contents_data:
        if file_data["type"] != "file":
            continue

        file_name = file_data["name"]
        if any(file_name.endswith(ext) for ext in priority_extensions) and len(code_samples) < max_files:
            try:
                file_content = requests.get(file_data["download_url"]).text
                # Limit file content to first 50 lines to avoid large files
                file_content = "\n".join(file_content.split("\n")[:50])
                code_samples.append({
                    "name": file_name,
                    "content": file_content,
                    "language": file_name.split(".")[-1]
                })
            except Exception as e:
                print(f"Error fetching {file_name}: {e}")

    return code_samples


def detect_technologies(files, languages_data):
    """Analyzes repo files and languages to determine the tech stack."""
    tech_stack = []

    # Add languages from GitHub API
    for language, bytes_of_code in languages_data.items():
        tech_stack.append(language)

    # File-based technology detection
    file_indicators = {
        "requirements.txt": "Python Packages",
        "package.json": "Node.js / npm",
        "webpack.config.js": "Webpack",
        "Dockerfile": "Docker",
        ".gitignore": "Git",
        "docker-compose.yml": "Docker Compose",
        "tsconfig.json": "TypeScript",
        "angular.json": "Angular",
        "next.config.js": "Next.js",
        "vite.config.js": "Vite",
        ".eslintrc": "ESLint",
        "tailwind.config.js": "Tailwind CSS"
    }

    for file in files:
        for key, value in file_indicators.items():
            if key in file:
                tech_stack.append(value)

    return list(set(tech_stack))  # Remove duplicates


def generate_readme(repo_info, tech_stack, code_samples):
    """Generates a professional README using Google Gemini API."""

    # Create code samples section
    code_samples_text = ""
    if code_samples:
        code_samples_text = "Here are some code samples from the repository:\n\n"
        for sample in code_samples:
            code_samples_text += f"**{sample['name']}**:\n```{sample['language']}\n{sample['content']}\n```\n\n"
    
    # Analyze code samples for API calls
    api_calls = detect_api_calls(code_samples)
    api_section = ""
    if api_calls:
        api_section = "## API Integration\n\nThis project integrates with the following APIs:\n\n"
        for api in api_calls:
            api_section += f"- **{api['name']}**: {api['description']}\n"

    prompt = f"""
    Generate a well-structured README.md for a GitHub project with the following details:
    
    - Project Name: {repo_info["name"]}
    - Description: {repo_info["description"]}
    - Owner: {repo_info["owner"]}
    - Stars: {repo_info["stars"]}
    - Forks: {repo_info["forks"]}
    - Open Issues: {repo_info["issues"]}
    - Main Language: {repo_info["language"]}
    - All Languages: {', '.join(repo_info["languages"].keys())}
    - License: {repo_info["license"]}
    - Detected Technologies: {', '.join(tech_stack)}
    
    {code_samples_text}
    
    **README.md Sections:**
    1. **Introduction** - Overview of the project
    2. **Features** - List of key features based on the code samples and technologies
    3. **API Documentation** - Explain any APIs being used in the repository, their endpoints, and how they're integrated
    4. **Tech Stack** - Explanation of detected technologies
    5. **Installation** - Setup instructions
    6. **Usage** - How to run the project
    7. **Contributing** - Contribution guidelines
    8. **License** - License details
    9. **Contact** - Owner's GitHub profile link
    
    Format the README in Markdown and include relevant code snippets from the provided samples. Make the README comprehensive but concise. If you detect any API usage in the code samples, please document them in the API Documentation section.
    
    Only generate the README.md content.
    """

    model = genai.GenerativeModel("gemini-1.5-pro")
    response = model.generate_content(prompt)

    return response.text  # Return the generated README content


def detect_api_calls(code_samples):
    """Analyzes code samples to detect API calls."""
    api_patterns = {
        "fetch\\(": {"name": "Fetch API", "description": "JavaScript interface for making HTTP requests."},
        "axios": {"name": "Axios", "description": "Promise-based HTTP client for the browser and Node.js."},
        "api.github.com": {"name": "GitHub API", "description": "RESTful API for GitHub data and actions."},
        "api.openai.com": {"name": "OpenAI API", "description": "AI services including GPT models."},
        "firebase": {"name": "Firebase API", "description": "Google's mobile and web application development platform."},
        "googleapis": {"name": "Google APIs", "description": "Various Google service APIs."},
        "stripe": {"name": "Stripe API", "description": "Payment processing platform."},
        "twilio": {"name": "Twilio API", "description": "Communication APIs for SMS, voice, and video."},
        "auth0": {"name": "Auth0 API", "description": "Authentication and authorization platform."},
        "requests.get\\(": {"name": "HTTP Requests", "description": "Making HTTP requests to external services."},
        "http.get\\(": {"name": "HTTP Client", "description": "Making HTTP requests to external services."},
    }
    
    detected_apis = []
    
    import re
    for sample in code_samples:
        content = sample["content"]
        for pattern, api_info in api_patterns.items():
            if re.search(pattern, content):
                if api_info not in detected_apis:
                    detected_apis.append(api_info)
    
    return detected_apis
