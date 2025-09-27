from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.authtoken.models import Token
from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.hashers import check_password
from django.utils import timezone
from django.db import models
from .serializers import UserSerializer, UserProfileSerializer, AnnouncementSerializer, AppContentSerializer, FAQSerializer, ContactInfoSerializer
from .models import Announcement, Registration, AppContent, FAQ, ContactInfo

User = get_user_model()


@api_view(['POST'])
@permission_classes([AllowAny])
def login(request):
    # Accept both username and email for flexibility
    username = request.data.get('username')
    email = request.data.get('email')
    password = request.data.get('password')

    # Use email if provided, otherwise use username (which could be email)
    login_field = email or username

    if not login_field or not password:
        return Response(
            {'error': 'Please provide email and password'},
            status=status.HTTP_400_BAD_REQUEST
        )

    # For CustomUser model, authenticate using email as username
    user = authenticate(username=login_field, password=password)

    if not user:
        return Response(
            {'error': 'Invalid credentials'},
            status=status.HTTP_401_UNAUTHORIZED
        )

    token, created = Token.objects.get_or_create(user=user)
    serializer = UserSerializer(user)

    return Response({
        'token': token.key,
        'user': serializer.data
    })


@api_view(['POST'])
@permission_classes([AllowAny])
def register(request):
    email = request.data.get('email')
    password = request.data.get('password')
    first_name = request.data.get('first_name', '')
    last_name = request.data.get('last_name', '')
    # For backward compatibility, also accept username but use email as primary
    username = request.data.get('username', email)

    if not email or not password:
        return Response(
            {'error': 'Please provide email and password'},
            status=status.HTTP_400_BAD_REQUEST
        )

    # Check if user with this email already exists
    if User.objects.filter(email=email).exists():
        return Response(
            {'error': 'Email already exists'},
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        # Create user - CustomUser uses email as the username field
        user = User.objects.create_user(
            username=email,  # Use email as username for CustomUser
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name
        )

        token, created = Token.objects.get_or_create(user=user)
        serializer = UserSerializer(user)

        return Response({
            'token': token.key,
            'user': serializer.data
        }, status=status.HTTP_201_CREATED)

    except Exception as e:
        return Response(
            {'error': f'Registration failed: {str(e)}'},
            status=status.HTTP_400_BAD_REQUEST
        )


@api_view(['POST'])
def logout(request):
    try:
        request.user.auth_token.delete()
        return Response({'message': 'Successfully logged out'})
    except:
        return Response({'error': 'Error logging out'}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET', 'PATCH'])
@permission_classes([IsAuthenticated])
def profile(request):
    """
    GET: Retrieve user profile
    PATCH: Update user profile (including profile image)
    """
    user = request.user

    if request.method == 'GET':
        serializer = UserProfileSerializer(user, context={'request': request})
        return Response(serializer.data)

    elif request.method == 'PATCH':
        # Handle profile image upload
        if 'profile_image' in request.FILES:
            user.profile_image = request.FILES['profile_image']
            user.save()
            serializer = UserProfileSerializer(user, context={'request': request})
            return Response(serializer.data)

        # Handle regular profile updates
        serializer = UserProfileSerializer(user, data=request.data, partial=True, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def change_password(request):
    """
    Change user password
    """
    user = request.user
    current_password = request.data.get('current_password')
    new_password = request.data.get('new_password')

    if not current_password or not new_password:
        return Response(
            {'error': 'Both current and new passwords are required'},
            status=status.HTTP_400_BAD_REQUEST
        )

    # Verify current password
    if not check_password(current_password, user.password):
        return Response(
            {'error': 'Current password is incorrect'},
            status=status.HTTP_400_BAD_REQUEST
        )

    # Validate new password length
    if len(new_password) < 6:
        return Response(
            {'error': 'New password must be at least 6 characters long'},
            status=status.HTTP_400_BAD_REQUEST
        )

    # Set new password
    user.set_password(new_password)
    user.save()

    return Response({'message': 'Password changed successfully'})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def announcements(request):
    """
    Get announcements for events the user is registered for
    """
    user = request.user

    # Get events the user is registered for
    registered_events = Registration.objects.filter(
        user=user,
        status='confirmed'
    ).values_list('event', flat=True)

    # Get announcements for these events
    announcements = Announcement.objects.filter(
        event__in=registered_events,
        is_active=True,
        publish_date__lte=timezone.now()
    ).filter(
        models.Q(expire_date__isnull=True) | models.Q(expire_date__gt=timezone.now())
    ).order_by('-priority', '-created_at')

    serializer = AnnouncementSerializer(announcements, many=True)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([AllowAny])
def app_content(request, content_type):
    """
    Get app content by type (privacy_policy, help_support, about)
    """
    try:
        content = AppContent.objects.get(
            content_type=content_type,
            is_active=True
        )
        serializer = AppContentSerializer(content)
        return Response(serializer.data)
    except AppContent.DoesNotExist:
        return Response(
            {'error': 'Content not found'},
            status=status.HTTP_404_NOT_FOUND
        )


@api_view(['GET'])
@permission_classes([AllowAny])
def faqs(request):
    """
    Get all active FAQs grouped by category
    """
    faqs = FAQ.objects.filter(is_active=True).order_by('category', 'order')
    serializer = FAQSerializer(faqs, many=True)

    # Group FAQs by category
    grouped_faqs = {}
    for faq_data in serializer.data:
        category = faq_data['category']
        if category not in grouped_faqs:
            grouped_faqs[category] = []
        grouped_faqs[category].append(faq_data)

    return Response(grouped_faqs)


@api_view(['GET'])
@permission_classes([AllowAny])
def contact_info(request):
    """
    Get all active contact information
    """
    contacts = ContactInfo.objects.filter(is_active=True).order_by('contact_type', 'order')
    serializer = ContactInfoSerializer(contacts, many=True)
    return Response(serializer.data)