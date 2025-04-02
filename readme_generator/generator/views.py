import markdown
import json
import logging
from django.shortcuts import render, redirect
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib import messages
from .forms import RepoForm
from .utils import fetch_repo_details

# Configure logging
logger = logging.getLogger(__name__)

def home(request):
    if request.method == "POST":
        form = RepoForm(request.POST)
        if form.is_valid():
            repo_url = form.cleaned_data["repo_url"]
            
            # Log the request
            logger.info(f"README generation requested for: {repo_url}")
            
            readme_content = fetch_repo_details(repo_url)

            if not readme_content:
                messages.error(request, "Failed to generate README. Please check the repository URL and try again.")
                return render(request, "generator/home.html", {
                    "form": form,
                    "error": "Invalid Repository URL or unable to access repository data"
                })
                
            if isinstance(readme_content, str) and readme_content.startswith("GitHub API rate limit exceeded"):
                messages.warning(request, readme_content)
                return render(request, "generator/home.html", {
                    "form": form,
                    "error": readme_content
                })

            # Use GitHub-flavored markdown with extensions
            readme_html = markdown.markdown(
                readme_content,
                extensions=[
                    'markdown.extensions.fenced_code',
                    'markdown.extensions.tables',
                    'markdown.extensions.codehilite',
                    'markdown.extensions.toc',
                    'markdown.extensions.sane_lists',
                    'markdown.extensions.nl2br'
                ]
            )
            
            # Store README content in session for download
            request.session['readme_content'] = readme_content
            request.session['repo_url'] = repo_url
            
            messages.success(request, "README generated successfully!")
            return render(request, "generator/home.html", {
                "form": form,
                "readme_html": readme_html,
                "readme_content": readme_content,
                "repo_url": repo_url
            })
            
        else:
            # Form validation failed
            messages.error(request, "Invalid form submission. Please check the URL format.")

    form = RepoForm()
    return render(request, "generator/home.html", {"form": form})


@csrf_exempt
def render_markdown(request):
    """Renders markdown content and returns HTML."""
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            content = data.get('content', '')
            
            # Use GitHub-flavored markdown with extensions
            html = markdown.markdown(
                content,
                extensions=[
                    'markdown.extensions.fenced_code',
                    'markdown.extensions.tables',
                    'markdown.extensions.codehilite',
                    'markdown.extensions.toc',
                    'markdown.extensions.sane_lists',
                    'markdown.extensions.nl2br'
                ]
            )
            
            return JsonResponse({'html': html})
        except json.JSONDecodeError:
            logger.error("Invalid JSON in render_markdown request")
            return JsonResponse({'error': 'Invalid JSON format'}, status=400)
        except Exception as e:
            logger.exception(f"Error in render_markdown: {str(e)}")
            return JsonResponse({'error': str(e)}, status=500)
    
    return JsonResponse({'error': 'Invalid request method'}, status=405)


def download_readme(request):
    """Handles README.md file downloads."""
    repo_url = request.GET.get("repo_url")
    
    # First check if README content is stored in session
    readme_content = request.session.get('readme_content')
    
    # If no content in session or repo_url doesn't match, generate new content
    if not readme_content or (repo_url and repo_url != request.session.get('repo_url')):
        if not repo_url:
            messages.error(request, "Missing repository URL")
            return redirect('home')

        try:
            readme_content = fetch_repo_details(repo_url)

            if not readme_content:
                messages.error(request, "Failed to generate README content")
                return redirect('home')
                
            if isinstance(readme_content, str) and readme_content.startswith("GitHub API rate limit exceeded"):
                messages.warning(request, readme_content)
                return redirect('home')
                
        except Exception as e:
            logger.exception(f"Error downloading README: {str(e)}")
            messages.error(request, f"An error occurred: {str(e)}")
            return redirect('home')
    
    # If we have content, return it as a downloadable file
    if readme_content:
        filename = "README.md"
        if repo_url:
            # Extract repo name from URL for the filename
            parts = repo_url.rstrip('/').split('/')
            if len(parts) >= 2:
                filename = f"README-{parts[-1]}.md"
                
        response = HttpResponse(readme_content, content_type="text/markdown")
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response
    
    # If we get here, something went wrong
    messages.error(request, "Unable to generate README content")
    return redirect('home')
