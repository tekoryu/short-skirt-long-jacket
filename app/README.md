# Short Skirt Long Jacket

A Django project with a modern main page featuring a top bar and user menu.

## Features

- **Top Bar**: Displays project name "Short Skirt Long Jacket" on the left
- **User Menu**: Interactive dropdown menu on the right with:
  - Settings option
  - Admin panel access
- **Responsive Design**: Mobile-friendly layout
- **Modern UI**: Clean, professional styling with gradients and animations

## Running the Project

```bash
# Start the development server
docker compose up

# Or run specific commands
docker compose run --rm app python manage.py migrate
docker compose run --rm app python manage.py collectstatic
docker compose run --rm app python manage.py runserver 0.0.0.0:8000
```

## URLs

- `/` - Main page
- `/settings/` - Settings page
- `/admin/` - Django admin
- `/health/` - Health check endpoint

## Static Files

The project includes custom CSS and JavaScript for the main page:
- `apps/core/static/core/css/main.css` - Main stylesheet
- `apps/core/static/core/js/main.js` - Interactive functionality

