from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse
from .forms import HELPSubmissionForm
from django.contrib.auth.models import Group, User
from django.contrib.auth import authenticate, login, logout
from .models import HELPForm, Category, Priority
from django.utils.dateparse import parse_date
from datetime import datetime 
from django.contrib import messages
from .forms import CategoryForm, PriorityForm
# Create your views here.

def home(request):
    
    return render(request, 'index.html', )

def create_help_form(request):
    if request.method == 'POST':
        form = HELPSubmissionForm(request.POST, request.FILES)
        if form.is_valid():
            submission = form.save(commit=False)
            attachment = request.FILES.get('attachment')  # For single file upload
            submission.attachment = attachment
            submission.user = request.user
            submission.save()

            form.save_m2m()

            # # Construct the email message
            # subject = "New PTW Form Submission"
            # message = f"""
            # A user has submitted a PTW form.

            # Details of the form:
            # -------------------
            # User: {request.user.get_full_name()} ({request.user.email})
            # Location: {submission.location}
            # Date Started: {submission.start_datetime}
            # Description: {submission.work_description}

            # You can view the form details in the admin panel.
            # """

            # # Send the email to the signed-in user and supervisors
            # send_mail_to_user_and_supervisors(submission.user.email, subject, message)

            return redirect('helpdesk:home')

        else:
            print(form.errors)
    else:
        form = HELPSubmissionForm()

    context = {'form':form}
    return render(request, 'new_ticket.html', context)



def help_list(request):
    start_date = None
    end_date = None
    status = None

    # Get the date range parameters from the request
    if 'startDate' in request.GET and 'endDate' in request.GET:
        start_date = request.GET.get('startDate')
        end_date = request.GET.get('endDate')
    
    # Parse the dates if they exist
    start_date = parse_date(start_date) if start_date else None
    end_date = parse_date(end_date) if end_date else None
    status = request.GET.get('status', None)

    report_data = []

    help_submissions = HELPForm.objects.filter(user=request.user)

    if start_date or end_date:
        if start_date and end_date:
            help_submissions = help_submissions.filter(date_submitted__range=[start_date, end_date])
        elif start_date:
            help_submissions = help_submissions.filter(date_submitted__gte=start_date)
        elif end_date:
            help_submissions = help_submissions.filter(date_submitted__lte=end_date)

    if status:
        help_submissions = help_submissions.filter(status=status)

    # Process the filtered submissions
    for submission in help_submissions:
        report_data.append({
            'form_id': submission.id,
            'location': submission.location,
            'date_submitted': submission.date_submitted.strftime('%Y-%m-%d'),
            'complaint': submission.complaint,
            'issue': submission.issue,
            'subject': submission.subject,
            'status': submission.status,
            'complainant_full_name': submission.user.get_full_name()
        })

    return render(request, 'list_ticket.html', {
        'start_date': start_date,
        'end_date': end_date,
        'status': status,  # Add the selected status to the context
        'total_help': len(help_submissions) if report_data else 0,
        'report_data': report_data,
    })


# View to list all categories
def category_list(request):
    categories = Category.objects.all()
    return render(request, 'category_list.html', {'categories': categories})

# View to create a new category
def category_create(request):
    if request.method == 'POST':
        form = CategoryForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Category created successfully!')
            return redirect('category-list')
    else:
        form = CategoryForm()
    
    return render(request, 'category_form.html', {'form': form})

def category_edit(request, pk):
    category = get_object_or_404(Category, pk=pk)

    if request.method == 'POST':
        form = CategoryForm(request.POST, instance=category)
        if form.is_valid():
            form.save()
            return redirect('helpdesk:category-list')  # After editing, redirect to the category list
    else:
        form = CategoryForm(instance=category)

    return render(request, 'category_form.html', {'form': form})


# View to delete a category
def category_delete(request, pk):
    category = get_object_or_404(Category, pk=pk)
    if request.method == 'POST':
        category.delete()
        messages.success(request, 'Category deleted successfully!')
        return redirect('category-list')
    return render(request, 'category_confirm_delete.html', {'category': category})


# View to list all priority
def priority_list(request):
    priority = Priority.objects.all()
    return render(request, 'priority_list.html', {'priority': priority})

# View to create a new priority
def priority_create(request):
    if request.method == 'POST':
        form = PriorityForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Priority created successfully!')
            return redirect('priority-list')
    else:
        form = PriorityForm()
    
    return render(request, 'priority_form.html', {'form': form})

def priority_edit(request, pk):
    priority = get_object_or_404(Priority, pk=pk)

    if request.method == 'POST':
        form = PriorityForm(request.POST, instance=priority)
        if form.is_valid():
            form.save()
            return redirect('helpdesk:priority-list')  # After editing, redirect to the priority list
    else:
        form = PriorityForm(instance=priority)

    return render(request, 'priority_form.html', {'form': form})


# View to delete a priority
def priority_delete(request, pk):
    priority = get_object_or_404(Priority, pk=pk)
    if request.method == 'POST':
        priority.delete()
        messages.success(request, 'Priority deleted successfully!')
        return redirect('priority-list')
    return render(request, 'priority_confirm_delete.html', {'priority': priority})



def ticket_others(request):
    users = User.objects.all()
    if request.method == 'POST':
        form = HELPSubmissionForm(request.POST, request.FILES)
        if form.is_valid():
            submission = form.save(commit=False)
            attachment = request.FILES.get('attachment')  # For single file upload
            submission.attachment = attachment
            user_id = request.POST.get('user')  # Assuming 'user' is the name of the field in the form
            submission.user = User.objects.get(id=user_id)
            submission.save()

            form.save_m2m()

            # # Construct the email message
            # subject = "New PTW Form Submission"
            # message = f"""
            # A user has submitted a PTW form.

            # Details of the form:
            # -------------------
            # User: {request.user.get_full_name()} ({request.user.email})
            # Location: {submission.location}
            # Date Started: {submission.start_datetime}
            # Description: {submission.work_description}

            # You can view the form details in the admin panel.
            # """

            # # Send the email to the signed-in user and supervisors
            # send_mail_to_user_and_supervisors(submission.user.email, subject, message)

            return redirect('helpdesk:home')

        else:
            print(form.errors)
    else:
        form = HELPSubmissionForm()

    context = {'form':form, 'users': users}

    return render(request, 'ticket_others.html', context)


def it_help_list(request):
    start_date = None
    end_date = None
    status = None

    # Get the date range parameters from the request
    if 'startDate' in request.GET and 'endDate' in request.GET:
        start_date = request.GET.get('startDate')
        end_date = request.GET.get('endDate')
    
    # Parse the dates if they exist
    start_date = parse_date(start_date) if start_date else None
    end_date = parse_date(end_date) if end_date else None
    status = request.GET.get('status', None)

    report_data = []

    help_submissions = HELPForm.objects.all()

    if start_date or end_date:
        if start_date and end_date:
            help_submissions = help_submissions.filter(date_submitted__range=[start_date, end_date])
        elif start_date:
            help_submissions = help_submissions.filter(date_submitted__gte=start_date)
        elif end_date:
            help_submissions = help_submissions.filter(date_submitted__lte=end_date)

    if status:
        help_submissions = help_submissions.filter(status=status)

    # Process the filtered submissions
    for submission in help_submissions:
        report_data.append({
            'form_id': submission.id,
            'location': submission.location,
            'date_submitted': submission.date_submitted.strftime('%Y-%m-%d'),
            'complaint': submission.complaint,
            'issue': submission.issue,
            'subject': submission.subject,
            'status': submission.status,
        })

    return render(request, 'it_list_ticket.html', {
        'start_date': start_date,
        'end_date': end_date,
        'status': status,  # Add the selected status to the context
        'total_help': len(help_submissions) if report_data else 0,
        'report_data': report_data,
    })


def admin_dash(request):
    
    return render(request, 'admin_dash.html', )