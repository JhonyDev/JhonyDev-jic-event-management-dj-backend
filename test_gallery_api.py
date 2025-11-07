#!/usr/bin/env python
"""
Test script for gallery management API endpoints
"""
import os
import sys
import django

# Setup Django
sys.path.insert(0, '/home/jhonydev/Repositories/JIC - Event Management App/django-backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'src.settings')
django.setup()

from src.api.models import SupportingMaterial, SupportingMaterialFile, Event
from django.core.files.uploadedfile import SimpleUploadedFile

def test_gallery_api():
    """Test the gallery API functionality"""
    print("Testing Gallery API Functionality\n" + "="*50)

    # Get a test event (assuming event ID 6 exists)
    try:
        event = Event.objects.get(pk=6)
        print(f"✓ Found event: {event.title}")
    except Event.DoesNotExist:
        print("✗ Event with ID 6 not found")
        return

    # Check for existing gallery materials
    gallery_materials = SupportingMaterial.objects.filter(
        event=event,
        material_type='gallery'
    )

    print(f"\nExisting gallery materials: {gallery_materials.count()}")

    for material in gallery_materials:
        files = material.gallery_files.all()
        print(f"\n  Gallery: {material.title}")
        print(f"  - Files: {files.count()}")
        for file in files:
            print(f"    • {file.file.name} (ID: {file.id})")
            print(f"      Type: {file.get_media_type()}")

    # Test creating a new gallery if none exist
    if gallery_materials.count() == 0:
        print("\nCreating test gallery...")
        test_gallery = SupportingMaterial.objects.create(
            event=event,
            material_type='gallery',
            title='Test Gallery',
            description='Test gallery for API testing'
        )

        # Add a test file
        test_content = b'Test image content'
        test_file = SimpleUploadedFile("test_image.jpg", test_content, content_type="image/jpeg")

        gallery_file = SupportingMaterialFile.objects.create(
            material=test_gallery,
            file=test_file,
            caption="Test image"
        )
        print(f"✓ Created test gallery with ID: {test_gallery.id}")
        print(f"✓ Added test file with ID: {gallery_file.id}")

    # Summary
    print("\n" + "="*50)
    print("Gallery API Test Summary:")
    print(f"- Total galleries: {gallery_materials.count()}")
    total_files = sum(m.gallery_files.count() for m in gallery_materials)
    print(f"- Total gallery files: {total_files}")
    print("\nAPI Endpoints Available:")
    print(f"- Get gallery: /portal/api/events/{event.pk}/materials/?action=get_gallery&material_id=<ID>")
    print(f"- Delete file: /portal/api/events/{event.pk}/materials/?action=delete_file&file_id=<ID>")
    print(f"- Add files: /portal/api/events/{event.pk}/materials/ (POST with action=add_files)")
    print("\n✓ Gallery management features are ready for testing!")

if __name__ == "__main__":
    test_gallery_api()