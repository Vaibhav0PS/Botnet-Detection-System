# 📤 PCAP Upload Feature Guide

## Overview

The dashboard now includes a **PCAP file upload feature** that allows you to upload and analyze PCAP files directly from the web interface!

## Features Added

### 🎯 **Upload Panel** (Top of Dashboard)

Three action buttons:

1. **📤 Upload PCAP** - Upload .pcap or .pcapng files
2. **🔄 Sync Database** - Manually sync Kafka data to database
3. **🗑️ Clear Data** - Clear all data from database

### 🔧 **Backend API Endpoints**

- `POST /api/upload-pcap` - Upload and process PCAP files
- `POST /api/sync-database` - Trigger database sync
- `DELETE /api/clear-data` - Clear all data

## How to Use

### Step 1: Access the Dashboard

Open your browser to: **http://localhost:5173/**

You'll see the new upload panel at the top, below the header.

### Step 2: Upload a PCAP File

1. Click the **"Upload PCAP"** button
2. Select a `.pcap` or `.pcapng` file from your computer
3. Wait for the upload and processing (shows "Uploading...")
4. You'll see a success message when complete

### Step 3: Sync Database (Automatic)

- The system automatically syncs the database 2 seconds after upload
- Or click **"Sync Database"** manually to refresh data
- The spinning icon indicates syncing in progress

### Step 4: View Results

- Statistics cards update automatically
- Flow stream shows new flows
- Alerts panel displays any botnet detections
- Charts update with new data

### Step 5: Clear Data (Optional)

- Click **"Clear Data"** to remove all data
- Confirms before clearing
- Useful for starting fresh with a new PCAP

## Workflow

```
User uploads PCAP
    ↓
Backend saves to uploads/ folder
    ↓
Producer replays PCAP → Kafka
    ↓
Consumer processes → Predictions
    ↓
Auto-sync to database (2 seconds)
    ↓
Dashboard updates automatically
```

## File Requirements

✅ **Accepted formats**: `.pcap`, `.pcapng`  
✅ **Max processing time**: 5 minutes  
✅ **Storage location**: `uploads/` directory  

## Example Files to Try

The project includes sample PCAP files:

1. **`Sample_Testing/Botnet.pcap`** - Mixed traffic (benign + botnet)
2. **`Sample_Testing/zeus1-117.10.28.pcap`** - Zeus botnet (high threat)
3. **`Sample_Testing/torrent_00018_20180321111851.pcap`** - Benign P2P traffic

## API Usage (For Developers)

### Upload PCAP

```bash
curl -X POST http://localhost:8000/api/upload-pcap \
  -F "file=@Sample_Testing/Botnet.pcap"
```

Response:
```json
{
  "success": true,
  "message": "Published 112 flow feature events to flow_features",
  "filename": "Botnet.pcap",
  "file_path": "uploads/Botnet.pcap"
}
```

### Sync Database

```bash
curl -X POST http://localhost:8000/api/sync-database
```

### Clear Data

```bash
curl -X DELETE http://localhost:8000/api/clear-data
```

## Troubleshooting

### Upload Fails

**Problem**: "Only .pcap and .pcapng files are allowed"  
**Solution**: Ensure file has correct extension

**Problem**: "Producer failed"  
**Solution**: Check if consumer is running: `python -m consumer.detection_consumer`

**Problem**: "PCAP processing timed out"  
**Solution**: File is too large (>5 min processing). Try a smaller file.

### No Data Showing

**Problem**: Upload succeeds but no data in dashboard  
**Solution**: Click "Sync Database" button manually

**Problem**: Sync fails with Windows error  
**Solution**: Use the `quick_sync.py` script instead:
```bash
python quick_sync.py
```

### Database Locked

**Problem**: "Database is locked" error  
**Solution**: Stop the backend, delete `backend/botnet_stream.db`, restart

## Technical Details

### Upload Process

1. File uploaded via multipart/form-data
2. Saved to `uploads/` directory
3. Producer subprocess spawned
4. Waits for completion (max 5 minutes)
5. Returns flow count

### Security Considerations

- Only `.pcap` and `.pcapng` extensions allowed
- Files stored in isolated `uploads/` directory
- Subprocess timeout prevents hanging
- File size limited by server configuration

### Performance

- Small files (<1MB): ~5-10 seconds
- Medium files (1-10MB): ~30-60 seconds
- Large files (>10MB): 1-5 minutes

## UI Components

### Upload Button
- **Color**: White background, gray border
- **Hover**: Light gray background, lifted shadow
- **Disabled**: 50% opacity when uploading

### Sync Button
- **Color**: Light blue background
- **Icon**: Spinning when active
- **Auto-trigger**: 2 seconds after upload

### Clear Button
- **Color**: Light red background
- **Confirmation**: Asks before clearing
- **Effect**: Immediate data removal

### Messages
- **Success**: Green background, dark green text
- **Error**: Red background, dark red text
- **Auto-hide**: Stays visible until next action

## Future Enhancements

Possible improvements:

- ✨ Drag-and-drop file upload
- ✨ Upload progress bar
- ✨ Multiple file upload
- ✨ File size validation
- ✨ Upload history
- ✨ Download results as CSV
- ✨ Real-time processing status
- ✨ WebSocket for live updates

## Integration with Existing Features

The upload feature works seamlessly with:

✅ **Live polling** - Dashboard updates every 2 seconds  
✅ **Statistics cards** - Auto-update with new data  
✅ **Flow stream** - Shows uploaded PCAP flows  
✅ **Alerts** - Displays botnet detections  
✅ **Charts** - Updates with new metrics  
✅ **Host monitoring** - Tracks IPs from uploaded file  

## Summary

The PCAP upload feature makes the dashboard **fully self-contained** - users can now:

1. ✅ Upload their own PCAP files
2. ✅ See real-time analysis
3. ✅ View botnet detections
4. ✅ Clear and restart
5. ✅ All from the web interface!

**No command-line needed!** 🎉
