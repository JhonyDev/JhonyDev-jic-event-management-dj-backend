# JIC - Event Management App - Project Context

## Project Overview
A Django-based event management application for organizing conferences, workshops, and other events. The system provides both administrative portal functionality for event organizers and public-facing pages for attendees.

## Architecture & Technology Stack
- **Framework**: Django (Python web framework)
- **Frontend**: Tabler UI framework for modern, responsive design
- **Database**: Django ORM (SQLite/PostgreSQL)
- **Authentication**: Django's built-in user authentication
- **Static Files**: Django static files handling
- **Templates**: Django template engine with Bootstrap/Tabler components

## Directory Structure
```
django-backend/
├── backend/                 # Django project settings
│   ├── settings.py         # Main settings configuration
│   └── urls.py             # Root URL configuration
├── src/                    # Django apps
│   ├── accounts/           # User authentication & profiles
│   ├── api/                # Core models & business logic
│   │   ├── models.py       # Event, Registration, Session, Speaker models
│   │   ├── forms.py        # Django forms
│   │   ├── admin.py        # Django admin configuration
│   │   └── utils.py        # Helper utilities
│   ├── portal/             # Admin portal for event organizers
│   │   ├── views.py        # Portal views
│   │   └── urls.py         # Portal URL patterns
│   └── website/            # Public-facing website
│       ├── views.py        # Website views
│       └── urls.py         # Website URL patterns
└── templates/              # Django templates
    ├── include/            # Shared templates (navigation, base)
    ├── portal/             # Admin portal templates
    └── website/            # Public website templates
```

## Core Models (src/api/models.py)
- **Event**: Main event model with title, description, dates, location, status
- **Registration**: Event registrations linking users to events
- **Session**: Event sessions/agenda items
- **Speaker**: Event speakers
- **Sponsor**: Event sponsors/partners
- **Agenda**: Day-by-day event schedules
- **VenueMap**: Venue maps and layouts
- **ExhibitionArea**: Exhibition spaces
- **Exhibitor**: Exhibition participants

## Key Features

### Public Website (src/website/)
- **Landing Page**: Overview with upcoming events
- **Event Browse**: List all published/cancelled events with filtering
- **Event Detail Pages**:
  - Main event overview
  - Detailed event information page (recently redesigned)
  - Event agenda/schedule
  - Speakers list
  - Venue maps
- **Self Registration**: Public event registration system

### Admin Portal (src/portal/)
- **Dashboard**: Event organizer overview
- **Event Management**: CRUD operations for events
- **Session Management**: Manage event sessions and agendas
- **Speaker Management**: Add/edit speakers
- **Registration Management**: View and manage attendee registrations
- **Publishing System**: Event publishing workflow

## Recent Major Updates

### Event Info Page Redesign (templates/website/event_info.html)
- **User Experience Focus**: Redesigned for "layman users" with simplified language
- **Visual Improvements**:
  - Hero banner with gradient background
  - Emoji-based section headers (📖, 📅, 🎯)
  - Step-by-step registration guide
  - Color-coded status indicators
- **Icon System**: All SVG icons updated with proper Tabler UI attributes
- **Avatar System**: Event avatars show initials when no image provided
- **Badge Consistency**: All badges use `text-white` class for readability

### Events Browse Enhancement (templates/website/events_browse.html)
- **Status Display**: Shows both published and cancelled events
- **Visual Indicators**: Color-coded status bars and badges
- **Registration Status**: Clear indication of registration availability

## UI Framework & Styling
- **Tabler UI**: Modern admin dashboard framework
- **Bootstrap Base**: Responsive grid system and components
- **Custom Styling**: Event-specific color schemes and layouts
- **Icon System**: Tabler icons with proper SVG attributes
- **Avatar Generation**: UI Avatars API for automatic initial generation

## Database Status & Migrations
- Uses Django's migration system
- Models support event lifecycle management
- User authentication integrated with Django's built-in system

## URL Patterns
```python
# Main URLs
/                           # Landing page
/browse/                    # Browse events
/events/<id>/               # Event detail
/events/<id>/info/          # Event information (redesigned)
/events/<id>/agenda/        # Event agenda
/events/<id>/speakers/      # Event speakers
/events/<id>/maps/          # Event maps

# Portal URLs (admin)
/portal/                    # Portal dashboard
/portal/events/             # Event management
/portal/sessions/           # Session management
/portal/speakers/           # Speaker management
```

## Development Context
- **Environment**: Django development server
- **Virtual Environment**: `env/bin/activate`
- **Run Command**: `python manage.py runserver`
- **Git Status**: Working on main branch with multiple modified files

## Key Design Principles
1. **User-Centric**: Interfaces designed for non-technical users
2. **Responsive**: Mobile-first design approach
3. **Accessible**: Clear visual hierarchy and readable text
4. **Consistent**: Uniform styling across all components
5. **Professional**: Clean, modern aesthetic suitable for business events

## Technical Debt & Improvements
- SVG icons recently standardized across all templates
- Badge styling made consistent with `text-white` class
- Event avatar system improved with proper fallbacks
- Alert text colors fixed for better accessibility

## Future Considerations
- Event capacity management and waitlists
- Advanced filtering and search capabilities
- Email notification system integration
- Payment processing for paid events
- Multi-language support
- Advanced analytics and reporting

## Development Notes
- Uses Django's template inheritance extensively
- Context processors provide global template variables
- Form handling follows Django best practices
- Admin interface customized for event management workflows
- Static file handling configured for production deployment

This project demonstrates a full-featured Django application with both public and administrative interfaces, modern UI components, and comprehensive event management capabilities.