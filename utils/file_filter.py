import os


class FileFilter:
    REVIEWABLE_EXTENSIONS = {
        # Backend
        '.py', '.java', '.rb', '.go', '.php', '.rs', '.kt', '.kts', '.scala',

        # Frontend/JavaScript
        '.js', '.jsx', '.ts', '.tsx', '.mjs', '.cjs',
        '.vue', '.svelte',

        # Mobile Native
        '.swift', '.m', '.mm', '.h',  # iOS
        '.kt', '.kts',  # Kotlin (already above)

        # Styles/Markup
        '.css', '.scss', '.sass', '.less',
        '.html', '.htm',

        # Config files (important ones)
        '.yaml', '.yml', '.json', '.toml',

        # Database
        '.sql',

        # Shell scripts
        '.sh', '.bash', '.zsh',

        # Other
        '.graphql', '.proto'
    }

    # Skip these directories even if file extension matches
    SKIP_DIRECTORIES = {
        'node_modules', 'vendor', 'dist', 'build', 'out',
        'Pods', '__pycache__', '.next', '.nuxt'
    }

    @classmethod
    def should_review(cls, filename: str) -> bool:
        """Returns True only if file should be reviewed"""

        # Skip if in excluded directory
        for skip_dir in cls.SKIP_DIRECTORIES:
            if f'/{skip_dir}/' in filename or filename.startswith(f'{skip_dir}/'):
                return False

        # Check extension
        _, ext = os.path.splitext(filename)
        return ext.lower() in cls.REVIEWABLE_EXTENSIONS