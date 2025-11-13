"""
Example Django views for HTMX endpoints
These demonstrate how to handle HTMX requests in your Django application
"""

from django.shortcuts import render
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_http_methods
import json


def index(request):
    """Main page view"""
    return render(request, 'index.html')


@require_http_methods(["GET"])
def get_stats(request):
    """
    HTMX endpoint for stats cards
    Returns HTML fragment with current stats
    """
    # In a real app, fetch these from your database
    stats = {
        'users': 42,
        'tasks': 128,
        'projects': 15,
        'completion': 98
    }
    
    html = f"""
    <div class="stats-card" x-data="{{{{ count: 0 }}}}" x-init="setInterval(() => count = Math.min(count + 1, {stats['users']}), 50)">
        <div class="stats-icon">
            <i class="fas fa-users"></i>
        </div>
        <div class="stats-content">
            <h3 x-text="count">{stats['users']}</h3>
            <p>Active Users</p>
        </div>
    </div>
    
    <div class="stats-card" x-data="{{{{ count: 0 }}}}" x-init="setInterval(() => count = Math.min(count + 3, {stats['tasks']}), 30)">
        <div class="stats-icon">
            <i class="fas fa-tasks"></i>
        </div>
        <div class="stats-content">
            <h3 x-text="count">{stats['tasks']}</h3>
            <p>Tasks Completed</p>
        </div>
    </div>
    
    <div class="stats-card" x-data="{{{{ count: 0 }}}}" x-init="setInterval(() => count = Math.min(count + 1, {stats['projects']}), 80)">
        <div class="stats-icon">
            <i class="fas fa-project-diagram"></i>
        </div>
        <div class="stats-content">
            <h3 x-text="count">{stats['projects']}</h3>
            <p>Active Projects</p>
        </div>
    </div>
    
    <div class="stats-card" x-data="{{{{ count: 0 }}}}" x-init="setInterval(() => count = Math.min(count + 2, {stats['completion']}), 20)">
        <div class="stats-icon">
            <i class="fas fa-chart-line"></i>
        </div>
        <div class="stats-content">
            <h3 x-text="count + '%'">{stats['completion']}%</h3>
            <p>Completion Rate</p>
        </div>
    </div>
    """
    
    return HttpResponse(html)


@require_http_methods(["GET"])
def get_activity(request):
    """
    HTMX endpoint for activity feed
    Returns HTML fragment with recent activities
    """
    # In a real app, fetch these from your database
    activities = [
        {
            'icon': 'fa-check-circle',
            'title': 'Task completed',
            'description': 'John completed "Update documentation"',
            'time': '2 minutes ago',
            'color': '#10b981'
        },
        {
            'icon': 'fa-user-plus',
            'title': 'New team member',
            'description': 'Sarah joined the project',
            'time': '15 minutes ago',
            'color': '#3b82f6'
        },
        {
            'icon': 'fa-file-alt',
            'title': 'Report generated',
            'description': 'Monthly report is ready',
            'time': '1 hour ago',
            'color': '#f59e0b'
        },
        {
            'icon': 'fa-comment',
            'title': 'New comment',
            'description': 'Mike commented on "Design review"',
            'time': '2 hours ago',
            'color': '#8b5cf6'
        },
    ]
    
    html = ""
    for activity in activities:
        html += f"""
        <div class="activity-item">
            <div class="activity-icon" style="background: {activity['color']};">
                <i class="fas {activity['icon']}"></i>
            </div>
            <div class="activity-content">
                <strong>{activity['title']}</strong>
                <p style="color: var(--text-secondary); margin: 0;">{activity['description']}</p>
                <small style="color: var(--text-secondary);">{activity['time']}</small>
            </div>
        </div>
        """
    
    return HttpResponse(html)


@require_http_methods(["GET"])
def new_project_modal(request):
    """
    HTMX endpoint for new project modal
    Returns HTML fragment with modal content
    """
    html = """
    <div class="modal-overlay" x-data="{ show: true }" x-show="show" @click.self="show = false; setTimeout(() => document.getElementById('modal-container').innerHTML = '', 300)">
        <div class="modal-content" 
             x-show="show"
             x-transition:enter="transition ease-out duration-300"
             x-transition:enter-start="opacity-0 transform scale-90"
             x-transition:enter-end="opacity-100 transform scale-100">
            <div class="modal-header">
                <h3>Create New Project</h3>
                <button @click="show = false; setTimeout(() => document.getElementById('modal-container').innerHTML = '', 300)" class="modal-close">
                    <i class="fas fa-times"></i>
                </button>
            </div>
            <div class="modal-body">
                <form hx-post="/projects/create/" hx-swap="none">
                    <div class="form-group">
                        <label>Project Name</label>
                        <input type="text" name="name" class="form-control" required>
                    </div>
                    <div class="form-group">
                        <label>Description</label>
                        <textarea name="description" class="form-control" rows="4"></textarea>
                    </div>
                    <div class="modal-footer">
                        <button type="button" @click="show = false; setTimeout(() => document.getElementById('modal-container').innerHTML = '', 300)" class="btn btn-secondary">Cancel</button>
                        <button type="submit" class="btn btn-primary">Create Project</button>
                    </div>
                </form>
            </div>
        </div>
    </div>
    
    <style>
        .modal-overlay {
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(0, 0, 0, 0.5);
            display: flex;
            align-items: center;
            justify-content: center;
            z-index: 9999;
        }
        
        .modal-content {
            background: var(--card-bg);
            border-radius: 16px;
            max-width: 500px;
            width: 90%;
            box-shadow: var(--shadow-lg);
        }
        
        .modal-header {
            padding: 1.5rem;
            border-bottom: 1px solid var(--border-color);
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        
        .modal-header h3 {
            margin: 0;
            color: var(--text-primary);
        }
        
        .modal-close {
            background: none;
            border: none;
            font-size: 1.5rem;
            color: var(--text-secondary);
            cursor: pointer;
            padding: 0;
            width: 32px;
            height: 32px;
            display: flex;
            align-items: center;
            justify-content: center;
            border-radius: 50%;
            transition: all 0.2s ease;
        }
        
        .modal-close:hover {
            background: var(--border-color);
            color: var(--text-primary);
        }
        
        .modal-body {
            padding: 1.5rem;
        }
        
        .form-group {
            margin-bottom: 1.5rem;
        }
        
        .form-group label {
            display: block;
            margin-bottom: 0.5rem;
            color: var(--text-primary);
            font-weight: 500;
        }
        
        .form-control {
            width: 100%;
            padding: 0.75rem;
            border: 1px solid var(--border-color);
            border-radius: 8px;
            background: var(--bg-color);
            color: var(--text-primary);
            font-size: 1rem;
            transition: all 0.2s ease;
        }
        
        .form-control:focus {
            outline: none;
            border-color: var(--primary-color);
            box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
        }
        
        .modal-footer {
            display: flex;
            gap: 1rem;
            justify-content: flex-end;
            margin-top: 2rem;
        }
        
        .btn {
            padding: 0.75rem 1.5rem;
            border-radius: 8px;
            border: none;
            cursor: pointer;
            font-size: 1rem;
            font-weight: 500;
            transition: all 0.2s ease;
        }
        
        .btn-primary {
            background: linear-gradient(135deg, var(--primary-gradient-start), var(--primary-gradient-end));
            color: white;
        }
        
        .btn-primary:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
        }
        
        .btn-secondary {
            background: var(--border-color);
            color: var(--text-primary);
        }
        
        .btn-secondary:hover {
            background: var(--text-secondary);
            color: white;
        }
    </style>
    """
    
    return HttpResponse(html)


# URL patterns example for urls.py:
"""
from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('api/stats/', views.get_stats, name='get_stats'),
    path('api/activity/', views.get_activity, name='get_activity'),
    path('projects/new/', views.new_project_modal, name='new_project_modal'),
    # Add more HTMX endpoints as needed
]
"""
