"""
Test script for Medicine Reminder App
Tests database functionality and basic operations
"""

from database import DatabaseManager
from notification_manager import NotificationManager
from datetime import date, timedelta
import os

def test_database():
    """Test database operations"""
    print("Testing Database Operations...")
    
    # Initialize database
    db = DatabaseManager("test_medicine_reminders.db")
    
    # Test adding users
    print("1. Testing user management...")
    users = db.get_users()
    print(f"   Initial users: {len(users)}")
    
    # Add a test user
    test_user_id = db.add_user("Test User")
    print(f"   Added test user with ID: {test_user_id}")
    
    # Test adding reminders
    print("2. Testing reminder management...")
    today = date.today()
    tomorrow = today + timedelta(days=1)
    
    # Add a test reminder
    reminder_id = db.add_reminder(
        user_id=test_user_id,
        medicine_name="Test Medicine",
        dose="1x",
        time_slot="Morning",
        specific_time="08:00",
        start_date=today,
        end_date=tomorrow,
        take_with_food=True
    )
    print(f"   Added test reminder with ID: {reminder_id}")
    
    # Test getting reminders
    print("3. Testing reminder retrieval...")
    reminders = db.get_reminders_for_date(today)
    print(f"   Found {len(reminders)} reminders for today")
    
    for reminder in reminders:
        print(f"   - {reminder['medicine_name']} at {reminder['specific_time']}")
    
    # Test marking as taken
    print("4. Testing mark as taken...")
    success = db.mark_reminder_taken(reminder_id)
    print(f"   Mark as taken: {'Success' if success else 'Failed'}")
    
    # Test updating reminder
    print("5. Testing reminder update...")
    success = db.update_reminder(reminder_id, medicine_name="Updated Medicine")
    print(f"   Update reminder: {'Success' if success else 'Failed'}")
    
    # Test deleting reminder
    print("6. Testing reminder deletion...")
    success = db.delete_reminder(reminder_id)
    print(f"   Delete reminder: {'Success' if success else 'Failed'}")
    
    # Clean up test database
    os.remove("test_medicine_reminders.db")
    print("7. Cleaned up test database")
    
    print("✅ All database tests passed!")

def test_notifications():
    """Test notification system"""
    print("\nTesting Notification System...")
    
    try:
        from plyer import notification
        
        # Test basic notification
        print("1. Testing basic notification...")
        notification.notify(
            title="Test Notification",
            message="This is a test notification from Medicine Reminder App",
            app_name="Medicine Reminder",
            timeout=3
        )
        print("   ✅ Test notification sent successfully")
        
        # Test notification manager
        print("2. Testing notification manager...")
        db = DatabaseManager("test_notifications.db")
        notif_manager = NotificationManager(db)
        
        # Send test notification
        notif_manager.send_test_notification()
        print("   ✅ Notification manager test passed")
        
        # Clean up
        os.remove("test_notifications.db")
        print("3. Cleaned up test database")
        
    except Exception as e:
        print(f"   ❌ Notification test failed: {e}")

def main():
    """Run all tests"""
    print("🧪 Medicine Reminder App - Test Suite")
    print("=" * 50)
    
    try:
        test_database()
        test_notifications()
        print("\n🎉 All tests completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Test suite failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
