from django import forms

class RepoForm(forms.Form):
    repo_url = forms.URLField(
        label="GitHub Repository URL",
        widget=forms.URLInput(
            attrs={
                'class': 'form-control form-control-lg',
                'placeholder': 'https://github.com/username/repository',
                'aria-label': 'GitHub Repository URL',
                'autocomplete': 'off',
                'spellcheck': 'false',
            }
        ),
        help_text="Enter the full URL of a GitHub repository"
    )

class ReadmeEditForm(forms.Form):
    content = forms.CharField(
        widget=forms.Textarea(
            attrs={
                'class': 'form-control',
                'rows': 25,
                'style': 'font-family: monospace;',
                'spellcheck': 'false',
            }
        ),
        required=True
    )
