# Medicine Reminder App

A comprehensive medicine reminder application built with Python and Tkinter for desktop, designed to be easily convertible to mobile using Kivy.

## Features

### Core Functionality
- ✅ **Create Medicine Reminders**: Add reminders with medicine name, dose, time, duration, and optional images
- ✅ **Database Storage**: SQLite database for persistent storage of reminders and users
- ✅ **User Management**: Support for multiple users (My Reminders / Family Reminders)
- ✅ **Cross-platform Notifications**: Desktop notifications using Plyer
- ✅ **Status Tracking**: Mark medicines as taken or missed
- ✅ **CRUD Operations**: Complete Create, Read, Update, Delete functionality

### UI Features
- 📅 **Date & Calendar Header**: Current date with horizontal calendar strip
- 🔄 **Toggle Tabs**: Switch between "My Reminders" and "Family Reminders"
- 📋 **Reminder Cards**: Visual cards showing medicine details with status indicators
- ➕ **Floating Action Button**: Quick access to add new reminders
- 🧭 **Bottom Navigation**: Easy navigation between different sections

### Visual Design
- 🎨 **Modern UI**: Clean, intuitive interface with green accent colors
- 📱 **Mobile-Ready**: Designed with mobile conversion in mind
- 🎯 **Status Indicators**: Color-coded strips (green=taken, red=overdue, orange=pending)
- 👥 **User Grouping**: Reminders organized by user with clear section headers

## Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/A2Zcoder404/medicine-reminder-app.git
   cd medicine-reminder-app
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the application**:
   ```bash
   python main.py
   ```

## Project Structure

```
medicine-reminder-app/
├── main.py                 # Main application with Tkinter UI
├── database.py             # SQLite database operations
├── notification_manager.py # Cross-platform notification system
├── models.py              # Data models and classes
├── requirements.txt       # Python dependencies
└── README.md             # This file
```

## Usage

### Adding a Reminder
1. Click the green "+" button (Floating Action Button)
2. Fill in the form:
   - Select time of day (Morning/Afternoon/Evening/Night)
   - Choose patient (Myself or family member)
   - Enter number of days
   - Select specific time
   - Enter medicine name
   - Select dose frequency
   - Optionally upload medicine image
3. Click "Save Reminder"

### Managing Reminders
- **View Reminders**: See all reminders for the current day
- **Mark as Taken**: Click "Mark as Taken" on any reminder card
- **Edit Reminder**: Click "Edit" to modify reminder details
- **Delete Reminder**: Click "Delete" to remove a reminder
- **Switch Views**: Use toggle tabs to switch between personal and family reminders

### Notifications
- The app automatically sends desktop notifications when it's time to take medicine
- Notifications are sent within 5 minutes of the scheduled time
- Test notifications can be sent from the Settings menu

## Database Schema

### Users Table
- `id`: Primary key
- `name`: User name
- `is_self`: Boolean indicating if this is the main user
- `created_at`: Timestamp

### Reminders Table
- `id`: Primary key
- `user_id`: Foreign key to users table
- `medicine_name`: Name of the medicine
- `dose`: Dosage information (e.g., "1x", "2x")
- `time_slot`: Time of day (Morning/Afternoon/Evening/Night)
- `specific_time`: Exact time (HH:MM format)
- `start_date`: Start date of medication
- `end_date`: End date of medication
- `take_with_food`: Boolean for food requirement
- `medicine_image_path`: Optional image path
- `is_taken`: Boolean for taken status
- `taken_at`: Timestamp when marked as taken
- `created_at`: Creation timestamp

## Mobile Conversion (Future)

The code is structured to be easily convertible to mobile using Kivy:

1. **Modular Design**: Database and business logic are separated from UI
2. **Model Classes**: Data models are ready for mobile adaptation
3. **Notification System**: Already uses cross-platform Plyer library
4. **Clean Architecture**: UI components can be easily replaced with Kivy widgets

### Planned Mobile Features
- Push notifications
- Swipe gestures for marking reminders
- Calendar integration
- Photo capture for medicine images
- Family sharing capabilities

## Dependencies

- **Plyer**: Cross-platform notifications
- **Pillow**: Image processing (for future image features)
- **Tkinter**: Built-in Python GUI framework
- **SQLite**: Built-in database support

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## License

This project is open source and available under the MIT License.

## Support

For issues and questions, please create an issue in the GitHub repository.

## Aditya branch

This branch introduces significant enhancements over `main`:

- Weekday-specific scheduling: choose Mon–Sun per reminder; UI shows only on selected days
- Flexible times: accepts 12/24‑hour formats (e.g., 12:39 am) with minute precision
- IST time zone: all checks and saved taken timestamps use IST (UTC+5:30)
- Daily confirmation dialog when a reminder fires; mark as Taken or Missed
- Persistent intake history: new `intake_logs` table storing taken/missed with timestamps
- Clickable weekday header buttons to navigate week days quickly
- Add Reminder dialog improvements: removed time‑of‑day radios, larger window
- Family management dialog: add and remove members; self user renamed to "Aditya"
- History view: filter by user/date range; delete selected entries or clear filtered set
- Navigation: History button placed beside top tabs; Medicines restored in bottom bar

Notes:
- Daily taken flags reset at IST midnight for active reminders, but history remains saved.
- Existing reminders without weekday selection behave as "all days" for backward compatibility.